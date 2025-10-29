"""
FiscalAI MVP - Sistema de Feedback Loop
Aprende com correções para melhorar acurácia
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from pathlib import Path
import numpy as np
from collections import defaultdict, Counter
import pickle

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    """Entrada de feedback"""
    id: str
    original_description: str
    predicted_ncm: str
    correct_ncm: str
    confidence: float
    user_id: str
    feedback_type: str  # 'correction', 'validation', 'rejection'
    timestamp: datetime
    context: Dict[str, Any]
    learning_weight: float = 1.0

@dataclass
class LearningPattern:
    """Padrão de aprendizado identificado"""
    pattern_id: str
    description_pattern: str
    correct_ncm: str
    confidence: float
    frequency: int
    last_seen: datetime
    examples: List[str]

@dataclass
class ModelImprovement:
    """Melhoria identificada no modelo"""
    improvement_type: str
    description: str
    impact_score: float
    affected_patterns: List[str]
    suggested_actions: List[str]

class FeedbackLoopSystem:
    """
    Sistema de feedback loop para aprendizado contínuo
    
    Funcionalidades:
    - Coleta de feedback de usuários
    - Identificação de padrões de erro
    - Aprendizado adaptativo
    - Sugestões de melhoria
    - Métricas de aprendizado
    """
    
    def __init__(self, feedback_dir: str = "feedback_data"):
        """
        Inicializa o sistema de feedback loop
        
        Args:
            feedback_dir: Diretório para armazenar dados de feedback
        """
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        # Armazenamento de feedback
        self.feedback_entries: List[FeedbackEntry] = []
        self.learning_patterns: List[LearningPattern] = []
        self.model_improvements: List[ModelImprovement] = []
        
        # Métricas de aprendizado
        self.learning_metrics = {
            'total_feedback': 0,
            'corrections': 0,
            'validations': 0,
            'rejections': 0,
            'patterns_identified': 0,
            'accuracy_improvement': 0.0
        }
        
        # Carregar dados existentes
        self._load_feedback_data()
    
    def add_feedback(self, 
                    original_description: str,
                    predicted_ncm: str,
                    correct_ncm: str,
                    confidence: float,
                    user_id: str,
                    feedback_type: str,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """
        Adiciona entrada de feedback
        
        Args:
            original_description: Descrição original do produto
            predicted_ncm: NCM predito pelo modelo
            correct_ncm: NCM correto
            confidence: Confiança da predição
            user_id: ID do usuário
            feedback_type: Tipo de feedback
            context: Contexto adicional
            
        Returns:
            ID da entrada de feedback
        """
        feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.feedback_entries)}"
        
        entry = FeedbackEntry(
            id=feedback_id,
            original_description=original_description,
            predicted_ncm=predicted_ncm,
            correct_ncm=correct_ncm,
            confidence=confidence,
            user_id=user_id,
            feedback_type=feedback_type,
            timestamp=datetime.now(),
            context=context or {},
            learning_weight=self._calculate_learning_weight(feedback_type, confidence)
        )
        
        self.feedback_entries.append(entry)
        self.learning_metrics['total_feedback'] += 1
        self.learning_metrics[feedback_type + 's'] += 1
        
        # Processar feedback para aprendizado
        self._process_feedback_for_learning(entry)
        
        # Salvar dados
        self._save_feedback_data()
        
        logger.info(f"Feedback adicionado: {feedback_id}")
        return feedback_id
    
    def _calculate_learning_weight(self, feedback_type: str, confidence: float) -> float:
        """
        Calcula peso de aprendizado baseado no tipo de feedback
        
        Args:
            feedback_type: Tipo de feedback
            confidence: Confiança da predição
            
        Returns:
            Peso de aprendizado
        """
        base_weights = {
            'correction': 1.0,  # Correção tem peso alto
            'validation': 0.8,  # Validação tem peso médio
            'rejection': 0.6    # Rejeição tem peso baixo
        }
        
        base_weight = base_weights.get(feedback_type, 0.5)
        
        # Ajustar peso baseado na confiança
        # Se confiança alta mas feedback negativo, peso maior
        if feedback_type == 'correction' and confidence > 0.8:
            return base_weight * 1.5
        elif feedback_type == 'validation' and confidence > 0.9:
            return base_weight * 1.2
        
        return base_weight
    
    def _process_feedback_for_learning(self, entry: FeedbackEntry):
        """
        Processa feedback para identificar padrões de aprendizado
        
        Args:
            entry: Entrada de feedback
        """
        # Identificar padrões de erro
        if entry.feedback_type == 'correction':
            self._identify_error_patterns(entry)
        
        # Identificar padrões de sucesso
        elif entry.feedback_type == 'validation':
            self._identify_success_patterns(entry)
        
        # Analisar padrões gerais
        self._analyze_learning_patterns()
    
    def _identify_error_patterns(self, entry: FeedbackEntry):
        """
        Identifica padrões de erro
        
        Args:
            entry: Entrada de feedback
        """
        # Extrair palavras-chave da descrição
        words = entry.original_description.lower().split()
        
        # Procurar padrões similares
        for pattern in self.learning_patterns:
            if pattern.correct_ncm == entry.correct_ncm:
                # Verificar similaridade
                common_words = set(words) & set(pattern.description_pattern.lower().split())
                if len(common_words) >= 2:  # Pelo menos 2 palavras em comum
                    pattern.frequency += 1
                    pattern.last_seen = entry.timestamp
                    pattern.examples.append(entry.original_description)
                    return
        
        # Criar novo padrão
        new_pattern = LearningPattern(
            pattern_id=f"pattern_{len(self.learning_patterns)}",
            description_pattern=entry.original_description,
            correct_ncm=entry.correct_ncm,
            confidence=entry.confidence,
            frequency=1,
            last_seen=entry.timestamp,
            examples=[entry.original_description]
        )
        
        self.learning_patterns.append(new_pattern)
        self.learning_metrics['patterns_identified'] += 1
    
    def _identify_success_patterns(self, entry: FeedbackEntry):
        """
        Identifica padrões de sucesso
        
        Args:
            entry: Entrada de feedback
        """
        # Procurar padrão existente
        for pattern in self.learning_patterns:
            if pattern.correct_ncm == entry.predicted_ncm:
                # Verificar similaridade
                words = entry.original_description.lower().split()
                pattern_words = pattern.description_pattern.lower().split()
                common_words = set(words) & set(pattern_words)
                
                if len(common_words) >= 2:
                    pattern.frequency += 1
                    pattern.confidence = (pattern.confidence + entry.confidence) / 2
                    pattern.last_seen = entry.timestamp
                    pattern.examples.append(entry.original_description)
                    return
    
    def _analyze_learning_patterns(self):
        """
        Analisa padrões de aprendizado para identificar melhorias
        """
        # Analisar frequência de erros por NCM
        error_counts = defaultdict(int)
        for entry in self.feedback_entries:
            if entry.feedback_type == 'correction':
                error_counts[entry.predicted_ncm] += 1
        
        # Identificar NCMs com muitos erros
        high_error_ncms = [ncm for ncm, count in error_counts.items() if count >= 3]
        
        for ncm in high_error_ncms:
            improvement = ModelImprovement(
                improvement_type="high_error_ncm",
                description=f"NCM {ncm} tem {error_counts[ncm]} correções",
                impact_score=error_counts[ncm] / len(self.feedback_entries),
                affected_patterns=[ncm],
                suggested_actions=[
                    f"Revisar regras para NCM {ncm}",
                    "Adicionar mais exemplos de treinamento",
                    "Ajustar pesos do modelo"
                ]
            )
            self.model_improvements.append(improvement)
        
        # Analisar padrões de confiança
        low_confidence_entries = [e for e in self.feedback_entries if e.confidence < 0.7]
        if len(low_confidence_entries) > len(self.feedback_entries) * 0.3:
            improvement = ModelImprovement(
                improvement_type="low_confidence",
                description="Muitas predições com baixa confiança",
                impact_score=0.5,
                affected_patterns=[],
                suggested_actions=[
                    "Melhorar qualidade dos dados de treinamento",
                    "Ajustar thresholds de confiança",
                    "Implementar validação cruzada"
                ]
            )
            self.model_improvements.append(improvement)
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Retorna insights de aprendizado
        
        Returns:
            Insights de aprendizado
        """
        if not self.feedback_entries:
            return {"message": "Nenhum feedback disponível"}
        
        # Estatísticas gerais
        total_feedback = len(self.feedback_entries)
        corrections = len([e for e in self.feedback_entries if e.feedback_type == 'correction'])
        validations = len([e for e in self.feedback_entries if e.feedback_type == 'validation'])
        
        # Análise de precisão
        accuracy_trend = self._calculate_accuracy_trend()
        
        # Padrões mais frequentes
        frequent_patterns = sorted(
            self.learning_patterns,
            key=lambda p: p.frequency,
            reverse=True
        )[:5]
        
        # Melhorias sugeridas
        recent_improvements = [
            imp for imp in self.model_improvements
            if imp.impact_score > 0.3
        ]
        
        return {
            'total_feedback': total_feedback,
            'corrections': corrections,
            'validations': validations,
            'accuracy_trend': accuracy_trend,
            'frequent_patterns': [
                {
                    'pattern_id': p.pattern_id,
                    'description': p.description_pattern[:50] + "...",
                    'correct_ncm': p.correct_ncm,
                    'frequency': p.frequency,
                    'confidence': p.confidence
                }
                for p in frequent_patterns
            ],
            'suggested_improvements': [
                {
                    'type': imp.improvement_type,
                    'description': imp.description,
                    'impact_score': imp.impact_score,
                    'suggested_actions': imp.suggested_actions
                }
                for imp in recent_improvements
            ],
            'learning_metrics': self.learning_metrics
        }
    
    def _calculate_accuracy_trend(self) -> List[float]:
        """
        Calcula tendência de precisão ao longo do tempo
        
        Returns:
            Lista de precisões por período
        """
        # Agrupar feedback por semana
        weekly_feedback = defaultdict(list)
        for entry in self.feedback_entries:
            week = entry.timestamp.strftime('%Y-W%U')
            weekly_feedback[week].append(entry)
        
        # Calcular precisão por semana
        accuracy_trend = []
        for week, entries in sorted(weekly_feedback.items()):
            validations = len([e for e in entries if e.feedback_type == 'validation'])
            corrections = len([e for e in entries if e.feedback_type == 'correction'])
            
            if validations + corrections > 0:
                accuracy = validations / (validations + corrections)
                accuracy_trend.append(accuracy)
        
        return accuracy_trend
    
    def generate_training_recommendations(self) -> List[Dict[str, Any]]:
        """
        Gera recomendações para treinamento
        
        Returns:
            Lista de recomendações
        """
        recommendations = []
        
        # Recomendação baseada em padrões frequentes
        frequent_patterns = [
            p for p in self.learning_patterns
            if p.frequency >= 3
        ]
        
        if frequent_patterns:
            recommendations.append({
                'type': 'pattern_training',
                'priority': 'high',
                'description': f"Identificados {len(frequent_patterns)} padrões frequentes",
                'action': "Adicionar exemplos destes padrões ao conjunto de treinamento",
                'patterns': [p.pattern_id for p in frequent_patterns]
            })
        
        # Recomendação baseada em NCMs problemáticos
        error_ncms = Counter([
            e.predicted_ncm for e in self.feedback_entries
            if e.feedback_type == 'correction'
        ])
        
        problematic_ncms = [ncm for ncm, count in error_ncms.most_common(3) if count >= 2]
        
        if problematic_ncms:
            recommendations.append({
                'type': 'ncm_focus',
                'priority': 'medium',
                'description': f"NCMs com mais erros: {', '.join(problematic_ncms)}",
                'action': "Focar treinamento nestes NCMs específicos",
                'ncms': problematic_ncms
            })
        
        # Recomendação baseada em confiança
        low_confidence_count = len([
            e for e in self.feedback_entries
            if e.confidence < 0.6
        ])
        
        if low_confidence_count > len(self.feedback_entries) * 0.2:
            recommendations.append({
                'type': 'confidence_improvement',
                'priority': 'high',
                'description': f"{low_confidence_count} predições com baixa confiança",
                'action': "Melhorar qualidade dos dados de treinamento",
                'suggestions': [
                    "Adicionar mais exemplos de treinamento",
                    "Implementar validação cruzada",
                    "Ajustar parâmetros do modelo"
                ]
            })
        
        return recommendations
    
    def export_learning_data(self, file_path: str):
        """
        Exporta dados de aprendizado
        
        Args:
            file_path: Caminho do arquivo
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'feedback_entries': [asdict(entry) for entry in self.feedback_entries],
            'learning_patterns': [asdict(pattern) for pattern in self.learning_patterns],
            'model_improvements': [asdict(improvement) for improvement in self.model_improvements],
            'learning_metrics': self.learning_metrics
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dados de aprendizado exportados para {file_path}")
    
    def _load_feedback_data(self):
        """Carrega dados de feedback existentes"""
        feedback_file = self.feedback_dir / "feedback_data.json"
        
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Carregar feedback entries
                for entry_data in data.get('feedback_entries', []):
                    entry = FeedbackEntry(
                        id=entry_data['id'],
                        original_description=entry_data['original_description'],
                        predicted_ncm=entry_data['predicted_ncm'],
                        correct_ncm=entry_data['correct_ncm'],
                        confidence=entry_data['confidence'],
                        user_id=entry_data['user_id'],
                        feedback_type=entry_data['feedback_type'],
                        timestamp=datetime.fromisoformat(entry_data['timestamp']),
                        context=entry_data.get('context', {}),
                        learning_weight=entry_data.get('learning_weight', 1.0)
                    )
                    self.feedback_entries.append(entry)
                
                # Carregar learning patterns
                for pattern_data in data.get('learning_patterns', []):
                    pattern = LearningPattern(
                        pattern_id=pattern_data['pattern_id'],
                        description_pattern=pattern_data['description_pattern'],
                        correct_ncm=pattern_data['correct_ncm'],
                        confidence=pattern_data['confidence'],
                        frequency=pattern_data['frequency'],
                        last_seen=datetime.fromisoformat(pattern_data['last_seen']),
                        examples=pattern_data['examples']
                    )
                    self.learning_patterns.append(pattern)
                
                # Carregar learning metrics
                self.learning_metrics.update(data.get('learning_metrics', {}))
                
                logger.info(f"Carregados {len(self.feedback_entries)} entradas de feedback")
                
            except Exception as e:
                logger.error(f"Erro ao carregar dados de feedback: {e}")
    
    def _save_feedback_data(self):
        """Salva dados de feedback"""
        feedback_file = self.feedback_dir / "feedback_data.json"
        
        data = {
            'exported_at': datetime.now().isoformat(),
            'feedback_entries': [asdict(entry) for entry in self.feedback_entries],
            'learning_patterns': [asdict(pattern) for pattern in self.learning_patterns],
            'model_improvements': [asdict(improvement) for improvement in self.model_improvements],
            'learning_metrics': self.learning_metrics
        }
        
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# Instância global do sistema
_feedback_system_instance: Optional[FeedbackLoopSystem] = None

def get_feedback_system() -> FeedbackLoopSystem:
    """Retorna instância global do sistema de feedback"""
    global _feedback_system_instance
    if _feedback_system_instance is None:
        _feedback_system_instance = FeedbackLoopSystem()
    return _feedback_system_instance

def add_feedback(original_description: str, predicted_ncm: str, correct_ncm: str,
                confidence: float, user_id: str, feedback_type: str,
                context: Optional[Dict[str, Any]] = None) -> str:
    """Função de conveniência para adicionar feedback"""
    return get_feedback_system().add_feedback(
        original_description, predicted_ncm, correct_ncm,
        confidence, user_id, feedback_type, context
    )

def get_learning_insights() -> Dict[str, Any]:
    """Função de conveniência para obter insights"""
    return get_feedback_system().get_learning_insights()
