"""
FiscalAI MVP - Detector de Triangulação Fiscal
Detecta padrões de triangulação entre empresas relacionadas
Usa análise de grafos para identificar ciclos e padrões suspeitos
"""

import pandas as pd
import networkx as nx
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from ..models import NFe, DeteccaoFraude, TipoFraude


class DetectorTriangulacao:
    """
    Detecta triangulação fiscal entre empresas relacionadas
    
    Padrões detectados:
    1. Ciclos de transações (A -> B -> C -> A)
    2. Ping-pong (A <-> B repetidamente)
    3. Produtos que retornam à origem com valor inflacionado
    4. Alta concentração de transações entre mesmas partes
    5. Relacionamento societário conhecido
    """
    
    def __init__(self,
                 historico: Optional[pd.DataFrame] = None,
                 base_relacionamentos: Optional[pd.DataFrame] = None):
        """
        Inicializa o detector
        
        Args:
            historico: DataFrame com histórico completo de NF-e
                Colunas esperadas: chave_acesso, cnpj_emitente, cnpj_destinatario,
                                  data_emissao, valor_total, ncms (string separada por vírgula)
            base_relacionamentos: DataFrame com CNPJs relacionados
                Colunas: cnpj_1, cnpj_2, tipo_relacionamento
        """
        self.historico = historico if historico is not None else pd.DataFrame()
        self.base_relacionamentos = base_relacionamentos if base_relacionamentos is not None else pd.DataFrame()
        
        # Construir grafo de transações
        self.grafo_transacoes = self._construir_grafo_transacoes()
        
        # Thresholds
        self.threshold_concentracao = 0.7  # 70% das transações com mesmo parceiro
        self.threshold_valorizacao = 50  # 50% de valorização em curto período
        self.threshold_score_minimo = 40
        self.janela_ping_pong_dias = 30
        self.janela_retorno_dias = 180
    
    def detectar(self, nfe: NFe) -> Optional[DeteccaoFraude]:
        """
        Detecta triangulação fiscal
        
        Args:
            nfe: NF-e a ser analisada
        
        Returns:
            DeteccaoFraude se houver suspeita, None caso contrário
        """
        cnpj_origem = nfe.cnpj_emitente
        cnpj_destino = nfe.cnpj_destinatario
        
        evidencias = []
        score = 0
        dados_adicionais = {}
        
        # 1. Verificar relacionamento conhecido
        if self._cnpjs_relacionados(cnpj_origem, cnpj_destino):
            score += 25
            tipo_rel = self._get_tipo_relacionamento(cnpj_origem, cnpj_destino)
            evidencias.append(
                f"Empresas possuem relacionamento conhecido: {tipo_rel}"
            )
            dados_adicionais['relacionamento'] = tipo_rel
        
        # 2. Detectar ciclos de transações
        ciclos = self._detectar_ciclos(cnpj_origem, cnpj_destino, max_profundidade=4)
        if ciclos:
            score += 40
            ciclo_str = ' → '.join(ciclos[0])
            evidencias.append(
                f"Detectado ciclo de transações: {ciclo_str}"
            )
            dados_adicionais['ciclos'] = ciclos
        
        # 3. Verificar padrão ping-pong
        if self._detectar_ping_pong(cnpj_origem, cnpj_destino, self.janela_ping_pong_dias):
            score += 30
            evidencias.append(
                f"Padrão de transações recíprocas frequentes (ping-pong) "
                f"nos últimos {self.janela_ping_pong_dias} dias"
            )
        
        # 4. Verificar retorno de produto com valorização
        retorno = self._verificar_retorno_produto(nfe)
        if retorno:
            score += 35
            evidencias.append(
                f"Produto retornou à origem com valorização de "
                f"{retorno['valorizacao']:.1f}% em {retorno['dias']} dias "
                f"(de R$ {retorno['valor_anterior']:.2f} para R$ {retorno['valor_atual']:.2f})"
            )
            dados_adicionais['retorno_produto'] = retorno
        
        # 5. Verificar concentração de transações
        concentracao = self._calcular_concentracao_transacoes(cnpj_origem, cnpj_destino)
        if concentracao > self.threshold_concentracao:
            score += 20
            evidencias.append(
                f"Alta concentração de transações entre as partes "
                f"({concentracao:.0%} das transações do emitente)"
            )
            dados_adicionais['concentracao'] = concentracao
        
        # 6. Verificar valor total alto (aumenta gravidade)
        if nfe.valor_total > 50000:  # Mais de R$ 50.000
            score += 10
            evidencias.append(
                f"Alto valor envolvido na transação: R$ {nfe.valor_total:,.2f}"
            )
        
        # Determinar se é fraude
        score = min(score, 100)
        
        if score >= self.threshold_score_minimo:
            justificativa = self._gerar_justificativa(
                nfe, cnpj_origem, cnpj_destino, ciclos, evidencias
            )
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.TRIANGULACAO,
                score=score,
                confianca=0.75,  # Confiança moderada (análise de padrões)
                evidencias=evidencias,
                justificativa=justificativa,
                metodo_deteccao="rule",
                dados_adicionais=dados_adicionais
            )
        
        return None
    
    def _construir_grafo_transacoes(self) -> nx.DiGraph:
        """Constrói grafo direcionado de transações entre CNPJs"""
        G = nx.DiGraph()
        
        if self.historico.empty:
            return G
        
        for _, row in self.historico.iterrows():
            origem = row['cnpj_emitente']
            destino = row['cnpj_destinatario']
            valor = row.get('valor_total', 0)
            data = row.get('data_emissao')
            chave = row.get('chave_acesso', '')
            
            if G.has_edge(origem, destino):
                # Atualizar edge existente
                G[origem][destino]['transacoes'].append({
                    'valor': valor,
                    'data': data,
                    'chave': chave
                })
                G[origem][destino]['valor_total'] += valor
                G[origem][destino]['count'] += 1
            else:
                # Criar novo edge
                G.add_edge(
                    origem, destino,
                    transacoes=[{'valor': valor, 'data': data, 'chave': chave}],
                    valor_total=valor,
                    count=1
                )
        
        return G
    
    def _cnpjs_relacionados(self, cnpj1: str, cnpj2: str) -> bool:
        """Verifica se dois CNPJs têm relacionamento conhecido"""
        if self.base_relacionamentos.empty:
            return False
        
        relacionados = self.base_relacionamentos[
            ((self.base_relacionamentos['cnpj_1'] == cnpj1) &
             (self.base_relacionamentos['cnpj_2'] == cnpj2)) |
            ((self.base_relacionamentos['cnpj_1'] == cnpj2) &
             (self.base_relacionamentos['cnpj_2'] == cnpj1))
        ]
        
        return len(relacionados) > 0
    
    def _get_tipo_relacionamento(self, cnpj1: str, cnpj2: str) -> str:
        """Retorna tipo de relacionamento entre CNPJs"""
        if self.base_relacionamentos.empty:
            return "desconhecido"
        
        rel = self.base_relacionamentos[
            ((self.base_relacionamentos['cnpj_1'] == cnpj1) &
             (self.base_relacionamentos['cnpj_2'] == cnpj2)) |
            ((self.base_relacionamentos['cnpj_1'] == cnpj2) &
             (self.base_relacionamentos['cnpj_2'] == cnpj1))
        ]
        
        if len(rel) > 0:
            return rel.iloc[0].get('tipo_relacionamento', 'relacionadas')
        return "desconhecido"
    
    def _detectar_ciclos(self,
                        origem: str,
                        destino: str,
                        max_profundidade: int = 4) -> List[List[str]]:
        """
        Detecta ciclos de transações partindo de origem
        
        Args:
            origem: CNPJ de origem
            destino: CNPJ de destino
            max_profundidade: Profundidade máxima do ciclo
        
        Returns:
            Lista de ciclos encontrados (cada ciclo é uma lista de CNPJs)
        """
        if not self.grafo_transacoes.has_node(origem) or not self.grafo_transacoes.has_node(destino):
            return []
        
        try:
            # Buscar caminhos de destino de volta para origem
            caminhos = list(nx.all_simple_paths(
                self.grafo_transacoes,
                source=destino,
                target=origem,
                cutoff=max_profundidade
            ))
            
            # Construir ciclos completos
            ciclos = [[origem] + caminho for caminho in caminhos]
            return ciclos[:3]  # Retornar no máximo 3 ciclos
            
        except nx.NetworkXNoPath:
            return []
        except Exception:
            return []
    
    def _detectar_ping_pong(self,
                           cnpj1: str,
                           cnpj2: str,
                           janela_dias: int) -> bool:
        """
        Detecta padrão de transações recíprocas frequentes
        
        Args:
            cnpj1: Primeiro CNPJ
            cnpj2: Segundo CNPJ
            janela_dias: Janela de tempo em dias
        
        Returns:
            True se detectar ping-pong, False caso contrário
        """
        if self.historico.empty:
            return False
        
        # Buscar transações nos dois sentidos
        trans_1_2 = self.historico[
            (self.historico['cnpj_emitente'] == cnpj1) &
            (self.historico['cnpj_destinatario'] == cnpj2)
        ]
        
        trans_2_1 = self.historico[
            (self.historico['cnpj_emitente'] == cnpj2) &
            (self.historico['cnpj_destinatario'] == cnpj1)
        ]
        
        # Verificar se há pelo menos 3 pares
        if len(trans_1_2) < 3 or len(trans_2_1) < 3:
            return False
        
        # Verificar proximidade temporal
        pares_encontrados = 0
        for _, t1 in trans_1_2.iterrows():
            data_1 = pd.to_datetime(t1['data_emissao'])
            
            # Buscar transação reversa próxima
            trans_proximas = trans_2_1[
                (pd.to_datetime(trans_2_1['data_emissao']) >= data_1) &
                (pd.to_datetime(trans_2_1['data_emissao']) <= data_1 + timedelta(days=janela_dias))
            ]
            
            if len(trans_proximas) > 0:
                pares_encontrados += 1
        
        return pares_encontrados >= 3
    
    def _verificar_retorno_produto(self, nfe: NFe) -> Optional[Dict[str, Any]]:
        """
        Verifica se produtos desta NF-e retornaram à origem anteriormente
        
        Args:
            nfe: NF-e atual
        
        Returns:
            Dict com informações do retorno ou None
        """
        if self.historico.empty:
            return None
        
        cnpj_origem = nfe.cnpj_emitente
        cnpj_destino = nfe.cnpj_destinatario
        
        # Buscar NF-e anteriores onde origem e destino estão invertidos
        nfes_anteriores = self.historico[
            (self.historico['cnpj_emitente'] == cnpj_destino) &
            (self.historico['cnpj_destinatario'] == cnpj_origem) &
            (pd.to_datetime(self.historico['data_emissao']) < nfe.data_emissao) &
            (pd.to_datetime(self.historico['data_emissao']) >= 
             nfe.data_emissao - timedelta(days=self.janela_retorno_dias))
        ]
        
        if nfes_anteriores.empty:
            return None
        
        # Comparar produtos (NCM)
        ncms_atual = set([item.ncm_declarado for item in nfe.itens])
        
        for _, nfe_anterior in nfes_anteriores.iterrows():
            # Assumindo que NCMs estão separados por vírgula no histórico
            ncms_anterior_str = nfe_anterior.get('ncms', '')
            if not ncms_anterior_str:
                continue
            
            ncms_anterior = set(ncms_anterior_str.split(','))
            
            # Verificar se há NCMs em comum
            if ncms_atual.intersection(ncms_anterior):
                # Mesmo produto retornou
                dias_decorridos = (nfe.data_emissao - pd.to_datetime(nfe_anterior['data_emissao'])).days
                valor_anterior = nfe_anterior['valor_total']
                valor_atual = nfe.valor_total
                
                if valor_anterior > 0:
                    valorizacao = ((valor_atual - valor_anterior) / valor_anterior) * 100
                    
                    if valorizacao > self.threshold_valorizacao:
                        return {
                            'dias': dias_decorridos,
                            'valor_anterior': valor_anterior,
                            'valor_atual': valor_atual,
                            'valorizacao': valorizacao,
                            'chave_anterior': nfe_anterior.get('chave_acesso', '')
                        }
        
        return None
    
    def _calcular_concentracao_transacoes(self, cnpj1: str, cnpj2: str) -> float:
        """
        Calcula % de transações de cnpj1 que são com cnpj2
        
        Args:
            cnpj1: CNPJ do emitente
            cnpj2: CNPJ do destinatário
        
        Returns:
            Percentual de concentração (0-1)
        """
        if self.historico.empty:
            return 0.0
        
        total_transacoes_cnpj1 = len(self.historico[
            self.historico['cnpj_emitente'] == cnpj1
        ])
        
        if total_transacoes_cnpj1 == 0:
            return 0.0
        
        transacoes_com_cnpj2 = len(self.historico[
            (self.historico['cnpj_emitente'] == cnpj1) &
            (self.historico['cnpj_destinatario'] == cnpj2)
        ])
        
        return transacoes_com_cnpj2 / total_transacoes_cnpj1
    
    def _gerar_justificativa(self,
                            nfe: NFe,
                            cnpj_origem: str,
                            cnpj_destino: str,
                            ciclos: List[List[str]],
                            evidencias: List[str]) -> str:
        """Gera justificativa da detecção"""
        just = (
            f"Detectado padrão suspeito de triangulação fiscal envolvendo "
            f"CNPJ emitente {cnpj_origem} e destinatário {cnpj_destino}. "
        )
        
        if ciclos:
            just += (
                f"Identificado ciclo de transações: {' → '.join(ciclos[0])}. "
            )
        
        just += (
            f"Este padrão pode indicar movimentação artificial de mercadorias "
            f"para fins de planejamento tributário abusivo, lavagem de dinheiro "
            f"ou simulação de operações comerciais. "
        )
        
        if len(evidencias) >= 3:
            just += (
                f"Foram identificadas {len(evidencias)} evidências de triangulação, "
                f"incluindo relacionamento entre as partes e padrões temporais suspeitos."
            )
        
        return just
    
    def get_estatisticas_grafo(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do grafo de transações
        
        Returns:
            Dict com estatísticas
        """
        if not self.grafo_transacoes:
            return {}
        
        return {
            'num_empresas': self.grafo_transacoes.number_of_nodes(),
            'num_transacoes': self.grafo_transacoes.number_of_edges(),
            'densidade': nx.density(self.grafo_transacoes),
            'componentes_conectados': nx.number_weakly_connected_components(self.grafo_transacoes),
        }

