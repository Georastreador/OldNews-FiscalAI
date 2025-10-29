"""
OldNews FiscalAI - Base Agent
Classe base para todos os agentes do sistema
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
from crewai import Agent
import logging

from .interfaces import IAgent


class BaseAgent(IAgent):
    """
    Classe base para todos os agentes do sistema
    
    Implementa funcionalidades comuns e define interface padrão
    """
    
    def __init__(self, 
                 llm: Any,
                 role: str,
                 goal: str,
                 backstory: str,
                 verbose: bool = True,
                 allow_delegation: bool = False):
        """
        Inicializa o agente base
        
        Args:
            llm: Instância do modelo de linguagem
            role: Papel do agente
            goal: Objetivo do agente
            backstory: Histórico/contexto do agente
            verbose: Se deve ser verboso
            allow_delegation: Se pode delegar tarefas
        """
        self._llm = llm
        self._role = role
        self._goal = goal
        self._backstory = backstory
        self._verbose = verbose
        self._allow_delegation = allow_delegation
        self._resultado = None
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Criar agente CrewAI
        self._agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            verbose=verbose,
            allow_delegation=allow_delegation,
        )
    
    @property
    def llm(self) -> Any:
        """Obtém o modelo de linguagem"""
        return self._llm
    
    @property
    def role(self) -> str:
        """Obtém o papel do agente"""
        return self._role
    
    @property
    def goal(self) -> str:
        """Obtém o objetivo do agente"""
        return self._goal
    
    @property
    def resultado(self) -> Any:
        """Obtém o resultado da última execução"""
        return self._resultado
    
    @resultado.setter
    def resultado(self, value: Any) -> None:
        """Define o resultado da execução"""
        self._resultado = value
    
    @abstractmethod
    def executar(self, *args, **kwargs) -> Any:
        """Executa a tarefa principal do agente"""
        pass
    
    @abstractmethod
    def validar_entrada(self, *args, **kwargs) -> bool:
        """Valida os dados de entrada"""
        pass
    
    def obter_resultado(self) -> Any:
        """Obtém o resultado da execução"""
        return self._resultado
    
    def _log_info(self, message: str) -> None:
        """Log de informação"""
        self._logger.info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log de aviso"""
        self._logger.warning(message)
    
    def _log_error(self, message: str) -> None:
        """Log de erro"""
        self._logger.error(message)
    
    def _validar_llm(self) -> bool:
        """Valida se o LLM está disponível"""
        if self._llm is None:
            self._log_error("LLM não foi inicializado")
            return False
        return True
    
    def _executar_com_validacao(self, *args, **kwargs) -> Any:
        """Executa com validação prévia"""
        if not self._validar_llm():
            raise ValueError("LLM não está disponível")
        
        if not self.validar_entrada(*args, **kwargs):
            raise ValueError("Dados de entrada inválidos")
        
        try:
            resultado = self.executar(*args, **kwargs)
            self.resultado = resultado
            return resultado
        except Exception as e:
            self._log_error(f"Erro na execução: {str(e)}")
            raise
