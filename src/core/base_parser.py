"""
OldNews FiscalAI - Base Parser
Classe base para todos os parsers de documentos fiscais
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
import logging

from .interfaces import IParser
from ..models import NFe


class BaseParser(IParser):
    """
    Classe base para todos os parsers de documentos fiscais
    
    Implementa funcionalidades comuns e define interface padrão
    """
    
    def __init__(self, 
                 tipos_suportados: List[str],
                 encoding_padrao: str = 'utf-8'):
        """
        Inicializa o parser base
        
        Args:
            tipos_suportados: Lista de tipos de documento suportados
            encoding_padrao: Encoding padrão para leitura de arquivos
        """
        self._tipos_suportados = tipos_suportados
        self._encoding_padrao = encoding_padrao
        self._logger = logging.getLogger(self.__class__.__name__)
        self._metadados_cache = {}
    
    @property
    def tipos_suportados(self) -> List[str]:
        """Obtém os tipos de documento suportados"""
        return self._tipos_suportados.copy()
    
    @property
    def encoding_padrao(self) -> str:
        """Obtém o encoding padrão"""
        return self._encoding_padrao
    
    @encoding_padrao.setter
    def encoding_padrao(self, value: str) -> None:
        """Define o encoding padrão"""
        self._encoding_padrao = value
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Union[NFe, List[NFe], Tuple[Any, str, str]]:
        """Faz o parsing de um arquivo"""
        pass
    
    def validar_estrutura(self, file_path: str) -> bool:
        """
        Valida a estrutura básica do arquivo
        
        Args:
            file_path: Caminho para o arquivo
        
        Returns:
            True se a estrutura é válida, False caso contrário
        """
        try:
            path = Path(file_path)
            
            # Verificar se o arquivo existe
            if not path.exists():
                self._log_error(f"Arquivo não encontrado: {file_path}")
                return False
            
            # Verificar se é um arquivo (não diretório)
            if not path.is_file():
                self._log_error(f"Caminho não é um arquivo: {file_path}")
                return False
            
            # Verificar extensão
            if path.suffix.lower() not in ['.xml', '.nfe', '.nfse']:
                self._log_warning(f"Extensão não reconhecida: {path.suffix}")
            
            # Verificar tamanho do arquivo
            if path.stat().st_size == 0:
                self._log_error(f"Arquivo vazio: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            self._log_error(f"Erro ao validar estrutura: {str(e)}")
            return False
    
    def obter_metadados(self, file_path: str) -> Dict[str, Any]:
        """
        Obtém metadados básicos do arquivo
        
        Args:
            file_path: Caminho para o arquivo
        
        Returns:
            Dicionário com metadados
        """
        if file_path in self._metadados_cache:
            return self._metadados_cache[file_path]
        
        try:
            path = Path(file_path)
            metadados = {
                'nome_arquivo': path.name,
                'tamanho_bytes': path.stat().st_size,
                'extensao': path.suffix.lower(),
                'caminho_absoluto': str(path.absolute()),
                'existe': path.exists(),
                'tipo_suportado': self._verificar_tipo_suportado(file_path)
            }
            
            # Cache dos metadados
            self._metadados_cache[file_path] = metadados
            return metadados
            
        except Exception as e:
            self._log_error(f"Erro ao obter metadados: {str(e)}")
            return {
                'nome_arquivo': Path(file_path).name,
                'erro': str(e)
            }
    
    def _verificar_tipo_suportado(self, file_path: str) -> bool:
        """
        Verifica se o tipo de arquivo é suportado
        
        Args:
            file_path: Caminho para o arquivo
        
        Returns:
            True se o tipo é suportado
        """
        try:
            # Ler primeiras linhas para identificar tipo
            with open(file_path, 'r', encoding=self._encoding_padrao) as f:
                conteudo = f.read(1000)  # Ler apenas os primeiros 1000 caracteres
            
            # Verificar se contém indicadores de documentos fiscais
            indicadores = ['<nfeProc>', '<NFe>', '<nfse>', '<NFS-e>', '<cteProc>', '<CTe>']
            return any(indicator in conteudo for indicator in indicadores)
            
        except Exception as e:
            self._log_error(f"Erro ao verificar tipo suportado: {str(e)}")
            return False
    
    def _limpar_cache_metadados(self) -> None:
        """Limpa o cache de metadados"""
        self._metadados_cache.clear()
    
    def _log_info(self, message: str) -> None:
        """Log de informação"""
        self._logger.info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log de aviso"""
        self._logger.warning(message)
    
    def _log_error(self, message: str) -> None:
        """Log de erro"""
        self._logger.error(message)
