"""
FiscalAI MVP - Regras de Negócio Avançadas
Regras específicas e contextuais para detecção de fraudes
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum
import json

logger = logging.getLogger(__name__)

class RuleType(Enum):
    """Tipos de regras de negócio"""
    PRICE_ANOMALY = "price_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    SUPPLIER_ANOMALY = "supplier_anomaly"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    NCM_ANOMALY = "ncm_anomaly"
    CFOP_ANOMALY = "cfop_anomaly"
    CROSS_REFERENCE = "cross_reference"

@dataclass
class BusinessRule:
    """Regra de negócio"""
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    conditions: List[Dict[str, Any]]
    actions: List[str]
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: float
    enabled: bool
    created_at: datetime
    last_updated: datetime

@dataclass
class RuleExecutionResult:
    """Resultado da execução de regra"""
    rule_id: str
    triggered: bool
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    execution_time: float

class AdvancedBusinessRulesEngine:
    """
    Motor de regras de negócio avançadas
    
    Funcionalidades:
    - Regras contextuais específicas
    - Validação cruzada entre regras
    - Aprendizado de padrões
    - Regras dinâmicas
    """
    
    def __init__(self):
        """Inicializa o motor de regras"""
        self.rules: Dict[str, BusinessRule] = {}
        self.execution_history: List[RuleExecutionResult] = []
        
        # Inicializar regras padrão
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Inicializa regras padrão"""
        # Regra 1: Anomalia de preço por categoria
        self.add_rule(BusinessRule(
            rule_id="price_category_anomaly",
            name="Anomalia de Preço por Categoria",
            description="Detecta preços anômalos baseado na categoria do produto",
            rule_type=RuleType.PRICE_ANOMALY,
            conditions=[
                {"field": "valor_unitario", "operator": ">", "value": "category_avg * 3"},
                {"field": "categoria", "operator": "in", "value": ["eletrônicos", "têxtil", "alimentício"]}
            ],
            actions=["flag_high_price", "request_validation"],
            severity="high",
            confidence=0.8,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 2: Volume suspeito
        self.add_rule(BusinessRule(
            rule_id="suspicious_volume",
            name="Volume Suspeito",
            description="Detecta volumes anômalos que podem indicar fraude",
            rule_type=RuleType.VOLUME_ANOMALY,
            conditions=[
                {"field": "quantidade", "operator": ">", "value": 10000},
                {"field": "valor_unitario", "operator": "<", "value": 1.0}
            ],
            actions=["flag_volume_anomaly", "request_verification"],
            severity="medium",
            confidence=0.7,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 3: Horário suspeito
        self.add_rule(BusinessRule(
            rule_id="suspicious_time",
            name="Horário Suspeito",
            description="Detecta transações em horários suspeitos",
            rule_type=RuleType.TEMPORAL_ANOMALY,
            conditions=[
                {"field": "hora_emissao", "operator": "between", "value": [22, 6]},
                {"field": "valor_total", "operator": ">", "value": 50000}
            ],
            actions=["flag_time_anomaly", "request_review"],
            severity="medium",
            confidence=0.6,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 4: Fornecedor de risco
        self.add_rule(BusinessRule(
            rule_id="risky_supplier",
            name="Fornecedor de Risco",
            description="Detecta transações com fornecedores de alto risco",
            rule_type=RuleType.SUPPLIER_ANOMALY,
            conditions=[
                {"field": "cnpj_emitente", "operator": "in", "value": "risky_suppliers_list"},
                {"field": "valor_total", "operator": ">", "value": 10000}
            ],
            actions=["flag_risky_supplier", "enhanced_verification"],
            severity="high",
            confidence=0.9,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 5: NCM inconsistente
        self.add_rule(BusinessRule(
            rule_id="inconsistent_ncm",
            name="NCM Inconsistente",
            description="Detecta inconsistências entre NCM e descrição do produto",
            rule_type=RuleType.NCM_ANOMALY,
            conditions=[
                {"field": "ncm_declarado", "operator": "not_matches", "value": "ncm_pattern"},
                {"field": "descricao", "operator": "contains", "value": "inconsistent_keywords"}
            ],
            actions=["flag_ncm_inconsistency", "request_ncm_review"],
            severity="high",
            confidence=0.85,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 6: CFOP suspeito
        self.add_rule(BusinessRule(
            rule_id="suspicious_cfop",
            name="CFOP Suspeito",
            description="Detecta uso suspeito de códigos CFOP",
            rule_type=RuleType.CFOP_ANOMALY,
            conditions=[
                {"field": "cfop", "operator": "in", "value": ["1102", "2102"]},
                {"field": "uf_emitente", "operator": "!=", "value": "uf_destinatario"},
                {"field": "valor_total", "operator": ">", "value": 5000}
            ],
            actions=["flag_cfop_anomaly", "verify_operation_type"],
            severity="medium",
            confidence=0.75,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
        
        # Regra 7: Referência cruzada
        self.add_rule(BusinessRule(
            rule_id="cross_reference_check",
            name="Verificação de Referência Cruzada",
            description="Verifica consistência entre diferentes campos",
            rule_type=RuleType.CROSS_REFERENCE,
            conditions=[
                {"field": "valor_total", "operator": "!=", "value": "quantidade * valor_unitario"},
                {"field": "tolerance", "operator": ">", "value": 0.01}
            ],
            actions=["flag_calculation_error", "request_recalculation"],
            severity="high",
            confidence=0.95,
            enabled=True,
            created_at=datetime.now(),
            last_updated=datetime.now()
        ))
    
    def add_rule(self, rule: BusinessRule):
        """
        Adiciona regra de negócio
        
        Args:
            rule: Regra a ser adicionada
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Regra adicionada: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """
        Remove regra de negócio
        
        Args:
            rule_id: ID da regra
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Regra removida: {rule_id}")
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]):
        """
        Atualiza regra de negócio
        
        Args:
            rule_id: ID da regra
            updates: Atualizações a aplicar
        """
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            rule.last_updated = datetime.now()
            logger.info(f"Regra atualizada: {rule_id}")
    
    def execute_rules(self, data: Dict[str, Any]) -> List[RuleExecutionResult]:
        """
        Executa todas as regras habilitadas
        
        Args:
            data: Dados para análise
            
        Returns:
            Lista de resultados de execução
        """
        results = []
        
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                result = self._execute_rule(rule, data)
                results.append(result)
                self.execution_history.append(result)
            except Exception as e:
                logger.error(f"Erro ao executar regra {rule_id}: {e}")
        
        return results
    
    def _execute_rule(self, rule: BusinessRule, data: Dict[str, Any]) -> RuleExecutionResult:
        """
        Executa uma regra específica
        
        Args:
            rule: Regra a executar
            data: Dados para análise
            
        Returns:
            Resultado da execução
        """
        start_time = datetime.now()
        
        # Verificar condições
        triggered = True
        evidence = []
        confidence = rule.confidence
        
        for condition in rule.conditions:
            field = condition['field']
            operator = condition['operator']
            value = condition['value']
            
            if field not in data:
                triggered = False
                break
            
            field_value = data[field]
            
            if not self._evaluate_condition(field_value, operator, value, data):
                triggered = False
                break
            
            evidence.append(f"{field} {operator} {value}")
        
        # Ajustar confiança baseado no contexto
        if triggered:
            confidence = self._adjust_confidence(rule, data, confidence)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return RuleExecutionResult(
            rule_id=rule.rule_id,
            triggered=triggered,
            confidence=confidence,
            evidence=evidence,
            recommendations=rule.actions if triggered else [],
            execution_time=execution_time
        )
    
    def _evaluate_condition(self, field_value: Any, operator: str, value: Any, context: Dict[str, Any]) -> bool:
        """
        Avalia condição de regra
        
        Args:
            field_value: Valor do campo
            operator: Operador
            value: Valor de comparação
            context: Contexto adicional
            
        Returns:
            True se condição for atendida
        """
        try:
            if operator == ">":
                return float(field_value) > float(value)
            elif operator == "<":
                return float(field_value) < float(value)
            elif operator == ">=":
                return float(field_value) >= float(value)
            elif operator == "<=":
                return float(field_value) <= float(value)
            elif operator == "==":
                return field_value == value
            elif operator == "!=":
                return field_value != value
            elif operator == "in":
                return field_value in value
            elif operator == "not_in":
                return field_value not in value
            elif operator == "contains":
                return str(value).lower() in str(field_value).lower()
            elif operator == "not_contains":
                return str(value).lower() not in str(field_value).lower()
            elif operator == "between":
                return float(value[0]) <= float(field_value) <= float(value[1])
            elif operator == "matches":
                return bool(re.search(str(value), str(field_value)))
            elif operator == "not_matches":
                return not bool(re.search(str(value), str(field_value)))
            elif operator == "category_avg":
                # Implementar lógica de média por categoria
                return self._check_category_average(field_value, value, context)
            else:
                logger.warning(f"Operador desconhecido: {operator}")
                return False
        except Exception as e:
            logger.error(f"Erro ao avaliar condição: {e}")
            return False
    
    def _check_category_average(self, field_value: float, multiplier: float, context: Dict[str, Any]) -> bool:
        """
        Verifica se valor está acima da média da categoria
        
        Args:
            field_value: Valor do campo
            multiplier: Multiplicador da média
            context: Contexto com categoria
            
        Returns:
            True se estiver acima da média
        """
        # Implementar lógica de verificação de média por categoria
        # Por enquanto, retornar False
        return False
    
    def _adjust_confidence(self, rule: BusinessRule, data: Dict[str, Any], base_confidence: float) -> float:
        """
        Ajusta confiança baseado no contexto
        
        Args:
            rule: Regra executada
            data: Dados analisados
            base_confidence: Confiança base
            
        Returns:
            Confiança ajustada
        """
        adjusted_confidence = base_confidence
        
        # Ajustar baseado no tipo de regra
        if rule.rule_type == RuleType.PRICE_ANOMALY:
            # Ajustar baseado na magnitude da anomalia
            if 'valor_unitario' in data and 'categoria' in data:
                # Lógica específica para anomalia de preço
                pass
        
        elif rule.rule_type == RuleType.TEMPORAL_ANOMALY:
            # Ajustar baseado no horário e valor
            if 'hora_emissao' in data and 'valor_total' in data:
                # Lógica específica para anomalia temporal
                pass
        
        # Ajustar baseado na severidade
        if rule.severity == 'critical':
            adjusted_confidence *= 1.2
        elif rule.severity == 'high':
            adjusted_confidence *= 1.1
        elif rule.severity == 'low':
            adjusted_confidence *= 0.9
        
        return min(adjusted_confidence, 1.0)
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das regras
        
        Returns:
            Estatísticas das regras
        """
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules.values() if r.enabled])
        
        # Estatísticas de execução
        total_executions = len(self.execution_history)
        triggered_executions = len([r for r in self.execution_history if r.triggered])
        
        # Regras por tipo
        rules_by_type = {}
        for rule in self.rules.values():
            rule_type = rule.rule_type.value
            if rule_type not in rules_by_type:
                rules_by_type[rule_type] = 0
            rules_by_type[rule_type] += 1
        
        # Regras por severidade
        rules_by_severity = {}
        for rule in self.rules.values():
            severity = rule.severity
            if severity not in rules_by_severity:
                rules_by_severity[severity] = 0
            rules_by_severity[severity] += 1
        
        return {
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'total_executions': total_executions,
            'triggered_executions': triggered_executions,
            'trigger_rate': triggered_executions / total_executions if total_executions > 0 else 0,
            'rules_by_type': rules_by_type,
            'rules_by_severity': rules_by_severity
        }
    
    def export_rules(self, file_path: str):
        """
        Exporta regras para arquivo
        
        Args:
            file_path: Caminho do arquivo
        """
        rules_data = {
            'exported_at': datetime.now().isoformat(),
            'rules': [
                {
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'description': rule.description,
                    'rule_type': rule.rule_type.value,
                    'conditions': rule.conditions,
                    'actions': rule.actions,
                    'severity': rule.severity,
                    'confidence': rule.confidence,
                    'enabled': rule.enabled,
                    'created_at': rule.created_at.isoformat(),
                    'last_updated': rule.last_updated.isoformat()
                }
                for rule in self.rules.values()
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Regras exportadas para {file_path}")
    
    def import_rules(self, file_path: str):
        """
        Importa regras de arquivo
        
        Args:
            file_path: Caminho do arquivo
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        
        for rule_data in rules_data.get('rules', []):
            rule = BusinessRule(
                rule_id=rule_data['rule_id'],
                name=rule_data['name'],
                description=rule_data['description'],
                rule_type=RuleType(rule_data['rule_type']),
                conditions=rule_data['conditions'],
                actions=rule_data['actions'],
                severity=rule_data['severity'],
                confidence=rule_data['confidence'],
                enabled=rule_data['enabled'],
                created_at=datetime.fromisoformat(rule_data['created_at']),
                last_updated=datetime.fromisoformat(rule_data['last_updated'])
            )
            self.rules[rule.rule_id] = rule
        
        logger.info(f"Regras importadas de {file_path}")


# Instância global do motor de regras
_rules_engine_instance: Optional[AdvancedBusinessRulesEngine] = None

def get_business_rules_engine() -> AdvancedBusinessRulesEngine:
    """Retorna instância global do motor de regras"""
    global _rules_engine_instance
    if _rules_engine_instance is None:
        _rules_engine_instance = AdvancedBusinessRulesEngine()
    return _rules_engine_instance

def execute_business_rules(data: Dict[str, Any]) -> List[RuleExecutionResult]:
    """Função de conveniência para executar regras"""
    return get_business_rules_engine().execute_rules(data)
