"""
FiscalAI MVP - Análise Temporal
Detecção de padrões históricos e anomalias temporais
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

@dataclass
class TemporalPattern:
    """Padrão temporal identificado"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    confidence: float
    time_range: Tuple[datetime, datetime]
    affected_entities: List[str]
    anomaly_score: float

@dataclass
class TemporalAnomaly:
    """Anomalia temporal detectada"""
    anomaly_id: str
    timestamp: datetime
    anomaly_type: str
    severity: str
    description: str
    affected_metrics: List[str]
    anomaly_score: float
    context: Dict[str, Any]

@dataclass
class SeasonalPattern:
    """Padrão sazonal"""
    pattern_id: str
    season_type: str  # 'daily', 'weekly', 'monthly', 'yearly'
    pattern_data: Dict[str, float]
    confidence: float
    start_date: datetime
    end_date: datetime

class TemporalAnalysisEngine:
    """
    Motor de análise temporal para detecção de padrões históricos
    
    Funcionalidades:
    - Detecção de padrões sazonais
    - Análise de tendências
    - Detecção de anomalias temporais
    - Previsão de comportamentos
    - Análise de correlações temporais
    """
    
    def __init__(self, data_dir: str = "temporal_data"):
        """
        Inicializa o motor de análise temporal
        
        Args:
            data_dir: Diretório para armazenar dados temporais
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Dados temporais
        self.temporal_data: List[Dict[str, Any]] = []
        self.patterns: List[TemporalPattern] = []
        self.anomalies: List[TemporalAnomaly] = []
        self.seasonal_patterns: List[SeasonalPattern] = []
        
        # Configurações
        self.anomaly_threshold = 0.7
        self.pattern_min_frequency = 3
        self.seasonal_confidence_threshold = 0.6
        
        # Carregar dados existentes
        self._load_temporal_data()
    
    def add_temporal_data(self, 
                         timestamp: datetime,
                         entity_id: str,
                         metrics: Dict[str, float],
                         context: Optional[Dict[str, Any]] = None):
        """
        Adiciona dados temporais
        
        Args:
            timestamp: Timestamp do evento
            entity_id: ID da entidade (CNPJ, produto, etc.)
            metrics: Métricas do evento
            context: Contexto adicional
        """
        data_point = {
            'timestamp': timestamp,
            'entity_id': entity_id,
            'metrics': metrics,
            'context': context or {}
        }
        
        self.temporal_data.append(data_point)
        logger.debug(f"Dados temporais adicionados: {entity_id} em {timestamp}")
    
    def detect_temporal_patterns(self) -> List[TemporalPattern]:
        """
        Detecta padrões temporais nos dados
        
        Returns:
            Lista de padrões detectados
        """
        if len(self.temporal_data) < 10:
            logger.warning("Poucos dados para detectar padrões temporais")
            return []
        
        # Converter para DataFrame
        df = self._prepare_dataframe()
        
        # Detectar padrões por tipo
        patterns = []
        
        # Padrões de frequência
        frequency_patterns = self._detect_frequency_patterns(df)
        patterns.extend(frequency_patterns)
        
        # Padrões de valor
        value_patterns = self._detect_value_patterns(df)
        patterns.extend(value_patterns)
        
        # Padrões de comportamento
        behavior_patterns = self._detect_behavior_patterns(df)
        patterns.extend(behavior_patterns)
        
        # Padrões de correlação
        correlation_patterns = self._detect_correlation_patterns(df)
        patterns.extend(correlation_patterns)
        
        self.patterns.extend(patterns)
        logger.info(f"Detectados {len(patterns)} padrões temporais")
        
        return patterns
    
    def detect_temporal_anomalies(self) -> List[TemporalAnomaly]:
        """
        Detecta anomalias temporais
        
        Returns:
            Lista de anomalias detectadas
        """
        if len(self.temporal_data) < 20:
            logger.warning("Poucos dados para detectar anomalias temporais")
            return []
        
        # Converter para DataFrame
        df = self._prepare_dataframe()
        
        anomalies = []
        
        # Anomalias estatísticas
        statistical_anomalies = self._detect_statistical_anomalies(df)
        anomalies.extend(statistical_anomalies)
        
        # Anomalias de comportamento
        behavior_anomalies = self._detect_behavior_anomalies(df)
        anomalies.extend(behavior_anomalies)
        
        # Anomalias sazonais
        seasonal_anomalies = self._detect_seasonal_anomalies(df)
        anomalies.extend(seasonal_anomalies)
        
        self.anomalies.extend(anomalies)
        logger.info(f"Detectadas {len(anomalies)} anomalias temporais")
        
        return anomalies
    
    def detect_seasonal_patterns(self) -> List[SeasonalPattern]:
        """
        Detecta padrões sazonais
        
        Returns:
            Lista de padrões sazonais
        """
        if len(self.temporal_data) < 30:
            logger.warning("Poucos dados para detectar padrões sazonais")
            return []
        
        # Converter para DataFrame
        df = self._prepare_dataframe()
        
        seasonal_patterns = []
        
        # Padrões diários
        daily_patterns = self._detect_daily_patterns(df)
        seasonal_patterns.extend(daily_patterns)
        
        # Padrões semanais
        weekly_patterns = self._detect_weekly_patterns(df)
        seasonal_patterns.extend(weekly_patterns)
        
        # Padrões mensais
        monthly_patterns = self._detect_monthly_patterns(df)
        seasonal_patterns.extend(monthly_patterns)
        
        self.seasonal_patterns.extend(seasonal_patterns)
        logger.info(f"Detectados {len(seasonal_patterns)} padrões sazonais")
        
        return seasonal_patterns
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """Prepara DataFrame para análise"""
        data = []
        for point in self.temporal_data:
            row = {
                'timestamp': point['timestamp'],
                'entity_id': point['entity_id']
            }
            row.update(point['metrics'])
            data.append(row)
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        return df
    
    def _detect_frequency_patterns(self, df: pd.DataFrame) -> List[TemporalPattern]:
        """Detecta padrões de frequência"""
        patterns = []
        
        # Agrupar por entidade e período
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        # Padrões de frequência por hora
        hourly_freq = df.groupby(['entity_id', 'hour']).size()
        for (entity, hour), count in hourly_freq.items():
            if count >= self.pattern_min_frequency:
                pattern = TemporalPattern(
                    pattern_id=f"freq_hourly_{entity}_{hour}",
                    pattern_type="frequency_hourly",
                    description=f"Entidade {entity} ativa {count} vezes na hora {hour}",
                    frequency=count,
                    confidence=min(count / 10, 1.0),
                    time_range=(df['timestamp'].min(), df['timestamp'].max()),
                    affected_entities=[entity],
                    anomaly_score=0.0
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_value_patterns(self, df: pd.DataFrame) -> List[TemporalPattern]:
        """Detecta padrões de valor"""
        patterns = []
        
        # Padrões de valor por entidade
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            # Calcular estatísticas
            numeric_cols = entity_data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col == 'timestamp':
                    continue
                
                values = entity_data[col].dropna()
                if len(values) < 3:
                    continue
                
                mean_val = values.mean()
                std_val = values.std()
                
                # Detectar valores consistentemente altos/baixos
                if std_val < mean_val * 0.1:  # Baixa variância
                    pattern = TemporalPattern(
                        pattern_id=f"value_consistent_{entity}_{col}",
                        pattern_type="value_consistent",
                        description=f"Entidade {entity} tem valores consistentes em {col}",
                        frequency=len(values),
                        confidence=0.8,
                        time_range=(entity_data['timestamp'].min(), entity_data['timestamp'].max()),
                        affected_entities=[entity],
                        anomaly_score=0.0
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_behavior_patterns(self, df: pd.DataFrame) -> List[TemporalPattern]:
        """Detecta padrões de comportamento"""
        patterns = []
        
        # Padrões de comportamento por entidade
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            # Calcular intervalos entre transações
            entity_data = entity_data.sort_values('timestamp')
            intervals = entity_data['timestamp'].diff().dt.total_seconds() / 3600  # em horas
            
            # Detectar padrões de intervalo
            if len(intervals) > 2:
                mean_interval = intervals.mean()
                std_interval = intervals.std()
                
                if std_interval < mean_interval * 0.3:  # Intervalos consistentes
                    pattern = TemporalPattern(
                        pattern_id=f"behavior_interval_{entity}",
                        pattern_type="behavior_interval",
                        description=f"Entidade {entity} tem intervalos consistentes entre transações",
                        frequency=len(intervals),
                        confidence=0.7,
                        time_range=(entity_data['timestamp'].min(), entity_data['timestamp'].max()),
                        affected_entities=[entity],
                        anomaly_score=0.0
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_correlation_patterns(self, df: pd.DataFrame) -> List[TemporalPattern]:
        """Detecta padrões de correlação"""
        patterns = []
        
        # Calcular correlações entre métricas
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return patterns
        
        correlation_matrix = df[numeric_cols].corr()
        
        # Encontrar correlações fortes
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                col1 = correlation_matrix.columns[i]
                col2 = correlation_matrix.columns[j]
                corr = correlation_matrix.iloc[i, j]
                
                if abs(corr) > 0.7:  # Correlação forte
                    pattern = TemporalPattern(
                        pattern_id=f"correlation_{col1}_{col2}",
                        pattern_type="correlation",
                        description=f"Correlação forte entre {col1} e {col2}: {corr:.3f}",
                        frequency=len(df),
                        confidence=abs(corr),
                        time_range=(df['timestamp'].min(), df['timestamp'].max()),
                        affected_entities=[],
                        anomaly_score=0.0
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_statistical_anomalies(self, df: pd.DataFrame) -> List[TemporalAnomaly]:
        """Detecta anomalias estatísticas"""
        anomalies = []
        
        # Usar Isolation Forest para detectar anomalias
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return anomalies
        
        # Preparar dados
        X = df[numeric_cols].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Aplicar Isolation Forest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        anomaly_labels = iso_forest.fit_predict(X_scaled)
        
        # Identificar anomalias
        for idx, label in enumerate(anomaly_labels):
            if label == -1:  # Anomalia detectada
                anomaly = TemporalAnomaly(
                    anomaly_id=f"statistical_{idx}",
                    timestamp=df.iloc[idx]['timestamp'],
                    anomaly_type="statistical",
                    severity="medium",
                    description="Anomalia estatística detectada",
                    affected_metrics=list(numeric_cols),
                    anomaly_score=abs(iso_forest.score_samples(X_scaled[idx:idx+1])[0]),
                    context={'entity_id': df.iloc[idx]['entity_id']}
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_behavior_anomalies(self, df: pd.DataFrame) -> List[TemporalAnomaly]:
        """Detecta anomalias de comportamento"""
        anomalies = []
        
        # Anomalias de frequência
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            if len(entity_data) < 5:
                continue
            
            # Calcular frequência por dia
            daily_freq = entity_data.groupby(entity_data['timestamp'].dt.date).size()
            
            # Detectar dias com frequência anômala
            mean_freq = daily_freq.mean()
            std_freq = daily_freq.std()
            
            for date, freq in daily_freq.items():
                if abs(freq - mean_freq) > 2 * std_freq:
                    anomaly = TemporalAnomaly(
                        anomaly_id=f"behavior_freq_{entity}_{date}",
                        timestamp=datetime.combine(date, datetime.min.time()),
                        anomaly_type="behavior_frequency",
                        severity="medium",
                        description=f"Frequência anômala para {entity} em {date}",
                        affected_metrics=['frequency'],
                        anomaly_score=abs(freq - mean_freq) / std_freq,
                        context={'entity_id': entity, 'frequency': freq}
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_seasonal_anomalies(self, df: pd.DataFrame) -> List[TemporalAnomaly]:
        """Detecta anomalias sazonais"""
        anomalies = []
        
        # Anomalias por dia da semana
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['hour'] = df['timestamp'].dt.hour
        
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            if len(entity_data) < 10:
                continue
            
            # Calcular padrão normal por dia da semana
            weekday_pattern = entity_data.groupby('day_of_week').size()
            
            # Detectar desvios do padrão
            for day, count in weekday_pattern.items():
                expected_count = weekday_pattern.mean()
                if abs(count - expected_count) > expected_count * 0.5:
                    anomaly = TemporalAnomaly(
                        anomaly_id=f"seasonal_weekday_{entity}_{day}",
                        timestamp=entity_data[entity_data['day_of_week'] == day]['timestamp'].iloc[0],
                        anomaly_type="seasonal_weekday",
                        severity="low",
                        description=f"Atividade anômala para {entity} na {day}",
                        affected_metrics=['frequency'],
                        anomaly_score=abs(count - expected_count) / expected_count,
                        context={'entity_id': entity, 'day_of_week': day}
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_daily_patterns(self, df: pd.DataFrame) -> List[SeasonalPattern]:
        """Detecta padrões diários"""
        patterns = []
        
        # Padrões por hora do dia
        df['hour'] = df['timestamp'].dt.hour
        
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            if len(entity_data) < 7:  # Pelo menos uma semana
                continue
            
            # Calcular atividade por hora
            hourly_activity = entity_data.groupby('hour').size()
            
            if len(hourly_activity) > 0:
                pattern_data = {str(hour): count for hour, count in hourly_activity.items()}
                
                pattern = SeasonalPattern(
                    pattern_id=f"daily_{entity}",
                    season_type="daily",
                    pattern_data=pattern_data,
                    confidence=0.8,
                    start_date=entity_data['timestamp'].min(),
                    end_date=entity_data['timestamp'].max()
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_weekly_patterns(self, df: pd.DataFrame) -> List[SeasonalPattern]:
        """Detecta padrões semanais"""
        patterns = []
        
        # Padrões por dia da semana
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            if len(entity_data) < 14:  # Pelo menos duas semanas
                continue
            
            # Calcular atividade por dia da semana
            weekday_activity = entity_data.groupby('day_of_week').size()
            
            if len(weekday_activity) > 0:
                pattern_data = {str(day): count for day, count in weekday_activity.items()}
                
                pattern = SeasonalPattern(
                    pattern_id=f"weekly_{entity}",
                    season_type="weekly",
                    pattern_data=pattern_data,
                    confidence=0.7,
                    start_date=entity_data['timestamp'].min(),
                    end_date=entity_data['timestamp'].max()
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_monthly_patterns(self, df: pd.DataFrame) -> List[SeasonalPattern]:
        """Detecta padrões mensais"""
        patterns = []
        
        # Padrões por mês
        df['month'] = df['timestamp'].dt.month
        
        for entity in df['entity_id'].unique():
            entity_data = df[df['entity_id'] == entity]
            
            if len(entity_data) < 30:  # Pelo menos um mês
                continue
            
            # Calcular atividade por mês
            monthly_activity = entity_data.groupby('month').size()
            
            if len(monthly_activity) > 0:
                pattern_data = {str(month): count for month, count in monthly_activity.items()}
                
                pattern = SeasonalPattern(
                    pattern_id=f"monthly_{entity}",
                    season_type="monthly",
                    pattern_data=pattern_data,
                    confidence=0.6,
                    start_date=entity_data['timestamp'].min(),
                    end_date=entity_data['timestamp'].max()
                )
                patterns.append(pattern)
        
        return patterns
    
    def get_temporal_insights(self) -> Dict[str, Any]:
        """
        Retorna insights temporais
        
        Returns:
            Insights temporais
        """
        return {
            'total_data_points': len(self.temporal_data),
            'patterns_detected': len(self.patterns),
            'anomalies_detected': len(self.anomalies),
            'seasonal_patterns': len(self.seasonal_patterns),
            'pattern_types': Counter([p.pattern_type for p in self.patterns]),
            'anomaly_types': Counter([a.anomaly_type for a in self.anomalies]),
            'seasonal_types': Counter([s.season_type for s in self.seasonal_patterns]),
            'high_confidence_patterns': len([p for p in self.patterns if p.confidence > 0.8]),
            'high_severity_anomalies': len([a for a in self.anomalies if a.severity in ['high', 'critical']])
        }
    
    def export_temporal_data(self, file_path: str):
        """
        Exporta dados temporais
        
        Args:
            file_path: Caminho do arquivo
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'temporal_data': self.temporal_data,
            'patterns': [
                {
                    'pattern_id': p.pattern_id,
                    'pattern_type': p.pattern_type,
                    'description': p.description,
                    'frequency': p.frequency,
                    'confidence': p.confidence,
                    'time_range': [p.time_range[0].isoformat(), p.time_range[1].isoformat()],
                    'affected_entities': p.affected_entities,
                    'anomaly_score': p.anomaly_score
                }
                for p in self.patterns
            ],
            'anomalies': [
                {
                    'anomaly_id': a.anomaly_id,
                    'timestamp': a.timestamp.isoformat(),
                    'anomaly_type': a.anomaly_type,
                    'severity': a.severity,
                    'description': a.description,
                    'affected_metrics': a.affected_metrics,
                    'anomaly_score': a.anomaly_score,
                    'context': a.context
                }
                for a in self.anomalies
            ],
            'seasonal_patterns': [
                {
                    'pattern_id': s.pattern_id,
                    'season_type': s.season_type,
                    'pattern_data': s.pattern_data,
                    'confidence': s.confidence,
                    'start_date': s.start_date.isoformat(),
                    'end_date': s.end_date.isoformat()
                }
                for s in self.seasonal_patterns
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dados temporais exportados para {file_path}")
    
    def _load_temporal_data(self):
        """Carrega dados temporais existentes"""
        data_file = self.data_dir / "temporal_data.json"
        
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.temporal_data = data.get('temporal_data', [])
                
                # Carregar padrões
                for pattern_data in data.get('patterns', []):
                    pattern = TemporalPattern(
                        pattern_id=pattern_data['pattern_id'],
                        pattern_type=pattern_data['pattern_type'],
                        description=pattern_data['description'],
                        frequency=pattern_data['frequency'],
                        confidence=pattern_data['confidence'],
                        time_range=(
                            datetime.fromisoformat(pattern_data['time_range'][0]),
                            datetime.fromisoformat(pattern_data['time_range'][1])
                        ),
                        affected_entities=pattern_data['affected_entities'],
                        anomaly_score=pattern_data['anomaly_score']
                    )
                    self.patterns.append(pattern)
                
                logger.info(f"Carregados {len(self.temporal_data)} pontos de dados temporais")
                
            except Exception as e:
                logger.error(f"Erro ao carregar dados temporais: {e}")
    
    def save_temporal_data(self):
        """Salva dados temporais"""
        data_file = self.data_dir / "temporal_data.json"
        
        data = {
            'exported_at': datetime.now().isoformat(),
            'temporal_data': self.temporal_data,
            'patterns': [
                {
                    'pattern_id': p.pattern_id,
                    'pattern_type': p.pattern_type,
                    'description': p.description,
                    'frequency': p.frequency,
                    'confidence': p.confidence,
                    'time_range': [p.time_range[0].isoformat(), p.time_range[1].isoformat()],
                    'affected_entities': p.affected_entities,
                    'anomaly_score': p.anomaly_score
                }
                for p in self.patterns
            ]
        }
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# Instância global do motor de análise temporal
_temporal_analysis_instance: Optional[TemporalAnalysisEngine] = None

def get_temporal_analysis_engine() -> TemporalAnalysisEngine:
    """Retorna instância global do motor de análise temporal"""
    global _temporal_analysis_instance
    if _temporal_analysis_instance is None:
        _temporal_analysis_instance = TemporalAnalysisEngine()
    return _temporal_analysis_instance

def add_temporal_data(timestamp: datetime, entity_id: str, metrics: Dict[str, float], context: Optional[Dict[str, Any]] = None):
    """Função de conveniência para adicionar dados temporais"""
    get_temporal_analysis_engine().add_temporal_data(timestamp, entity_id, metrics, context)

def detect_temporal_patterns() -> List[TemporalPattern]:
    """Função de conveniência para detectar padrões temporais"""
    return get_temporal_analysis_engine().detect_temporal_patterns()
