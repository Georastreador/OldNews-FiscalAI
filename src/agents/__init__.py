"""
OldNews FiscalAI - Agents Package
Sistema multi-agente para análise fiscal de NF-e
"""

from .agente1_extrator import Agente1Extrator
from .agente2_classificador import Agente2Classificador
from .agente3_validador import Agente3Validador
from .agente4_orquestrador import Agente4Orquestrador
from .agente5_interface import Agente5Interface

__all__ = [
    "Agente1Extrator",
    "Agente2Classificador",
    "Agente3Validador",
    "Agente4Orquestrador",
    "Agente5Interface",
]

