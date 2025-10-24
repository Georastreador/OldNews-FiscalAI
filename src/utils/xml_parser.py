"""
FiscalAI MVP - XML Parser
Parser de arquivos XML de Nota Fiscal Eletrônica (NF-e)
"""

import xmltodict
import lxml.etree as ET
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..models import NFe, ItemNFe, StatusProcessamento


class NFeXMLParser:
    """
    Parser de arquivos XML de NF-e
    Extrai informações estruturadas do XML da Nota Fiscal Eletrônica
    """
    
    def __init__(self):
        """Inicializa o parser"""
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def parse_file(self, xml_path: str) -> NFe:
        """
        Faz parsing de um arquivo XML de NF-e
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Objeto NFe com dados estruturados
        
        Raises:
            FileNotFoundError: Se arquivo não existir
            ValueError: Se XML for inválido ou incompleto
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {xml_path}")
        
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        return self.parse_string(xml_content)
    
    def parse_string(self, xml_content: str) -> NFe:
        """
        Faz parsing de uma string XML de NF-e
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Objeto NFe com dados estruturados
        
        Raises:
            ValueError: Se XML for inválido ou incompleto
        """
        try:
            # Converter XML para dict com proteção contra XXE
            xml_dict = xmltodict.parse(
                xml_content,
                process_namespaces=False,
                disable_entities=True,
                process_comments=False,
                strip_whitespace=True
            )
            
            # Navegar na estrutura do XML
            # Estrutura típica: nfeProc -> NFe -> infNFe
            if 'nfeProc' in xml_dict:
                nfe_root = xml_dict['nfeProc']['NFe']['infNFe']
            elif 'NFe' in xml_dict:
                nfe_root = xml_dict['NFe']['infNFe']
            elif 'infNFe' in xml_dict:
                nfe_root = xml_dict['infNFe']
            else:
                raise ValueError("Estrutura XML inválida: raiz não encontrada")
            
            # Extrair dados
            nfe_data = self._extract_nfe_data(nfe_root)
            
            # Criar objeto NFe
            nfe = NFe(**nfe_data)
            nfe.status = StatusProcessamento.CONCLUIDO
            nfe.data_processamento = datetime.now()
            
            return nfe
            
        except Exception as e:
            raise ValueError(f"Erro ao fazer parsing do XML: {str(e)}")
    
    def _extract_nfe_data(self, nfe_root: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai dados estruturados do dict XML
        
        Args:
            nfe_root: Dict com dados da raiz infNFe
        
        Returns:
            Dict com dados para criar objeto NFe
        """
        # Identificação da NF-e
        ide = nfe_root['ide']
        chave_acesso = nfe_root.get('@Id', '').replace('NFe', '')
        
        # Emitente
        emit = nfe_root['emit']
        cnpj_emitente = emit.get('CNPJ', '')
        razao_social_emitente = emit.get('xNome', '')
        
        # Destinatário
        dest = nfe_root['dest']
        cnpj_destinatario = dest.get('CNPJ', '')
        razao_social_destinatario = dest.get('xNome', '')
        
        # Totais
        total = nfe_root['total']['ICMSTot']
        valor_total = float(total.get('vNF', 0))
        valor_produtos = float(total.get('vProd', 0))
        valor_impostos = float(total.get('vTotTrib', 0))
        
        # Data de emissão
        data_emissao_str = ide.get('dhEmi') or ide.get('dEmi')
        data_emissao = self._parse_datetime(data_emissao_str)
        
        # Itens (produtos)
        det = nfe_root['det']
        if not isinstance(det, list):
            det = [det]  # Garantir que seja lista
        
        itens = [self._extract_item_data(item, idx + 1) for idx, item in enumerate(det)]
        
        return {
            'chave_acesso': chave_acesso,
            'numero': str(ide.get('nNF', '')),
            'serie': str(ide.get('serie', '')),
            'data_emissao': data_emissao,
            'cnpj_emitente': cnpj_emitente,
            'razao_social_emitente': razao_social_emitente,
            'cnpj_destinatario': cnpj_destinatario,
            'razao_social_destinatario': razao_social_destinatario,
            'valor_total': valor_total,
            'valor_produtos': valor_produtos,
            'valor_impostos': valor_impostos,
            'itens': itens,
        }
    
    def _extract_item_data(self, item_dict: Dict[str, Any], numero_item: int) -> ItemNFe:
        """
        Extrai dados de um item (produto) da NF-e
        
        Args:
            item_dict: Dict com dados do item (tag <det>)
            numero_item: Número sequencial do item
        
        Returns:
            Objeto ItemNFe
        """
        prod = item_dict['prod']
        
        # Dados básicos do produto
        descricao = prod.get('xProd', '')
        ncm = prod.get('NCM', '')
        cfop = str(prod.get('CFOP', ''))
        
        # Quantidades e valores
        quantidade = float(prod.get('qCom', 0))
        valor_unitario = float(prod.get('vUnCom', 0))
        valor_total = float(prod.get('vProd', 0))
        unidade = prod.get('uCom', 'UN')
        
        # Códigos opcionais
        codigo_produto = prod.get('cProd')
        ean = prod.get('cEAN')
        
        return ItemNFe(
            numero_item=numero_item,
            descricao=descricao,
            ncm_declarado=ncm,
            cfop=cfop,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            unidade=unidade,
            codigo_produto=codigo_produto,
            ean=ean if ean and ean != 'SEM GTIN' else None,
        )
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Faz parsing de string de data/hora do XML
        
        Args:
            dt_str: String de data no formato ISO ou brasileiro
        
        Returns:
            Objeto datetime
        """
        if not dt_str:
            return datetime.now()
        
        # Tentar formatos comuns
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',  # ISO com timezone
            '%Y-%m-%dT%H:%M:%S',     # ISO sem timezone
            '%Y-%m-%d',               # Apenas data
            '%d/%m/%Y',               # Formato brasileiro
        ]
        
        for fmt in formats:
            try:
                # Remover timezone se presente (simplificação)
                dt_str_clean = dt_str.split('-03:00')[0].split('+')[0]
                return datetime.strptime(dt_str_clean, fmt)
            except ValueError:
                continue
        
        # Fallback
        return datetime.now()
    
    def validate_xml(self, xml_path: str) -> tuple[bool, Optional[str]]:
        """
        Valida estrutura básica do XML de NF-e
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (is_valid, error_message)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Verificar elementos obrigatórios (busca recursiva com namespaces)
            required_elements = ['ide', 'emit', 'dest', 'det', 'total']
            
            for elem in required_elements:
                # Buscar com e sem namespace
                found = False
                
                # Tentar com namespace
                for prefix, uri in self.namespaces.items():
                    if root.find(f'.//{{{uri}}}{elem}') is not None:
                        found = True
                        break
                
                # Tentar sem namespace
                if not found:
                    if root.find(f'.//{elem}') is not None:
                        found = True
                
                if not found:
                    return False, f"Elemento obrigatório não encontrado: {elem}"
            
            return True, None
            
        except ET.XMLSyntaxError as e:
            return False, f"Erro de sintaxe XML: {str(e)}"
        except Exception as e:
            return False, f"Erro ao validar XML: {str(e)}"


# Função de conveniência
def parse_nfe_xml(xml_path: str) -> NFe:
    """
    Função de conveniência para fazer parsing de NF-e XML
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Objeto NFe
    """
    parser = NFeXMLParser()
    return parser.parse_file(xml_path)

