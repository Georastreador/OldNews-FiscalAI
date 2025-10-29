"""
FiscalAI MVP - Sanitizador de Input
Validação e sanitização robusta de dados de entrada
"""

import re
import html
import base64
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SanitizationResult:
    """Resultado da sanitização"""
    is_safe: bool
    sanitized_data: Any
    original_data: Any
    threats_detected: List[str]
    sanitization_applied: List[str]
    confidence_score: float

class InputSanitizer:
    """
    Sanitizador de input com foco em segurança
    
    Funcionalidades:
    - Validação de tipos de dados
    - Sanitização de strings maliciosas
    - Validação de formatos específicos
    - Detecção de ataques comuns
    - Limpeza de dados sensíveis
    """
    
    def __init__(self):
        """Inicializa o sanitizador"""
        # Padrões de ataque conhecidos
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+'.*'\s*=\s*'.*')",
            r"(\bUNION\s+SELECT\b)",
            r"(\bDROP\s+TABLE\b)",
            r"(\bINSERT\s+INTO\b)",
            r"(\bDELETE\s+FROM\b)",
            r"(\bUPDATE\s+SET\b)",
            r"(\bALTER\s+TABLE\b)",
            r"(\bEXEC\s+\()",
            r"(\bEXECUTE\s+\()",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)"
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
            r"<applet[^>]*>.*?</applet>",
            r"<form[^>]*>.*?</form>",
            r"<input[^>]*>",
            r"<button[^>]*>.*?</button>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"onfocus\s*=",
            r"onblur\s*=",
            r"onchange\s*=",
            r"onsubmit\s*="
        ]
        
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"\.\.%2f",
            r"\.\.%5c",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\.\.%252f",
            r"\.\.%255c"
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$]",
            r"\b(cat|ls|dir|type|more|less|head|tail|grep|find|locate|which|whereis)\b",
            r"\b(rm|del|remove|delete|mv|move|cp|copy|chmod|chown|chgrp)\b",
            r"\b(wget|curl|nc|netcat|telnet|ftp|ssh|scp|rsync)\b",
            r"\b(python|perl|ruby|php|bash|sh|cmd|powershell)\b",
            r"\b(eval|exec|system|shell_exec|passthru|popen|proc_open)\b"
        ]
        
        # Padrões de dados fiscais válidos
        self.cnpj_pattern = re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
        self.cpf_pattern = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")
        self.ncm_pattern = re.compile(r"^\d{8}$")
        self.cfop_pattern = re.compile(r"^\d{4}$")
        self.cep_pattern = re.compile(r"^\d{5}-?\d{3}$")
        
        # Configurações
        self.max_string_length = 10000
        self.max_array_length = 1000
        self.max_object_depth = 10
        
    def sanitize_string(self, value: str, allow_html: bool = False) -> SanitizationResult:
        """
        Sanitiza string de entrada
        
        Args:
            value: String a ser sanitizada
            allow_html: Se permite HTML básico
            
        Returns:
            Resultado da sanitização
        """
        if not isinstance(value, str):
            return SanitizationResult(
                is_safe=False,
                sanitized_data=str(value),
                original_data=value,
                threats_detected=["invalid_type"],
                sanitization_applied=["type_conversion"],
                confidence_score=0.0
            )
        
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        # Verificar tamanho
        if len(value) > self.max_string_length:
            value = value[:self.max_string_length]
            sanitization_applied.append("truncated_length")
        
        # Normalizar unicode
        value = unicodedata.normalize('NFKC', value)
        sanitization_applied.append("unicode_normalized")
        
        # Detectar SQL injection
        if self._detect_sql_injection(value):
            threats_detected.append("sql_injection")
            value = self._sanitize_sql_injection(value)
            sanitization_applied.append("sql_injection_removed")
        
        # Detectar XSS
        if self._detect_xss(value):
            threats_detected.append("xss")
            if not allow_html:
                value = self._sanitize_xss(value)
                sanitization_applied.append("xss_removed")
        
        # Detectar path traversal
        if self._detect_path_traversal(value):
            threats_detected.append("path_traversal")
            value = self._sanitize_path_traversal(value)
            sanitization_applied.append("path_traversal_removed")
        
        # Detectar command injection
        if self._detect_command_injection(value):
            threats_detected.append("command_injection")
            value = self._sanitize_command_injection(value)
            sanitization_applied.append("command_injection_removed")
        
        # Escapar caracteres especiais
        if not allow_html:
            value = html.escape(value, quote=True)
            sanitization_applied.append("html_escaped")
        
        # Remover caracteres de controle
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        sanitization_applied.append("control_chars_removed")
        
        # Calcular score de confiança
        confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
        
        return SanitizationResult(
            is_safe=len(threats_detected) == 0,
            sanitized_data=value,
            original_data=original_value,
            threats_detected=threats_detected,
            sanitization_applied=sanitization_applied,
            confidence_score=confidence_score
        )
    
    def sanitize_number(self, value: Union[int, float, str]) -> SanitizationResult:
        """
        Sanitiza número de entrada
        
        Args:
            value: Número a ser sanitizado
            
        Returns:
            Resultado da sanitização
        """
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        try:
            # Converter para string primeiro
            if isinstance(value, str):
                # Verificar se é um número válido
                if not re.match(r'^-?\d+(\.\d+)?$', value.strip()):
                    threats_detected.append("invalid_number_format")
                    return SanitizationResult(
                        is_safe=False,
                        sanitized_data=0,
                        original_data=original_value,
                        threats_detected=threats_detected,
                        sanitization_applied=sanitization_applied,
                        confidence_score=0.0
                    )
                
                # Converter para float
                sanitized_value = float(value)
                sanitization_applied.append("string_to_float")
            else:
                sanitized_value = float(value)
            
            # Verificar limites
            if abs(sanitized_value) > 1e15:
                threats_detected.append("number_too_large")
                sanitized_value = 1e15 if sanitized_value > 0 else -1e15
                sanitization_applied.append("number_capped")
            
            # Verificar se é NaN ou infinito
            if not (sanitized_value == sanitized_value):  # NaN check
                threats_detected.append("nan_value")
                sanitized_value = 0
                sanitization_applied.append("nan_replaced")
            
            if abs(sanitized_value) == float('inf'):
                threats_detected.append("infinite_value")
                sanitized_value = 1e15 if sanitized_value > 0 else -1e15
                sanitization_applied.append("infinite_replaced")
            
            confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
            
            return SanitizationResult(
                is_safe=len(threats_detected) == 0,
                sanitized_data=sanitized_value,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=confidence_score
            )
            
        except (ValueError, TypeError) as e:
            threats_detected.append("conversion_error")
            return SanitizationResult(
                is_safe=False,
                sanitized_data=0,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=0.0
            )
    
    def sanitize_cnpj(self, value: str) -> SanitizationResult:
        """
        Sanitiza e valida CNPJ
        
        Args:
            value: CNPJ a ser sanitizado
            
        Returns:
            Resultado da sanitização
        """
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        # Remover caracteres não numéricos
        cnpj_clean = re.sub(r'[^\d]', '', value)
        sanitization_applied.append("non_numeric_removed")
        
        # Verificar tamanho
        if len(cnpj_clean) != 14:
            threats_detected.append("invalid_cnpj_length")
            return SanitizationResult(
                is_safe=False,
                sanitized_data=cnpj_clean,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=0.0
            )
        
        # Verificar se não é sequência de números iguais
        if cnpj_clean == cnpj_clean[0] * 14:
            threats_detected.append("cnpj_sequence")
        
        # Formatar CNPJ
        formatted_cnpj = f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:14]}"
        sanitization_applied.append("cnpj_formatted")
        
        # Validar CNPJ
        if self._validate_cnpj(cnpj_clean):
            sanitization_applied.append("cnpj_validated")
        else:
            threats_detected.append("invalid_cnpj")
        
        confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
        
        return SanitizationResult(
            is_safe=len(threats_detected) == 0,
            sanitized_data=formatted_cnpj,
            original_data=original_value,
            threats_detected=threats_detected,
            sanitization_applied=sanitization_applied,
            confidence_score=confidence_score
        )
    
    def sanitize_cpf(self, value: str) -> SanitizationResult:
        """
        Sanitiza e valida CPF
        
        Args:
            value: CPF a ser sanitizado
            
        Returns:
            Resultado da sanitização
        """
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        # Remover caracteres não numéricos
        cpf_clean = re.sub(r'[^\d]', '', value)
        sanitization_applied.append("non_numeric_removed")
        
        # Verificar tamanho
        if len(cpf_clean) != 11:
            threats_detected.append("invalid_cpf_length")
            return SanitizationResult(
                is_safe=False,
                sanitized_data=cpf_clean,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=0.0
            )
        
        # Verificar se não é sequência de números iguais
        if cpf_clean == cpf_clean[0] * 11:
            threats_detected.append("cpf_sequence")
        
        # Formatar CPF
        formatted_cpf = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:11]}"
        sanitization_applied.append("cpf_formatted")
        
        # Validar CPF
        if self._validate_cpf(cpf_clean):
            sanitization_applied.append("cpf_validated")
        else:
            threats_detected.append("invalid_cpf")
        
        confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
        
        return SanitizationResult(
            is_safe=len(threats_detected) == 0,
            sanitized_data=formatted_cpf,
            original_data=original_value,
            threats_detected=threats_detected,
            sanitization_applied=sanitization_applied,
            confidence_score=confidence_score
        )
    
    def sanitize_ncm(self, value: str) -> SanitizationResult:
        """
        Sanitiza e valida NCM
        
        Args:
            value: NCM a ser sanitizado
            
        Returns:
            Resultado da sanitização
        """
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        # Remover caracteres não numéricos
        ncm_clean = re.sub(r'[^\d]', '', value)
        sanitization_applied.append("non_numeric_removed")
        
        # Verificar tamanho
        if len(ncm_clean) != 8:
            threats_detected.append("invalid_ncm_length")
            return SanitizationResult(
                is_safe=False,
                sanitized_data=ncm_clean,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=0.0
            )
        
        # Verificar se não é sequência de zeros
        if ncm_clean == "00000000":
            threats_detected.append("ncm_zero_sequence")
        
        confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
        
        return SanitizationResult(
            is_safe=len(threats_detected) == 0,
            sanitized_data=ncm_clean,
            original_data=original_value,
            threats_detected=threats_detected,
            sanitization_applied=sanitization_applied,
            confidence_score=confidence_score
        )
    
    def sanitize_json(self, value: str) -> SanitizationResult:
        """
        Sanitiza JSON de entrada
        
        Args:
            value: JSON a ser sanitizado
            
        Returns:
            Resultado da sanitização
        """
        original_value = value
        threats_detected = []
        sanitization_applied = []
        
        try:
            # Parse JSON
            data = json.loads(value)
            sanitization_applied.append("json_parsed")
            
            # Sanitizar recursivamente
            sanitized_data = self._sanitize_recursive(data, 0)
            sanitization_applied.append("recursive_sanitization")
            
            confidence_score = self._calculate_confidence_score(threats_detected, sanitization_applied)
            
            return SanitizationResult(
                is_safe=len(threats_detected) == 0,
                sanitized_data=sanitized_data,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=confidence_score
            )
            
        except json.JSONDecodeError as e:
            threats_detected.append("invalid_json")
            return SanitizationResult(
                is_safe=False,
                sanitized_data=value,
                original_data=original_value,
                threats_detected=threats_detected,
                sanitization_applied=sanitization_applied,
                confidence_score=0.0
            )
    
    def _detect_sql_injection(self, value: str) -> bool:
        """Detecta tentativas de SQL injection"""
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in self.sql_injection_patterns)
    
    def _detect_xss(self, value: str) -> bool:
        """Detecta tentativas de XSS"""
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in self.xss_patterns)
    
    def _detect_path_traversal(self, value: str) -> bool:
        """Detecta tentativas de path traversal"""
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in self.path_traversal_patterns)
    
    def _detect_command_injection(self, value: str) -> bool:
        """Detecta tentativas de command injection"""
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in self.command_injection_patterns)
    
    def _sanitize_sql_injection(self, value: str) -> str:
        """Remove padrões de SQL injection"""
        for pattern in self.sql_injection_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        return value
    
    def _sanitize_xss(self, value: str) -> str:
        """Remove padrões de XSS"""
        for pattern in self.xss_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        return value
    
    def _sanitize_path_traversal(self, value: str) -> str:
        """Remove padrões de path traversal"""
        for pattern in self.path_traversal_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        return value
    
    def _sanitize_command_injection(self, value: str) -> str:
        """Remove padrões de command injection"""
        for pattern in self.command_injection_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        return value
    
    def _sanitize_recursive(self, data: Any, depth: int) -> Any:
        """Sanitiza dados recursivamente"""
        if depth > self.max_object_depth:
            return str(data)
        
        if isinstance(data, str):
            return self.sanitize_string(data).sanitized_data
        elif isinstance(data, (int, float)):
            return self.sanitize_number(data).sanitized_data
        elif isinstance(data, list):
            if len(data) > self.max_array_length:
                data = data[:self.max_array_length]
            return [self._sanitize_recursive(item, depth + 1) for item in data]
        elif isinstance(data, dict):
            return {key: self._sanitize_recursive(value, depth + 1) for key, value in data.items()}
        else:
            return str(data)
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ usando algoritmo oficial"""
        if len(cnpj) != 14:
            return False
        
        # Calcular primeiro dígito verificador
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0
        
        # Calcular segundo dígito verificador
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0
        
        return cnpj[12] == str(digit1) and cnpj[13] == str(digit2)
    
    def _validate_cpf(self, cpf: str) -> bool:
        """Valida CPF usando algoritmo oficial"""
        if len(cpf) != 11:
            return False
        
        # Calcular primeiro dígito verificador
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0
        
        # Calcular segundo dígito verificador
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0
        
        return cpf[9] == str(digit1) and cpf[10] == str(digit2)
    
    def _calculate_confidence_score(self, threats: List[str], sanitizations: List[str]) -> float:
        """Calcula score de confiança"""
        if not threats:
            return 1.0
        
        # Penalizar por ameaças detectadas
        threat_penalty = len(threats) * 0.2
        
        # Bonificar por sanitizações aplicadas
        sanitization_bonus = min(len(sanitizations) * 0.1, 0.5)
        
        score = max(0.0, 1.0 - threat_penalty + sanitization_bonus)
        return score


# Instância global do sanitizador
_input_sanitizer_instance: Optional[InputSanitizer] = None

def get_input_sanitizer() -> InputSanitizer:
    """Retorna instância global do sanitizador"""
    global _input_sanitizer_instance
    if _input_sanitizer_instance is None:
        _input_sanitizer_instance = InputSanitizer()
    return _input_sanitizer_instance

def sanitize_input(data: Any, input_type: str = "string") -> SanitizationResult:
    """Função de conveniência para sanitização"""
    sanitizer = get_input_sanitizer()
    
    if input_type == "string":
        return sanitizer.sanitize_string(data)
    elif input_type == "number":
        return sanitizer.sanitize_number(data)
    elif input_type == "cnpj":
        return sanitizer.sanitize_cnpj(data)
    elif input_type == "cpf":
        return sanitizer.sanitize_cpf(data)
    elif input_type == "ncm":
        return sanitizer.sanitize_ncm(data)
    elif input_type == "json":
        return sanitizer.sanitize_json(data)
    else:
        return sanitizer.sanitize_string(str(data))
