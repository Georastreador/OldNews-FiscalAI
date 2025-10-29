"""
OldNews FiscalAI - Universal Multiple XML Parser
Parser universal que detecta automaticamente o tipo de documento fiscal
e processa múltiplas notas quando aplicável
"""

from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import logging

from .xml_type_detector import XMLTypeDetector
from .xml_parser import NFeXMLParser
from .xml_parser_robusto import NFeXMLParserRobusto
from .nfse_parser import NFeSEXMLParser
from .nfse_multiple_parser import NFeSEMultipleParser
from ..models import NFe

logger = logging.getLogger(__name__)


class UniversalMultipleXMLParser:
    """
    Parser universal que detecta automaticamente o tipo de documento fiscal
    e processa múltiplas notas quando aplicável
    """
    
    def __init__(self):
        """Inicializa o parser universal"""
        self.type_detector = XMLTypeDetector()
        self.parsers = {
            'nfe': NFeXMLParserRobusto(),  # Usar parser robusto para NF-e
            'nfse': NFeSEXMLParser(),  # Parser original para NFS-e única
        }
        self.multiple_parsers = {
            'nfse': NFeSEMultipleParser(),  # Parser para múltiplas NFS-e
        }
    
    def parse_file(self, xml_path: str, multiple: bool = True) -> Union[NFe, List[NFe], Tuple[NFe, str, str], Tuple[List[NFe], str, str]]:
        """
        Faz parsing de um arquivo XML detectando automaticamente o tipo
        
        Args:
            xml_path: Caminho para o arquivo XML
            multiple: Se deve processar múltiplas notas quando possível
        
        Returns:
            Se multiple=True: Lista de objetos NFe ou objeto único
            Se multiple=False: Tuple (objeto_nfe, tipo_documento, descricao)
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {xml_path}")
        
        # Detectar tipo do documento
        doc_type, description, metadata = self.type_detector.detect_type(str(xml_path))
        
        logger.info(f"Tipo detectado: {doc_type} - {description}")
        
        if doc_type == 'unknown':
            raise ValueError(f"Tipo de documento não suportado: {description}")
        
        # Verificar se tem suporte para múltiplas notas
        if multiple and doc_type in self.multiple_parsers:
            parser = self.multiple_parsers[doc_type]
            nfes = parser.parse_file(str(xml_path))
            
            # Adicionar metadados sobre o tipo de documento
            for nfe in nfes:
                nfe.tipo_documento = doc_type
                nfe.descricao_documento = description
            
            return nfes, doc_type, description
        
        elif doc_type in self.parsers:
            parser = self.parsers[doc_type]
            nfe = parser.parse_file(str(xml_path))
            
            # Adicionar metadados sobre o tipo de documento
            nfe.tipo_documento = doc_type
            nfe.descricao_documento = description
            
            if multiple:
                return [nfe], doc_type, description
            else:
                return nfe, doc_type, description
        
        else:
            raise ValueError(f"Parser não disponível para tipo: {doc_type}")
    
    def parse_string(self, xml_content: str, multiple: bool = True) -> Union[NFe, List[NFe], Tuple[NFe, str, str], Tuple[List[NFe], str, str]]:
        """
        Faz parsing de uma string XML detectando automaticamente o tipo
        
        Args:
            xml_content: Conteúdo XML como string
            multiple: Se deve processar múltiplas notas quando possível
        
        Returns:
            Se multiple=True: Lista de objetos NFe ou objeto único
            Se multiple=False: Tuple (objeto_nfe, tipo_documento, descricao)
        """
        # Salvar conteúdo em arquivo temporário para detecção
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            return self.parse_file(temp_path, multiple)
        finally:
            # Limpar arquivo temporário
            Path(temp_path).unlink(missing_ok=True)
    
    def get_supported_types(self) -> Dict[str, str]:
        """
        Retorna lista de tipos suportados
        
        Returns:
            Dict com tipos e descrições
        """
        return self.type_detector.get_supported_types()
    
    def is_supported(self, xml_path: str) -> bool:
        """
        Verifica se o tipo de documento é suportado
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            True se suportado, False caso contrário
        """
        return self.type_detector.is_supported(xml_path)
    
    def supports_multiple(self, xml_path: str) -> bool:
        """
        Verifica se o tipo de documento suporta múltiplas notas
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            True se suporta múltiplas notas, False caso contrário
        """
        doc_type, _, _ = self.type_detector.detect_type(xml_path)
        return doc_type in self.multiple_parsers
    
    def validate_xml(self, xml_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Valida XML e retorna informações sobre o tipo
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (is_valid, error_message, document_type)
        """
        try:
            # Detectar tipo primeiro
            doc_type, description, metadata = self.type_detector.detect_type(xml_path)
            
            if doc_type == 'unknown':
                return False, f"Tipo de documento não suportado: {description}", None
            
            if doc_type not in self.parsers and doc_type not in self.multiple_parsers:
                return False, f"Parser não disponível para tipo: {doc_type}", doc_type
            
            # Validar com parser apropriado
            if doc_type in self.parsers:
                parser = self.parsers[doc_type]
            else:
                parser = self.multiple_parsers[doc_type]
            
            # Verificar se parser tem método validate_xml
            if hasattr(parser, 'validate_xml'):
                is_valid, error_message = parser.validate_xml(xml_path)
            else:
                # Tentar fazer parsing para validar
                try:
                    if doc_type in self.multiple_parsers:
                        parser.parse_file(xml_path)
                    else:
                        parser.parse_file(xml_path)
                    is_valid, error_message = True, None
                except Exception as e:
                    is_valid, error_message = False, str(e)
            
            return is_valid, error_message, doc_type
            
        except Exception as e:
            return False, f"Erro na validação: {str(e)}", None


# Funções de conveniência
def parse_fiscal_xml_multiple(xml_path: str) -> Tuple[List[NFe], str, str]:
    """
    Função de conveniência para fazer parsing universal de XML fiscal com múltiplas notas
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Tuple (lista_objetos_nfe, tipo_documento, descricao)
    """
    parser = UniversalMultipleXMLParser()
    return parser.parse_file(xml_path, multiple=True)


def parse_fiscal_xml_single(xml_path: str) -> Tuple[NFe, str, str]:
    """
    Função de conveniência para fazer parsing universal de XML fiscal com nota única
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Tuple (objeto_nfe, tipo_documento, descricao)
    """
    parser = UniversalMultipleXMLParser()
    return parser.parse_file(xml_path, multiple=False)
