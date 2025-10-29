"""
OldNews FiscalAI - Detectors Package
Sistema de detecção de fraudes fiscais
"""

from .detector_subfaturamento import DetectorSubfaturamento
from .detector_ncm_incorreto import DetectorNCMIncorreto
from .detector_triangulacao import DetectorTriangulacao
from .orquestrador_deteccao import OrquestradorDeteccaoFraudes

__all__ = [
    "DetectorSubfaturamento",
    "DetectorNCMIncorreto",
    "DetectorTriangulacao",
    "OrquestradorDeteccaoFraudes",
]

