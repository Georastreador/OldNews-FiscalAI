"""
FiscalAI MVP - Detector de Fornecedor de Risco
Detecta fornecedores com histórico de problemas fiscais
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..models.schemas import NFe, DeteccaoFraude, TipoFraude, NivelRisco


class DetectorFornecedorRisco:
    """
    Detector de Fornecedor de Risco
    
    Analisa histórico do fornecedor para detectar padrões suspeitos
    """
    
    def __init__(self):
        self.nome = "Detector de Fornecedor de Risco"
        self.descricao = "Detecta fornecedores com histórico de problemas fiscais"
        
        # Thresholds configuráveis
        self.limite_fraudes_historico = 3  # Número de fraudes no histórico
        self.periodo_analise_dias = 90  # Dias para análise do histórico
        self.limite_nfes_suspeitas = 5  # NF-e suspeitas no período
    
    def detectar(self, nfe: NFe, historico_nfes: List[NFe] = None) -> List[DeteccaoFraude]:
        """
        Detecta fornecedores de risco
        
        Args:
            nfe: NF-e atual para análise
            historico_nfes: Histórico de NF-e do fornecedor
            
        Returns:
            Lista de fraudes detectadas
        """
        fraudes = []
        
        if not historico_nfes:
            historico_nfes = []
        
        # 1. Analisar histórico de fraudes
        fraude_historico = self._analisar_historico_fraudes(nfe, historico_nfes)
        if fraude_historico:
            fraudes.append(fraude_historico)
        
        # 2. Analisar padrões de valores
        fraude_valores = self._analisar_padroes_valores(nfe, historico_nfes)
        if fraude_valores:
            fraudes.append(fraude_valores)
        
        # 3. Analisar frequência de emissão
        fraude_frequencia = self._analisar_frequencia_emissao(nfe, historico_nfes)
        if fraude_frequencia:
            fraudes.append(fraude_frequencia)
        
        # 4. Analisar diversidade de clientes
        fraude_diversidade = self._analisar_diversidade_clientes(nfe, historico_nfes)
        if fraude_diversidade:
            fraudes.append(fraude_diversidade)
        
        return fraudes
    
    def _analisar_historico_fraudes(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Analisa histórico de fraudes do fornecedor"""
        
        # Filtrar NF-e do fornecedor no período
        nfes_fornecedor = self._filtrar_nfes_fornecedor(nfe, historico, dias=self.periodo_analise_dias)
        
        if len(nfes_fornecedor) < 5:
            return None
        
        # Simular análise de fraudes (em produção, viria de base de dados)
        nfes_suspeitas = self._identificar_nfes_suspeitas(nfes_fornecedor)
        
        if len(nfes_suspeitas) >= self.limite_fraudes_historico:
            percentual_suspeitas = len(nfes_suspeitas) / len(nfes_fornecedor)
            score = min(100, percentual_suspeitas * 100)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FORNECEDOR_RISCO,
                score=int(score),
                descricao=f"Fornecedor com histórico de problemas: {len(nfes_suspeitas)} "
                         f"NF-e suspeitas em {len(nfes_fornecedor)} análises",
                evidencias=f"NF-e suspeitas: {len(nfes_suspeitas)}, "
                          f"Total analisadas: {len(nfes_fornecedor)}, "
                          f"Percentual: {percentual_suspeitas:.1%}",
                item_id=None
            )
        
        return None
    
    def _analisar_padroes_valores(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Analisa padrões de valores do fornecedor"""
        
        nfes_fornecedor = self._filtrar_nfes_fornecedor(nfe, historico, dias=self.periodo_analise_dias)
        
        if len(nfes_fornecedor) < 10:
            return None
        
        # Calcular estatísticas de valores
        valores = [nf.valor_total for nf in nfes_fornecedor]
        media = np.mean(valores)
        desvio_padrao = np.std(valores)
        
        # Verificar se valor atual é outlier
        z_score = abs((nfe.valor_total - media) / desvio_padrao) if desvio_padrao > 0 else 0
        
        if z_score > 3:  # Outlier significativo
            score = min(100, z_score * 20)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FORNECEDOR_RISCO,
                score=int(score),
                descricao=f"Valor atípico para o fornecedor: R$ {nfe.valor_total:,.2f} "
                         f"(média histórica: R$ {media:,.2f})",
                evidencias=f"Valor atual: R$ {nfe.valor_total:,.2f}, "
                          f"Média: R$ {media:,.2f}, "
                          f"Z-score: {z_score:.2f}",
                item_id=None
            )
        
        return None
    
    def _analisar_frequencia_emissao(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Analisa frequência de emissão de NF-e"""
        
        nfes_fornecedor = self._filtrar_nfes_fornecedor(nfe, historico, dias=30)
        
        if len(nfes_fornecedor) < 5:
            return None
        
        # Calcular frequência média
        datas = [nf.data_emissao for nf in nfes_fornecedor]
        datas.sort()
        
        intervalos = []
        for i in range(1, len(datas)):
            intervalo = (datas[i] - datas[i-1]).total_seconds() / 3600  # horas
            intervalos.append(intervalo)
        
        if not intervalos:
            return None
        
        intervalo_medio = np.mean(intervalos)
        
        # Verificar se há emissão muito frequente (possível fraude)
        if intervalo_medio < 1:  # Menos de 1 hora entre emissões
            score = min(100, (1 / intervalo_medio) * 20)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FORNECEDOR_RISCO,
                score=int(score),
                descricao=f"Emissão muito frequente: média de {intervalo_medio:.1f}h entre NF-e",
                evidencias=f"Intervalo médio: {intervalo_medio:.1f}h, "
                          f"NF-e analisadas: {len(nfes_fornecedor)}",
                item_id=None
            )
        
        return None
    
    def _analisar_diversidade_clientes(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Analisa diversidade de clientes do fornecedor"""
        
        nfes_fornecedor = self._filtrar_nfes_fornecedor(nfe, historico, dias=self.periodo_analise_dias)
        
        if len(nfes_fornecedor) < 10:
            return None
        
        # Contar clientes únicos
        clientes_unicos = set(nf.cnpj_destinatario for nf in nfes_fornecedor)
        
        # Calcular concentração de clientes
        concentracao_clientes = {}
        for nf in nfes_fornecedor:
            cnpj = nf.cnpj_destinatario
            if cnpj not in concentracao_clientes:
                concentracao_clientes[cnpj] = 0
            concentracao_clientes[cnpj] += 1
        
        # Verificar se há concentração excessiva
        max_concentracao = max(concentracao_clientes.values())
        percentual_max_concentracao = max_concentracao / len(nfes_fornecedor)
        
        if percentual_max_concentracao > 0.8:  # Mais de 80% para um cliente
            score = min(100, percentual_max_concentracao * 100)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.FORNECEDOR_RISCO,
                score=int(score),
                descricao=f"Concentração excessiva de clientes: {percentual_max_concentracao:.1%} "
                         f"das vendas para um cliente",
                evidencias=f"Concentração máxima: {percentual_max_concentracao:.1%}, "
                          f"Clientes únicos: {len(clientes_unicos)}, "
                          f"Total NF-e: {len(nfes_fornecedor)}",
                item_id=None
            )
        
        return None
    
    def _filtrar_nfes_fornecedor(self, nfe: NFe, historico: List[NFe], dias: int) -> List[NFe]:
        """Filtra NF-e do fornecedor no período especificado"""
        
        limite_tempo = nfe.data_emissao - timedelta(days=dias)
        
        nfes_fornecedor = []
        for nf in historico:
            # Mesmo fornecedor
            mesmo_fornecedor = nf.cnpj_emitente == nfe.cnpj_emitente
            
            # Dentro do período
            dentro_periodo = nf.data_emissao >= limite_tempo
            
            if mesmo_fornecedor and dentro_periodo:
                nfes_fornecedor.append(nf)
        
        return nfes_fornecedor
    
    def _identificar_nfes_suspeitas(self, nfes: List[NFe]) -> List[NFe]:
        """Identifica NF-e suspeitas no histórico (simulado)"""
        
        nfes_suspeitas = []
        
        for nf in nfes:
            # Critérios simplificados para identificar suspeitas
            suspeita = False
            
            # 1. Valores muito baixos ou muito altos
            if nf.valor_total < 100 or nf.valor_total > 1000000:
                suspeita = True
            
            # 2. Muitos itens com valores baixos
            itens_baixos = sum(1 for item in nf.itens if item.valor_total < 10)
            if itens_baixos > len(nf.itens) * 0.5:
                suspeita = True
            
            # 3. Descrições muito genéricas
            descricoes_genericas = ["PRODUTO", "MERCADORIA", "ITEM", "SERVICO"]
            for item in nf.itens:
                if any(gen in item.descricao.upper() for gen in descricoes_genericas):
                    suspeita = True
                    break
            
            if suspeita:
                nfes_suspeitas.append(nf)
        
        return nfes_suspeitas
