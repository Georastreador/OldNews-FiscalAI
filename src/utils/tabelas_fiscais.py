"""
FiscalAI MVP - Gerenciador de Tabelas Fiscais
Integra o ncm_cfop_reader.py com a aplicação
"""

import sys
from pathlib import Path
import pandas as pd
from typing import Optional, Dict, Any
import logging

# Adicionar o diretório atual ao path para importar ncm_cfop_reader
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ncm_cfop_reader import LeitorTabelasFiscais
    NCM_CFOP_READER_AVAILABLE = True
except ImportError:
    NCM_CFOP_READER_AVAILABLE = False
    logging.warning("ncm_cfop_reader.py não encontrado. Tabelas fiscais não estarão disponíveis.")

logger = logging.getLogger(__name__)

class GerenciadorTabelasFiscais:
    """Gerenciador centralizado de tabelas fiscais NCM e CFOP"""
    
    def __init__(self):
        self.leitor = None
        self.df_ncm = None
        self.df_cfop = None
        self.df_cfop_categorizado = None
        self._inicializado = False
        
        if NCM_CFOP_READER_AVAILABLE:
            self.leitor = LeitorTabelasFiscais()
    
    def inicializar(self, 
                   caminho_ncm: Optional[str] = None,
                   caminho_cfop: Optional[str] = None) -> bool:
        """
        Inicializa as tabelas fiscais
        
        Args:
            caminho_ncm: Caminho para arquivo NCM (opcional)
            caminho_cfop: Caminho para arquivo CFOP (opcional)
            
        Returns:
            True se inicializado com sucesso
        """
        if not NCM_CFOP_READER_AVAILABLE:
            logger.error("ncm_cfop_reader.py não está disponível")
            return False
        
        try:
            # Caminhos padrão
            if caminho_ncm is None:
                caminho_ncm = self._encontrar_arquivo_ncm()
            
            if caminho_cfop is None:
                caminho_cfop = self._encontrar_arquivo_cfop()
            
            # Carregar tabelas
            if caminho_ncm and Path(caminho_ncm).exists():
                logger.info(f"Carregando tabela NCM: {caminho_ncm}")
                self.df_ncm = self.leitor.carregar_ncm(caminho_ncm)
                logger.info(f"Tabela NCM carregada: {len(self.df_ncm)} registros")
            else:
                logger.warning("Arquivo NCM não encontrado, usando dados mock")
                self.df_ncm = self._criar_tabela_ncm_mock()
            
            if caminho_cfop and Path(caminho_cfop).exists():
                logger.info(f"Carregando tabela CFOP: {caminho_cfop}")
                self.df_cfop = self.leitor.carregar_cfop_estruturado(caminho_cfop)
                logger.info(f"Tabela CFOP carregada: {len(self.df_cfop)} registros")
            else:
                logger.warning("Arquivo CFOP não encontrado, usando dados mock")
                self.df_cfop = self._criar_tabela_cfop_mock()
            
            self._inicializado = True
            logger.info("Tabelas fiscais inicializadas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar tabelas fiscais: {e}")
            return False
    
    def _encontrar_arquivo_ncm(self) -> Optional[str]:
        """Encontra arquivo NCM automaticamente"""
        possiveis_caminhos = [
            # FiscalAI_MVP
            Path(__file__).parent.parent.parent / "data" / "tables" / "BaseDESC_NCM.csv",
            Path(__file__).parent.parent.parent / "data" / "tables" / "BaseDESC_NCM.zip",
            
            # Eleven base
            Path(__file__).parent.parent.parent.parent / "Eleven base" / "BaseDESC_NCM.csv",
            Path(__file__).parent.parent.parent.parent / "Eleven base" / "BaseDESC_NCM.zip",
            
            # Outros locais possíveis
            Path(__file__).parent.parent.parent / "BaseDESC_NCM.csv",
            Path(__file__).parent.parent.parent / "BaseDESC_NCM.zip",
        ]
        
        for caminho in possiveis_caminhos:
            if caminho.exists():
                return str(caminho)
        
        return None
    
    def _encontrar_arquivo_cfop(self) -> Optional[str]:
        """Encontra arquivo CFOP automaticamente"""
        possiveis_caminhos = [
            # FiscalAI_MVP
            Path(__file__).parent.parent.parent / "data" / "tables" / "CFOPcpoy.xlsx",
            Path(__file__).parent.parent.parent / "data" / "tables" / "Tabela_CFOPOperacoesGeradorasCreditos.xls",
            
            # Eleven base
            Path(__file__).parent.parent.parent.parent / "Eleven base" / "CFOPcpoy.xlsx",
            Path(__file__).parent.parent.parent.parent / "Eleven base" / "Tabela_CFOPOperacoesGeradorasCreditos.xls",
            
            # Outros locais possíveis
            Path(__file__).parent.parent.parent / "CFOPcpoy.xlsx",
            Path(__file__).parent.parent.parent / "Tabela_CFOPOperacoesGeradorasCreditos.xls",
        ]
        
        for caminho in possiveis_caminhos:
            if caminho.exists():
                return str(caminho)
        
        return None
    
    def obter_tabela_ncm(self) -> pd.DataFrame:
        """Retorna tabela NCM"""
        if not self._inicializado:
            self.inicializar()
        return self.df_ncm if self.df_ncm is not None else self._criar_tabela_ncm_mock()
    
    def obter_tabela_cfop(self) -> pd.DataFrame:
        """Retorna tabela CFOP"""
        if not self._inicializado:
            self.inicializar()
        return self.df_cfop if self.df_cfop is not None else self._criar_tabela_cfop_mock()
    
    def buscar_ncm(self, codigo_ncm: str) -> Optional[Dict[str, Any]]:
        """Busca informações de um NCM"""
        df_ncm = self.obter_tabela_ncm()
        
        if df_ncm.empty or codigo_ncm not in df_ncm.index:
            return None
        
        return {
            "codigo": codigo_ncm,
            "descricao": df_ncm.loc[codigo_ncm, "descricao"],
            "categoria": df_ncm.loc[codigo_ncm, "categoria"] if "categoria" in df_ncm.columns else None
        }
    
    def buscar_cfop(self, codigo_cfop: str) -> Optional[Dict[str, Any]]:
        """Busca informações de um CFOP"""
        df_cfop = self.obter_tabela_cfop()
        
        if df_cfop.empty or codigo_cfop not in df_cfop.index:
            return None
        
        return {
            "codigo": codigo_cfop,
            "descricao": df_cfop.loc[codigo_cfop, "descricao"],
            "categoria": df_cfop.loc[codigo_cfop, "categoria"] if "categoria" in df_cfop.columns else None
        }
    
    def validar_ncm(self, codigo_ncm: str) -> bool:
        """Valida se um código NCM existe"""
        return self.buscar_ncm(codigo_ncm) is not None
    
    def validar_cfop(self, codigo_cfop: str) -> bool:
        """Valida se um código CFOP existe"""
        return self.buscar_cfop(codigo_cfop) is not None
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas das tabelas"""
        df_ncm = self.obter_tabela_ncm()
        df_cfop = self.obter_tabela_cfop()
        
        return {
            "ncm": {
                "total_registros": len(df_ncm),
                "colunas": list(df_ncm.columns) if not df_ncm.empty else [],
                "inicializado": self._inicializado
            },
            "cfop": {
                "total_registros": len(df_cfop),
                "colunas": list(df_cfop.columns) if not df_cfop.empty else [],
                "inicializado": self._inicializado
            },
            "ncm_cfop_reader_disponivel": NCM_CFOP_READER_AVAILABLE
        }
    
    def _criar_tabela_ncm_mock(self) -> pd.DataFrame:
        """Cria tabela NCM mock para testes"""
        dados = {
            'ncm': [
                '12345678', '87654321', '11111111', '22222222', '33333333',
                '44444444', '55555555', '66666666', '77777777', '88888888'
            ],
            'descricao': [
                'Produto eletrônico genérico',
                'Componente mecânico',
                'Material de construção',
                'Produto químico',
                'Alimento processado',
                'Têxtil',
                'Produto farmacêutico',
                'Equipamento industrial',
                'Produto agrícola',
                'Produto mineral'
            ]
        }
        
        df = pd.DataFrame(dados)
        df.set_index('ncm', inplace=True)
        return df
    
    def _criar_tabela_cfop_mock(self) -> pd.DataFrame:
        """Cria tabela CFOP mock para testes"""
        dados = {
            'cfop': [
                '1101', '1102', '1201', '1202', '2101',
                '2102', '2201', '2202', '3101', '3102'
            ],
            'descricao': [
                'Compra para comercialização',
                'Compra para industrialização',
                'Venda de mercadoria',
                'Venda de produto industrializado',
                'Compra para uso',
                'Compra para consumo',
                'Venda de ativo imobilizado',
                'Venda de mercadoria',
                'Entrada de mercadoria',
                'Saída de mercadoria'
            ]
        }
        
        df = pd.DataFrame(dados)
        df.set_index('cfop', inplace=True)
        return df

# Alias para compatibilidade
TabelasFiscais = GerenciadorTabelasFiscais

# Instância global do gerenciador
_tabelas_fiscais_manager = None

def get_tabelas_fiscais_manager() -> GerenciadorTabelasFiscais:
    """Retorna instância global do gerenciador de tabelas fiscais"""
    global _tabelas_fiscais_manager
    if _tabelas_fiscais_manager is None:
        _tabelas_fiscais_manager = GerenciadorTabelasFiscais()
    return _tabelas_fiscais_manager

def inicializar_tabelas_fiscais(caminho_ncm: Optional[str] = None,
                               caminho_cfop: Optional[str] = None) -> bool:
    """Inicializa as tabelas fiscais globalmente"""
    manager = get_tabelas_fiscais_manager()
    return manager.inicializar(caminho_ncm, caminho_cfop)

if __name__ == "__main__":
    # Teste do gerenciador
    print("🧪 Testando Gerenciador de Tabelas Fiscais")
    print("=" * 50)
    
    manager = get_tabelas_fiscais_manager()
    
    # Inicializar
    sucesso = manager.inicializar()
    print(f"✅ Inicialização: {'Sucesso' if sucesso else 'Falha'}")
    
    # Estatísticas
    stats = manager.obter_estatisticas()
    print(f"\n📊 Estatísticas:")
    print(f"  NCM: {stats['ncm']['total_registros']} registros")
    print(f"  CFOP: {stats['cfop']['total_registros']} registros")
    print(f"  ncm_cfop_reader disponível: {stats['ncm_cfop_reader_disponivel']}")
    
    # Teste de busca
    print(f"\n🔍 Teste de busca:")
    ncm_info = manager.buscar_ncm("12345678")
    if ncm_info:
        print(f"  NCM 12345678: {ncm_info['descricao']}")
    
    cfop_info = manager.buscar_cfop("1101")
    if cfop_info:
        print(f"  CFOP 1101: {cfop_info['descricao']}")
    
    print("\n🎉 Teste concluído!")
