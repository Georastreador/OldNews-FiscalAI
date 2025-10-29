"""
FiscalAI MVP - Calibrador de Thresholds
Calibra thresholds baseado em dados reais para melhorar acurácia
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
from sklearn.metrics import precision_recall_curve, roc_curve, auc
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

@dataclass
class ThresholdCalibration:
    """Calibração de threshold"""
    detector_name: str
    original_threshold: float
    calibrated_threshold: float
    precision_improvement: float
    recall_improvement: float
    f1_improvement: float
    calibration_data_points: int
    confidence_interval: Tuple[float, float]

@dataclass
class CalibrationMetrics:
    """Métricas de calibração"""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    auc_score: float

class ThresholdCalibrator:
    """
    Calibrador de thresholds para detectores de fraude
    
    Funcionalidades:
    - Análise de dados históricos
    - Otimização de thresholds
    - Validação cruzada
    - Métricas de performance
    """
    
    def __init__(self, calibration_data_dir: str = "calibration_data"):
        """
        Inicializa o calibrador
        
        Args:
            calibration_data_dir: Diretório com dados de calibração
        """
        self.calibration_data_dir = Path(calibration_data_dir)
        self.calibration_data_dir.mkdir(exist_ok=True)
        
        # Dados de calibração
        self.calibration_data: List[Dict[str, Any]] = []
        self.calibrated_thresholds: Dict[str, float] = {}
        
        # Carregar dados existentes
        self._load_calibration_data()
    
    def add_calibration_data(self, 
                           detector_name: str,
                           true_label: bool,
                           predicted_score: float,
                           context: Optional[Dict[str, Any]] = None):
        """
        Adiciona dados de calibração
        
        Args:
            detector_name: Nome do detector
            true_label: Label verdadeiro (True = fraude, False = normal)
            predicted_score: Score predito pelo detector
            context: Contexto adicional
        """
        data_point = {
            'detector_name': detector_name,
            'true_label': true_label,
            'predicted_score': predicted_score,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        self.calibration_data.append(data_point)
        logger.debug(f"Dados de calibração adicionados para {detector_name}")
    
    def calibrate_detector_threshold(self, 
                                   detector_name: str,
                                   method: str = 'f1_optimization') -> ThresholdCalibration:
        """
        Calibra threshold para um detector específico
        
        Args:
            detector_name: Nome do detector
            method: Método de calibração
            
        Returns:
            Resultado da calibração
        """
        # Filtrar dados do detector
        detector_data = [
            d for d in self.calibration_data
            if d['detector_name'] == detector_name
        ]
        
        if len(detector_data) < 10:
            raise ValueError(f"Poucos dados para calibração do detector {detector_name}")
        
        # Extrair scores e labels
        scores = np.array([d['predicted_score'] for d in detector_data])
        labels = np.array([d['true_label'] for d in detector_data])
        
        # Threshold original (assumir 0.5)
        original_threshold = 0.5
        
        # Calibrar threshold
        if method == 'f1_optimization':
            calibrated_threshold = self._optimize_f1_threshold(scores, labels)
        elif method == 'precision_recall_balance':
            calibrated_threshold = self._balance_precision_recall(scores, labels)
        elif method == 'roc_optimization':
            calibrated_threshold = self._optimize_roc_threshold(scores, labels)
        else:
            raise ValueError(f"Método de calibração desconhecido: {method}")
        
        # Calcular métricas
        original_metrics = self._calculate_metrics(scores, labels, original_threshold)
        calibrated_metrics = self._calculate_metrics(scores, labels, calibrated_threshold)
        
        # Calcular melhorias
        precision_improvement = calibrated_metrics.precision - original_metrics.precision
        recall_improvement = calibrated_metrics.recall - original_metrics.recall
        f1_improvement = calibrated_metrics.f1_score - original_metrics.f1_score
        
        # Calcular intervalo de confiança
        confidence_interval = self._calculate_confidence_interval(scores, labels, calibrated_threshold)
        
        # Criar resultado
        calibration = ThresholdCalibration(
            detector_name=detector_name,
            original_threshold=original_threshold,
            calibrated_threshold=calibrated_threshold,
            precision_improvement=precision_improvement,
            recall_improvement=recall_improvement,
            f1_improvement=f1_improvement,
            calibration_data_points=len(detector_data),
            confidence_interval=confidence_interval
        )
        
        # Armazenar threshold calibrado
        self.calibrated_thresholds[detector_name] = calibrated_threshold
        
        logger.info(f"Threshold calibrado para {detector_name}: {original_threshold:.3f} -> {calibrated_threshold:.3f}")
        
        return calibration
    
    def _optimize_f1_threshold(self, scores: np.ndarray, labels: np.ndarray) -> float:
        """
        Otimiza threshold para maximizar F1-score
        
        Args:
            scores: Scores preditos
            labels: Labels verdadeiros
            
        Returns:
            Threshold otimizado
        """
        # Calcular F1-score para diferentes thresholds
        thresholds = np.linspace(0, 1, 100)
        f1_scores = []
        
        for threshold in thresholds:
            predicted = (scores >= threshold).astype(int)
            f1 = self._calculate_f1_score(labels, predicted)
            f1_scores.append(f1)
        
        # Encontrar threshold com maior F1-score
        best_idx = np.argmax(f1_scores)
        return thresholds[best_idx]
    
    def _balance_precision_recall(self, scores: np.ndarray, labels: np.ndarray) -> float:
        """
        Balanceia precision e recall
        
        Args:
            scores: Scores preditos
            labels: Labels verdadeiros
            
        Returns:
            Threshold balanceado
        """
        # Calcular precision e recall para diferentes thresholds
        thresholds = np.linspace(0, 1, 100)
        precisions = []
        recalls = []
        
        for threshold in thresholds:
            predicted = (scores >= threshold).astype(int)
            precision = self._calculate_precision(labels, predicted)
            recall = self._calculate_recall(labels, predicted)
            precisions.append(precision)
            recalls.append(recall)
        
        # Encontrar threshold onde precision e recall são mais próximos
        differences = np.abs(np.array(precisions) - np.array(recalls))
        best_idx = np.argmin(differences)
        return thresholds[best_idx]
    
    def _optimize_roc_threshold(self, scores: np.ndarray, labels: np.ndarray) -> float:
        """
        Otimiza threshold usando curva ROC
        
        Args:
            scores: Scores preditos
            labels: Labels verdadeiros
            
        Returns:
            Threshold otimizado
        """
        # Calcular curva ROC
        fpr, tpr, thresholds = roc_curve(labels, scores)
        
        # Encontrar threshold que maximiza TPR - FPR
        optimal_idx = np.argmax(tpr - fpr)
        return thresholds[optimal_idx]
    
    def _calculate_metrics(self, scores: np.ndarray, labels: np.ndarray, threshold: float) -> CalibrationMetrics:
        """
        Calcula métricas para um threshold específico
        
        Args:
            scores: Scores preditos
            labels: Labels verdadeiros
            threshold: Threshold a usar
            
        Returns:
            Métricas calculadas
        """
        predicted = (scores >= threshold).astype(int)
        
        precision = self._calculate_precision(labels, predicted)
        recall = self._calculate_recall(labels, predicted)
        f1_score = self._calculate_f1_score(labels, predicted)
        accuracy = self._calculate_accuracy(labels, predicted)
        
        # Calcular taxas de erro
        tn, fp, fn, tp = self._calculate_confusion_matrix(labels, predicted)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        # Calcular AUC
        try:
            auc_score = auc(*roc_curve(labels, scores)[:2])
        except:
            auc_score = 0.0
        
        return CalibrationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=accuracy,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            auc_score=auc_score
        )
    
    def _calculate_precision(self, labels: np.ndarray, predicted: np.ndarray) -> float:
        """Calcula precision"""
        tp = np.sum((labels == 1) & (predicted == 1))
        fp = np.sum((labels == 0) & (predicted == 1))
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    def _calculate_recall(self, labels: np.ndarray, predicted: np.ndarray) -> float:
        """Calcula recall"""
        tp = np.sum((labels == 1) & (predicted == 1))
        fn = np.sum((labels == 1) & (predicted == 0))
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    def _calculate_f1_score(self, labels: np.ndarray, predicted: np.ndarray) -> float:
        """Calcula F1-score"""
        precision = self._calculate_precision(labels, predicted)
        recall = self._calculate_recall(labels, predicted)
        return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    def _calculate_accuracy(self, labels: np.ndarray, predicted: np.ndarray) -> float:
        """Calcula accuracy"""
        return np.mean(labels == predicted)
    
    def _calculate_confusion_matrix(self, labels: np.ndarray, predicted: np.ndarray) -> Tuple[int, int, int, int]:
        """Calcula matriz de confusão"""
        tn = np.sum((labels == 0) & (predicted == 0))
        fp = np.sum((labels == 0) & (predicted == 1))
        fn = np.sum((labels == 1) & (predicted == 0))
        tp = np.sum((labels == 1) & (predicted == 1))
        return tn, fp, fn, tp
    
    def _calculate_confidence_interval(self, scores: np.ndarray, labels: np.ndarray, threshold: float, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calcula intervalo de confiança para o threshold
        
        Args:
            scores: Scores preditos
            labels: Labels verdadeiros
            threshold: Threshold
            confidence: Nível de confiança
            
        Returns:
            Intervalo de confiança
        """
        # Bootstrap para calcular intervalo de confiança
        n_bootstrap = 1000
        bootstrap_thresholds = []
        
        for _ in range(n_bootstrap):
            # Amostra bootstrap
            indices = np.random.choice(len(scores), size=len(scores), replace=True)
            bootstrap_scores = scores[indices]
            bootstrap_labels = labels[indices]
            
            # Calcular threshold otimizado
            bootstrap_threshold = self._optimize_f1_threshold(bootstrap_scores, bootstrap_labels)
            bootstrap_thresholds.append(bootstrap_threshold)
        
        # Calcular percentis
        alpha = 1 - confidence
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        return (
            np.percentile(bootstrap_thresholds, lower_percentile),
            np.percentile(bootstrap_thresholds, upper_percentile)
        )
    
    def calibrate_all_detectors(self) -> Dict[str, ThresholdCalibration]:
        """
        Calibra thresholds para todos os detectores
        
        Returns:
            Dicionário com calibrações
        """
        # Obter lista de detectores
        detectors = list(set(d['detector_name'] for d in self.calibration_data))
        
        calibrations = {}
        for detector in detectors:
            try:
                calibration = self.calibrate_detector_threshold(detector)
                calibrations[detector] = calibration
            except Exception as e:
                logger.error(f"Erro ao calibrar detector {detector}: {e}")
        
        return calibrations
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """
        Gera relatório de calibração
        
        Returns:
            Relatório de calibração
        """
        if not self.calibrated_thresholds:
            return {"message": "Nenhuma calibração realizada"}
        
        # Calcular estatísticas gerais
        total_data_points = len(self.calibration_data)
        detectors_calibrated = len(self.calibrated_thresholds)
        
        # Calcular melhorias médias
        calibrations = self.calibrate_all_detectors()
        avg_precision_improvement = np.mean([c.precision_improvement for c in calibrations.values()])
        avg_recall_improvement = np.mean([c.recall_improvement for c in calibrations.values()])
        avg_f1_improvement = np.mean([c.f1_improvement for c in calibrations.values()])
        
        return {
            'total_data_points': total_data_points,
            'detectors_calibrated': detectors_calibrated,
            'average_improvements': {
                'precision': avg_precision_improvement,
                'recall': avg_recall_improvement,
                'f1_score': avg_f1_improvement
            },
            'calibrated_thresholds': self.calibrated_thresholds,
            'calibration_details': [
                {
                    'detector': c.detector_name,
                    'original_threshold': c.original_threshold,
                    'calibrated_threshold': c.calibrated_threshold,
                    'precision_improvement': c.precision_improvement,
                    'recall_improvement': c.recall_improvement,
                    'f1_improvement': c.f1_improvement,
                    'data_points': c.calibration_data_points
                }
                for c in calibrations.values()
            ]
        }
    
    def export_calibration_data(self, file_path: str):
        """
        Exporta dados de calibração
        
        Args:
            file_path: Caminho do arquivo
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'calibration_data': self.calibration_data,
            'calibrated_thresholds': self.calibrated_thresholds,
            'report': self.get_calibration_report()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dados de calibração exportados para {file_path}")
    
    def _load_calibration_data(self):
        """Carrega dados de calibração existentes"""
        calibration_file = self.calibration_data_dir / "calibration_data.json"
        
        if calibration_file.exists():
            try:
                with open(calibration_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.calibration_data = data.get('calibration_data', [])
                self.calibrated_thresholds = data.get('calibrated_thresholds', {})
                
                logger.info(f"Carregados {len(self.calibration_data)} pontos de calibração")
                
            except Exception as e:
                logger.error(f"Erro ao carregar dados de calibração: {e}")
    
    def save_calibration_data(self):
        """Salva dados de calibração"""
        calibration_file = self.calibration_data_dir / "calibration_data.json"
        
        data = {
            'exported_at': datetime.now().isoformat(),
            'calibration_data': self.calibration_data,
            'calibrated_thresholds': self.calibrated_thresholds
        }
        
        with open(calibration_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# Instância global do calibrador
_calibrator_instance: Optional[ThresholdCalibrator] = None

def get_threshold_calibrator() -> ThresholdCalibrator:
    """Retorna instância global do calibrador"""
    global _calibrator_instance
    if _calibrator_instance is None:
        _calibrator_instance = ThresholdCalibrator()
    return _calibrator_instance

def add_calibration_data(detector_name: str, true_label: bool, predicted_score: float, context: Optional[Dict[str, Any]] = None):
    """Função de conveniência para adicionar dados de calibração"""
    get_threshold_calibrator().add_calibration_data(detector_name, true_label, predicted_score, context)

def calibrate_detector(detector_name: str, method: str = 'f1_optimization') -> ThresholdCalibration:
    """Função de conveniência para calibrar detector"""
    return get_threshold_calibrator().calibrate_detector_threshold(detector_name, method)
