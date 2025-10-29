"""
FiscalAI MVP - Treinador de Modelo NCM Brasileiro
Sistema de treinamento específico para produtos brasileiros
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import re

logger = logging.getLogger(__name__)

@dataclass
class NCMTrainingData:
    """Dados de treinamento NCM"""
    description: str
    ncm_code: str
    category: str
    subcategory: str
    confidence: float
    source: str
    validated: bool = False

@dataclass
class NCMTrainingResult:
    """Resultado do treinamento"""
    model_accuracy: float
    test_accuracy: float
    feature_importance: Dict[str, float]
    confusion_matrix: List[List[int]]
    training_samples: int
    validation_samples: int

class BrazilianNCMTrainer:
    """
    Treinador de modelo NCM específico para produtos brasileiros
    
    Funcionalidades:
    - Dataset brasileiro específico
    - Features linguísticas em português
    - Validação com dados reais
    - Modelo adaptativo
    """
    
    def __init__(self, training_data_dir: str = "training_data"):
        """
        Inicializa o treinador
        
        Args:
            training_data_dir: Diretório com dados de treinamento
        """
        self.training_data_dir = Path(training_data_dir)
        self.training_data_dir.mkdir(exist_ok=True)
        
        # Modelos
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words=None,  # Usar stop words em português
            lowercase=True,
            strip_accents='unicode'
        )
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        # Dados de treinamento
        self.training_data: List[NCMTrainingData] = []
        self.validation_data: List[NCMTrainingData] = []
        
        # Features específicas do Brasil
        self.brazilian_features = self._load_brazilian_features()
        
        # Carregar dados iniciais
        self._load_training_data()
    
    def _load_brazilian_features(self) -> Dict[str, List[str]]:
        """Carrega features específicas do Brasil"""
        return {
            'industries': [
                'agronegócio', 'agropecuária', 'agricultura', 'pecuária',
                'mineração', 'siderurgia', 'química', 'petroquímica',
                'têxtil', 'confecção', 'calçados', 'couro',
                'automotivo', 'aeronáutico', 'naval', 'ferroviário',
                'construção civil', 'engenharia', 'infraestrutura',
                'tecnologia', 'software', 'hardware', 'eletrônicos',
                'alimentício', 'bebidas', 'farmacêutico', 'cosméticos'
            ],
            'materials': [
                'aço', 'ferro', 'alumínio', 'cobre', 'bronze',
                'plástico', 'borracha', 'madeira', 'vidro', 'cerâmica',
                'têxtil', 'algodão', 'poliester', 'nylon', 'couro',
                'papel', 'cartão', 'papelão', 'metal', 'inox'
            ],
            'products': [
                'máquina', 'equipamento', 'ferramenta', 'instrumento',
                'peça', 'componente', 'acessório', 'utensílio',
                'produto', 'artigo', 'item', 'mercadoria',
                'alimento', 'bebida', 'medicamento', 'cosmético',
                'roupa', 'calçado', 'bolsa', 'cinto', 'relógio'
            ],
            'units': [
                'unidade', 'un', 'kg', 'quilograma', 'grama', 'g',
                'litro', 'l', 'ml', 'mililitro',
                'metro', 'm', 'cm', 'centímetro', 'mm', 'milímetro',
                'm²', 'metro quadrado', 'm³', 'metro cúbico',
                'tonelada', 't', 'quintal', 'arroba'
            ],
            'qualities': [
                'premium', 'superior', 'especial', 'exclusivo',
                'padrão', 'comum', 'básico', 'econômico',
                'importado', 'nacional', 'local', 'regional',
                'novo', 'usado', 'seminovo', 'recondicionado'
            ]
        }
    
    def _load_training_data(self):
        """Carrega dados de treinamento"""
        # Dataset base brasileiro
        base_data = self._create_base_training_data()
        self.training_data.extend(base_data)
        
        # Carregar dados de arquivos se existirem
        self._load_from_files()
        
        logger.info(f"Carregados {len(self.training_data)} exemplos de treinamento")
    
    def _create_base_training_data(self) -> List[NCMTrainingData]:
        """Cria dataset base com produtos brasileiros comuns"""
        base_data = [
            # Alimentos
            NCMTrainingData("Arroz branco tipo 1", "1006.30.21", "Cereais", "Arroz", 0.95, "base"),
            NCMTrainingData("Feijão preto", "0713.32.00", "Leguminosas", "Feijão", 0.95, "base"),
            NCMTrainingData("Açúcar cristal", "1701.14.00", "Açúcares", "Açúcar", 0.95, "base"),
            NCMTrainingData("Café torrado em grão", "0901.21.00", "Café", "Café", 0.95, "base"),
            NCMTrainingData("Óleo de soja", "1507.90.00", "Óleos", "Óleo", 0.95, "base"),
            
            # Bebidas
            NCMTrainingData("Cerveja", "2203.00.00", "Bebidas", "Cerveja", 0.95, "base"),
            NCMTrainingData("Refrigerante", "2202.10.00", "Bebidas", "Refrigerante", 0.95, "base"),
            NCMTrainingData("Suco de laranja", "2009.12.00", "Sucos", "Suco", 0.95, "base"),
            
            # Têxtil
            NCMTrainingData("Camiseta de algodão", "6109.10.00", "Vestuário", "Camiseta", 0.95, "base"),
            NCMTrainingData("Calça jeans", "6203.42.00", "Vestuário", "Calça", 0.95, "base"),
            NCMTrainingData("Tênis esportivo", "6404.11.00", "Calçados", "Tênis", 0.95, "base"),
            
            # Eletrônicos
            NCMTrainingData("Smartphone", "8517.12.00", "Telecomunicações", "Telefone", 0.95, "base"),
            NCMTrainingData("Notebook", "8471.30.00", "Informática", "Computador", 0.95, "base"),
            NCMTrainingData("Televisão LED", "8528.72.00", "Eletrônicos", "TV", 0.95, "base"),
            
            # Automotivo
            NCMTrainingData("Pneu de carro", "4011.10.00", "Automotivo", "Pneu", 0.95, "base"),
            NCMTrainingData("Bateria de carro", "8507.20.00", "Automotivo", "Bateria", 0.95, "base"),
            NCMTrainingData("Óleo de motor", "2710.19.00", "Automotivo", "Óleo", 0.95, "base"),
            
            # Construção
            NCMTrainingData("Cimento Portland", "2523.29.00", "Construção", "Cimento", 0.95, "base"),
            NCMTrainingData("Tijolo cerâmico", "6904.10.00", "Construção", "Tijolo", 0.95, "base"),
            NCMTrainingData("Tinta acrílica", "3209.10.00", "Construção", "Tinta", 0.95, "base"),
            
            # Química
            NCMTrainingData("Detergente líquido", "3402.20.00", "Química", "Detergente", 0.95, "base"),
            NCMTrainingData("Shampoo", "3305.10.00", "Cosméticos", "Shampoo", 0.95, "base"),
            NCMTrainingData("Medicamento genérico", "3004.90.00", "Farmacêutico", "Medicamento", 0.95, "base"),
        ]
        
        return base_data
    
    def _load_from_files(self):
        """Carrega dados de arquivos externos"""
        # Procurar por arquivos de treinamento
        for file_path in self.training_data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data:
                    training_item = NCMTrainingData(
                        description=item['description'],
                        ncm_code=item['ncm_code'],
                        category=item.get('category', ''),
                        subcategory=item.get('subcategory', ''),
                        confidence=item.get('confidence', 0.8),
                        source=item.get('source', 'file'),
                        validated=item.get('validated', False)
                    )
                    self.training_data.append(training_item)
                
                logger.info(f"Carregados dados de {file_path}")
            except Exception as e:
                logger.warning(f"Erro ao carregar {file_path}: {e}")
    
    def add_training_example(self, description: str, ncm_code: str, 
                           category: str = "", subcategory: str = "", 
                           confidence: float = 0.8, validated: bool = False):
        """
        Adiciona exemplo de treinamento
        
        Args:
            description: Descrição do produto
            ncm_code: Código NCM
            category: Categoria
            subcategory: Subcategoria
            confidence: Confiança na classificação
            validated: Se foi validado por especialista
        """
        example = NCMTrainingData(
            description=description,
            ncm_code=ncm_code,
            category=category,
            subcategory=subcategory,
            confidence=confidence,
            source="user",
            validated=validated
        )
        
        self.training_data.append(example)
        logger.info(f"Adicionado exemplo de treinamento: {description} -> {ncm_code}")
    
    def extract_features(self, description: str) -> Dict[str, Any]:
        """
        Extrai features específicas para produtos brasileiros
        
        Args:
            description: Descrição do produto
            
        Returns:
            Features extraídas
        """
        features = {}
        
        # Features básicas
        features['length'] = len(description)
        features['word_count'] = len(description.split())
        features['has_numbers'] = bool(re.search(r'\d', description))
        features['has_units'] = any(unit in description.lower() for unit in self.brazilian_features['units'])
        
        # Features de indústria
        for industry in self.brazilian_features['industries']:
            features[f'industry_{industry}'] = industry in description.lower()
        
        # Features de material
        for material in self.brazilian_features['materials']:
            features[f'material_{material}'] = material in description.lower()
        
        # Features de produto
        for product in self.brazilian_features['products']:
            features[f'product_{product}'] = product in description.lower()
        
        # Features de qualidade
        for quality in self.brazilian_features['qualities']:
            features[f'quality_{quality}'] = quality in description.lower()
        
        # Features linguísticas
        features['has_portuguese_chars'] = bool(re.search(r'[áàâãéêíóôõúç]', description.lower()))
        features['has_abbreviations'] = bool(re.search(r'\b[A-Z]{2,}\b', description))
        features['has_brand'] = bool(re.search(r'\b[A-Z][a-z]+\b', description))
        
        return features
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepara dados para treinamento
        
        Returns:
            (X, y, feature_names)
        """
        if not self.training_data:
            raise ValueError("Nenhum dado de treinamento disponível")
        
        # Separar descrições e códigos NCM
        descriptions = [item.description for item in self.training_data]
        ncm_codes = [item.ncm_code for item in self.training_data]
        
        # Vetorizar descrições
        X_text = self.vectorizer.fit_transform(descriptions)
        
        # Extrair features específicas
        X_features = []
        for description in descriptions:
            features = self.extract_features(description)
            X_features.append(list(features.values()))
        
        X_features = np.array(X_features)
        
        # Combinar features textuais e específicas
        X = np.hstack([X_text.toarray(), X_features])
        
        # Obter nomes das features
        text_features = self.vectorizer.get_feature_names_out()
        specific_features = list(self.extract_features("").keys())
        feature_names = list(text_features) + specific_features
        
        return X, np.array(ncm_codes), feature_names
    
    def train_model(self, test_size: float = 0.2) -> NCMTrainingResult:
        """
        Treina o modelo NCM
        
        Args:
            test_size: Proporção dos dados para teste
            
        Returns:
            Resultado do treinamento
        """
        if len(self.training_data) < 10:
            raise ValueError("Poucos dados de treinamento. Mínimo 10 exemplos necessários.")
        
        # Preparar dados
        X, y, feature_names = self.prepare_training_data()
        
        # Dividir em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Treinar modelo
        logger.info("Iniciando treinamento do modelo NCM...")
        self.classifier.fit(X_train, y_train)
        
        # Avaliar modelo
        train_pred = self.classifier.predict(X_train)
        test_pred = self.classifier.predict(X_test)
        
        train_accuracy = accuracy_score(y_train, train_pred)
        test_accuracy = accuracy_score(y_test, test_pred)
        
        # Feature importance
        feature_importance = dict(zip(feature_names, self.classifier.feature_importances_))
        
        # Confusion matrix (simplificada)
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_test, test_pred)
        
        result = NCMTrainingResult(
            model_accuracy=train_accuracy,
            test_accuracy=test_accuracy,
            feature_importance=feature_importance,
            confusion_matrix=cm.tolist(),
            training_samples=len(X_train),
            validation_samples=len(X_test)
        )
        
        logger.info(f"Treinamento concluído - Acurácia: {test_accuracy:.3f}")
        
        return result
    
    def predict_ncm(self, description: str) -> Dict[str, Any]:
        """
        Prediz código NCM para descrição
        
        Args:
            description: Descrição do produto
            
        Returns:
            Predição com confiança
        """
        if not hasattr(self.classifier, 'classes_'):
            raise ValueError("Modelo não foi treinado ainda")
        
        # Preparar features
        X_text = self.vectorizer.transform([description])
        features = self.extract_features(description)
        X_features = np.array([list(features.values())])
        X = np.hstack([X_text.toarray(), X_features])
        
        # Predição
        prediction = self.classifier.predict(X)[0]
        probabilities = self.classifier.predict_proba(X)[0]
        
        # Encontrar confiança
        confidence = max(probabilities)
        
        # Top 3 predições
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top_predictions = [
            {
                'ncm': self.classifier.classes_[idx],
                'confidence': float(probabilities[idx])
            }
            for idx in top_indices
        ]
        
        return {
            'predicted_ncm': prediction,
            'confidence': float(confidence),
            'top_predictions': top_predictions,
            'features_used': len(features)
        }
    
    def save_model(self, file_path: str):
        """Salva modelo treinado"""
        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'training_data': self.training_data,
            'brazilian_features': self.brazilian_features
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Modelo salvo em {file_path}")
    
    def load_model(self, file_path: str):
        """Carrega modelo treinado"""
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vectorizer = model_data['vectorizer']
        self.classifier = model_data['classifier']
        self.training_data = model_data['training_data']
        self.brazilian_features = model_data['brazilian_features']
        
        logger.info(f"Modelo carregado de {file_path}")
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do treinamento"""
        if not self.training_data:
            return {}
        
        # Estatísticas por fonte
        sources = {}
        for item in self.training_data:
            source = item.source
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
        
        # Estatísticas por categoria
        categories = {}
        for item in self.training_data:
            if item.category:
                if item.category not in categories:
                    categories[item.category] = 0
                categories[item.category] += 1
        
        return {
            'total_samples': len(self.training_data),
            'sources': sources,
            'categories': categories,
            'validated_samples': sum(1 for item in self.training_data if item.validated),
            'avg_confidence': sum(item.confidence for item in self.training_data) / len(self.training_data)
        }


# Instância global do treinador
_trainer_instance: Optional[BrazilianNCMTrainer] = None

def get_brazilian_trainer() -> BrazilianNCMTrainer:
    """Retorna instância global do treinador"""
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = BrazilianNCMTrainer()
    return _trainer_instance

def train_brazilian_ncm_model() -> NCMTrainingResult:
    """Função de conveniência para treinar modelo"""
    return get_brazilian_trainer().train_model()

def predict_brazilian_ncm(description: str) -> Dict[str, Any]:
    """Função de conveniência para predição"""
    return get_brazilian_trainer().predict_ncm(description)
