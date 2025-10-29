"""
OldNews FiscalAI - Interfaces
Definições de interfaces para garantir contratos consistentes
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from ..models import NFe, ItemNFe, ClassificacaoNCM, ResultadoAnalise, DeteccaoFraude


class IAgent(ABC):
    """Interface para todos os agentes do sistema"""
    
    @abstractmethod
    def executar(self, *args, **kwargs) -> Any:
        """Executa a tarefa principal do agente"""
        pass
    
    @abstractmethod
    def validar_entrada(self, *args, **kwargs) -> bool:
        """Valida os dados de entrada"""
        pass
    
    @abstractmethod
    def obter_resultado(self) -> Any:
        """Obtém o resultado da execução"""
        pass


class IDetector(ABC):
    """Interface para todos os detectores de fraude"""
    
    @abstractmethod
    def detectar(self, item: ItemNFe, nfe: NFe) -> Optional[DeteccaoFraude]:
        """Detecta fraudes em um item específico"""
        pass
    
    @abstractmethod
    def analisar_nfe(self, nfe: NFe, classificacoes: Optional[Dict[int, ClassificacaoNCM]] = None) -> List[DeteccaoFraude]:
        """Analisa uma NF-e completa para fraudes"""
        pass
    
    @abstractmethod
    def configurar_thresholds(self, **kwargs) -> None:
        """Configura os thresholds de detecção"""
        pass


class IParser(ABC):
    """Interface para todos os parsers de documentos fiscais"""
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Union[NFe, List[NFe], Tuple[Any, str, str]]:
        """Faz o parsing de um arquivo"""
        pass
    
    @abstractmethod
    def validar_estrutura(self, file_path: str) -> bool:
        """Valida a estrutura do arquivo"""
        pass
    
    @abstractmethod
    def obter_metadados(self, file_path: str) -> Dict[str, Any]:
        """Obtém metadados do arquivo"""
        pass


class IModelManager(ABC):
    """Interface para gerenciadores de modelos de IA"""
    
    @abstractmethod
    def get_llm(self, model_name: str) -> Any:
        """Obtém uma instância do modelo especificado"""
        pass
    
    @abstractmethod
    def listar_modelos_disponiveis(self) -> List[str]:
        """Lista todos os modelos disponíveis"""
        pass
    
    @abstractmethod
    def validar_modelo(self, model_name: str) -> bool:
        """Valida se um modelo está disponível"""
        pass
