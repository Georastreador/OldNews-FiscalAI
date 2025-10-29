"""
FiscalAI MVP - Detector de Anomalia Temporal
Detecta anomalias temporais em emissão de NF-e
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, time
from ..models.schemas import NFe, DeteccaoFraude, TipoFraude, NivelRisco


class DetectorAnomaliaTemporal:
    """
    Detector de Anomalia Temporal
    
    Detecta padrões temporais suspeitos na emissão de NF-e
    """
    
    def __init__(self):
        self.nome = "Detector de Anomalia Temporal"
        self.descricao = "Detecta anomalias temporais em emissão de NF-e"
        
        # Thresholds configuráveis
        self.horario_suspeito_inicio = time(22, 0)  # 22:00
        self.horario_suspeito_fim = time(6, 0)      # 06:00
        self.limite_emissao_fim_semana = 5  # NF-e em fim de semana
        self.limite_emissao_feriado = 3     # NF-e em feriados
    
    def detectar(self, nfe: NFe, historico_nfes: List[NFe] = None) -> List[DeteccaoFraude]:
        """
        Detecta anomalias temporais
        
        Args:
            nfe: NF-e atual para análise
            historico_nfes: Histórico de NF-e do fornecedor
            
        Returns:
            Lista de fraudes detectadas
        """
        fraudes = []
        
        if not historico_nfes:
            historico_nfes = []
        
        # 1. Detectar emissão em horário suspeito
        fraude_horario = self._detectar_horario_suspeito(nfe)
        if fraude_horario:
            fraudes.append(fraude_horario)
        
        # 2. Detectar emissão em fim de semana
        fraude_fim_semana = self._detectar_fim_semana(nfe, historico_nfes)
        if fraude_fim_semana:
            fraudes.append(fraude_fim_semana)
        
        # 3. Detectar emissão em feriados
        fraude_feriado = self._detectar_feriado(nfe, historico_nfes)
        if fraude_feriado:
            fraudes.append(fraude_feriado)
        
        # 4. Detectar padrão de emissão atípico
        fraude_padrao = self._detectar_padrao_atipico(nfe, historico_nfes)
        if fraude_padrao:
            fraudes.append(fraude_padrao)
        
        return fraudes
    
    def _detectar_horario_suspeito(self, nfe: NFe) -> Optional[DeteccaoFraude]:
        """Detecta emissão em horário suspeito"""
        
        horario_emissao = nfe.data_emissao.time()
        
        # Verificar se está no horário suspeito (madrugada/noite)
        if (horario_emissao >= self.horario_suspeito_inicio or 
            horario_emissao <= self.horario_suspeito_fim):
            
            score = 30  # Score base para horário suspeito
            
            # Ajustar score baseado na hora
            if horario_emissao >= time(0, 0) and horario_emissao <= time(4, 0):
                score = 50  # Madrugada é mais suspeito
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.ANOMALIA_TEMPORAL,
                score=score,
                descricao=f"Emissão em horário suspeito: {horario_emissao.strftime('%H:%M')}",
                evidencias=f"Horário: {horario_emissao.strftime('%H:%M')}, "
                          f"Período suspeito: {self.horario_suspeito_inicio} - {self.horario_suspeito_fim}",
                item_id=None
            )
        
        return None
    
    def _detectar_fim_semana(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta emissão excessiva em fins de semana"""
        
        # Verificar se é fim de semana
        if nfe.data_emissao.weekday() < 5:  # Segunda a sexta
            return None
        
        # Contar NF-e em fins de semana do fornecedor
        nfes_fim_semana = self._contar_nfes_fim_semana(nfe, historico)
        
        if nfes_fim_semana >= self.limite_emissao_fim_semana:
            score = min(100, nfes_fim_semana * 15)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.ANOMALIA_TEMPORAL,
                score=int(score),
                descricao=f"Emissão excessiva em fins de semana: {nfes_fim_semana} NF-e",
                evidencias=f"NF-e em fins de semana: {nfes_fim_semana}, "
                          f"Limite: {self.limite_emissao_fim_semana}",
                item_id=None
            )
        
        return None
    
    def _detectar_feriado(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta emissão em feriados"""
        
        # Verificar se é feriado (lista simplificada)
        if not self._eh_feriado(nfe.data_emissao):
            return None
        
        # Contar NF-e em feriados do fornecedor
        nfes_feriado = self._contar_nfes_feriado(nfe, historico)
        
        if nfes_feriado >= self.limite_emissao_feriado:
            score = min(100, nfes_feriado * 20)
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.ANOMALIA_TEMPORAL,
                score=int(score),
                descricao=f"Emissão em feriado: {nfes_feriado} NF-e",
                evidencias=f"NF-e em feriados: {nfes_feriado}, "
                          f"Limite: {self.limite_emissao_feriado}",
                item_id=None
            )
        
        return None
    
    def _detectar_padrao_atipico(self, nfe: NFe, historico: List[NFe]) -> Optional[DeteccaoFraude]:
        """Detecta padrões de emissão atípicos"""
        
        # Filtrar NF-e do fornecedor nos últimos 30 dias
        nfes_recentes = self._filtrar_nfes_recentes(nfe, historico, dias=30)
        
        if len(nfes_recentes) < 5:
            return None
        
        # Analisar padrão de dias da semana
        dias_semana = [nf.data_emissao.weekday() for nf in nfes_recentes]
        contagem_dias = {}
        
        for dia in dias_semana:
            contagem_dias[dia] = contagem_dias.get(dia, 0) + 1
        
        # Verificar se há concentração em dias específicos
        max_emissao_dia = max(contagem_dias.values())
        total_emissao = len(nfes_recentes)
        
        concentracao_dia = max_emissao_dia / total_emissao
        
        if concentracao_dia > 0.7:  # Mais de 70% em um dia
            score = min(100, concentracao_dia * 100)
            
            dia_max = max(contagem_dias, key=contagem_dias.get)
            nome_dia = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][dia_max]
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.ANOMALIA_TEMPORAL,
                score=int(score),
                descricao=f"Concentração excessiva em {nome_dia}: {concentracao_dia:.1%} das emissões",
                evidencias=f"Concentração: {concentracao_dia:.1%}, "
                          f"Dia: {nome_dia}, "
                          f"Total NF-e: {total_emissao}",
                item_id=None
            )
        
        return None
    
    def _contar_nfes_fim_semana(self, nfe: NFe, historico: List[NFe]) -> int:
        """Conta NF-e emitidas em fins de semana pelo fornecedor"""
        
        count = 0
        for nf in historico:
            if (nf.cnpj_emitente == nfe.cnpj_emitente and 
                nf.data_emissao.weekday() >= 5):  # Sábado ou domingo
                count += 1
        
        return count
    
    def _contar_nfes_feriado(self, nfe: NFe, historico: List[NFe]) -> int:
        """Conta NF-e emitidas em feriados pelo fornecedor"""
        
        count = 0
        for nf in historico:
            if (nf.cnpj_emitente == nfe.cnpj_emitente and 
                self._eh_feriado(nf.data_emissao)):
                count += 1
        
        return count
    
    def _filtrar_nfes_recentes(self, nfe: NFe, historico: List[NFe], dias: int) -> List[NFe]:
        """Filtra NF-e recentes do fornecedor"""
        
        limite_tempo = nfe.data_emissao - timedelta(days=dias)
        
        nfes_recentes = []
        for nf in historico:
            if (nf.cnpj_emitente == nfe.cnpj_emitente and 
                nf.data_emissao >= limite_tempo):
                nfes_recentes.append(nf)
        
        return nfes_recentes
    
    def _eh_feriado(self, data: datetime) -> bool:
        """Verifica se a data é feriado (lista simplificada)"""
        
        # Feriados fixos
        feriados_fixos = [
            (1, 1),   # Ano Novo
            (4, 21),  # Tiradentes
            (5, 1),   # Dia do Trabalhador
            (9, 7),   # Independência
            (10, 12), # Nossa Senhora Aparecida
            (11, 2),  # Finados
            (11, 15), # Proclamação da República
            (12, 25), # Natal
        ]
        
        # Verificar feriados fixos
        if (data.month, data.day) in feriados_fixos:
            return True
        
        # Verificar feriados móveis (simplificado)
        # Páscoa, Carnaval, etc. (implementação simplificada)
        
        return False
