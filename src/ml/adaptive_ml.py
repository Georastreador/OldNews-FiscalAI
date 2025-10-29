"""
FiscalAI MVP - Machine Learning Adaptativo
Algoritmos adaptativos para detecção de fraudes
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import pickle
import json
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)

@dataclass
class MLModel:
    """Modelo de Machine Learning"""
    name: str
    model_type: str
    model: Any
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_samples: int
    last_trained: datetime
    features_importance: Dict[str, float]

@dataclass
class AdaptiveLearningResult:
    """Resultado do aprendizado adaptativo"""
    model_name: str
    improvement_type: str
    accuracy_improvement: float
    new_accuracy: float
    features_added: List[str]
    samples_added: int
    learning_timestamp: datetime

class AdaptiveMLSystem:
    """
    Sistema de Machine Learning adaptativo para detecção de fraudes
    
    Funcionalidades:
    - Múltiplos algoritmos de ML
    - Aprendizado incremental
    - Seleção automática de features
    - Ensemble learning
    - Detecção de drift
    """
    
    def __init__(self, models_dir: str = "ml_models"):
        """
        Inicializa o sistema de ML adaptativo
        
        Args:
            models_dir: Diretório para armazenar modelos
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Modelos disponíveis
        self.models: Dict[str, MLModel] = {}
        self.ensemble_weights: Dict[str, float] = {}
        
        # Dados de treinamento
        self.training_data: List[Dict[str, Any]] = []
        self.feature_names: List[str] = []
        
        # Configurações
        self.retraining_threshold = 0.05  # 5% de degradação
        self.min_samples_for_retraining = 100
        self.ensemble_size = 5
        
        # Inicializar modelos
        self._initialize_models()
    
    def _initialize_models(self):
        """Inicializa modelos de ML"""
        # Random Forest
        self.models['random_forest'] = MLModel(
            name='Random Forest',
            model_type='ensemble',
            model=RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            ),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Gradient Boosting
        self.models['gradient_boosting'] = MLModel(
            name='Gradient Boosting',
            model_type='ensemble',
            model=GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Logistic Regression
        self.models['logistic_regression'] = MLModel(
            name='Logistic Regression',
            model_type='linear',
            model=LogisticRegression(
                random_state=42,
                max_iter=1000
            ),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Support Vector Machine
        self.models['svm'] = MLModel(
            name='Support Vector Machine',
            model_type='kernel',
            model=SVC(
                kernel='rbf',
                probability=True,
                random_state=42
            ),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Neural Network
        self.models['neural_network'] = MLModel(
            name='Neural Network',
            model_type='neural',
            model=MLPClassifier(
                hidden_layer_sizes=(100, 50),
                max_iter=1000,
                random_state=42
            ),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Inicializar pesos do ensemble
        self.ensemble_weights = {name: 1.0 / len(self.models) for name in self.models.keys()}
    
    def add_training_data(self, 
                         features: Dict[str, float],
                         label: bool,
                         context: Optional[Dict[str, Any]] = None):
        """
        Adiciona dados de treinamento
        
        Args:
            features: Features do exemplo
            label: Label verdadeiro (True = fraude, False = normal)
            context: Contexto adicional
        """
        data_point = {
            'features': features,
            'label': label,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.training_data.append(data_point)
        
        # Atualizar lista de features
        for feature_name in features.keys():
            if feature_name not in self.feature_names:
                self.feature_names.append(feature_name)
        
        logger.debug(f"Dados de treinamento adicionados: {len(self.training_data)} exemplos")
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara dados para treinamento
        
        Returns:
            (X, y) - Features e labels
        """
        if not self.training_data:
            raise ValueError("Nenhum dado de treinamento disponível")
        
        # Converter para arrays
        X = []
        y = []
        
        for data_point in self.training_data:
            # Criar vetor de features
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(data_point['features'].get(feature_name, 0.0))
            
            X.append(feature_vector)
            y.append(data_point['label'])
        
        return np.array(X), np.array(y)
    
    def train_model(self, model_name: str) -> MLModel:
        """
        Treina um modelo específico
        
        Args:
            model_name: Nome do modelo
            
        Returns:
            Modelo treinado
        """
        if model_name not in self.models:
            raise ValueError(f"Modelo {model_name} não encontrado")
        
        # Preparar dados
        X, y = self.prepare_training_data()
        
        if len(X) < 10:
            raise ValueError("Poucos dados para treinamento")
        
        # Dividir em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Normalizar features para alguns modelos
        if model_name in ['logistic_regression', 'svm', 'neural_network']:
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
        
        # Treinar modelo
        model = self.models[model_name]
        model.model.fit(X_train, y_train)
        
        # Avaliar modelo
        y_pred = model.model.predict(X_test)
        
        # Calcular métricas
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # Atualizar modelo
        model.accuracy = accuracy
        model.precision = precision
        model.recall = recall
        model.f1_score = f1
        model.training_samples = len(X_train)
        model.last_trained = datetime.now()
        
        # Calcular importância das features
        if hasattr(model.model, 'feature_importances_'):
            model.features_importance = dict(zip(self.feature_names, model.model.feature_importances_))
        elif hasattr(model.model, 'coef_'):
            # Para modelos lineares
            coef = model.model.coef_[0] if len(model.model.coef_.shape) > 1 else model.model.coef_
            model.features_importance = dict(zip(self.feature_names, np.abs(coef)))
        
        logger.info(f"Modelo {model_name} treinado - Acurácia: {accuracy:.3f}")
        
        return model
    
    def train_all_models(self) -> Dict[str, MLModel]:
        """
        Treina todos os modelos
        
        Returns:
            Dicionário com modelos treinados
        """
        trained_models = {}
        
        for model_name in self.models.keys():
            try:
                trained_model = self.train_model(model_name)
                trained_models[model_name] = trained_model
            except Exception as e:
                logger.error(f"Erro ao treinar modelo {model_name}: {e}")
        
        return trained_models
    
    def create_ensemble_model(self) -> MLModel:
        """
        Cria modelo ensemble
        
        Returns:
            Modelo ensemble
        """
        # Treinar todos os modelos
        trained_models = self.train_all_models()
        
        if not trained_models:
            raise ValueError("Nenhum modelo treinado disponível")
        
        # Calcular pesos baseados na performance
        total_f1 = sum(model.f1_score for model in trained_models.values())
        if total_f1 > 0:
            self.ensemble_weights = {
                name: model.f1_score / total_f1
                for name, model in trained_models.items()
            }
        
        # Criar modelo ensemble
        ensemble_model = MLModel(
            name='Ensemble',
            model_type='ensemble',
            model=None,  # Será implementado como função
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            training_samples=0,
            last_trained=datetime.now(),
            features_importance={}
        )
        
        # Calcular métricas do ensemble
        X, y = self.prepare_training_data()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        ensemble_predictions = self._ensemble_predict(X_test, trained_models)
        
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        ensemble_model.accuracy = accuracy_score(y_test, ensemble_predictions)
        ensemble_model.precision = precision_score(y_test, ensemble_predictions, zero_division=0)
        ensemble_model.recall = recall_score(y_test, ensemble_predictions, zero_division=0)
        ensemble_model.f1_score = f1_score(y_test, ensemble_predictions, zero_division=0)
        ensemble_model.training_samples = len(X_train)
        
        # Armazenar modelos treinados
        self.models.update(trained_models)
        self.models['ensemble'] = ensemble_model
        
        logger.info(f"Modelo ensemble criado - Acurácia: {ensemble_model.accuracy:.3f}")
        
        return ensemble_model
    
    def _ensemble_predict(self, X: np.ndarray, models: Dict[str, MLModel]) -> np.ndarray:
        """
        Prediz usando ensemble de modelos
        
        Args:
            X: Features
            models: Modelos treinados
            
        Returns:
            Predições do ensemble
        """
        predictions = []
        
        for model_name, model in models.items():
            if model_name == 'ensemble':
                continue
            
            # Normalizar features se necessário
            if model_name in ['logistic_regression', 'svm', 'neural_network']:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                pred = model.model.predict_proba(X_scaled)[:, 1]
            else:
                pred = model.model.predict_proba(X)[:, 1]
            
            predictions.append(pred)
        
        # Calcular média ponderada
        ensemble_pred = np.zeros(len(X))
        for i, pred in enumerate(predictions):
            model_name = list(models.keys())[i]
            weight = self.ensemble_weights.get(model_name, 1.0)
            ensemble_pred += weight * pred
        
        # Converter para predições binárias
        return (ensemble_pred > 0.5).astype(int)
    
    def predict_fraud(self, features: Dict[str, float], model_name: str = 'ensemble') -> Dict[str, Any]:
        """
        Prediz se é fraude
        
        Args:
            features: Features do exemplo
            model_name: Nome do modelo a usar
            
        Returns:
            Predição com confiança
        """
        if model_name not in self.models:
            raise ValueError(f"Modelo {model_name} não encontrado")
        
        model = self.models[model_name]
        
        if model.training_samples == 0:
            raise ValueError(f"Modelo {model_name} não foi treinado")
        
        # Preparar features
        feature_vector = []
        for feature_name in self.feature_names:
            feature_vector.append(features.get(feature_name, 0.0))
        
        X = np.array([feature_vector])
        
        # Normalizar se necessário
        if model_name in ['logistic_regression', 'svm', 'neural_network']:
            scaler = StandardScaler()
            X = scaler.fit_transform(X)
        
        # Predição
        if model_name == 'ensemble':
            # Usar ensemble
            trained_models = {name: m for name, m in self.models.items() if name != 'ensemble' and m.training_samples > 0}
            prediction = self._ensemble_predict(X, trained_models)[0]
            confidence = 0.5  # Placeholder
        else:
            # Usar modelo individual
            prediction = model.model.predict(X)[0]
            confidence = model.model.predict_proba(X)[0].max()
        
        return {
            'prediction': bool(prediction),
            'confidence': float(confidence),
            'model_used': model_name,
            'features_used': len(features)
        }
    
    def detect_drift(self, new_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta drift nos dados
        
        Args:
            new_data: Novos dados
            
        Returns:
            Resultado da detecção de drift
        """
        if len(new_data) < 10:
            return {"drift_detected": False, "message": "Poucos dados para detectar drift"}
        
        # Preparar dados antigos e novos
        old_X, _ = self.prepare_training_data()
        new_X = []
        
        for data_point in new_data:
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(data_point['features'].get(feature_name, 0.0))
            new_X.append(feature_vector)
        
        new_X = np.array(new_X)
        
        # Calcular estatísticas
        old_mean = np.mean(old_X, axis=0)
        new_mean = np.mean(new_X, axis=0)
        old_std = np.std(old_X, axis=0)
        new_std = np.std(new_X, axis=0)
        
        # Calcular distância entre distribuições
        mean_distance = np.linalg.norm(old_mean - new_mean)
        std_distance = np.linalg.norm(old_std - new_std)
        
        # Thresholds para drift
        mean_threshold = 0.5
        std_threshold = 0.3
        
        drift_detected = (mean_distance > mean_threshold) or (std_distance > std_threshold)
        
        return {
            'drift_detected': drift_detected,
            'mean_distance': float(mean_distance),
            'std_distance': float(std_distance),
            'mean_threshold': mean_threshold,
            'std_threshold': std_threshold,
            'samples_compared': len(new_data)
        }
    
    def adaptive_learning(self, new_data: List[Dict[str, Any]]) -> AdaptiveLearningResult:
        """
        Aprendizado adaptativo com novos dados
        
        Args:
            new_data: Novos dados para aprendizado
            
        Returns:
            Resultado do aprendizado adaptativo
        """
        # Detectar drift
        drift_result = self.detect_drift(new_data)
        
        if not drift_result['drift_detected']:
            return AdaptiveLearningResult(
                model_name='none',
                improvement_type='no_drift',
                accuracy_improvement=0.0,
                new_accuracy=0.0,
                features_added=[],
                samples_added=0,
                learning_timestamp=datetime.now()
            )
        
        # Adicionar novos dados
        for data_point in new_data:
            self.add_training_data(
                data_point['features'],
                data_point['label'],
                data_point.get('context')
            )
        
        # Retreinar modelos
        old_accuracy = self.models['ensemble'].accuracy if 'ensemble' in self.models else 0.0
        
        # Treinar ensemble
        ensemble_model = self.create_ensemble_model()
        
        accuracy_improvement = ensemble_model.accuracy - old_accuracy
        
        # Identificar features adicionadas
        new_features = []
        for data_point in new_data:
            for feature_name in data_point['features'].keys():
                if feature_name not in self.feature_names:
                    new_features.append(feature_name)
        
        return AdaptiveLearningResult(
            model_name='ensemble',
            improvement_type='drift_adaptation',
            accuracy_improvement=accuracy_improvement,
            new_accuracy=ensemble_model.accuracy,
            features_added=new_features,
            samples_added=len(new_data),
            learning_timestamp=datetime.now()
        )
    
    def get_model_performance(self) -> Dict[str, Any]:
        """
        Retorna performance dos modelos
        
        Returns:
            Performance dos modelos
        """
        performance = {}
        
        for name, model in self.models.items():
            if model.training_samples > 0:
                performance[name] = {
                    'accuracy': model.accuracy,
                    'precision': model.precision,
                    'recall': model.recall,
                    'f1_score': model.f1_score,
                    'training_samples': model.training_samples,
                    'last_trained': model.last_trained.isoformat(),
                    'features_importance': model.features_importance
                }
        
        return performance
    
    def save_models(self):
        """Salva modelos treinados"""
        for name, model in self.models.items():
            if model.training_samples > 0:
                model_file = self.models_dir / f"{name}_model.pkl"
                with open(model_file, 'wb') as f:
                    pickle.dump(model, f)
        
        # Salvar configurações
        config = {
            'feature_names': self.feature_names,
            'ensemble_weights': self.ensemble_weights,
            'training_data_count': len(self.training_data)
        }
        
        config_file = self.models_dir / "ml_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("Modelos salvos com sucesso")
    
    def load_models(self):
        """Carrega modelos salvos"""
        for name in self.models.keys():
            model_file = self.models_dir / f"{name}_model.pkl"
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    self.models[name] = pickle.load(f)
        
        # Carregar configurações
        config_file = self.models_dir / "ml_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.feature_names = config.get('feature_names', [])
                self.ensemble_weights = config.get('ensemble_weights', {})
        
        logger.info("Modelos carregados com sucesso")


# Instância global do sistema
_adaptive_ml_instance: Optional[AdaptiveMLSystem] = None

def get_adaptive_ml_system() -> AdaptiveMLSystem:
    """Retorna instância global do sistema"""
    global _adaptive_ml_instance
    if _adaptive_ml_instance is None:
        _adaptive_ml_instance = AdaptiveMLSystem()
    return _adaptive_ml_instance

def predict_fraud_ml(features: Dict[str, float], model_name: str = 'ensemble') -> Dict[str, Any]:
    """Função de conveniência para predição"""
    return get_adaptive_ml_system().predict_fraud(features, model_name)

def add_ml_training_data(features: Dict[str, float], label: bool, context: Optional[Dict[str, Any]] = None):
    """Função de conveniência para adicionar dados de treinamento"""
    get_adaptive_ml_system().add_training_data(features, label, context)
