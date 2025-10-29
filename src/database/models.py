"""
FiscalAI MVP - Database Models
SQLAlchemy models for persistent storage
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from typing import Optional, Dict, Any
import json

Base = declarative_base()


class AnalysisRecord(Base):
    """Registro de análise de NF-e"""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), unique=True, index=True)  # UUID
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Dados da NF-e
    nfe_number = Column(String(50))
    nfe_key = Column(String(50), index=True)
    nfe_date = Column(DateTime)
    issuer_cnpj = Column(String(20), index=True)
    issuer_name = Column(String(255))
    recipient_cnpj = Column(String(20), index=True)
    recipient_name = Column(String(255))
    total_value = Column(Float)
    items_count = Column(Integer)
    
    # Resultados da análise
    risk_score = Column(Integer)
    risk_level = Column(String(20))
    frauds_detected = Column(Integer, default=0)
    processing_time = Column(Float)
    
    # Dados completos (JSON)
    nfe_data = Column(JSON)
    classifications = Column(JSON)
    fraud_analysis = Column(JSON)
    recommendations = Column(JSON)
    
    # Status
    status = Column(String(20), default="completed")
    error_message = Column(Text)
    
    # Relacionamentos
    frauds = relationship("FraudRecord", back_populates="analysis")
    classifications_records = relationship("ClassificationRecord", back_populates="analysis")


class FraudRecord(Base):
    """Registro de fraude detectada"""
    __tablename__ = "frauds"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.analysis_id"))
    fraud_type = Column(String(50))
    score = Column(Integer)
    description = Column(Text)
    evidence = Column(Text)
    item_id = Column(Integer)  # ID do item da NF-e
    
    # Relacionamento
    analysis = relationship("AnalysisRecord", back_populates="frauds")


class ClassificationRecord(Base):
    """Registro de classificação NCM"""
    __tablename__ = "classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.analysis_id"))
    item_id = Column(Integer)
    product_description = Column(Text)
    declared_ncm = Column(String(20))
    predicted_ncm = Column(String(20))
    confidence = Column(Float)
    justification = Column(Text)
    is_correct = Column(Boolean)
    
    # Relacionamento
    analysis = relationship("AnalysisRecord", back_populates="classifications_records")


class ModelUsageRecord(Base):
    """Registro de uso de modelos LLM"""
    __tablename__ = "model_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), index=True)
    model_name = Column(String(100))
    provider = Column(String(50))
    tokens_used = Column(Integer)
    cost = Column(Float)
    processing_time = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


class SystemStats(Base):
    """Estatísticas do sistema"""
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_analyses = Column(Integer)
    total_frauds_detected = Column(Integer)
    avg_processing_time = Column(Float)
    risk_level_distribution = Column(JSON)
    model_usage_stats = Column(JSON)


# Database Manager
class DatabaseManager:
    """Gerenciador do banco de dados"""
    
    def __init__(self, database_url: str = "sqlite:///./fiscalai.db"):
        """
        Inicializa o gerenciador de banco
        
        Args:
            database_url: URL do banco de dados
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Criar tabelas
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Retorna sessão do banco"""
        return self.SessionLocal()
    
    def save_analysis(self, 
                     analysis_id: str,
                     nfe_data: Dict[str, Any],
                     classifications: Dict[str, Any],
                     fraud_analysis: Dict[str, Any],
                     recommendations: list,
                     processing_time: float,
                     model_name: str = None) -> bool:
        """
        Salva análise no banco de dados
        
        Args:
            analysis_id: ID único da análise
            nfe_data: Dados da NF-e
            classifications: Classificações NCM
            fraud_analysis: Análise de fraudes
            recommendations: Recomendações
            processing_time: Tempo de processamento
            model_name: Nome do modelo usado
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            session = self.get_session()
            
            # Extrair dados da NF-e
            nfe_info = nfe_data.get('nfe', {})
            
            # Criar registro principal
            analysis_record = AnalysisRecord(
                analysis_id=analysis_id,
                nfe_number=nfe_info.get('numero'),
                nfe_key=nfe_info.get('chave_acesso'),
                nfe_date=nfe_info.get('data_emissao'),
                issuer_cnpj=nfe_info.get('cnpj_emitente'),
                issuer_name=nfe_info.get('razao_social_emitente'),
                recipient_cnpj=nfe_info.get('cnpj_destinatario'),
                recipient_name=nfe_info.get('razao_social_destinatario'),
                total_value=nfe_info.get('valor_total'),
                items_count=len(nfe_info.get('itens', [])),
                risk_score=fraud_analysis.get('score_risco'),
                risk_level=fraud_analysis.get('nivel_risco'),
                frauds_detected=len(fraud_analysis.get('fraudes_detectadas', [])),
                processing_time=processing_time,
                nfe_data=nfe_data,
                classifications=classifications,
                fraud_analysis=fraud_analysis,
                recommendations=recommendations,
                status="completed"
            )
            
            session.add(analysis_record)
            
            # Salvar fraudes detectadas
            for fraud in fraud_analysis.get('fraudes_detectadas', []):
                fraud_record = FraudRecord(
                    analysis_id=analysis_id,
                    fraud_type=fraud.get('tipo_fraude'),
                    score=fraud.get('score'),
                    description=fraud.get('descricao'),
                    evidence=fraud.get('evidencias'),
                    item_id=fraud.get('item_id')
                )
                session.add(fraud_record)
            
            # Salvar classificações
            for item_id, classification in classifications.items():
                classification_record = ClassificationRecord(
                    analysis_id=analysis_id,
                    item_id=item_id,
                    product_description=classification.get('descricao_produto'),
                    declared_ncm=classification.get('ncm_declarado'),
                    predicted_ncm=classification.get('ncm_predito'),
                    confidence=classification.get('confianca'),
                    justification=classification.get('justificativa'),
                    is_correct=classification.get('ncm_declarado') == classification.get('ncm_predito')
                )
                session.add(classification_record)
            
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            print(f"Erro ao salvar análise: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False
    
    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera análise por ID
        
        Args:
            analysis_id: ID da análise
            
        Returns:
            Dados da análise ou None
        """
        try:
            session = self.get_session()
            
            analysis = session.query(AnalysisRecord).filter(
                AnalysisRecord.analysis_id == analysis_id
            ).first()
            
            if not analysis:
                return None
            
            result = {
                "analysis_id": analysis.analysis_id,
                "timestamp": analysis.timestamp.isoformat(),
                "nfe_data": analysis.nfe_data,
                "classifications": analysis.classifications,
                "fraud_analysis": analysis.fraud_analysis,
                "recommendations": analysis.recommendations,
                "risk_score": analysis.risk_score,
                "risk_level": analysis.risk_level,
                "processing_time": analysis.processing_time
            }
            
            session.close()
            return result
            
        except Exception as e:
            print(f"Erro ao recuperar análise: {e}")
            return None
    
    def get_analyses_by_cnpj(self, cnpj: str, limit: int = 10) -> list:
        """
        Recupera análises por CNPJ
        
        Args:
            cnpj: CNPJ do emitente ou destinatário
            limit: Limite de resultados
            
        Returns:
            Lista de análises
        """
        try:
            session = self.get_session()
            
            analyses = session.query(AnalysisRecord).filter(
                (AnalysisRecord.issuer_cnpj == cnpj) | 
                (AnalysisRecord.recipient_cnpj == cnpj)
            ).order_by(AnalysisRecord.timestamp.desc()).limit(limit).all()
            
            results = []
            for analysis in analyses:
                results.append({
                    "analysis_id": analysis.analysis_id,
                    "timestamp": analysis.timestamp.isoformat(),
                    "nfe_number": analysis.nfe_number,
                    "risk_score": analysis.risk_score,
                    "risk_level": analysis.risk_level,
                    "frauds_detected": analysis.frauds_detected
                })
            
            session.close()
            return results
            
        except Exception as e:
            print(f"Erro ao recuperar análises por CNPJ: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Recupera estatísticas do sistema
        
        Returns:
            Estatísticas consolidadas
        """
        try:
            session = self.get_session()
            
            # Total de análises
            total_analyses = session.query(AnalysisRecord).count()
            
            # Total de fraudes
            total_frauds = session.query(FraudRecord).count()
            
            # Distribuição por nível de risco
            risk_distribution = {}
            for level in ['baixo', 'medio', 'alto', 'critico']:
                count = session.query(AnalysisRecord).filter(
                    AnalysisRecord.risk_level == level
                ).count()
                risk_distribution[level] = count
            
            # Tempo médio de processamento
            avg_time = session.query(AnalysisRecord).with_entities(
                AnalysisRecord.processing_time
            ).all()
            avg_processing_time = sum(t[0] for t in avg_time if t[0]) / len(avg_time) if avg_time else 0
            
            session.close()
            
            return {
                "total_analyses": total_analyses,
                "total_frauds_detected": total_frauds,
                "risk_level_distribution": risk_distribution,
                "avg_processing_time": avg_processing_time
            }
            
        except Exception as e:
            print(f"Erro ao recuperar estatísticas: {e}")
            return {}


# Instância global do gerenciador
db_manager = DatabaseManager()
