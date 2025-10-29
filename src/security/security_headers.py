"""
FiscalAI MVP - Headers de Segurança
Implementação de headers de segurança para proteção da aplicação
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class SecurityHeader:
    """Header de segurança"""
    name: str
    value: str
    description: str
    priority: str  # 'high', 'medium', 'low'

class SecurityHeadersManager:
    """
    Gerenciador de headers de segurança
    
    Funcionalidades:
    - Headers CORS
    - Content Security Policy (CSP)
    - Headers de proteção
    - Headers de privacidade
    - Headers de performance
    """
    
    def __init__(self):
        """Inicializa o gerenciador de headers"""
        self.headers: Dict[str, SecurityHeader] = {}
        self._initialize_default_headers()
    
    def _initialize_default_headers(self):
        """Inicializa headers padrão de segurança"""
        # CORS Headers
        self.add_header(SecurityHeader(
            name="Access-Control-Allow-Origin",
            value="https://fiscalai.example.com",
            description="Controla quais domínios podem acessar a API",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="Access-Control-Allow-Methods",
            value="GET, POST, PUT, DELETE, OPTIONS",
            description="Métodos HTTP permitidos",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="Access-Control-Allow-Headers",
            value="Content-Type, Authorization, X-Requested-With, X-API-Key",
            description="Headers permitidos nas requisições",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="Access-Control-Max-Age",
            value="3600",
            description="Tempo de cache para preflight requests",
            priority="medium"
        ))
        
        # Content Security Policy
        self.add_header(SecurityHeader(
            name="Content-Security-Policy",
            value="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.openai.com https://api.anthropic.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            description="Política de segurança de conteúdo",
            priority="high"
        ))
        
        # Headers de Proteção
        self.add_header(SecurityHeader(
            name="X-Content-Type-Options",
            value="nosniff",
            description="Previne MIME type sniffing",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="X-Frame-Options",
            value="DENY",
            description="Previne clickjacking",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="X-XSS-Protection",
            value="1; mode=block",
            description="Ativa proteção XSS do navegador",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="Referrer-Policy",
            value="strict-origin-when-cross-origin",
            description="Controla informações de referrer",
            priority="medium"
        ))
        
        self.add_header(SecurityHeader(
            name="Permissions-Policy",
            value="geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()",
            description="Controla permissões do navegador",
            priority="medium"
        ))
        
        # Headers de Privacidade
        self.add_header(SecurityHeader(
            name="Strict-Transport-Security",
            value="max-age=31536000; includeSubDomains; preload",
            description="Força HTTPS",
            priority="high"
        ))
        
        self.add_header(SecurityHeader(
            name="Cross-Origin-Embedder-Policy",
            value="require-corp",
            description="Controla recursos cross-origin",
            priority="medium"
        ))
        
        self.add_header(SecurityHeader(
            name="Cross-Origin-Opener-Policy",
            value="same-origin",
            description="Isola contexto de navegação",
            priority="medium"
        ))
        
        # Headers de Performance
        self.add_header(SecurityHeader(
            name="X-DNS-Prefetch-Control",
            value="off",
            description="Desabilita prefetch de DNS",
            priority="low"
        ))
        
        self.add_header(SecurityHeader(
            name="X-Download-Options",
            value="noopen",
            description="Previne execução automática de downloads",
            priority="medium"
        ))
        
        # Headers Customizados
        self.add_header(SecurityHeader(
            name="X-FiscalAI-Version",
            value="1.0.0",
            description="Versão da aplicação",
            priority="low"
        ))
        
        self.add_header(SecurityHeader(
            name="X-Content-Security-Policy-Report-Only",
            value="default-src 'self'; report-uri /csp-report",
            description="CSP em modo de relatório",
            priority="medium"
        ))
    
    def add_header(self, header: SecurityHeader):
        """
        Adiciona header de segurança
        
        Args:
            header: Header a ser adicionado
        """
        self.headers[header.name] = header
        logger.debug(f"Header adicionado: {header.name}")
    
    def remove_header(self, header_name: str):
        """
        Remove header de segurança
        
        Args:
            header_name: Nome do header
        """
        if header_name in self.headers:
            del self.headers[header_name]
            logger.debug(f"Header removido: {header_name}")
    
    def update_header(self, header_name: str, new_value: str):
        """
        Atualiza valor de header
        
        Args:
            header_name: Nome do header
            new_value: Novo valor
        """
        if header_name in self.headers:
            self.headers[header_name].value = new_value
            logger.debug(f"Header atualizado: {header_name}")
    
    def get_headers(self, priority: Optional[str] = None) -> Dict[str, str]:
        """
        Obtém headers de segurança
        
        Args:
            priority: Filtrar por prioridade
            
        Returns:
            Dicionário com headers
        """
        if priority:
            return {
                name: header.value 
                for name, header in self.headers.items() 
                if header.priority == priority
            }
        else:
            return {
                name: header.value 
                for name, header in self.headers.items()
            }
    
    def get_headers_for_streamlit(self) -> Dict[str, str]:
        """
        Obtém headers otimizados para Streamlit
        
        Returns:
            Headers para Streamlit
        """
        # Headers específicos para Streamlit
        streamlit_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",  # Streamlit precisa de frames
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://api.openai.com https://api.anthropic.com; frame-ancestors 'self'",
            "X-FiscalAI-Version": "1.0.0"
        }
        
        return streamlit_headers
    
    def get_cors_headers(self) -> Dict[str, str]:
        """
        Obtém headers CORS
        
        Returns:
            Headers CORS
        """
        cors_headers = {}
        
        for name, header in self.headers.items():
            if name.startswith("Access-Control-"):
                cors_headers[name] = header.value
        
        return cors_headers
    
    def get_csp_header(self) -> str:
        """
        Obtém header CSP completo
        
        Returns:
            Content Security Policy
        """
        return self.headers.get("Content-Security-Policy", SecurityHeader("", "", "", "")).value
    
    def update_csp(self, new_csp: str):
        """
        Atualiza Content Security Policy
        
        Args:
            new_csp: Nova política CSP
        """
        self.update_header("Content-Security-Policy", new_csp)
        logger.info("CSP atualizado")
    
    def add_csp_directive(self, directive: str, value: str):
        """
        Adiciona diretiva ao CSP
        
        Args:
            directive: Nome da diretiva
            value: Valor da diretiva
        """
        current_csp = self.get_csp_header()
        
        # Remover diretiva existente se houver
        if directive in current_csp:
            import re
            current_csp = re.sub(f"{directive}[^;]*;?", "", current_csp)
        
        # Adicionar nova diretiva
        new_csp = f"{current_csp}; {directive} {value}".strip("; ")
        self.update_csp(new_csp)
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        Gera relatório de segurança dos headers
        
        Returns:
            Relatório de segurança
        """
        total_headers = len(self.headers)
        high_priority = len([h for h in self.headers.values() if h.priority == "high"])
        medium_priority = len([h for h in self.headers.values() if h.priority == "medium"])
        low_priority = len([h for h in self.headers.values() if h.priority == "low"])
        
        # Verificar headers críticos
        critical_headers = [
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        missing_critical = [
            header for header in critical_headers 
            if header not in self.headers
        ]
        
        return {
            "total_headers": total_headers,
            "priority_distribution": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            },
            "critical_headers_present": len(critical_headers) - len(missing_critical),
            "missing_critical_headers": missing_critical,
            "security_score": self._calculate_security_score(),
            "headers_list": [
                {
                    "name": name,
                    "value": header.value,
                    "description": header.description,
                    "priority": header.priority
                }
                for name, header in self.headers.items()
            ]
        }
    
    def _calculate_security_score(self) -> float:
        """
        Calcula score de segurança baseado nos headers
        
        Returns:
            Score de segurança (0-100)
        """
        # Headers críticos
        critical_headers = [
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        # Headers importantes
        important_headers = [
            "Access-Control-Allow-Origin",
            "Referrer-Policy",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy",
            "Cross-Origin-Opener-Policy"
        ]
        
        score = 0
        
        # Pontuar headers críticos
        for header in critical_headers:
            if header in self.headers:
                score += 20
        
        # Pontuar headers importantes
        for header in important_headers:
            if header in self.headers:
                score += 5
        
        # Bonificação por total de headers
        total_headers = len(self.headers)
        if total_headers > 10:
            score += 10
        elif total_headers > 5:
            score += 5
        
        return min(score, 100)
    
    def export_headers(self, file_path: str):
        """
        Exporta headers para arquivo
        
        Args:
            file_path: Caminho do arquivo
        """
        import json
        
        headers_data = {
            "exported_at": datetime.now().isoformat(),
            "headers": [
                {
                    "name": name,
                    "value": header.value,
                    "description": header.description,
                    "priority": header.priority
                }
                for name, header in self.headers.items()
            ],
            "security_report": self.get_security_report()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(headers_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Headers exportados para {file_path}")
    
    def validate_headers(self) -> List[str]:
        """
        Valida configuração dos headers
        
        Returns:
            Lista de problemas encontrados
        """
        issues = []
        
        # Verificar CSP
        csp = self.get_csp_header()
        if not csp:
            issues.append("Content-Security-Policy não configurado")
        elif "default-src" not in csp:
            issues.append("CSP sem default-src")
        
        # Verificar CORS
        if "Access-Control-Allow-Origin" not in self.headers:
            issues.append("CORS não configurado")
        elif self.headers["Access-Control-Allow-Origin"].value == "*":
            issues.append("CORS muito permissivo (*)")
        
        # Verificar HTTPS
        if "Strict-Transport-Security" not in self.headers:
            issues.append("HSTS não configurado")
        
        # Verificar XSS
        if "X-XSS-Protection" not in self.headers:
            issues.append("Proteção XSS não configurada")
        
        return issues


# Instância global do gerenciador
_security_headers_instance: Optional[SecurityHeadersManager] = None

def get_security_headers_manager() -> SecurityHeadersManager:
    """Retorna instância global do gerenciador"""
    global _security_headers_instance
    if _security_headers_instance is None:
        _security_headers_instance = SecurityHeadersManager()
    return _security_headers_instance

def get_security_headers() -> Dict[str, str]:
    """Função de conveniência para obter headers"""
    return get_security_headers_manager().get_headers()

def get_streamlit_headers() -> Dict[str, str]:
    """Função de conveniência para headers do Streamlit"""
    return get_security_headers_manager().get_headers_for_streamlit()
