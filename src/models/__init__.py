"""
OldNews FiscalAI - Models Package
"""

from .schemas import (
    # Enums
    TipoFraude,
    NivelRisco,
    StatusProcessamento,
    LLMProvider,
    
    # NF-e Models
    ItemNFe,
    NFe,
    
    # Fraud Detection
    DeteccaoFraude,
    ResultadoAnalise,
    
    # Classification
    ClassificacaoNCM,
    
    # Configuration
    LLMConfig,
    
    # Reports
    RelatorioFiscal,
    
    # Persistence
    NFePersistencia,
    
    # Utilities
    determinar_nivel_risco,
    formatar_cnpj,
    formatar_ncm,
)

__all__ = [
    # Enums
    "TipoFraude",
    "NivelRisco",
    "StatusProcessamento",
    "LLMProvider",
    
    # NF-e Models
    "ItemNFe",
    "NFe",
    
    # Fraud Detection
    "DeteccaoFraude",
    "ResultadoAnalise",
    
    # Classification
    "ClassificacaoNCM",
    
    # Configuration
    "LLMConfig",
    
    # Reports
    "RelatorioFiscal",
    
    # Persistence
    "NFePersistencia",
    
    # Utilities
    "determinar_nivel_risco",
    "formatar_cnpj",
    "formatar_ncm",
]

