"""
OldNews FiscalAI - Base Detector
Classe base para todos os detectores de fraude
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
import logging

from .interfaces import IDetector
from ..models import NFe, ItemNFe, ClassificacaoNCM, DeteccaoFraude, TipoFraude


class BaseDetector(IDetector):
    """
    Classe base para todos os detectores de fraude
    
    Implementa funcionalidades comuns e define interface padrão
    """
    
    def __init__(self, 
                 tipo_fraude: TipoFraude,
                 threshold_score_minimo: int = 30,
                 threshold_confianca_minima: float = 0.5):
        """
        Inicializa o detector base
        
        Args:
            tipo_fraude: Tipo de fraude que este detector identifica
            threshold_score_minimo: Score mínimo para reportar fraude
            threshold_confianca_minima: Confiança mínima para reportar fraude
        """
        self._tipo_fraude = tipo_fraude
        self._threshold_score_minimo = threshold_score_minimo
        self._threshold_confianca_minima = threshold_confianca_minima
        self._logger = logging.getLogger(self.__class__.__name__)
        self._configuracoes = {}
    
    @property
    def tipo_fraude(self) -> TipoFraude:
        """Obtém o tipo de fraude detectado"""
        return self._tipo_fraude
    
    @property
    def threshold_score_minimo(self) -> int:
        """Obtém o threshold de score mínimo"""
        return self._threshold_score_minimo
    
    @threshold_score_minimo.setter
    def threshold_score_minimo(self, value: int) -> None:
        """Define o threshold de score mínimo"""
        if not 0 <= value <= 100:
            raise ValueError("Threshold de score deve estar entre 0 e 100")
        self._threshold_score_minimo = value
    
    @property
    def threshold_confianca_minima(self) -> float:
        """Obtém o threshold de confiança mínima"""
        return self._threshold_confianca_minima
    
    @threshold_confianca_minima.setter
    def threshold_confianca_minima(self, value: float) -> None:
        """Define o threshold de confiança mínima"""
        if not 0.0 <= value <= 1.0:
            raise ValueError("Threshold de confiança deve estar entre 0.0 e 1.0")
        self._threshold_confianca_minima = value
    
    @abstractmethod
    def detectar(self, item: ItemNFe, nfe: NFe) -> Optional[DeteccaoFraude]:
        """Detecta fraudes em um item específico"""
        pass
    
    def analisar_nfe(self, 
                    nfe: NFe, 
                    classificacoes: Optional[Dict[int, ClassificacaoNCM]] = None) -> List[DeteccaoFraude]:
        """
        Analisa uma NF-e completa para fraudes
        
        Args:
            nfe: NF-e a ser analisada
            classificacoes: Classificações NCM dos itens (opcional)
        
        Returns:
            Lista de fraudes detectadas
        """
        fraudes_detectadas = []
        
        for item in nfe.itens:
            try:
                fraude = self.detectar(item, nfe)
                if fraude is not None:
                    fraudes_detectadas.append(fraude)
            except Exception as e:
                self._log_error(f"Erro ao analisar item {item.numero_item}: {str(e)}")
                continue
        
        return fraudes_detectadas
    
    def configurar_thresholds(self, **kwargs) -> None:
        """
        Configura os thresholds de detecção
        
        Args:
            **kwargs: Parâmetros de configuração
        """
        if 'score_minimo' in kwargs:
            self.threshold_score_minimo = kwargs['score_minimo']
        
        if 'confianca_minima' in kwargs:
            self.threshold_confianca_minima = kwargs['confianca_minima']
        
        # Salvar outras configurações específicas
        for key, value in kwargs.items():
            if key not in ['score_minimo', 'confianca_minima']:
                self._configuracoes[key] = value
    
    def _criar_deteccao_fraude(self,
                              item: ItemNFe,
                              score: int,
                              confianca: float,
                              evidencias: List[str],
                              justificativa: str,
                              metodo_deteccao: str = "statistical",
                              dados_adicionais: Optional[Dict[str, Any]] = None) -> DeteccaoFraude:
        """
        Cria um objeto DeteccaoFraude padronizado
        
        Args:
            item: Item da NF-e
            score: Score de risco (0-100)
            confianca: Confiança na detecção (0-1)
            evidencias: Lista de evidências
            justificativa: Justificativa textual
            metodo_deteccao: Método usado para detecção
            dados_adicionais: Dados adicionais da análise
        
        Returns:
            Objeto DeteccaoFraude
        """
        return DeteccaoFraude(
            tipo_fraude=self._tipo_fraude,
            score=score,
            confianca=confianca,
            evidencias=evidencias,
            justificativa=justificativa,
            metodo_deteccao=metodo_deteccao,
            item_numero=item.numero_item,
            dados_adicionais=dados_adicionais or {}
        )
    
    def _validar_score(self, score: int) -> bool:
        """Valida se o score está no range válido"""
        return 0 <= score <= 100
    
    def _validar_confianca(self, confianca: float) -> bool:
        """Valida se a confiança está no range válido"""
        return 0.0 <= confianca <= 1.0
    
    def _log_info(self, message: str) -> None:
        """Log de informação"""
        self._logger.info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log de aviso"""
        self._logger.warning(message)
    
    def _log_error(self, message: str) -> None:
        """Log de erro"""
        self._logger.error(message)
