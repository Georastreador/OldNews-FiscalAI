"""
FiscalAI MVP - Gerenciador de Tabelas Fiscais V2
Versão atualizada que usa o configurador inteligente
"""

import sys
from pathlib import Path
import pandas as pd
from typing import Optional, Dict, Any
import logging

# Importar o configurador inteligente
from .configurador_tabelas import get_configurador_tabelas, ModoCarregamento

logger = logging.getLogger(__name__)


class GerenciadorTabelasFiscaisV2:
    """
    Gerenciador centralizado de tabelas fiscais NCM e CFOP
    Versão 2 que usa o configurador inteligente
    """
    
    def __init__(self):
        self.configurador = get_configurador_tabelas()
        self._inicializado = False
    
    def inicializar(self, 
                   modo: str = "automatico",
                   caminho_ncm: Optional[str] = None,
                   caminho_cfop: Optional[str] = None) -> bool:
        """
        Inicializa o gerenciador com configuração específica
        
        Args:
            modo: Modo de carregamento ("automatico", "manual", "mock", "hibrido")
            caminho_ncm: Caminho para arquivo NCM (opcional)
            caminho_cfop: Caminho para arquivo CFOP (opcional)
        
        Returns:
            bool: True se inicialização foi bem-sucedida
        """
        try:
            resultado = self.configurador.configurar_modo(
                ModoCarregamento(modo),
                caminho_ncm,
                caminho_cfop
            )
            
            self._inicializado = resultado["sucesso"]
            
            if resultado["sucesso"]:
                logger.info(f"Gerenciador inicializado com modo: {modo}")
                if resultado["tabelas_carregadas"]:
                    logger.info(f"Tabelas carregadas: {resultado['tabelas_carregadas']}")
                if resultado["avisos"]:
                    for aviso in resultado["avisos"]:
                        logger.warning(aviso)
            else:
                logger.error(f"Falha na inicialização: {resultado['erros']}")
            
            return self._inicializado
            
        except Exception as e:
            logger.error(f"Erro na inicialização: {e}")
            return False
    
    def obter_tabela_ncm(self) -> pd.DataFrame:
        """Retorna tabela NCM"""
        if not self._inicializado:
            self.inicializar()
        return self.configurador.obter_tabela_ncm()
    
    def obter_tabela_cfop(self) -> pd.DataFrame:
        """Retorna tabela CFOP"""
        if not self._inicializado:
            self.inicializar()
        return self.configurador.obter_tabela_cfop()
    
    def buscar_ncm(self, codigo_ncm: str) -> Optional[Dict[str, Any]]:
        """Busca informações de um NCM"""
        df_ncm = self.obter_tabela_ncm()
        
        if df_ncm.empty:
            return None
        
        # Buscar por código
        if codigo_ncm in df_ncm.index:
            return {
                "codigo": codigo_ncm,
                "descricao": df_ncm.loc[codigo_ncm, "descricao"],
                "categoria": df_ncm.loc[codigo_ncm, "categoria"] if "categoria" in df_ncm.columns else None
            }
        
        # Buscar por similaridade se não encontrar exato
        for idx in df_ncm.index:
            if str(idx).startswith(codigo_ncm) or codigo_ncm in str(idx):
                return {
                    "codigo": idx,
                    "descricao": df_ncm.loc[idx, "descricao"],
                    "categoria": df_ncm.loc[idx, "categoria"] if "categoria" in df_ncm.columns else None
                }
        
        return None
    
    def buscar_cfop(self, codigo_cfop: str) -> Optional[Dict[str, Any]]:
        """Busca informações de um CFOP"""
        df_cfop = self.obter_tabela_cfop()
        
        if df_cfop.empty:
            return None
        
        # Buscar por código
        if codigo_cfop in df_cfop.index:
            return {
                "codigo": codigo_cfop,
                "descricao": df_cfop.loc[codigo_cfop, "descricao"],
                "categoria": df_cfop.loc[codigo_cfop, "categoria"] if "categoria" in df_cfop.columns else None
            }
        
        # Buscar por similaridade se não encontrar exato
        for idx in df_cfop.index:
            if str(idx).startswith(codigo_cfop) or codigo_cfop in str(idx):
                return {
                    "codigo": idx,
                    "descricao": df_cfop.loc[idx, "descricao"],
                    "categoria": df_cfop.loc[idx, "categoria"] if "categoria" in df_cfop.columns else None
                }
        
        return None
    
    def validar_ncm(self, codigo_ncm: str) -> bool:
        """Valida se um código NCM existe"""
        return self.buscar_ncm(codigo_ncm) is not None
    
    def validar_cfop(self, codigo_cfop: str) -> bool:
        """Valida se um código CFOP existe"""
        return self.buscar_cfop(codigo_cfop) is not None
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas das tabelas"""
        status = self.configurador.obter_status()
        
        return {
            "modo_carregamento": status["modo"],
            "tabelas_disponiveis": status["tabelas_disponiveis"],
            "registros_ncm": status["registros_ncm"],
            "registros_cfop": status["registros_cfop"],
            "inicializado": status["inicializado"],
            "ncm_reader_disponivel": status["ncm_reader_disponivel"]
        }
    
    def reconfigurar(self, modo: str, caminho_ncm: Optional[str] = None, caminho_cfop: Optional[str] = None) -> bool:
        """Reconfigura o gerenciador com novos parâmetros"""
        return self.inicializar(modo, caminho_ncm, caminho_cfop)
    
    def obter_configurador(self):
        """Retorna instância do configurador para acesso direto"""
        return self.configurador


# Instância global
gerenciador_global = GerenciadorTabelasFiscaisV2()


def get_tabelas_fiscais() -> GerenciadorTabelasFiscaisV2:
    """Retorna instância global do gerenciador de tabelas fiscais"""
    return gerenciador_global


def inicializar_tabelas_fiscais(modo: str = "automatico", 
                               caminho_ncm: Optional[str] = None,
                               caminho_cfop: Optional[str] = None) -> bool:
    """
    Função de conveniência para inicializar tabelas fiscais
    
    Args:
        modo: Modo de carregamento
        caminho_ncm: Caminho para arquivo NCM
        caminho_cfop: Caminho para arquivo CFOP
    
    Returns:
        bool: True se inicialização foi bem-sucedida
    """
    return gerenciador_global.inicializar(modo, caminho_ncm, caminho_cfop)
