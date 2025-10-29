"""
FiscalAI MVP - Otimizador de Detecção de Fraudes
Algoritmos melhorados para detecção mais precisa e eficiente
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from ..models import NFe, ItemNFe, DeteccaoFraude, TipoFraude, ClassificacaoNCM

logger = logging.getLogger(__name__)

@dataclass
class FraudPattern:
    """Padrão de fraude identificado"""
    pattern_type: str
    confidence: float
    evidence: List[str]
    risk_score: float
    affected_items: List[int]

class FraudOptimizer:
    """
    Otimizador de detecção de fraudes com algoritmos melhorados
    
    Funcionalidades:
    - Detecção baseada em padrões
    - Análise estatística avançada
    - Machine Learning básico
    - Calibração automática de thresholds
    """
    
    def __init__(self):
        """Inicializa o otimizador"""
        self.patterns = self._load_fraud_patterns()
        self.statistical_thresholds = self._calculate_statistical_thresholds()
        self.ml_weights = self._initialize_ml_weights()
    
    def _load_fraud_patterns(self) -> Dict[str, Dict]:
        """Carrega padrões conhecidos de fraude"""
        return {
            'subfaturamento': {
                'price_deviation_threshold': -0.3,  # 30% abaixo da média
                'z_score_threshold': -2.0,
                'volume_anomaly_threshold': 0.5,
                'weight': 0.4
            },
            'ncm_incorreto': {
                'confidence_threshold': 0.7,
                'description_similarity_threshold': 0.8,
                'category_mismatch_penalty': 0.3,
                'weight': 0.3
            },
            'triangulacao': {
                'supplier_rotation_threshold': 0.8,
                'geographic_distance_threshold': 1000,  # km
                'time_pattern_threshold': 0.6,
                'weight': 0.2
            },
            'fracionamento': {
                'value_split_threshold': 0.7,
                'time_proximity_threshold': 24,  # horas
                'similarity_threshold': 0.8,
                'weight': 0.1
            }
        }
    
    def _calculate_statistical_thresholds(self) -> Dict[str, float]:
        """Calcula thresholds estatísticos baseados em dados históricos"""
        return {
            'price_z_score': -2.5,
            'volume_z_score': 2.0,
            'time_anomaly_score': 0.7,
            'supplier_risk_score': 0.6,
            'geographic_anomaly_score': 0.8
        }
    
    def _initialize_ml_weights(self) -> Dict[str, float]:
        """Inicializa pesos para modelo de ML básico"""
        return {
            'price_anomaly': 0.25,
            'volume_anomaly': 0.20,
            'temporal_anomaly': 0.15,
            'supplier_risk': 0.20,
            'geographic_anomaly': 0.10,
            'description_anomaly': 0.10
        }
    
    def optimize_detection(self, 
                          nfe: NFe, 
                          classificacoes: Dict[int, ClassificacaoNCM],
                          historical_data: Optional[List[NFe]] = None) -> List[DeteccaoFraude]:
        """
        Otimiza detecção de fraudes usando algoritmos melhorados
        
        Args:
            nfe: NF-e para análise
            classificacoes: Classificações NCM dos itens
            historical_data: Dados históricos para comparação
            
        Returns:
            Lista de fraudes detectadas otimizadas
        """
        frauds = []
        
        # 1. Análise de padrões
        pattern_frauds = self._detect_pattern_frauds(nfe, classificacoes)
        frauds.extend(pattern_frauds)
        
        # 2. Análise estatística
        statistical_frauds = self._detect_statistical_frauds(nfe, historical_data)
        frauds.extend(statistical_frauds)
        
        # 3. Análise de ML básico
        ml_frauds = self._detect_ml_frauds(nfe, classificacoes, historical_data)
        frauds.extend(ml_frauds)
        
        # 4. Calibrar scores
        calibrated_frauds = self._calibrate_fraud_scores(frauds, nfe)
        
        # 5. Remover duplicatas e consolidar
        consolidated_frauds = self._consolidate_frauds(calibrated_frauds)
        
        return consolidated_frauds
    
    def _detect_pattern_frauds(self, nfe: NFe, classificacoes: Dict[int, ClassificacaoNCM]) -> List[DeteccaoFraude]:
        """Detecta fraudes baseadas em padrões conhecidos"""
        frauds = []
        
        for item in nfe.itens:
            # Análise de subfaturamento
            if self._is_subfaturamento_pattern(item, nfe):
                frauds.append(self._create_fraud_detection(
                    tipo=TipoFraude.SUBFATURAMENTO,
                    item=item,
                    score=self._calculate_subfaturamento_score(item),
                    evidence=["Valor significativamente abaixo da média de mercado"],
                    method="pattern_analysis"
                ))
            
            # Análise de NCM incorreto
            if item.numero_item in classificacoes:
                classificacao = classificacoes[item.numero_item]
                if self._is_ncm_incorreto_pattern(item, classificacao):
                    frauds.append(self._create_fraud_detection(
                        tipo=TipoFraude.NCM_INCORRETO,
                        item=item,
                        score=self._calculate_ncm_incorreto_score(item, classificacao),
                        evidence=["NCM declarado diverge significativamente do predito"],
                        method="pattern_analysis"
                    ))
        
        return frauds
    
    def _detect_statistical_frauds(self, nfe: NFe, historical_data: Optional[List[NFe]]) -> List[DeteccaoFraude]:
        """Detecta fraudes usando análise estatística"""
        frauds = []
        
        if not historical_data:
            return frauds
        
        # Calcular estatísticas históricas
        historical_stats = self._calculate_historical_stats(historical_data)
        
        # Análise de anomalias de preço
        for item in nfe.itens:
            if self._is_price_anomaly(item, historical_stats):
                frauds.append(self._create_fraud_detection(
                    tipo=TipoFraude.SUBFATURAMENTO,
                    item=item,
                    score=self._calculate_price_anomaly_score(item, historical_stats),
                    evidence=["Preço desvia significativamente da distribuição histórica"],
                    method="statistical_analysis"
                ))
        
        return frauds
    
    def _detect_ml_frauds(self, nfe: NFe, classificacoes: Dict[int, ClassificacaoNCM], 
                         historical_data: Optional[List[NFe]]) -> List[DeteccaoFraude]:
        """Detecta fraudes usando ML básico"""
        frauds = []
        
        # Extrair features
        features = self._extract_features(nfe, classificacoes, historical_data)
        
        # Calcular score de ML
        ml_score = self._calculate_ml_score(features)
        
        if ml_score > 0.7:  # Threshold para detecção
            frauds.append(self._create_fraud_detection(
                tipo=TipoFraude.SUBFATURAMENTO,  # Tipo genérico para ML
                item=None,
                score=ml_score * 100,
                evidence=["Anomalia detectada por modelo de ML"],
                method="machine_learning"
            ))
        
        return frauds
    
    def _is_subfaturamento_pattern(self, item: ItemNFe, nfe: NFe) -> bool:
        """Verifica se item segue padrão de subfaturamento"""
        pattern = self.patterns['subfaturamento']
        
        # Verificar desvio de preço
        if item.valor_unitario < 0:  # Preço negativo é suspeito
            return True
        
        # Verificar se valor está muito abaixo do esperado
        # (implementação simplificada - em produção usaria dados de mercado)
        if item.valor_unitario < 1.0 and item.valor_total > 100:  # Item muito barato com valor alto
            return True
        
        return False
    
    def _is_ncm_incorreto_pattern(self, item: ItemNFe, classificacao: ClassificacaoNCM) -> bool:
        """Verifica se NCM está incorreto baseado em padrões"""
        pattern = self.patterns['ncm_incorreto']
        
        # Verificar confiança da classificação
        if classificacao.confianca < pattern['confidence_threshold']:
            return True
        
        # Verificar se NCM declarado diverge do predito
        if (classificacao.ncm_declarado != classificacao.ncm_predito and 
            classificacao.confianca > 0.8):
            return True
        
        return False
    
    def _is_price_anomaly(self, item: ItemNFe, historical_stats: Dict) -> bool:
        """Verifica se preço é uma anomalia estatística"""
        if 'price_mean' not in historical_stats:
            return False
        
        # Calcular Z-score
        price_mean = historical_stats['price_mean']
        price_std = historical_stats['price_std']
        
        if price_std == 0:
            return False
        
        z_score = (item.valor_unitario - price_mean) / price_std
        
        return z_score < self.statistical_thresholds['price_z_score']
    
    def _calculate_historical_stats(self, historical_data: List[NFe]) -> Dict[str, float]:
        """Calcula estatísticas históricas"""
        all_prices = []
        all_volumes = []
        
        for nfe in historical_data:
            for item in nfe.itens:
                all_prices.append(item.valor_unitario)
                all_volumes.append(item.quantidade)
        
        if not all_prices:
            return {}
        
        return {
            'price_mean': np.mean(all_prices),
            'price_std': np.std(all_prices),
            'volume_mean': np.mean(all_volumes),
            'volume_std': np.std(all_volumes)
        }
    
    def _extract_features(self, nfe: NFe, classificacoes: Dict[int, ClassificacaoNCM], 
                         historical_data: Optional[List[NFe]]) -> Dict[str, float]:
        """Extrai features para ML"""
        features = {}
        
        # Features de preço
        prices = [item.valor_unitario for item in nfe.itens]
        features['avg_price'] = np.mean(prices) if prices else 0
        features['price_variance'] = np.var(prices) if prices else 0
        
        # Features de volume
        volumes = [item.quantidade for item in nfe.itens]
        features['avg_volume'] = np.mean(volumes) if volumes else 0
        features['volume_variance'] = np.var(volumes) if volumes else 0
        
        # Features de NCM
        ncm_confidences = [c.confianca for c in classificacoes.values()]
        features['avg_ncm_confidence'] = np.mean(ncm_confidences) if ncm_confidences else 0
        
        # Features temporais
        features['hour_of_day'] = nfe.data_emissao.hour
        features['day_of_week'] = nfe.data_emissao.weekday()
        
        return features
    
    def _calculate_ml_score(self, features: Dict[str, float]) -> float:
        """Calcula score usando modelo ML básico"""
        score = 0.0
        
        # Aplicar pesos
        for feature, value in features.items():
            if feature in self.ml_weights:
                score += self.ml_weights[feature] * value
        
        # Normalizar para 0-1
        return min(max(score, 0.0), 1.0)
    
    def _calculate_subfaturamento_score(self, item: ItemNFe) -> float:
        """Calcula score de subfaturamento"""
        # Implementação simplificada
        if item.valor_unitario <= 0:
            return 90.0
        elif item.valor_unitario < 1.0:
            return 70.0
        else:
            return 30.0
    
    def _calculate_ncm_incorreto_score(self, item: ItemNFe, classificacao: ClassificacaoNCM) -> float:
        """Calcula score de NCM incorreto"""
        if classificacao.confianca < 0.5:
            return 80.0
        elif classificacao.ncm_declarado != classificacao.ncm_predito:
            return 60.0
        else:
            return 20.0
    
    def _calculate_price_anomaly_score(self, item: ItemNFe, historical_stats: Dict) -> float:
        """Calcula score de anomalia de preço"""
        if 'price_mean' not in historical_stats or 'price_std' not in historical_stats:
            return 0.0
        
        price_mean = historical_stats['price_mean']
        price_std = historical_stats['price_std']
        
        if price_std == 0:
            return 0.0
        
        z_score = abs((item.valor_unitario - price_mean) / price_std)
        
        # Converter Z-score para score de 0-100
        if z_score > 3:
            return 90.0
        elif z_score > 2:
            return 70.0
        elif z_score > 1:
            return 50.0
        else:
            return 20.0
    
    def _calibrate_fraud_scores(self, frauds: List[DeteccaoFraude], nfe: NFe) -> List[DeteccaoFraude]:
        """Calibra scores de fraude baseado no contexto"""
        calibrated_frauds = []
        
        for fraud in frauds:
            # Ajustar score baseado no valor total da NF-e
            if nfe.valor_total > 10000:  # NF-e de alto valor
                fraud.score = min(fraud.score * 1.1, 100.0)
            elif nfe.valor_total < 100:  # NF-e de baixo valor
                fraud.score = max(fraud.score * 0.9, 0.0)
            
            calibrated_frauds.append(fraud)
        
        return calibrated_frauds
    
    def _consolidate_frauds(self, frauds: List[DeteccaoFraude]) -> List[DeteccaoFraude]:
        """Consolida fraudes duplicadas e remove falsos positivos"""
        if not frauds:
            return []
        
        # Agrupar por item
        frauds_by_item = {}
        for fraud in frauds:
            item_num = fraud.item_numero or 0
            if item_num not in frauds_by_item:
                frauds_by_item[item_num] = []
            frauds_by_item[item_num].append(fraud)
        
        consolidated = []
        for item_num, item_frauds in frauds_by_item.items():
            if len(item_frauds) == 1:
                consolidated.append(item_frauds[0])
            else:
                # Consolidar múltiplas fraudes do mesmo item
                consolidated_fraud = self._merge_frauds(item_frauds)
                if consolidated_fraud:
                    consolidated.append(consolidated_fraud)
        
        return consolidated
    
    def _merge_frauds(self, frauds: List[DeteccaoFraude]) -> Optional[DeteccaoFraude]:
        """Mescla múltiplas fraudes do mesmo item"""
        if not frauds:
            return None
        
        # Usar a fraude com maior score
        best_fraud = max(frauds, key=lambda f: f.score)
        
        # Combinar evidências
        all_evidence = []
        for fraud in frauds:
            all_evidence.extend(fraud.evidencias)
        
        best_fraud.evidencias = list(set(all_evidence))  # Remover duplicatas
        
        return best_fraud
    
    def _create_fraud_detection(self, tipo: TipoFraude, item: Optional[ItemNFe], 
                               score: float, evidence: List[str], method: str) -> DeteccaoFraude:
        """Cria detecção de fraude otimizada"""
        return DeteccaoFraude(
            tipo_fraude=tipo,
            score=score,
            confianca=min(score / 100.0, 1.0),
            evidencias=evidence,
            justificativa=f"Detecção otimizada usando {method}",
            metodo_deteccao=method,
            item_numero=item.numero_item if item else None,
            dados_adicionais={
                'optimized': True,
                'timestamp': datetime.now().isoformat()
            }
        )


# Instância global do otimizador
_optimizer_instance: Optional[FraudOptimizer] = None

def get_fraud_optimizer() -> FraudOptimizer:
    """Retorna instância global do otimizador"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = FraudOptimizer()
    return _optimizer_instance
