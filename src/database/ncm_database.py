"""
FiscalAI MVP - Base de Dados NCM Expandida
Sistema para gerenciar e expandir base de dados NCM
"""

import pandas as pd
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sqlite3
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)

@dataclass
class NCMEntry:
    """Entrada da base de dados NCM"""
    codigo: str
    descricao: str
    capitulo: str
    posicao: str
    subposicao: str
    item: str
    subitem: str
    categoria: str
    subcategoria: str
    observacoes: str
    fonte: str
    validado: bool
    data_atualizacao: datetime

@dataclass
class NCMStatistics:
    """Estatísticas da base de dados NCM"""
    total_entries: int
    validated_entries: int
    entries_by_chapter: Dict[str, int]
    entries_by_source: Dict[str, int]
    last_update: datetime
    coverage_percentage: float

class NCMDatabaseManager:
    """
    Gerenciador da base de dados NCM expandida
    
    Funcionalidades:
    - Carregamento de dados oficiais
    - Enriquecimento com dados externos
    - Validação e limpeza
    - Busca inteligente
    - Estatísticas e métricas
    """
    
    def __init__(self, db_path: str = "data/ncm_database.db"):
        """
        Inicializa o gerenciador da base de dados
        
        Args:
            db_path: Caminho do banco de dados
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializar banco de dados
        self._init_database()
        
        # Carregar dados iniciais
        self._load_initial_data()
    
    def _init_database(self):
        """Inicializa estrutura do banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela principal de NCM
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ncm_entries (
                    codigo TEXT PRIMARY KEY,
                    descricao TEXT NOT NULL,
                    capitulo TEXT,
                    posicao TEXT,
                    subposicao TEXT,
                    item TEXT,
                    subitem TEXT,
                    categoria TEXT,
                    subcategoria TEXT,
                    observacoes TEXT,
                    fonte TEXT,
                    validado BOOLEAN DEFAULT FALSE,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de sinônimos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ncm_synonyms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_ncm TEXT,
                    sinonimo TEXT,
                    tipo TEXT,
                    fonte TEXT,
                    FOREIGN KEY (codigo_ncm) REFERENCES ncm_entries (codigo)
                )
            ''')
            
            # Tabela de validações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ncm_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_ncm TEXT,
                    usuario TEXT,
                    acao TEXT,
                    comentario TEXT,
                    data_validacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (codigo_ncm) REFERENCES ncm_entries (codigo)
                )
            ''')
            
            conn.commit()
    
    def _load_initial_data(self):
        """Carrega dados iniciais da base NCM"""
        # Verificar se já existem dados
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ncm_entries")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("Carregando dados iniciais da base NCM...")
                self._load_official_ncm_data()
                self._load_common_products()
                self._load_industry_specific_data()
    
    def _load_official_ncm_data(self):
        """Carrega dados oficiais da NCM"""
        # Dados oficiais básicos da NCM (exemplo)
        official_data = [
            # Capítulo 1 - Animais vivos
            ("0101.21.00", "Cavalos, asnos, mulas e burros, reprodutores de raça pura", "01", "01", "21", "00", "", "Animais Vivos", "Equinos", "Reprodutores", "oficial"),
            ("0101.29.00", "Cavalos, asnos, mulas e burros, exceto reprodutores", "01", "01", "29", "00", "", "Animais Vivos", "Equinos", "Outros", "oficial"),
            
            # Capítulo 2 - Carne e miudezas comestíveis
            ("0201.10.00", "Carne de bovinos, fresca ou refrigerada, com osso", "02", "01", "10", "00", "", "Carnes", "Bovinos", "Fresca/Refrigerada", "oficial"),
            ("0201.20.00", "Carne de bovinos, fresca ou refrigerada, sem osso", "02", "01", "20", "00", "", "Carnes", "Bovinos", "Fresca/Refrigerada", "oficial"),
            
            # Capítulo 3 - Peixes e crustáceos
            ("0301.11.00", "Peixes vivos, ornamentais", "03", "01", "11", "00", "", "Peixes", "Vivos", "Ornamentais", "oficial"),
            ("0302.11.00", "Peixes frescos ou refrigerados, salmão", "03", "02", "11", "00", "", "Peixes", "Frescos", "Salmão", "oficial"),
            
            # Capítulo 4 - Leite e laticínios
            ("0401.10.00", "Leite e creme, não concentrados nem adicionados de açúcar", "04", "01", "10", "00", "", "Laticínios", "Leite", "Natural", "oficial"),
            ("0402.10.00", "Leite e creme, concentrados", "04", "02", "10", "00", "", "Laticínios", "Leite", "Concentrado", "oficial"),
            
            # Capítulo 5 - Outros produtos de origem animal
            ("0501.00.00", "Pêlos de animais, não cardados nem penteados", "05", "01", "00", "00", "", "Produtos Animais", "Pêlos", "Naturais", "oficial"),
            ("0502.10.00", "Cerdas de porco, preparadas", "05", "02", "10", "00", "", "Produtos Animais", "Cerdas", "Preparadas", "oficial"),
        ]
        
        self._insert_ncm_entries(official_data)
        logger.info(f"Carregados {len(official_data)} códigos oficiais da NCM")
    
    def _load_common_products(self):
        """Carrega produtos comuns brasileiros"""
        common_products = [
            # Alimentos básicos
            ("1006.30.21", "Arroz branco, tipo 1", "10", "06", "30", "21", "", "Cereais", "Arroz", "Branco", "comum"),
            ("0713.32.00", "Feijão preto", "07", "13", "32", "00", "", "Leguminosas", "Feijão", "Preto", "comum"),
            ("1701.14.00", "Açúcar cristal", "17", "01", "14", "00", "", "Açúcares", "Cristal", "Refinado", "comum"),
            ("0901.21.00", "Café torrado em grão", "09", "01", "21", "00", "", "Café", "Torrado", "Grão", "comum"),
            ("1507.90.00", "Óleo de soja", "15", "07", "90", "00", "", "Óleos", "Soja", "Vegetal", "comum"),
            
            # Bebidas
            ("2203.00.00", "Cerveja", "22", "03", "00", "00", "", "Bebidas", "Cerveja", "Alcoólica", "comum"),
            ("2202.10.00", "Refrigerante", "22", "02", "10", "00", "", "Bebidas", "Refrigerante", "Gaseificada", "comum"),
            ("2009.12.00", "Suco de laranja", "20", "09", "12", "00", "", "Sucos", "Laranja", "Natural", "comum"),
            
            # Têxtil e vestuário
            ("6109.10.00", "Camiseta de algodão", "61", "09", "10", "00", "", "Vestuário", "Camiseta", "Algodão", "comum"),
            ("6203.42.00", "Calça jeans", "62", "03", "42", "00", "", "Vestuário", "Calça", "Jeans", "comum"),
            ("6404.11.00", "Tênis esportivo", "64", "04", "11", "00", "", "Calçados", "Tênis", "Esportivo", "comum"),
            
            # Eletrônicos
            ("8517.12.00", "Smartphone", "85", "17", "12", "00", "", "Telecomunicações", "Telefone", "Celular", "comum"),
            ("8471.30.00", "Notebook", "84", "71", "30", "00", "", "Informática", "Computador", "Portátil", "comum"),
            ("8528.72.00", "Televisão LED", "85", "28", "72", "00", "", "Eletrônicos", "TV", "LED", "comum"),
            
            # Automotivo
            ("4011.10.00", "Pneu de carro", "40", "11", "10", "00", "", "Automotivo", "Pneu", "Carro", "comum"),
            ("8507.20.00", "Bateria de carro", "85", "07", "20", "00", "", "Automotivo", "Bateria", "Carro", "comum"),
            ("2710.19.00", "Óleo de motor", "27", "10", "19", "00", "", "Automotivo", "Óleo", "Motor", "comum"),
            
            # Construção civil
            ("2523.29.00", "Cimento Portland", "25", "23", "29", "00", "", "Construção", "Cimento", "Portland", "comum"),
            ("6904.10.00", "Tijolo cerâmico", "69", "04", "10", "00", "", "Construção", "Tijolo", "Cerâmico", "comum"),
            ("3209.10.00", "Tinta acrílica", "32", "09", "10", "00", "", "Construção", "Tinta", "Acrílica", "comum"),
            
            # Química e farmacêutica
            ("3402.20.00", "Detergente líquido", "34", "02", "20", "00", "", "Química", "Detergente", "Líquido", "comum"),
            ("3305.10.00", "Shampoo", "33", "05", "10", "00", "", "Cosméticos", "Shampoo", "Cabelo", "comum"),
            ("3004.90.00", "Medicamento genérico", "30", "04", "90", "00", "", "Farmacêutico", "Medicamento", "Genérico", "comum"),
        ]
        
        self._insert_ncm_entries(common_products)
        logger.info(f"Carregados {len(common_products)} produtos comuns")
    
    def _load_industry_specific_data(self):
        """Carrega dados específicos por indústria"""
        # Dados do agronegócio
        agribusiness_data = [
            ("8432.10.00", "Máquina de plantio", "84", "32", "10", "00", "", "Agronegócio", "Máquina", "Plantio", "agronegocio"),
            ("8432.20.00", "Máquina de colheita", "84", "32", "20", "00", "", "Agronegócio", "Máquina", "Colheita", "agronegocio"),
            ("8432.30.00", "Máquina de pulverização", "84", "32", "30", "00", "", "Agronegócio", "Máquina", "Pulverização", "agronegocio"),
            ("8432.40.00", "Trator agrícola", "84", "32", "40", "00", "", "Agronegócio", "Trator", "Agrícola", "agronegocio"),
        ]
        
        # Dados da indústria têxtil
        textile_data = [
            ("8444.00.00", "Máquina de tecelagem", "84", "44", "00", "00", "", "Têxtil", "Máquina", "Tecelagem", "textil"),
            ("8445.10.00", "Máquina de costura", "84", "45", "10", "00", "", "Têxtil", "Máquina", "Costura", "textil"),
            ("8445.20.00", "Máquina de bordado", "84", "45", "20", "00", "", "Têxtil", "Máquina", "Bordado", "textil"),
        ]
        
        # Dados da indústria automotiva
        automotive_data = [
            ("8708.10.00", "Para-choque de carro", "87", "08", "10", "00", "", "Automotivo", "Para-choque", "Carro", "automotivo"),
            ("8708.20.00", "Porta de carro", "87", "08", "20", "00", "", "Automotivo", "Porta", "Carro", "automotivo"),
            ("8708.30.00", "Capô de carro", "87", "08", "30", "00", "", "Automotivo", "Capô", "Carro", "automotivo"),
        ]
        
        all_industry_data = agribusiness_data + textile_data + automotive_data
        self._insert_ncm_entries(all_industry_data)
        logger.info(f"Carregados {len(all_industry_data)} produtos industriais")
    
    def _insert_ncm_entries(self, entries: List[Tuple]):
        """Insere entradas na base de dados"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for entry in entries:
                cursor.execute('''
                    INSERT OR REPLACE INTO ncm_entries 
                    (codigo, descricao, capitulo, posicao, subposicao, item, subitem, 
                     categoria, subcategoria, observacoes, fonte, validado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', entry + (False,))
            
            conn.commit()
    
    def search_ncm(self, query: str, limit: int = 10) -> List[NCMEntry]:
        """
        Busca códigos NCM por descrição
        
        Args:
            query: Termo de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de entradas NCM
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Busca por descrição (case-insensitive)
            cursor.execute('''
                SELECT codigo, descricao, capitulo, posicao, subposicao, item, subitem,
                       categoria, subcategoria, observacoes, fonte, validado, data_atualizacao
                FROM ncm_entries
                WHERE descricao LIKE ? OR codigo LIKE ?
                ORDER BY 
                    CASE WHEN descricao LIKE ? THEN 1 ELSE 2 END,
                    validado DESC,
                    data_atualizacao DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', f'{query}%', limit))
            
            results = cursor.fetchall()
            
            return [
                NCMEntry(
                    codigo=row[0],
                    descricao=row[1],
                    capitulo=row[2],
                    posicao=row[3],
                    subposicao=row[4],
                    item=row[5],
                    subitem=row[6],
                    categoria=row[7],
                    subcategoria=row[8],
                    observacoes=row[9],
                    fonte=row[10],
                    validado=bool(row[11]),
                    data_atualizacao=datetime.fromisoformat(row[12])
                )
                for row in results
            ]
    
    def get_ncm_by_code(self, codigo: str) -> Optional[NCMEntry]:
        """
        Obtém entrada NCM por código
        
        Args:
            codigo: Código NCM
            
        Returns:
            Entrada NCM ou None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT codigo, descricao, capitulo, posicao, subposicao, item, subitem,
                       categoria, subcategoria, observacoes, fonte, validado, data_atualizacao
                FROM ncm_entries
                WHERE codigo = ?
            ''', (codigo,))
            
            row = cursor.fetchone()
            if row:
                return NCMEntry(
                    codigo=row[0],
                    descricao=row[1],
                    capitulo=row[2],
                    posicao=row[3],
                    subposicao=row[4],
                    item=row[5],
                    subitem=row[6],
                    categoria=row[7],
                    subcategoria=row[8],
                    observacoes=row[9],
                    fonte=row[10],
                    validado=bool(row[11]),
                    data_atualizacao=datetime.fromisoformat(row[12])
                )
            
            return None
    
    def add_synonym(self, codigo_ncm: str, sinonimo: str, tipo: str = "descricao", fonte: str = "usuario"):
        """
        Adiciona sinônimo para código NCM
        
        Args:
            codigo_ncm: Código NCM
            sinonimo: Sinônimo
            tipo: Tipo do sinônimo
            fonte: Fonte do sinônimo
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ncm_synonyms (codigo_ncm, sinonimo, tipo, fonte)
                VALUES (?, ?, ?, ?)
            ''', (codigo_ncm, sinonimo, tipo, fonte))
            
            conn.commit()
    
    def get_synonyms(self, codigo_ncm: str) -> List[str]:
        """
        Obtém sinônimos para código NCM
        
        Args:
            codigo_ncm: Código NCM
            
        Returns:
            Lista de sinônimos
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT sinonimo FROM ncm_synonyms
                WHERE codigo_ncm = ?
                ORDER BY tipo, fonte
            ''', (codigo_ncm,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def validate_ncm(self, codigo_ncm: str, usuario: str, acao: str, comentario: str = ""):
        """
        Valida código NCM
        
        Args:
            codigo_ncm: Código NCM
            usuario: Usuário que validou
            acao: Ação realizada (validar, rejeitar, corrigir)
            comentario: Comentário sobre a validação
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Registrar validação
            cursor.execute('''
                INSERT INTO ncm_validations (codigo_ncm, usuario, acao, comentario)
                VALUES (?, ?, ?, ?)
            ''', (codigo_ncm, usuario, acao, comentario))
            
            # Atualizar status de validação
            if acao == "validar":
                cursor.execute('''
                    UPDATE ncm_entries SET validado = TRUE, data_atualizacao = CURRENT_TIMESTAMP
                    WHERE codigo = ?
                ''', (codigo_ncm,))
            
            conn.commit()
    
    def get_statistics(self) -> NCMStatistics:
        """Retorna estatísticas da base de dados"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total de entradas
            cursor.execute("SELECT COUNT(*) FROM ncm_entries")
            total_entries = cursor.fetchone()[0]
            
            # Entradas validadas
            cursor.execute("SELECT COUNT(*) FROM ncm_entries WHERE validado = TRUE")
            validated_entries = cursor.fetchone()[0]
            
            # Entradas por capítulo
            cursor.execute('''
                SELECT capitulo, COUNT(*) FROM ncm_entries
                GROUP BY capitulo ORDER BY capitulo
            ''')
            entries_by_chapter = dict(cursor.fetchall())
            
            # Entradas por fonte
            cursor.execute('''
                SELECT fonte, COUNT(*) FROM ncm_entries
                GROUP BY fonte ORDER BY COUNT(*) DESC
            ''')
            entries_by_source = dict(cursor.fetchall())
            
            # Última atualização
            cursor.execute('''
                SELECT MAX(data_atualizacao) FROM ncm_entries
            ''')
            last_update_str = cursor.fetchone()[0]
            last_update = datetime.fromisoformat(last_update_str) if last_update_str else datetime.now()
            
            # Calcular cobertura (assumindo 99 capítulos da NCM)
            coverage_percentage = (len(entries_by_chapter) / 99) * 100 if entries_by_chapter else 0
            
            return NCMStatistics(
                total_entries=total_entries,
                validated_entries=validated_entries,
                entries_by_chapter=entries_by_chapter,
                entries_by_source=entries_by_source,
                last_update=last_update,
                coverage_percentage=coverage_percentage
            )
    
    def export_database(self, file_path: str):
        """Exporta base de dados para arquivo"""
        with sqlite3.connect(self.db_path) as conn:
            # Exportar para CSV
            df = pd.read_sql_query("SELECT * FROM ncm_entries", conn)
            df.to_csv(file_path, index=False, encoding='utf-8')
        
        logger.info(f"Base de dados exportada para {file_path}")
    
    def import_external_data(self, file_path: str, fonte: str = "externo"):
        """
        Importa dados externos
        
        Args:
            file_path: Caminho do arquivo
            fonte: Fonte dos dados
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path, encoding='utf-8')
            else:
                raise ValueError("Formato de arquivo não suportado")
            
            # Processar dados
            entries = []
            for _, row in df.iterrows():
                entry = (
                    row.get('codigo', ''),
                    row.get('descricao', ''),
                    row.get('capitulo', ''),
                    row.get('posicao', ''),
                    row.get('subposicao', ''),
                    row.get('item', ''),
                    row.get('subitem', ''),
                    row.get('categoria', ''),
                    row.get('subcategoria', ''),
                    row.get('observacoes', ''),
                    fonte,
                    False
                )
                entries.append(entry)
            
            self._insert_ncm_entries(entries)
            logger.info(f"Importados {len(entries)} registros de {file_path}")
            
        except Exception as e:
            logger.error(f"Erro ao importar dados de {file_path}: {e}")


# Instância global do gerenciador
_database_manager_instance: Optional[NCMDatabaseManager] = None

def get_ncm_database_manager() -> NCMDatabaseManager:
    """Retorna instância global do gerenciador"""
    global _database_manager_instance
    if _database_manager_instance is None:
        _database_manager_instance = NCMDatabaseManager()
    return _database_manager_instance

def search_ncm_database(query: str, limit: int = 10) -> List[NCMEntry]:
    """Função de conveniência para busca"""
    return get_ncm_database_manager().search_ncm(query, limit)

def get_ncm_database_stats() -> NCMStatistics:
    """Função de conveniência para estatísticas"""
    return get_ncm_database_manager().get_statistics()
