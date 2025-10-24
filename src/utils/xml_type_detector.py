"""
FiscalAI MVP - XML Type Detector
Detector automático do tipo de documento fiscal XML
"""

import xmltodict
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class XMLTypeDetector:
    """
    Detecta automaticamente o tipo de documento fiscal XML
    """
    
    def __init__(self):
        """Inicializa o detector"""
        self.supported_types = {
            'nfe': {
                'root_elements': ['nfeProc', 'NFe', 'infNFe'],
                'namespaces': ['http://www.portalfiscal.inf.br/nfe'],
                'description': 'Nota Fiscal Eletrônica (NF-e)'
            },
            'nfse': {
                'root_elements': ['ConsultarNfseResposta', 'ListaNfse', 'CompNfse'],
                'namespaces': ['http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd'],
                'description': 'Nota Fiscal de Serviços Eletrônica (NFS-e)'
            },
            'cte': {
                'root_elements': ['cteProc', 'CTe', 'infCte'],
                'namespaces': ['http://www.portalfiscal.inf.br/cte'],
                'description': 'Conhecimento de Transporte Eletrônico (CT-e)'
            },
            'mdfe': {
                'root_elements': ['mdfeProc', 'MDFe', 'infMDFe'],
                'namespaces': ['http://www.portalfiscal.inf.br/mdfe'],
                'description': 'Manifesto Eletrônico de Documentos Fiscais (MDF-e)'
            }
        }
    
    def detect_type(self, xml_path: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Detecta o tipo de documento fiscal XML
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (tipo, descricao, metadados)
        """
        try:
            # Ler o arquivo completo para análise
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tentar fazer parsing do XML
            try:
                # Limpar quebras de linha e espaços extras
                content_clean = ' '.join(content.split())
                xml_dict = xmltodict.parse(
                    content_clean,
                    process_namespaces=False,
                    disable_entities=True,
                    process_comments=False,
                    strip_whitespace=True
                )
            except Exception as e:
                logger.warning(f"Erro ao fazer parsing do XML: {e}")
                return 'unknown', 'Documento XML não reconhecido', {}
            
            # Analisar estrutura do XML
            detected_type = self._analyze_structure(xml_dict, content)
            
            if detected_type in self.supported_types:
                type_info = self.supported_types[detected_type]
                return detected_type, type_info['description'], {
                    'root_elements': type_info['root_elements'],
                    'namespaces': type_info['namespaces']
                }
            else:
                return 'unknown', 'Tipo de documento não suportado', {}
                
        except Exception as e:
            logger.error(f"Erro ao detectar tipo do XML: {e}")
            return 'unknown', f'Erro na detecção: {str(e)}', {}
    
    def _analyze_structure(self, xml_dict: Dict[str, Any], content: str) -> str:
        """
        Analisa a estrutura do XML para determinar o tipo
        
        Args:
            xml_dict: Dict com dados XML parseados
            content: Conteúdo XML como string
        
        Returns:
            Tipo detectado
        """
        # Verificar elementos raiz
        root_keys = list(xml_dict.keys())
        
        # Verificar namespaces no conteúdo
        namespaces_found = []
        for namespace in ['http://www.portalfiscal.inf.br/nfe', 
                         'http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd',
                         'http://www.portalfiscal.inf.br/cte',
                         'http://www.portalfiscal.inf.br/mdfe']:
            if namespace in content:
                namespaces_found.append(namespace)
        
        # Detectar por elementos raiz
        for doc_type, type_info in self.supported_types.items():
            for root_element in type_info['root_elements']:
                if root_element in root_keys:
                    logger.info(f"Tipo detectado por elemento raiz: {doc_type} (elemento: {root_element})")
                    return doc_type
        
        # Detectar por namespace
        for doc_type, type_info in self.supported_types.items():
            for namespace in type_info['namespaces']:
                if namespace in namespaces_found:
                    logger.info(f"Tipo detectado por namespace: {doc_type} (namespace: {namespace})")
                    return doc_type
        
        # Detectar por conteúdo específico
        if 'ConsultarNfseResposta' in content or 'ListaNfse' in content:
            return 'nfse'
        elif 'nfeProc' in content or 'infNFe' in content:
            return 'nfe'
        elif 'cteProc' in content or 'infCte' in content:
            return 'cte'
        elif 'mdfeProc' in content or 'infMDFe' in content:
            return 'mdfe'
        
        return 'unknown'
    
    def get_supported_types(self) -> Dict[str, str]:
        """
        Retorna lista de tipos suportados
        
        Returns:
            Dict com tipos e descrições
        """
        return {doc_type: info['description'] 
                for doc_type, info in self.supported_types.items()}
    
    def is_supported(self, xml_path: str) -> bool:
        """
        Verifica se o tipo de documento é suportado
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            True se suportado, False caso contrário
        """
        doc_type, _, _ = self.detect_type(xml_path)
        return doc_type != 'unknown'


# Função de conveniência
def detect_xml_type(xml_path: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    Função de conveniência para detectar tipo de XML
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Tuple (tipo, descricao, metadados)
    """
    detector = XMLTypeDetector()
    return detector.detect_type(xml_path)
