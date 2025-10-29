"""
FiscalAI MVP - Validador de Dados
Sistema robusto de validação para reduzir erros de processamento
"""

import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, date
from dataclasses import dataclass
import logging
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Resultado de validação"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    validated_data: Any = None

@dataclass
class ValidationRule:
    """Regra de validação"""
    field_name: str
    rule_type: str
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    custom_validator: Optional[callable] = None

class DataValidator:
    """
    Validador robusto de dados fiscais
    
    Funcionalidades:
    - Validação de campos obrigatórios
    - Validação de formatos (CNPJ, CPF, etc.)
    - Validação de ranges numéricos
    - Validação de consistência
    - Sanitização de dados
    """
    
    def __init__(self):
        """Inicializa o validador"""
        self.rules = self._load_validation_rules()
        self.patterns = self._load_validation_patterns()
    
    def _load_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Carrega regras de validação"""
        return {
            'nfe': [
                ValidationRule('chave_acesso', 'string', required=True, min_length=44, max_length=44),
                ValidationRule('cnpj_emitente', 'cnpj', required=True),
                ValidationRule('cnpj_destinatario', 'cnpj', required=False),
                ValidationRule('valor_total', 'numeric', required=True, min_value=0),
                ValidationRule('data_emissao', 'datetime', required=True),
                ValidationRule('data_saida_entrada', 'datetime', required=False),
                ValidationRule('uf_emitente', 'uf', required=True),
                ValidationRule('uf_destinatario', 'uf', required=False),
                ValidationRule('cfop', 'cfop', required=True),
                ValidationRule('natureza_operacao', 'string', required=True, min_length=1),
            ],
            'item_nfe': [
                ValidationRule('numero_item', 'integer', required=True, min_value=1),
                ValidationRule('codigo_produto', 'string', required=True, min_length=1),
                ValidationRule('descricao', 'string', required=True, min_length=1),
                ValidationRule('ncm_declarado', 'ncm', required=True),
                ValidationRule('cfop', 'cfop', required=True),
                ValidationRule('quantidade', 'numeric', required=True, min_value=0),
                ValidationRule('valor_unitario', 'numeric', required=True, min_value=0),
                ValidationRule('valor_total', 'numeric', required=True, min_value=0),
                ValidationRule('unidade_comercial', 'string', required=True, min_length=1),
            ],
            'csv': [
                ValidationRule('cnpj', 'cnpj', required=True),
                ValidationRule('data_emissao', 'date', required=True),
                ValidationRule('valor_total', 'numeric', required=True, min_value=0),
                ValidationRule('cfop', 'cfop', required=True),
                ValidationRule('ncm', 'ncm', required=True),
                ValidationRule('descricao', 'string', required=True, min_length=1),
            ]
        }
    
    def _load_validation_patterns(self) -> Dict[str, str]:
        """Carrega padrões de validação"""
        return {
            'cnpj': r'^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$',
            'cpf': r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
            'ncm': r'^\d{8}$',
            'cfop': r'^\d{4}$',
            'uf': r'^[A-Z]{2}$',
            'chave_acesso': r'^\d{44}$',
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'telefone': r'^\(\d{2}\)\s\d{4,5}-\d{4}$',
        }
    
    def validate_nfe(self, nfe_data: Dict[str, Any]) -> ValidationResult:
        """
        Valida dados de NF-e
        
        Args:
            nfe_data: Dados da NF-e
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Validar campos obrigatórios
        for rule in self.rules['nfe']:
            field_value = nfe_data.get(rule.field_name)
            
            if rule.required and (field_value is None or field_value == ''):
                errors.append(f"Campo obrigatório '{rule.field_name}' não informado")
                continue
            
            if field_value is not None and field_value != '':
                field_errors, field_warnings, field_suggestions = self._validate_field(
                    rule, field_value, rule.field_name
                )
                errors.extend(field_errors)
                warnings.extend(field_warnings)
                suggestions.extend(field_suggestions)
        
        # Validações de consistência
        consistency_errors, consistency_warnings = self._validate_nfe_consistency(nfe_data)
        errors.extend(consistency_errors)
        warnings.extend(consistency_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_data=nfe_data
        )
    
    def validate_item_nfe(self, item_data: Dict[str, Any]) -> ValidationResult:
        """
        Valida dados de item de NF-e
        
        Args:
            item_data: Dados do item
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Validar campos obrigatórios
        for rule in self.rules['item_nfe']:
            field_value = item_data.get(rule.field_name)
            
            if rule.required and (field_value is None or field_value == ''):
                errors.append(f"Campo obrigatório '{rule.field_name}' não informado")
                continue
            
            if field_value is not None and field_value != '':
                field_errors, field_warnings, field_suggestions = self._validate_field(
                    rule, field_value, rule.field_name
                )
                errors.extend(field_errors)
                warnings.extend(field_warnings)
                suggestions.extend(field_suggestions)
        
        # Validações de consistência
        consistency_errors, consistency_warnings = self._validate_item_consistency(item_data)
        errors.extend(consistency_errors)
        warnings.extend(consistency_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_data=item_data
        )
    
    def validate_csv_data(self, df: pd.DataFrame) -> ValidationResult:
        """
        Valida dados de CSV
        
        Args:
            df: DataFrame com dados CSV
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Verificar colunas obrigatórias
        required_columns = ['cnpj', 'data_emissao', 'valor_total', 'cfop', 'ncm', 'descricao']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            errors.append(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
        
        # Validar cada linha
        for index, row in df.iterrows():
            row_errors, row_warnings, row_suggestions = self._validate_csv_row(row, index)
            errors.extend(row_errors)
            warnings.extend(row_warnings)
            suggestions.extend(row_suggestions)
        
        # Validações de consistência do dataset
        dataset_errors, dataset_warnings = self._validate_csv_consistency(df)
        errors.extend(dataset_errors)
        warnings.extend(dataset_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_data=df
        )
    
    def _validate_field(self, rule: ValidationRule, value: Any, field_name: str) -> Tuple[List[str], List[str], List[str]]:
        """Valida um campo específico"""
        errors = []
        warnings = []
        suggestions = []
        
        # Validar tipo
        if rule.rule_type == 'string':
            if not isinstance(value, str):
                errors.append(f"Campo '{field_name}' deve ser string")
                return errors, warnings, suggestions
            
            if rule.min_length and len(value) < rule.min_length:
                errors.append(f"Campo '{field_name}' deve ter pelo menos {rule.min_length} caracteres")
            
            if rule.max_length and len(value) > rule.max_length:
                errors.append(f"Campo '{field_name}' deve ter no máximo {rule.max_length} caracteres")
        
        elif rule.rule_type == 'numeric':
            try:
                num_value = float(value)
                if rule.min_value is not None and num_value < rule.min_value:
                    errors.append(f"Campo '{field_name}' deve ser maior ou igual a {rule.min_value}")
                if rule.max_value is not None and num_value > rule.max_value:
                    errors.append(f"Campo '{field_name}' deve ser menor ou igual a {rule.max_value}")
            except (ValueError, TypeError):
                errors.append(f"Campo '{field_name}' deve ser numérico")
        
        elif rule.rule_type == 'integer':
            try:
                int_value = int(value)
                if rule.min_value is not None and int_value < rule.min_value:
                    errors.append(f"Campo '{field_name}' deve ser maior ou igual a {rule.min_value}")
                if rule.max_value is not None and int_value > rule.max_value:
                    errors.append(f"Campo '{field_name}' deve ser menor ou igual a {rule.max_value}")
            except (ValueError, TypeError):
                errors.append(f"Campo '{field_name}' deve ser inteiro")
        
        # Validar padrões
        if rule.pattern and rule.rule_type in ['cnpj', 'cpf', 'ncm', 'cfop', 'uf', 'chave_acesso', 'email', 'telefone']:
            pattern = self.patterns.get(rule.rule_type)
            if pattern and not re.match(pattern, str(value)):
                errors.append(f"Campo '{field_name}' tem formato inválido")
        
        # Validar valores permitidos
        if rule.allowed_values and str(value) not in rule.allowed_values:
            errors.append(f"Campo '{field_name}' deve ser um dos valores: {', '.join(rule.allowed_values)}")
        
        # Validador customizado
        if rule.custom_validator:
            try:
                custom_result = rule.custom_validator(value)
                if not custom_result:
                    errors.append(f"Campo '{field_name}' falhou na validação customizada")
            except Exception as e:
                errors.append(f"Erro na validação customizada do campo '{field_name}': {str(e)}")
        
        return errors, warnings, suggestions
    
    def _validate_nfe_consistency(self, nfe_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Valida consistência de dados de NF-e"""
        errors = []
        warnings = []
        
        # Validar datas
        if 'data_emissao' in nfe_data and 'data_saida_entrada' in nfe_data:
            try:
                data_emissao = pd.to_datetime(nfe_data['data_emissao'])
                data_saida = pd.to_datetime(nfe_data['data_saida_entrada'])
                
                if data_saida < data_emissao:
                    errors.append("Data de saída/entrada não pode ser anterior à data de emissão")
            except:
                pass
        
        # Validar valor total
        if 'valor_total' in nfe_data:
            try:
                valor_total = float(nfe_data['valor_total'])
                if valor_total <= 0:
                    errors.append("Valor total deve ser maior que zero")
            except:
                pass
        
        return errors, warnings
    
    def _validate_item_consistency(self, item_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Valida consistência de dados de item"""
        errors = []
        warnings = []
        
        # Validar cálculo de valor total
        if all(k in item_data for k in ['quantidade', 'valor_unitario', 'valor_total']):
            try:
                quantidade = float(item_data['quantidade'])
                valor_unitario = float(item_data['valor_unitario'])
                valor_total = float(item_data['valor_total'])
                
                valor_calculado = quantidade * valor_unitario
                diferenca = abs(valor_calculado - valor_total)
                
                if diferenca > 0.01:  # Tolerância de 1 centavo
                    warnings.append(f"Valor total calculado ({valor_calculado:.2f}) difere do informado ({valor_total:.2f})")
            except:
                pass
        
        return errors, warnings
    
    def _validate_csv_row(self, row: pd.Series, index: int) -> Tuple[List[str], List[str], List[str]]:
        """Valida uma linha do CSV"""
        errors = []
        warnings = []
        suggestions = []
        
        # Validar CNPJ
        if 'cnpj' in row and pd.notna(row['cnpj']):
            if not self._is_valid_cnpj(str(row['cnpj'])):
                errors.append(f"Linha {index + 1}: CNPJ inválido")
        
        # Validar data
        if 'data_emissao' in row and pd.notna(row['data_emissao']):
            try:
                pd.to_datetime(row['data_emissao'])
            except:
                errors.append(f"Linha {index + 1}: Data de emissão inválida")
        
        # Validar valores numéricos
        numeric_fields = ['valor_total', 'quantidade', 'valor_unitario']
        for field in numeric_fields:
            if field in row and pd.notna(row[field]):
                try:
                    valor = float(row[field])
                    if valor < 0:
                        errors.append(f"Linha {index + 1}: {field} não pode ser negativo")
                except:
                    errors.append(f"Linha {index + 1}: {field} deve ser numérico")
        
        return errors, warnings, suggestions
    
    def _validate_csv_consistency(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Valida consistência do dataset CSV"""
        errors = []
        warnings = []
        
        # Verificar duplicatas
        if 'chave_acesso' in df.columns:
            duplicates = df[df.duplicated(subset=['chave_acesso'], keep=False)]
            if not duplicates.empty:
                warnings.append(f"Encontradas {len(duplicates)} chaves de acesso duplicadas")
        
        # Verificar valores extremos
        if 'valor_total' in df.columns:
            valores = pd.to_numeric(df['valor_total'], errors='coerce')
            if valores.notna().any():
                q99 = valores.quantile(0.99)
                outliers = valores[valores > q99 * 10]
                if not outliers.empty:
                    warnings.append(f"Encontrados {len(outliers)} valores extremos de valor total")
        
        return errors, warnings
    
    def _is_valid_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ"""
        # Remove caracteres não numéricos
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        
        if len(cnpj) != 14:
            return False
        
        # Verificar se todos os dígitos são iguais
        if cnpj == cnpj[0] * 14:
            return False
        
        # Calcular dígitos verificadores
        def calculate_digit(cnpj, weights):
            sum_val = sum(int(cnpj[i]) * weights[i] for i in range(len(weights)))
            remainder = sum_val % 11
            return 0 if remainder < 2 else 11 - remainder
        
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        digit1 = calculate_digit(cnpj[:12], weights1)
        digit2 = calculate_digit(cnpj[:13], weights2)
        
        return int(cnpj[12]) == digit1 and int(cnpj[13]) == digit2
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza dados de entrada
        
        Args:
            data: Dados para sanitizar
            
        Returns:
            Dados sanitizados
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remover espaços extras
                sanitized[key] = value.strip()
                
                # Converter para maiúsculas se necessário
                if key.upper() in ['UF_EMITENTE', 'UF_DESTINATARIO', 'UF']:
                    sanitized[key] = value.upper()
                
                # Remover caracteres especiais de CNPJ/CPF
                if key.upper() in ['CNPJ_EMITENTE', 'CNPJ_DESTINATARIO', 'CNPJ']:
                    sanitized[key] = re.sub(r'[^0-9]', '', value)
                
            elif isinstance(value, (int, float)):
                # Arredondar valores monetários
                if 'valor' in key.lower():
                    sanitized[key] = round(float(value), 2)
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value
        
        return sanitized


# Instância global do validador
_validator_instance: Optional[DataValidator] = None

def get_data_validator() -> DataValidator:
    """Retorna instância global do validador"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance

def validate_nfe_data(nfe_data: Dict[str, Any]) -> ValidationResult:
    """Função de conveniência para validar NF-e"""
    return get_data_validator().validate_nfe(nfe_data)

def validate_item_data(item_data: Dict[str, Any]) -> ValidationResult:
    """Função de conveniência para validar item"""
    return get_data_validator().validate_item_nfe(item_data)

def validate_csv_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Função de conveniência para validar CSV"""
    return get_data_validator().validate_csv_data(df)

def sanitize_input_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Função de conveniência para sanitizar dados"""
    return get_data_validator().sanitize_data(data)
