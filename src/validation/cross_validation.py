"""
FiscalAI MVP - Validação Cruzada com Múltiplos LLMs
Sistema de validação cruzada para melhorar acurácia
"""

import asyncio
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import json
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)

@dataclass
class LLMValidationResult:
    """Resultado de validação de um LLM"""
    llm_name: str
    predicted_ncm: str
    confidence: float
    reasoning: str
    processing_time: float
    success: bool
    error: Optional[str] = None

@dataclass
class CrossValidationResult:
    """Resultado da validação cruzada"""
    item_description: str
    consensus_ncm: str
    consensus_confidence: float
    individual_results: List[LLMValidationResult]
    agreement_level: float
    disagreement_reasons: List[str]
    validation_timestamp: datetime

class CrossValidationEngine:
    """
    Motor de validação cruzada com múltiplos LLMs
    
    Funcionalidades:
    - Validação paralela com múltiplos LLMs
    - Consenso inteligente
    - Detecção de divergências
    - Métricas de confiabilidade
    """
    
    def __init__(self, llm_configs: List[Dict[str, Any]]):
        """
        Inicializa o motor de validação cruzada
        
        Args:
            llm_configs: Lista de configurações de LLMs
        """
        self.llm_configs = llm_configs
        self.validation_history: List[CrossValidationResult] = []
        
        # Configurações de consenso
        self.consensus_threshold = 0.7  # 70% de acordo mínimo
        self.confidence_threshold = 0.8  # Confiança mínima para aceitar
        self.max_processing_time = 30.0  # Timeout em segundos
    
    async def validate_with_multiple_llms(self, 
                                        item_description: str,
                                        context: Optional[Dict[str, Any]] = None) -> CrossValidationResult:
        """
        Valida classificação NCM com múltiplos LLMs
        
        Args:
            item_description: Descrição do item
            context: Contexto adicional
            
        Returns:
            Resultado da validação cruzada
        """
        logger.info(f"Iniciando validação cruzada para: {item_description[:50]}...")
        
        # Executar validação paralela
        tasks = []
        for config in self.llm_configs:
            task = self._validate_with_llm(item_description, config, context)
            tasks.append(task)
        
        # Aguardar todas as validações
        individual_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processar resultados
        valid_results = []
        for i, result in enumerate(individual_results):
            if isinstance(result, Exception):
                logger.error(f"Erro na validação com {self.llm_configs[i]['name']}: {result}")
                valid_results.append(LLMValidationResult(
                    llm_name=self.llm_configs[i]['name'],
                    predicted_ncm="",
                    confidence=0.0,
                    reasoning="Erro na validação",
                    processing_time=0.0,
                    success=False,
                    error=str(result)
                ))
            else:
                valid_results.append(result)
        
        # Calcular consenso
        consensus_result = self._calculate_consensus(valid_results)
        
        # Criar resultado final
        cross_validation_result = CrossValidationResult(
            item_description=item_description,
            consensus_ncm=consensus_result['ncm'],
            consensus_confidence=consensus_result['confidence'],
            individual_results=valid_results,
            agreement_level=consensus_result['agreement'],
            disagreement_reasons=consensus_result['disagreements'],
            validation_timestamp=datetime.now()
        )
        
        # Armazenar histórico
        self.validation_history.append(cross_validation_result)
        
        logger.info(f"Validação cruzada concluída - Consenso: {consensus_result['agreement']:.2f}")
        
        return cross_validation_result
    
    async def _validate_with_llm(self, 
                                description: str, 
                                config: Dict[str, Any],
                                context: Optional[Dict[str, Any]] = None) -> LLMValidationResult:
        """
        Valida com um LLM específico
        
        Args:
            description: Descrição do item
            config: Configuração do LLM
            context: Contexto adicional
            
        Returns:
            Resultado da validação
        """
        start_time = datetime.now()
        
        try:
            # Simular chamada para LLM (implementar conforme necessário)
            result = await self._call_llm(description, config, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return LLMValidationResult(
                llm_name=config['name'],
                predicted_ncm=result['ncm'],
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return LLMValidationResult(
                llm_name=config['name'],
                predicted_ncm="",
                confidence=0.0,
                reasoning="Erro na validação",
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
    
    async def _call_llm(self, description: str, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Chama LLM específico (implementar conforme necessário)
        
        Args:
            description: Descrição do item
            config: Configuração do LLM
            context: Contexto adicional
            
        Returns:
            Resultado do LLM
        """
        # Simulação de chamada para LLM
        # Em implementação real, aqui seria feita a chamada para o LLM específico
        
        await asyncio.sleep(0.1)  # Simular latência
        
        # Simular resultado baseado no tipo de LLM
        if 'gpt' in config['name'].lower():
            return {
                'ncm': '12345678',
                'confidence': 0.85,
                'reasoning': 'Classificação baseada em padrões GPT'
            }
        elif 'claude' in config['name'].lower():
            return {
                'ncm': '12345678',
                'confidence': 0.82,
                'reasoning': 'Análise Claude com foco em contexto'
            }
        elif 'local' in config['name'].lower():
            return {
                'ncm': '87654321',
                'confidence': 0.75,
                'reasoning': 'Modelo local com conhecimento limitado'
            }
        else:
            return {
                'ncm': '11111111',
                'confidence': 0.70,
                'reasoning': 'Classificação genérica'
            }
    
    def _calculate_consensus(self, results: List[LLMValidationResult]) -> Dict[str, Any]:
        """
        Calcula consenso entre os resultados
        
        Args:
            results: Lista de resultados individuais
            
        Returns:
            Resultado do consenso
        """
        # Filtrar apenas resultados válidos
        valid_results = [r for r in results if r.success and r.predicted_ncm]
        
        if not valid_results:
            return {
                'ncm': '',
                'confidence': 0.0,
                'agreement': 0.0,
                'disagreements': ['Nenhum resultado válido']
            }
        
        # Contar votos por NCM
        ncm_votes = {}
        for result in valid_results:
            ncm = result.predicted_ncm
            if ncm not in ncm_votes:
                ncm_votes[ncm] = []
            ncm_votes[ncm].append(result)
        
        # Encontrar NCM com mais votos
        best_ncm = max(ncm_votes.keys(), key=lambda k: len(ncm_votes[k]))
        best_votes = ncm_votes[best_ncm]
        
        # Calcular nível de acordo
        total_votes = len(valid_results)
        agreement = len(best_votes) / total_votes
        
        # Calcular confiança média
        avg_confidence = statistics.mean([r.confidence for r in best_votes])
        
        # Identificar divergências
        disagreements = []
        for ncm, votes in ncm_votes.items():
            if ncm != best_ncm:
                for vote in votes:
                    disagreements.append(f"{vote.llm_name}: {vote.predicted_ncm} ({vote.confidence:.2f})")
        
        return {
            'ncm': best_ncm,
            'confidence': avg_confidence,
            'agreement': agreement,
            'disagreements': disagreements
        }
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de validação"""
        if not self.validation_history:
            return {}
        
        # Estatísticas gerais
        total_validations = len(self.validation_history)
        high_agreement = sum(1 for v in self.validation_history if v.agreement_level >= 0.8)
        medium_agreement = sum(1 for v in self.validation_history if 0.6 <= v.agreement_level < 0.8)
        low_agreement = sum(1 for v in self.validation_history if v.agreement_level < 0.6)
        
        # Estatísticas por LLM
        llm_stats = {}
        for validation in self.validation_history:
            for result in validation.individual_results:
                llm_name = result.llm_name
                if llm_name not in llm_stats:
                    llm_stats[llm_name] = {
                        'total_calls': 0,
                        'successful_calls': 0,
                        'avg_confidence': 0.0,
                        'avg_processing_time': 0.0
                    }
                
                llm_stats[llm_name]['total_calls'] += 1
                if result.success:
                    llm_stats[llm_name]['successful_calls'] += 1
                    llm_stats[llm_name]['avg_confidence'] += result.confidence
                    llm_stats[llm_name]['avg_processing_time'] += result.processing_time
        
        # Calcular médias
        for llm_name, stats in llm_stats.items():
            if stats['successful_calls'] > 0:
                stats['avg_confidence'] /= stats['successful_calls']
                stats['avg_processing_time'] /= stats['successful_calls']
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls']
            else:
                stats['success_rate'] = 0.0
        
        return {
            'total_validations': total_validations,
            'agreement_distribution': {
                'high': high_agreement,
                'medium': medium_agreement,
                'low': low_agreement
            },
            'llm_performance': llm_stats,
            'avg_consensus_confidence': statistics.mean([v.consensus_confidence for v in self.validation_history]),
            'avg_agreement_level': statistics.mean([v.agreement_level for v in self.validation_history])
        }
    
    def export_validation_data(self, file_path: str):
        """Exporta dados de validação"""
        data = {
            'exported_at': datetime.now().isoformat(),
            'configurations': self.llm_configs,
            'validation_history': [
                {
                    'item_description': v.item_description,
                    'consensus_ncm': v.consensus_ncm,
                    'consensus_confidence': v.consensus_confidence,
                    'agreement_level': v.agreement_level,
                    'individual_results': [
                        {
                            'llm_name': r.llm_name,
                            'predicted_ncm': r.predicted_ncm,
                            'confidence': r.confidence,
                            'reasoning': r.reasoning,
                            'processing_time': r.processing_time,
                            'success': r.success
                        }
                        for r in v.individual_results
                    ],
                    'validation_timestamp': v.validation_timestamp.isoformat()
                }
                for v in self.validation_history
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Dados de validação exportados para {file_path}")


class LLMConfigManager:
    """Gerenciador de configurações de LLMs"""
    
    @staticmethod
    def get_default_configs() -> List[Dict[str, Any]]:
        """Retorna configurações padrão de LLMs"""
        return [
            {
                'name': 'GPT-4o',
                'type': 'openai',
                'model': 'gpt-4o',
                'temperature': 0.1,
                'max_tokens': 512,
                'weight': 1.0
            },
            {
                'name': 'GPT-4o-mini',
                'type': 'openai',
                'model': 'gpt-4o-mini',
                'temperature': 0.1,
                'max_tokens': 512,
                'weight': 0.8
            },
            {
                'name': 'Claude-3.5-Sonnet',
                'type': 'anthropic',
                'model': 'claude-3-5-sonnet-20241022',
                'temperature': 0.1,
                'max_tokens': 512,
                'weight': 0.9
            },
            {
                'name': 'Local-Mistral',
                'type': 'local',
                'model': 'mistral-7b-instruct',
                'temperature': 0.1,
                'max_tokens': 512,
                'weight': 0.6
            }
        ]
    
    @staticmethod
    def create_custom_config(name: str, llm_type: str, **kwargs) -> Dict[str, Any]:
        """Cria configuração customizada de LLM"""
        base_config = {
            'name': name,
            'type': llm_type,
            'temperature': 0.1,
            'max_tokens': 512,
            'weight': 1.0
        }
        base_config.update(kwargs)
        return base_config


# Instância global do motor de validação
_validation_engine_instance: Optional[CrossValidationEngine] = None

def get_cross_validation_engine() -> CrossValidationEngine:
    """Retorna instância global do motor de validação"""
    global _validation_engine_instance
    if _validation_engine_instance is None:
        configs = LLMConfigManager.get_default_configs()
        _validation_engine_instance = CrossValidationEngine(configs)
    return _validation_engine_instance

async def validate_ncm_cross_validation(description: str, context: Optional[Dict[str, Any]] = None) -> CrossValidationResult:
    """Função de conveniência para validação cruzada"""
    engine = get_cross_validation_engine()
    return await engine.validate_with_multiple_llms(description, context)
