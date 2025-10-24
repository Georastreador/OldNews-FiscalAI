"""
FiscalAI MVP - Detector de Fracionamento
Detecta tentativas de fracionamento de operações para burlar limites fiscais
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..models.schemas import NFe, DeteccaoFraude, TipoFraude, NivelRisco


class DetectorFracionamento:
    """
    Detector de Fracionamento de Operações
    
    Detecta tentativas de dividir uma operação em múltiplas NF-e
    para burlar limites fiscais ou reduzir alíquotas
    """
    
    def __init__(self):
        self.nome = "Detector de Fracionamento"
        self.descricao = "Detecta tentativas de fracionamento de operações"
        
        # Thresholds configuráveis
        self.limite_valor_fracionamento = 10000.0  # R$ 10.000
        self.tempo_maximo_fracionamento = 24  # horas
        self.percentual_similaridade = 0.8  # 80%
    
    def detectar(self, nfe: NFe, historico_nfes: List[NFe] = None) -> List[DeteccaoFraude]:
        """
        Detecta possíveis fracionamentos
        
        Args:
            nfe: NF-e atual para análise
            historico_nfes: Histórico de NF-e do mesmo fornecedor/cliente
            
        Returns:
            Lista de fraudes detectadas
        """
        fraudes = []
        
        if not historico_nfes:
            historico_nfes = []
        
        # 1. Detectar fracionamento por valor
        fraude_valor = self._detectar_fracionamento_valor(nfe, historico_nfes)
        if fraude_valor:
            fraudes.append(fraude_valor)
        
        # 2. Detectar fracionamento temporal
        fraude_temporal = self._detectar_fracionamento_temporal(nfe, historico_nfes)
        if fraude_temporal:
            fraudes.append(fraude_temporal)
        
        # 3. Detectar fracionamento por produtos similares
        fraude_produtos = self._detectar_fracionamento_produtos(nfe, historico_nfes)
        if fraude_produtos:
            fraudes.append(fraude_produtos)
        
        # 4. Detectar fracionamento por CFOP
        fraude_cfop = self._detectar_fracionamento_cfop(nfe, historico_nfes)
        if fraude_cfop:
            fraudes.append(fraude_cfop)
        
        return fraudes
    
    def _detectar_fracionamento_valor(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta fracionamento baseado em valores"""
        
        # Filtrar NF-e do mesmo fornecedor/cliente em período recente
        nfes_recentes = self._filtrar_nfes_recentes(nfe, historico, horas=24)
        
        if len(nfes_recentes) < 2:
            return None
        
        # Calcular valor total das NF-e recentes
        valor_total_recente = sum(nf.valor_total for nf in nfes_recentes)
        
        # Verificar se o valor total excede limite
        if valor_total_recente > self.limite_valor_fracionamento:
            # Calcular score baseado no valor e número de NF-e
            score = min(100, (valor_total_recente / self.limite_valor_fracionamento) * 50)
            score += min(50, len(nfes_recentes) * 10)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FRACIONAMENTO,
                score=int(score),
                descricao=f"Possível fracionamento de operação: {len(nfes_recentes)} NF-e "
                         f"totalizando R$ {valor_total_recente:,.2f} em 24h",
                evidencias=f"Valor total: R$ {valor_total_recente:,.2f}, "
                          f"Limite: R$ {self.limite_valor_fracionamento:,.2f}, "
                          f"NF-e: {len(nfes_recentes)}",
                item_id=None
            )
        
        return None
    
    def _detectar_fracionamento_temporal(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta fracionamento baseado em tempo"""
        
        # Filtrar NF-e do mesmo fornecedor/cliente em período muito curto
        nfes_curto_periodo = self._filtrar_nfes_recentes(nfe, historico, horas=2)
        
        if len(nfes_curto_periodo) < 3:
            return None
        
        # Verificar se há muitas NF-e em período muito curto
        if len(nfes_curto_periodo) >= 3:
            valor_total = sum(nf.valor_total for nf in nfes_curto_periodo)
            
            score = min(100, len(nfes_curto_periodo) * 20)
            if valor_total > self.limite_valor_fracionamento:
                score += 30
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FRACIONAMENTO,
                score=int(score),
                descricao=f"Possível fracionamento temporal: {len(nfes_curto_periodo)} NF-e "
                         f"em menos de 2 horas",
                evidencias=f"NF-e em 2h: {len(nfes_curto_periodo)}, "
                          f"Valor total: R$ {valor_total:,.2f}",
                item_id=None
            )
        
        return None
    
    def _detectar_fracionamento_produtos(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta fracionamento baseado em produtos similares"""
        
        nfes_recentes = self._filtrar_nfes_recentes(nfe, historico, horas=24)
        
        if len(nfes_recentes) < 2:
            return None
        
        # Extrair produtos de todas as NF-e
        todos_produtos = []
        for nf in nfes_recentes:
            for item in nf.itens:
                todos_produtos.append({
                    'nfe_id': nf.numero,
                    'descricao': item.descricao,
                    'ncm': item.ncm,
                    'valor': item.valor_total
                })
        
        # Agrupar produtos similares
        produtos_similares = self._agrupar_produtos_similares(todos_produtos)
        
        # Verificar se há agrupamentos suspeitos
        for grupo in produtos_similares:
            if len(grupo) >= 2:
                nfes_diferentes = set(p['nfe_id'] for p in grupo)
                if len(nfes_diferentes) >= 2:
                    valor_grupo = sum(p['valor'] for p in grupo)
                    
                    if valor_grupo > self.limite_valor_fracionamento * 0.5:
                        score = min(100, len(grupo) * 15 + (valor_grupo / 1000))
                        
                        return DeteccaoFraude(
                            tipo_fraude=TipoFraude.FRACIONAMENTO,
                            score=int(score),
                            descricao=f"Possível fracionamento de produtos: {len(grupo)} produtos "
                                     f"similares em {len(nfes_diferentes)} NF-e diferentes",
                            evidencias=f"Produtos similares: {len(grupo)}, "
                                      f"NF-e diferentes: {len(nfes_diferentes)}, "
                                      f"Valor grupo: R$ {valor_grupo:,.2f}",
                            item_id=None
                        )
        
        return None
    
    def _detectar_fracionamento_cfop(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta fracionamento baseado em CFOPs"""
        
        nfes_recentes = self._filtrar_nfes_recentes(nfe, historico, horas=24)
        
        if len(nfes_recentes) < 2:
            return None
        
        # Extrair CFOPs de todas as NF-e
        cfops_por_nfe = {}
        for nf in nfes_recentes:
            cfops = [item.cfop for item in nf.itens]
            cfops_por_nfe[nf.numero] = cfops
        
        # Verificar padrões suspeitos de CFOP
        cfops_suspeitos = self._analisar_cfops_suspeitos(cfops_por_nfe)
        
        if cfops_suspeitos:
            score = min(100, len(cfops_suspeitos) * 25)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FRACIONAMENTO,
                score=int(score),
                descricao=f"Possível fracionamento por CFOP: padrão suspeito detectado",
                evidencias=f"CFOPs suspeitos: {', '.join(cfops_suspeitos)}",
                item_id=None
            )
        
        return None
    
    def _filtrar_nfes_recentes(self, nfe: NFe, historico: List[NFe], horas: int) -> List[NFe]:
        """Filtra NF-e recentes do mesmo fornecedor/cliente"""
        
        limite_tempo = nfe.data_emissao - timedelta(hours=horas)
        
        nfes_recentes = []
        for nf in historico:
            # Mesmo fornecedor ou destinatário
            mesmo_fornecedor = nf.cnpj_emitente == nfe.cnpj_emitente
            mesmo_destinatario = nf.cnpj_destinatario == nfe.cnpj_destinatario
            
            # Dentro do período
            dentro_periodo = nf.data_emissao >= limite_tempo
            
            if (mesmo_fornecedor or mesmo_destinatario) and dentro_periodo:
                nfes_recentes.append(nf)
        
        return nfes_recentes
    
    def _agrupar_produtos_similares(self, produtos: List[Dict]) -> List[List[Dict]]:
        """Agrupa produtos similares baseado em descrição e NCM"""
        
        grupos = []
        produtos_processados = set()
        
        for i, produto in enumerate(produtos):
            if i in produtos_processados:
                continue
            
            grupo = [produto]
            produtos_processados.add(i)
            
            for j, outro_produto in enumerate(produtos[i+1:], i+1):
                if j in produtos_processados:
                    continue
                
                # Verificar similaridade
                similar = self._produtos_similares(produto, outro_produto)
                if similar:
                    grupo.append(outro_produto)
                    produtos_processados.add(j)
            
            if len(grupo) > 1:
                grupos.append(grupo)
        
        return grupos
    
    def _produtos_similares(self, produto1: Dict, produto2: Dict) -> bool:
        """Verifica se dois produtos são similares"""
        
        # Mesmo NCM
        if produto1['ncm'] == produto2['ncm']:
            return True
        
        # Descrições similares (simplificado)
        desc1 = produto1['descricao'].lower()
        desc2 = produto2['descricao'].lower()
        
        # Palavras em comum
        palavras1 = set(desc1.split())
        palavras2 = set(desc2.split())
        
        if len(palavras1) == 0 or len(palavras2) == 0:
            return False
        
        similaridade = len(palavras1.intersection(palavras2)) / len(palavras1.union(palavras2))
        
        return similaridade >= self.percentual_similaridade
    
    def _analisar_cfops_suspeitos(self, cfops_por_nfe: Dict[str, List[str]]) -> List[str]:
        """Analisa CFOPs para detectar padrões suspeitos"""
        
        cfops_suspeitos = []
        
        # CFOPs que indicam fracionamento
        cfops_fracionamento = [
            "1102",  # Venda de mercadoria para comercialização
            "1202",  # Devolução de venda de mercadoria para comercialização
            "2102",  # Compra de mercadoria para comercialização
            "2202",  # Devolução de compra de mercadoria para comercialização
        ]
        
        # Verificar se há uso excessivo de CFOPs de fracionamento
        for nfe_id, cfops in cfops_por_nfe.items():
            cfops_fracionamento_count = sum(1 for cfop in cfops if cfop in cfops_fracionamento)
            
            if cfops_fracionamento_count > len(cfops) * 0.7:  # Mais de 70% dos CFOPs
                cfops_suspeitos.extend(cfops_fracionamento_count)
        
        return list(set(cfops_suspeitos))
