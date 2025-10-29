"""
FiscalAI MVP - Configurador de Tabelas Fiscais
Sistema híbrido para carregamento inteligente de tabelas NCM e CFOP
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import logging
from enum import Enum
import json

# Adicionar o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ncm_cfop_reader import LeitorTabelasFiscais
    NCM_CFOP_READER_AVAILABLE = True
except ImportError:
    NCM_CFOP_READER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModoCarregamento(str, Enum):
    """Modos de carregamento das tabelas fiscais"""
    AUTOMATICO = "automatico"          # Detecção automática inteligente
    MANUAL = "manual"                  # Usuário especifica caminhos
    MOCK = "mock"                      # Usa dados simulados
    HIBRIDO = "hibrido"                # Combina dados reais + mock


class ConfiguradorTabelasFiscais:
    """
    Configurador inteligente para carregamento de tabelas NCM e CFOP
    
    Funcionalidades:
    - Detecção automática de arquivos CSV
    - Validação de formatos
    - Fallback para dados mock
    - Configuração via interface
    - Cache de configurações
    """
    
    def __init__(self):
        self.leitor = None
        self.modo_atual = ModoCarregamento.AUTOMATICO
        self.caminhos_configurados = {}
        self.tabelas_carregadas = {}
        self._inicializado = False
        
        # Diretórios padrão para busca automática
        self.diretorios_busca = [
            Path.cwd(),
            Path.cwd() / "data",
            Path.cwd() / "tabelas",
            Path.cwd() / "dados",
            Path.home() / "Documents" / "FiscalAI",
            Path.home() / "Downloads"
        ]
        
        # Padrões de arquivos para detecção automática
        self.padroes_ncm = [
            "ncm*.csv",
            "*ncm*.csv", 
            "produtos*.csv",
            "tabela_ncm*.csv",
            "ncm_*.csv"
        ]
        
        self.padroes_cfop = [
            "cfop*.csv",
            "*cfop*.csv",
            "operacoes*.csv", 
            "tabela_cfop*.csv",
            "cfop_*.csv"
        ]
        
        if NCM_CFOP_READER_AVAILABLE:
            self.leitor = LeitorTabelasFiscais()
    
    def configurar_modo(self, modo: ModoCarregamento, 
                       caminho_ncm: Optional[str] = None,
                       caminho_cfop: Optional[str] = None) -> Dict[str, Any]:
        """
        Configura o modo de carregamento das tabelas
        
        Args:
            modo: Modo de carregamento
            caminho_ncm: Caminho opcional para arquivo NCM
            caminho_cfop: Caminho opcional para arquivo CFOP
            
        Returns:
            Dict com status da configuração
        """
        self.modo_atual = modo
        resultado = {
            "modo": modo.value,
            "sucesso": False,
            "tabelas_carregadas": [],
            "erros": [],
            "avisos": []
        }
        
        try:
            if modo == ModoCarregamento.AUTOMATICO:
                resultado = self._configurar_automatico()
            elif modo == ModoCarregamento.MANUAL:
                resultado = self._configurar_manual(caminho_ncm, caminho_cfop)
            elif modo == ModoCarregamento.MOCK:
                resultado = self._configurar_mock()
            elif modo == ModoCarregamento.HIBRIDO:
                resultado = self._configurar_hibrido(caminho_ncm, caminho_cfop)
            
            self._inicializado = True
            
        except Exception as e:
            logger.error(f"Erro ao configurar modo {modo.value}: {e}")
            resultado["erros"].append(str(e))
            resultado["sucesso"] = False
        
        return resultado
    
    def _configurar_automatico(self) -> Dict[str, Any]:
        """Configuração automática inteligente"""
        resultado = {
            "modo": "automatico",
            "sucesso": False,
            "tabelas_carregadas": [],
            "erros": [],
            "avisos": []
        }
        
        # Buscar arquivos NCM
        arquivo_ncm = self._buscar_arquivo_automatico(self.padroes_ncm)
        if arquivo_ncm:
            resultado["tabelas_carregadas"].append(f"NCM: {arquivo_ncm}")
            self.caminhos_configurados["ncm"] = str(arquivo_ncm)
        
        # Buscar arquivos CFOP
        arquivo_cfop = self._buscar_arquivo_automatico(self.padroes_cfop)
        if arquivo_cfop:
            resultado["tabelas_carregadas"].append(f"CFOP: {arquivo_cfop}")
            self.caminhos_configurados["cfop"] = str(arquivo_cfop)
        
        # Se encontrou pelo menos uma tabela, tentar carregar
        if self.caminhos_configurados:
            sucesso_carregamento = self._carregar_tabelas()
            if sucesso_carregamento:
                resultado["sucesso"] = True
            else:
                resultado["avisos"].append("Arquivos encontrados mas falha no carregamento. Usando dados mock.")
                self._carregar_dados_mock()
                resultado["sucesso"] = True
        else:
            resultado["avisos"].append("Nenhum arquivo encontrado automaticamente. Usando dados mock.")
            self._carregar_dados_mock()
            resultado["sucesso"] = True
        
        return resultado
    
    def _configurar_manual(self, caminho_ncm: Optional[str], caminho_cfop: Optional[str]) -> Dict[str, Any]:
        """Configuração manual com caminhos específicos"""
        resultado = {
            "modo": "manual",
            "sucesso": False,
            "tabelas_carregadas": [],
            "erros": [],
            "avisos": []
        }
        
        if caminho_ncm and os.path.exists(caminho_ncm):
            self.caminhos_configurados["ncm"] = caminho_ncm
            resultado["tabelas_carregadas"].append(f"NCM: {caminho_ncm}")
        elif caminho_ncm:
            resultado["erros"].append(f"Arquivo NCM não encontrado: {caminho_ncm}")
        
        if caminho_cfop and os.path.exists(caminho_cfop):
            self.caminhos_configurados["cfop"] = caminho_cfop
            resultado["tabelas_carregadas"].append(f"CFOP: {caminho_cfop}")
        elif caminho_cfop:
            resultado["erros"].append(f"Arquivo CFOP não encontrado: {caminho_cfop}")
        
        if self.caminhos_configurados:
            sucesso_carregamento = self._carregar_tabelas()
            if sucesso_carregamento:
                resultado["sucesso"] = True
            else:
                resultado["erros"].append("Falha no carregamento dos arquivos especificados")
        else:
            resultado["avisos"].append("Nenhum caminho válido fornecido. Usando dados mock.")
            self._carregar_dados_mock()
            resultado["sucesso"] = True
        
        return resultado
    
    def _configurar_mock(self) -> Dict[str, Any]:
        """Configuração com dados mock"""
        resultado = {
            "modo": "mock",
            "sucesso": True,
            "tabelas_carregadas": ["NCM: Dados Mock", "CFOP: Dados Mock"],
            "erros": [],
            "avisos": ["Usando dados simulados para demonstração"]
        }
        
        self._carregar_dados_mock()
        return resultado
    
    def _configurar_hibrido(self, caminho_ncm: Optional[str], caminho_cfop: Optional[str]) -> Dict[str, Any]:
        """Configuração híbrida: dados reais + mock para complementar"""
        resultado = {
            "modo": "hibrido",
            "sucesso": False,
            "tabelas_carregadas": [],
            "erros": [],
            "avisos": []
        }
        
        # Tentar carregar dados reais primeiro
        if caminho_ncm and os.path.exists(caminho_ncm):
            self.caminhos_configurados["ncm"] = caminho_ncm
            resultado["tabelas_carregadas"].append(f"NCM: {caminho_ncm}")
        else:
            # Buscar automaticamente
            arquivo_ncm = self._buscar_arquivo_automatico(self.padroes_ncm)
            if arquivo_ncm:
                self.caminhos_configurados["ncm"] = str(arquivo_ncm)
                resultado["tabelas_carregadas"].append(f"NCM: {arquivo_ncm}")
        
        if caminho_cfop and os.path.exists(caminho_cfop):
            self.caminhos_configurados["cfop"] = caminho_cfop
            resultado["tabelas_carregadas"].append(f"CFOP: {caminho_cfop}")
        else:
            # Buscar automaticamente
            arquivo_cfop = self._buscar_arquivo_automatico(self.padroes_cfop)
            if arquivo_cfop:
                self.caminhos_configurados["cfop"] = str(arquivo_cfop)
                resultado["tabelas_carregadas"].append(f"CFOP: {arquivo_cfop}")
        
        # Carregar dados reais disponíveis
        sucesso_real = self._carregar_tabelas()
        
        # Complementar com dados mock se necessário
        if "ncm" not in self.tabelas_carregadas:
            self._carregar_dados_mock_ncm()
            resultado["avisos"].append("NCM: Complementado com dados mock")
        
        if "cfop" not in self.tabelas_carregadas:
            self._carregar_dados_mock_cfop()
            resultado["avisos"].append("CFOP: Complementado com dados mock")
        
        resultado["sucesso"] = True
        return resultado
    
    def _buscar_arquivo_automatico(self, padroes: List[str]) -> Optional[Path]:
        """Busca arquivo automaticamente nos diretórios configurados"""
        for diretorio in self.diretorios_busca:
            if not diretorio.exists():
                continue
                
            for padrao in padroes:
                for arquivo in diretorio.glob(padrao):
                    if arquivo.is_file() and self._validar_arquivo_csv(arquivo):
                        return arquivo
        
        return None
    
    def _validar_arquivo_csv(self, caminho: Path) -> bool:
        """Valida se arquivo CSV tem formato adequado"""
        try:
            # Ler apenas as primeiras linhas para validação
            df = pd.read_csv(caminho, nrows=5, encoding='utf-8-sig')
            
            # Verificar se tem colunas mínimas
            colunas = [col.lower() for col in df.columns]
            
            # Para NCM: deve ter coluna com 'ncm' ou 'codigo'
            if any('ncm' in col or 'codigo' in col for col in colunas):
                return True
            
            # Para CFOP: deve ter coluna com 'cfop' ou 'codigo'
            if any('cfop' in col or 'codigo' in col for col in colunas):
                return True
                
            return False
            
        except Exception:
            return False
    
    def _carregar_tabelas(self) -> bool:
        """Carrega tabelas usando o leitor"""
        if not self.leitor:
            return False
        
        sucesso = True
        
        try:
            if "ncm" in self.caminhos_configurados:
                self.leitor.carregar_ncm(self.caminhos_configurados["ncm"])
                self.tabelas_carregadas["ncm"] = self.leitor.df_ncm
                logger.info(f"NCM carregado: {len(self.tabelas_carregadas['ncm'])} registros")
            
            if "cfop" in self.caminhos_configurados:
                self.leitor.carregar_cfop_estruturado(self.caminhos_configurados["cfop"])
                self.tabelas_carregadas["cfop"] = self.leitor.df_cfop
                logger.info(f"CFOP carregado: {len(self.tabelas_carregadas['cfop'])} registros")
                
        except Exception as e:
            logger.error(f"Erro ao carregar tabelas: {e}")
            sucesso = False
        
        return sucesso
    
    def _carregar_dados_mock(self):
        """Carrega dados mock para ambas as tabelas"""
        self._carregar_dados_mock_ncm()
        self._carregar_dados_mock_cfop()
    
    def _carregar_dados_mock_ncm(self):
        """Carrega dados mock para NCM"""
        dados_ncm = {
            "codigo": ["12345678", "87654321", "11223344", "44332211", "55667788"],
            "descricao": [
                "Produto de Exemplo 1",
                "Produto de Exemplo 2", 
                "Produto de Exemplo 3",
                "Produto de Exemplo 4",
                "Produto de Exemplo 5"
            ],
            "categoria": ["Categoria A", "Categoria B", "Categoria A", "Categoria C", "Categoria B"]
        }
        
        self.tabelas_carregadas["ncm"] = pd.DataFrame(dados_ncm)
        self.tabelas_carregadas["ncm"].set_index("codigo", inplace=True)
    
    def _carregar_dados_mock_cfop(self):
        """Carrega dados mock para CFOP"""
        dados_cfop = {
            "codigo": ["1101", "1102", "1201", "1202", "2101"],
            "descricao": [
                "Compra para Industrialização",
                "Compra para Comercialização",
                "Devolução de Venda",
                "Devolução de Compra", 
                "Venda para Industrialização"
            ],
            "categoria": ["01", "01", "12", "12", "21"]
        }
        
        self.tabelas_carregadas["cfop"] = pd.DataFrame(dados_cfop)
        self.tabelas_carregadas["cfop"].set_index("codigo", inplace=True)
    
    def obter_tabela_ncm(self) -> pd.DataFrame:
        """Retorna tabela NCM"""
        if not self._inicializado:
            self.configurar_modo(ModoCarregamento.AUTOMATICO)
        
        return self.tabelas_carregadas.get("ncm", pd.DataFrame())
    
    def obter_tabela_cfop(self) -> pd.DataFrame:
        """Retorna tabela CFOP"""
        if not self._inicializado:
            self.configurar_modo(ModoCarregamento.AUTOMATICO)
        
        return self.tabelas_carregadas.get("cfop", pd.DataFrame())
    
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
    
    def obter_status(self) -> Dict[str, Any]:
        """Retorna status atual da configuração"""
        return {
            "modo": self.modo_atual.value,
            "inicializado": self._inicializado,
            "tabelas_disponiveis": list(self.tabelas_carregadas.keys()),
            "caminhos_configurados": self.caminhos_configurados,
            "ncm_reader_disponivel": NCM_CFOP_READER_AVAILABLE,
            "registros_ncm": len(self.tabelas_carregadas.get("ncm", [])),
            "registros_cfop": len(self.tabelas_carregadas.get("cfop", []))
        }
    
    def salvar_configuracao(self, caminho: str = "config_tabelas.json"):
        """Salva configuração atual"""
        config = {
            "modo": self.modo_atual.value,
            "caminhos": self.caminhos_configurados,
            "diretorios_busca": [str(d) for d in self.diretorios_busca]
        }
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def carregar_configuracao(self, caminho: str = "config_tabelas.json"):
        """Carrega configuração salva"""
        if not os.path.exists(caminho):
            return False
        
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            modo = ModoCarregamento(config.get("modo", "automatico"))
            caminhos = config.get("caminhos", {})
            
            return self.configurar_modo(
                modo,
                caminhos.get("ncm"),
                caminhos.get("cfop")
            )
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return False


# Instância global
configurador_global = ConfiguradorTabelasFiscais()


def get_configurador_tabelas() -> ConfiguradorTabelasFiscais:
    """Retorna instância global do configurador"""
    return configurador_global


def configurar_tabelas_fiscais(modo: str = "automatico", 
                              caminho_ncm: Optional[str] = None,
                              caminho_cfop: Optional[str] = None) -> Dict[str, Any]:
    """
    Função de conveniência para configurar tabelas fiscais
    
    Args:
        modo: "automatico", "manual", "mock", "hibrido"
        caminho_ncm: Caminho para arquivo NCM (opcional)
        caminho_cfop: Caminho para arquivo CFOP (opcional)
    
    Returns:
        Dict com resultado da configuração
    """
    try:
        modo_enum = ModoCarregamento(modo.lower())
        return configurador_global.configurar_modo(modo_enum, caminho_ncm, caminho_cfop)
    except ValueError:
        return {
            "sucesso": False,
            "erros": [f"Modo inválido: {modo}. Use: automatico, manual, mock, hibrido"]
        }
