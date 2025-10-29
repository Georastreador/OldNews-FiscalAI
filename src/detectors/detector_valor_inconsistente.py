"""
FiscalAI MVP - Detector de Valor Inconsistente
Detecta inconsistências em valores e cálculos fiscais
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from ..models.schemas import NFe, DeteccaoFraude, TipoFraude, NivelRisco, ItemNFe

# Configuração de debug com proteção para produção
PRODUCTION_MODE = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true' and not PRODUCTION_MODE
DEBUG_LEVEL = int(os.getenv('FISCALAI_DEBUG_LEVEL', '1')) if DEBUG_MODE else 0

def debug_log(message: str, level: int = 1):
    """Função de debug temporária"""
    if DEBUG_MODE and level <= DEBUG_LEVEL:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # Log removido para evitar poluição do terminal


class DetectorValorInconsistente:
    """
    Detector de Valor Inconsistente
    
    Detecta inconsistências em valores, cálculos e impostos
    """
    
    def __init__(self):
        self.nome = "Detector de Valor Inconsistente"
        self.descricao = "Detecta inconsistências em valores e cálculos fiscais"
        
        # Thresholds configuráveis
        self.tolerancia_calculo = 0.01  # R$ 0,01
        self.tolerancia_percentual = 0.001  # 0,1%
        self.limite_diferenca_imposto = 0.05  # 5%
    
    def detectar(self, nfe: NFe, historico_nfes: List[NFe] = None) -> List[DeteccaoFraude]:
        """
        Detecta inconsistências de valores
        
        Args:
            nfe: NF-e atual para análise
            historico_nfes: Histórico de NF-e (não usado neste detector)
            
        Returns:
            Lista de fraudes detectadas
        """
        debug_log(f"Iniciando verificação de valores para NF-e: {nfe.chave_acesso}", 1)
        debug_log(f"Valor total NF-e: R$ {nfe.valor_total:.2f}, Itens: {len(nfe.itens)}", 2)
        
        fraudes = []
        
        # 1. Verificar cálculos de impostos
        debug_log("Verificando cálculos de impostos...", 2)
        fraude_impostos = self._verificar_calculos_impostos(nfe)
        if fraude_impostos:
            fraudes.extend(fraude_impostos)
            debug_log(f"Encontradas {len(fraude_impostos)} inconsistências de impostos", 3)
        
        # 2. Verificar consistência de valores
        debug_log("Verificando consistência de valores...", 2)
        fraude_valores = self._verificar_consistencia_valores(nfe)
        if fraude_valores:
            fraudes.extend(fraude_valores)
            debug_log(f"Encontradas {len(fraude_valores)} inconsistências de valores", 3)
        
        # 3. Verificar arredondamentos
        debug_log("Verificando arredondamentos suspeitos...", 2)
        fraude_arredondamento = self._verificar_arredondamentos(nfe)
        if fraude_arredondamento:
            fraudes.extend(fraude_arredondamento)
            debug_log(f"Encontrados {len(fraude_arredondamento)} arredondamentos suspeitos", 3)
        
        # 4. Verificar proporções de impostos
        debug_log("Verificando proporções de impostos...", 2)
        fraude_proporcoes = self._verificar_proporcoes_impostos(nfe)
        if fraude_proporcoes:
            fraudes.extend(fraude_proporcoes)
            debug_log(f"Encontradas {len(fraude_proporcoes)} inconsistências de proporções", 3)
        
        debug_log(f"Total de fraudes detectadas: {len(fraudes)}", 1)
        return fraudes
    
    def _verificar_calculos_impostos(self, nfe: NFe) -> List[DeteccaoFraude]:
        """Verifica cálculos de impostos"""
        
        fraudes = []
        
        for i, item in enumerate(nfe.itens):
            # Verificar ICMS - usar getattr com valores padrão
            icms_valor = getattr(item, 'icms_valor', 0.0)
            icms_aliquota = getattr(item, 'icms_aliquota', 0.0)
            
            if icms_valor > 0 and icms_aliquota > 0:
                icms_calculado = self._calcular_icms(item)
                diferenca = abs(icms_valor - icms_calculado)
                
                if diferenca > self.tolerancia_calculo:
                    score = min(100, (diferenca / item.valor_total) * 1000)
                    
                    fraudes.append(DeteccaoFraude(
                        tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                        score=int(score),
                        confianca=0.8,
                        justificativa=f"ICMS inconsistente no item {i+1}: "
                                     f"declarado R$ {icms_valor:.2f}, "
                                     f"calculado R$ {icms_calculado:.2f}",
                        evidencias=[f"ICMS declarado: R$ {icms_valor:.2f}", 
                                   f"ICMS calculado: R$ {icms_calculado:.2f}", 
                                   f"Diferença: R$ {diferenca:.2f}"],
                        metodo_deteccao="rule_based",
                        item_numero=item.numero_item
                    ))
            
            # Verificar IPI - usar getattr com valores padrão
            ipi_valor = getattr(item, 'ipi_valor', 0.0)
            ipi_aliquota = getattr(item, 'ipi_aliquota', 0.0)
            
            if ipi_valor > 0 and ipi_aliquota > 0:
                ipi_calculado = self._calcular_ipi(item)
                diferenca = abs(ipi_valor - ipi_calculado)
                
                if diferenca > self.tolerancia_calculo:
                    score = min(100, (diferenca / item.valor_total) * 1000)
                    
                    fraudes.append(DeteccaoFraude(
                        tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                        score=int(score),
                        confianca=0.8,
                        justificativa=f"IPI inconsistente no item {i+1}: "
                                     f"declarado R$ {ipi_valor:.2f}, "
                                     f"calculado R$ {ipi_calculado:.2f}",
                        evidencias=[f"IPI declarado: R$ {ipi_valor:.2f}", 
                                   f"IPI calculado: R$ {ipi_calculado:.2f}", 
                                   f"Diferença: R$ {diferenca:.2f}"],
                        metodo_deteccao="rule_based",
                        item_numero=item.numero_item
                    ))
        
        return fraudes
    
    def _verificar_consistencia_valores(self, nfe: NFe) -> List[DeteccaoFraude]:
        """Verifica consistência de valores"""
        
        fraudes = []
        
        # Verificar se soma dos itens bate com total
        soma_itens = sum(item.valor_total for item in nfe.itens)
        diferenca_total = abs(nfe.valor_total - soma_itens)
        
        if diferenca_total > self.tolerancia_calculo:
            score = min(100, (diferenca_total / nfe.valor_total) * 1000)
            
            fraudes.append(DeteccaoFraude(
                tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                score=int(score),
                confianca=0.9,
                justificativa=f"Total da NF-e inconsistente: "
                             f"declarado R$ {nfe.valor_total:.2f}, "
                             f"soma itens R$ {soma_itens:.2f}",
                evidencias=[f"Total declarado: R$ {nfe.valor_total:.2f}", 
                           f"Soma itens: R$ {soma_itens:.2f}", 
                           f"Diferença: R$ {diferenca_total:.2f}"],
                metodo_deteccao="rule_based",
                item_numero=None
            ))
        
        # Verificar valores de produtos vs total
        valor_produtos = getattr(nfe, 'valor_produtos', None)
        if valor_produtos is not None:
            diferenca_produtos = abs(valor_produtos - soma_itens)
            
            if diferenca_produtos > self.tolerancia_calculo:
                score = min(100, (diferenca_produtos / valor_produtos) * 1000)
                
                fraudes.append(DeteccaoFraude(
                    tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                    score=int(score),
                    confianca=0.8,
                    justificativa=f"Valor produtos inconsistente: "
                                 f"declarado R$ {valor_produtos:.2f}, "
                                 f"soma itens R$ {soma_itens:.2f}",
                    evidencias=[f"Valor produtos: R$ {valor_produtos:.2f}", 
                               f"Soma itens: R$ {soma_itens:.2f}", 
                               f"Diferença: R$ {diferenca_produtos:.2f}"],
                    metodo_deteccao="rule_based",
                    item_numero=None
                ))
        
        return fraudes
    
    def _verificar_arredondamentos(self, nfe: NFe) -> List[DeteccaoFraude]:
        """Verifica arredondamentos suspeitos"""
        
        fraudes = []
        
        for i, item in enumerate(nfe.itens):
            # Verificar se valores têm muitos zeros (suspeito)
            valor_str = f"{item.valor_total:.2f}"
            zeros_consecutivos = self._contar_zeros_consecutivos(valor_str)
            
            if zeros_consecutivos >= 3:  # R$ 1000,00 ou similar
                score = min(50, zeros_consecutivos * 10)
                
                fraudes.append(DeteccaoFraude(
                    tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                    score=score,
                    confianca=0.6,
                    justificativa=f"Valor com arredondamento suspeito no item {i+1}: "
                                 f"R$ {item.valor_total:.2f}",
                    evidencias=[f"Valor: R$ {item.valor_total:.2f}", 
                               f"Zeros consecutivos: {zeros_consecutivos}"],
                    metodo_deteccao="rule_based",
                    item_numero=item.numero_item
                ))
        
        return fraudes
    
    def _verificar_proporcoes_impostos(self, nfe: NFe) -> List[DeteccaoFraude]:
        """Verifica proporções de impostos"""
        
        fraudes = []
        
        for i, item in enumerate(nfe.itens):
            # Verificar se alíquota de ICMS está dentro do esperado
            icms_aliquota = getattr(item, 'icms_aliquota', 0.0)
            icms_valor = getattr(item, 'icms_valor', 0.0)
            
            if icms_aliquota > 0 and icms_valor > 0 and item.valor_total > 0:
                aliquota_calculada = (icms_valor / item.valor_total) * 100
                diferenca_aliquota = abs(icms_aliquota - aliquota_calculada)
                
                if diferenca_aliquota > self.limite_diferenca_imposto:
                    score = min(100, diferenca_aliquota * 1000)
                    
                    fraudes.append(DeteccaoFraude(
                        tipo_fraude=TipoFraude.VALOR_INCONSISTENTE,
                        score=int(score),
                        confianca=0.8,
                        justificativa=f"Alíquota ICMS inconsistente no item {i+1}: "
                                     f"declarada {icms_aliquota:.2f}%, "
                                     f"calculada {aliquota_calculada:.2f}%",
                        evidencias=[f"Alíquota declarada: {icms_aliquota:.2f}%", 
                                   f"Alíquota calculada: {aliquota_calculada:.2f}%", 
                                   f"Diferença: {diferenca_aliquota:.2f}%"],
                        metodo_deteccao="rule_based",
                        item_numero=item.numero_item
                    ))
        
        return fraudes
    
    def _calcular_icms(self, item: ItemNFe) -> float:
        """Calcula ICMS baseado na alíquota"""
        
        icms_aliquota = getattr(item, 'icms_aliquota', 0.0)
        if icms_aliquota <= 0:
            return 0.0
        
        # Base de cálculo (valor do item)
        base_calculo = item.valor_total
        
        # Calcular ICMS
        icms = base_calculo * (icms_aliquota / 100)
        
        # Arredondar para 2 casas decimais
        return round(icms, 2)
    
    def _calcular_ipi(self, item: ItemNFe) -> float:
        """Calcula IPI baseado na alíquota"""
        
        ipi_aliquota = getattr(item, 'ipi_aliquota', 0.0)
        if ipi_aliquota <= 0:
            return 0.0
        
        # Base de cálculo (valor do item)
        base_calculo = item.valor_total
        
        # Calcular IPI
        ipi = base_calculo * (ipi_aliquota / 100)
        
        # Arredondar para 2 casas decimais
        return round(ipi, 2)
    
    def _contar_zeros_consecutivos(self, valor_str: str) -> int:
        """Conta zeros consecutivos no final do valor"""
        
        # Remover ponto decimal
        valor_limpo = valor_str.replace('.', '')
        
        # Contar zeros do final
        zeros = 0
        for char in reversed(valor_limpo):
            if char == '0':
                zeros += 1
            else:
                break
        
        return zeros
