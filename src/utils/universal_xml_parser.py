"""
FiscalAI MVP - Universal XML Parser
Parser universal que detecta automaticamente o tipo de documento fiscal
e usa o parser apropriado
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging

from .xml_type_detector import XMLTypeDetector
from .xml_parser import NFeXMLParser
from .xml_parser_robusto import NFeXMLParserRobusto
from .nfse_parser import NFeSEXMLParser
from ..models import NFe

logger = logging.getLogger(__name__)


class UniversalXMLParser:
    """
    Parser universal que detecta automaticamente o tipo de documento fiscal
    e usa o parser apropriado
    """
    
    def __init__(self):
        """Inicializa o parser universal"""
        self.type_detector = XMLTypeDetector()
        self.parsers = {
            'nfe': NFeXMLParserRobusto(),  # Usar parser robusto para NF-e
            'nfse': NFeSEXMLParser(),
            # Adicionar outros parsers conforme necessário
        }
    
    def parse_file(self, xml_path: str) -> Tuple[NFe, str, str]:
        """
        Faz parsing de um arquivo XML detectando automaticamente o tipo
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (objeto_nfe, tipo_documento, descricao)
        
        Raises:
            FileNotFoundError: Se arquivo não existir
            ValueError: Se XML for inválido ou tipo não suportado
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {xml_path}")
        
        # Detectar tipo do documento
        doc_type, description, metadata = self.type_detector.detect_type(str(xml_path))
        
        logger.info(f"Tipo detectado: {doc_type} - {description}")
        
        if doc_type == 'unknown':
            raise ValueError(f"Tipo de documento não suportado: {description}")
        
        if doc_type not in self.parsers:
            raise ValueError(f"Parser não disponível para tipo: {doc_type}")
        
        # Usar parser apropriado
        parser = self.parsers[doc_type]
        nfe = parser.parse_file(str(xml_path))
        
        # Adicionar metadados sobre o tipo de documento
        nfe.tipo_documento = doc_type
        nfe.descricao_documento = description
        
        return nfe, doc_type, description
    
    def parse_string(self, xml_content: str) -> Tuple[NFe, str, str]:
        """
        Faz parsing de uma string XML detectando automaticamente o tipo
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Tuple (objeto_nfe, tipo_documento, descricao)
        
        Raises:
            ValueError: Se XML for inválido ou tipo não suportado
        """
        # Salvar conteúdo em arquivo temporário para detecção
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            return self.parse_file(temp_path)
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
            
            if doc_type not in self.parsers:
                return False, f"Parser não disponível para tipo: {doc_type}", doc_type
            
            # Validar com parser apropriado
            parser = self.parsers[doc_type]
            is_valid, error_message = parser.validate_xml(xml_path)
            
            return is_valid, error_message, doc_type
            
        except Exception as e:
            return False, f"Erro na validação: {str(e)}", None


# Função de conveniência
def parse_fiscal_xml(xml_path: str) -> Tuple[NFe, str, str]:
    """
    Função de conveniência para fazer parsing universal de XML fiscal
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Tuple (objeto_nfe, tipo_documento, descricao)
    """
    parser = UniversalXMLParser()
    return parser.parse_file(xml_path)
