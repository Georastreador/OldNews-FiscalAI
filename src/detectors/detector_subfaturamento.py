"""
FiscalAI MVP - Detector de Subfaturamento
Detecta produtos com valores significativamente abaixo do mercado
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Optional, Dict
from datetime import datetime, timedelta

from ..models import ItemNFe, NFe, DeteccaoFraude, TipoFraude


class DetectorSubfaturamento:
    """
    Detecta subfaturamento comparando com preços de mercado e histórico
    
    Métodos de detecção:
    1. Comparação com base de preços de mercado
    2. Análise estatística (Z-score, outliers)
    3. Verificação de histórico do fornecedor
    4. Detecção de padrões suspeitos (alto valor total + baixo preço unitário)
    """
    
    def __init__(self, 
                 base_precos: Optional[pd.DataFrame] = None,
                 historico: Optional[pd.DataFrame] = None):
        """
        Inicializa o detector
        
        Args:
            base_precos: DataFrame com colunas [ncm, preco_medio, preco_min, preco_max, desvio_padrao]
            historico: DataFrame com histórico de NF-e processadas
        """
        self.base_precos = base_precos if base_precos is not None else self._criar_base_precos_mock()
        self.historico = historico if historico is not None else pd.DataFrame()
        
        # Thresholds de detecção
        self.threshold_desvio_percentual = -30  # -30% do preço médio
        self.threshold_z_score = -3  # 3 desvios-padrão abaixo
        self.threshold_valor_alto = 10000  # R$ 10.000
        self.threshold_score_minimo = 30  # Score mínimo para reportar
    
    def detectar(self, item: ItemNFe, nfe: NFe) -> Optional[DeteccaoFraude]:
        """
        Detecta subfaturamento em um item
        
        Args:
            item: Item da NF-e a ser analisado
            nfe: NF-e completa (para contexto)
        
        Returns:
            DeteccaoFraude se houver suspeita, None caso contrário
        """
        ncm = item.ncm_declarado
        valor_unitario = item.valor_unitario
        
        # 1. Buscar preço de referência
        preco_ref = self._obter_preco_referencia(ncm)
        
        if preco_ref is None:
            # Sem dados de referência, usar histórico próprio
            preco_ref = self._obter_preco_historico(ncm)
        
        if preco_ref is None:
            # Sem dados suficientes para análise
            return None
        
        # 2. Calcular métricas
        desvio_percentual = ((valor_unitario - preco_ref['medio']) / preco_ref['medio']) * 100
        
        if preco_ref['desvio_padrao'] > 0:
            z_score = (valor_unitario - preco_ref['medio']) / preco_ref['desvio_padrao']
        else:
            z_score = 0
        
        # 3. Aplicar regras de detecção
        evidencias = []
        score = 0
        
        # Regra 1: Valor muito abaixo da média
        if desvio_percentual < self.threshold_desvio_percentual:
            pontos = min(40, int(abs(desvio_percentual) / 2))  # Até 40 pontos
            score += pontos
            evidencias.append(
                f"Valor {abs(desvio_percentual):.1f}% abaixo da média de mercado "
                f"(R$ {preco_ref['medio']:.2f})"
            )
        
        # Regra 2: Valor abaixo do mínimo histórico
        if valor_unitario < preco_ref['minimo']:
            score += 30
            evidencias.append(
                f"Valor R$ {valor_unitario:.2f} abaixo do mínimo histórico "
                f"R$ {preco_ref['minimo']:.2f}"
            )
        
        # Regra 3: Outlier estatístico
        if z_score < self.threshold_z_score:
            score += 30
            evidencias.append(
                f"Outlier estatístico significativo (Z-score: {z_score:.2f})"
            )
        
        # Regra 4: Alto valor total com preço unitário suspeito
        if item.valor_total > self.threshold_valor_alto and desvio_percentual < -20:
            score += 20
            evidencias.append(
                f"Alto valor total (R$ {item.valor_total:,.2f}) com preço unitário suspeito"
            )
        
        # Regra 5: Fornecedor com histórico de subfaturamento
        if self._fornecedor_tem_historico_subfaturamento(nfe.cnpj_emitente):
            score += 15
            evidencias.append(
                "Fornecedor possui histórico de subfaturamento em transações anteriores"
            )
        
        # 4. Determinar se é fraude
        score = min(score, 100)  # Cap em 100
        
        if score >= self.threshold_score_minimo:
            justificativa = self._gerar_justificativa(
                item, preco_ref, desvio_percentual, z_score
            )
            
            confianca = self._calcular_confianca(preco_ref, len(evidencias))
            
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.SUBFATURAMENTO,
                score=score,
                confianca=confianca,
                evidencias=evidencias,
                justificativa=justificativa,
                metodo_deteccao="statistical",
                item_numero=item.numero_item,
                dados_adicionais={
                    'preco_declarado': valor_unitario,
                    'preco_referencia': preco_ref['medio'],
                    'desvio_percentual': desvio_percentual,
                    'z_score': z_score,
                    'preco_minimo': preco_ref['minimo'],
                    'preco_maximo': preco_ref['maximo'],
                }
            )
        
        return None
    
    def _obter_preco_referencia(self, ncm: str) -> Optional[Dict]:
        """Obtém preço de referência da base de mercado"""
        if self.base_precos is None or ncm not in self.base_precos.index:
            return None
        
        row = self.base_precos.loc[ncm]
        return {
            'medio': float(row['preco_medio']),
            'minimo': float(row['preco_min']),
            'maximo': float(row['preco_max']),
            'desvio_padrao': float(row['desvio_padrao']),
            'fonte': 'mercado',
            'amostras': int(row.get('num_amostras', 100))
        }
    
    def _obter_preco_historico(self, ncm: str) -> Optional[Dict]:
        """Calcula preço de referência do histórico próprio"""
        if self.historico.empty:
            return None
        
        hist_ncm = self.historico[self.historico['ncm'] == ncm]
        
        if len(hist_ncm) < 5:  # Mínimo de 5 amostras
            return None
        
        precos = hist_ncm['valor_unitario']
        return {
            'medio': float(precos.mean()),
            'minimo': float(precos.min()),
            'maximo': float(precos.max()),
            'desvio_padrao': float(precos.std()),
            'fonte': 'historico',
            'amostras': len(hist_ncm)
        }
    
    def _fornecedor_tem_historico_subfaturamento(self, cnpj: str) -> bool:
        """Verifica se fornecedor tem histórico de subfaturamento"""
        if self.historico.empty:
            return False
        
        # Buscar fraudes anteriores deste fornecedor
        fraudes_fornecedor = self.historico[
            (self.historico['cnpj_emitente'] == cnpj) &
            (self.historico['fraude_detectada'] == 'subfaturamento')
        ]
        
        return len(fraudes_fornecedor) >= 2  # 2+ ocorrências
    
    def _calcular_confianca(self, preco_ref: Dict, num_evidencias: int) -> float:
        """
        Calcula confiança na detecção baseado na qualidade dos dados
        
        Args:
            preco_ref: Dict com dados de referência
            num_evidencias: Número de evidências encontradas
        
        Returns:
            Confiança entre 0 e 1
        """
        # Base de confiança pela fonte dos dados
        if preco_ref.get('fonte') == 'mercado':
            base_confianca = 0.9
        else:
            base_confianca = 0.7
        
        # Ajustar pela quantidade de amostras
        num_amostras = preco_ref.get('amostras', 10)
        if num_amostras < 10:
            base_confianca *= 0.8
        elif num_amostras > 100:
            base_confianca *= 1.05
        
        # Reduzir confiança se desvio-padrão for muito alto (dados inconsistentes)
        cv = preco_ref['desvio_padrao'] / preco_ref['medio']  # Coeficiente de variação
        if cv > 0.5:  # Variação > 50%
            base_confianca *= 0.8
        elif cv < 0.2:  # Variação < 20% (dados consistentes)
            base_confianca *= 1.1
        
        # Aumentar confiança com mais evidências
        base_confianca *= (1 + (num_evidencias - 1) * 0.05)
        
        # Garantir que fique entre 0 e 1
        return min(max(base_confianca, 0.0), 1.0)
    
    def _gerar_justificativa(self, 
                            item: ItemNFe, 
                            preco_ref: Dict,
                            desvio_percentual: float, 
                            z_score: float) -> str:
        """Gera justificativa textual da detecção"""
        justificativa = (
            f"O produto '{item.descricao}' (NCM {item.ncm_declarado}) foi declarado "
            f"com valor unitário de R$ {item.valor_unitario:.2f}, que está "
            f"{abs(desvio_percentual):.1f}% abaixo do preço médio de mercado "
            f"(R$ {preco_ref['medio']:.2f}). "
        )
        
        if z_score < -3:
            justificativa += (
                f"Este valor representa um outlier estatístico significativo "
                f"(Z-score: {z_score:.2f}), "
            )
        
        justificativa += (
            f"indicando possível subfaturamento para redução de base tributária. "
            f"O preço declarado está abaixo do mínimo histórico de R$ {preco_ref['minimo']:.2f}."
        )
        
        return justificativa
    
    def _criar_base_precos_mock(self) -> pd.DataFrame:
        """
        Cria base de preços mock para testes
        Em produção, isso seria substituído por dados reais de mercado
        """
        # Alguns NCMs comuns com preços de referência
        data = {
            'ncm': [
                '85171231',  # Smartphones
                '84713012',  # Notebooks
                '85176255',  # Roteadores
                '85044090',  # Carregadores
                '39202090',  # Placas de plástico
            ],
            'preco_medio': [2000.00, 3500.00, 150.00, 50.00, 25.00],
            'preco_min': [1200.00, 2000.00, 80.00, 20.00, 10.00],
            'preco_max': [4000.00, 8000.00, 400.00, 150.00, 80.00],
            'desvio_padrao': [500.00, 1200.00, 60.00, 20.00, 10.00],
            'num_amostras': [150, 200, 80, 120, 50],
        }
        
        df = pd.DataFrame(data)
        df.set_index('ncm', inplace=True)
        return df

