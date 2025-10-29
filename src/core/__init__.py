"""
OldNews FiscalAI - Core Package
Classes base e interfaces para orientação a objeto adequada
"""

from .base_agent import BaseAgent
from .base_detector import BaseDetector
from .base_parser import BaseParser
from .interfaces import IAgent, IDetector, IParser, IModelManager

__all__ = [
    "BaseAgent",
    "BaseDetector", 
    "BaseParser",
    "IAgent",
    "IDetector",
    "IParser",
    "IModelManager"
]
