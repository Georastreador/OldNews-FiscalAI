"""
FiscalAI MVP - Smart Fiscal Parser
Sistema inteligente de identificação e processamento de documentos fiscais
Suporta NF-e, NFS-e, CPF, CNPJ com detecção automática
"""

import re
import hashlib
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
import logging
from datetime import datetime

from .universal_xml_parser import UniversalXMLParser
from ..models import NFe, ItemNFe, StatusProcessamento

logger = logging.getLogger(__name__)


class SmartFiscalParser:
    """
    Parser inteligente que identifica automaticamente o tipo de documento fiscal
    e normaliza os dados para processamento unificado
    """
    
    def __init__(self):
        """Inicializa o parser inteligente"""
        self.universal_parser = UniversalXMLParser()
        
        # Padrões de identificação
        self.cpf_pattern = re.compile(r'^\d{11}$')
        self.cnpj_pattern = re.compile(r'^\d{14}$')
        self.cpf_cnpj_pattern = re.compile(r'^\d{11,14}$')
        
        # Mapeamento de tipos de documento
        self.document_types = {
            'nfe': 'Nota Fiscal Eletrônica',
            'nfse': 'Nota Fiscal de Serviços Eletrônica',
            'cte': 'Conhecimento de Transporte Eletrônico',
            'mdfe': 'Manifesto Eletrônico de Documentos Fiscais'
        }
    
    def parse_document(self, xml_path: str) -> Dict[str, Any]:
        """
        Processa documento fiscal com identificação inteligente
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Dict com dados processados e metadados
        """
        try:
            logger.info(f"Iniciando processamento inteligente: {xml_path}")
            
            # 1. Detectar e fazer parsing do documento
            nfe, doc_type, doc_description = self.universal_parser.parse_file(xml_path)
            
            # 2. Identificar e normalizar dados
            processed_data = self._process_document_data(nfe, doc_type, doc_description)
            
            # 3. Validar e enriquecer dados
            validated_data = self._validate_and_enrich(processed_data)
            
            # 4. Gerar metadados inteligentes
            metadata = self._generate_smart_metadata(validated_data, doc_type)
            
            logger.info(f"Processamento concluído: {doc_type} - {metadata['document_summary']}")
            
            return {
                'nfe': validated_data['nfe'],
                'document_type': doc_type,
                'document_description': doc_description,
                'metadata': metadata,
                'processing_info': {
                    'timestamp': datetime.now(),
                    'parser_version': '2.0.0',
                    'smart_features': True
                }
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento inteligente: {e}")
            raise ValueError(f"Erro no processamento do documento: {str(e)}")
    
    def _process_document_data(self, nfe: NFe, doc_type: str, doc_description: str) -> Dict[str, Any]:
        """
        Processa e normaliza dados do documento
        
        Args:
            nfe: Objeto NFe parseado
            doc_type: Tipo do documento
            doc_description: Descrição do documento
        
        Returns:
            Dict com dados processados
        """
        # Identificar tipo de documento fiscal
        fiscal_type = self._identify_fiscal_type(nfe, doc_type)
        
        # Normalizar dados do emitente
        emitente_data = self._normalize_emitente_data(nfe)
        
        # Normalizar dados do destinatário
        destinatario_data = self._normalize_destinatario_data(nfe)
        
        # Processar itens
        itens_data = self._process_items(nfe.itens, doc_type)
        
        # Calcular métricas fiscais
        fiscal_metrics = self._calculate_fiscal_metrics(nfe, doc_type)
        
        return {
            'nfe': nfe,
            'fiscal_type': fiscal_type,
            'emitente': emitente_data,
            'destinatario': destinatario_data,
            'itens': itens_data,
            'metrics': fiscal_metrics,
            'document_type': doc_type,
            'document_description': doc_description
        }
    
    def _identify_fiscal_type(self, nfe: NFe, doc_type: str) -> Dict[str, Any]:
        """
        Identifica o tipo fiscal do documento
        
        Args:
            nfe: Objeto NFe
            doc_type: Tipo do documento
        
        Returns:
            Dict com informações do tipo fiscal
        """
        fiscal_type = {
            'category': doc_type,
            'description': self.document_types.get(doc_type, 'Documento fiscal'),
            'is_service': doc_type == 'nfse',
            'is_merchandise': doc_type == 'nfe',
            'is_transport': doc_type in ['cte', 'mdfe'],
            'has_items': len(nfe.itens) > 0,
            'total_value': nfe.valor_total,
            'tax_value': nfe.valor_impostos or 0
        }
        
        # Identificar características específicas
        if doc_type == 'nfse':
            fiscal_type['service_indicators'] = {
                'has_service_codes': any(item.ncm_declarado.startswith('00') for item in nfe.itens),
                'average_service_value': nfe.valor_total / len(nfe.itens) if nfe.itens else 0,
                'service_count': len(nfe.itens)
            }
        elif doc_type == 'nfe':
            fiscal_type['merchandise_indicators'] = {
                'has_ncm_codes': any(not item.ncm_declarado.startswith('00') for item in nfe.itens),
                'average_item_value': nfe.valor_total / len(nfe.itens) if nfe.itens else 0,
                'item_count': len(nfe.itens)
            }
        
        return fiscal_type
    
    def _normalize_emitente_data(self, nfe: NFe) -> Dict[str, Any]:
        """
        Normaliza dados do emitente
        
        Args:
            nfe: Objeto NFe
        
        Returns:
            Dict com dados normalizados do emitente
        """
        cnpj = nfe.cnpj_emitente
        document_type = self._identify_document_type(cnpj)
        
        return {
            'cnpj': cnpj,
            'document_type': document_type,
            'is_cpf': document_type == 'cpf',
            'is_cnpj': document_type == 'cnpj',
            'razao_social': nfe.razao_social_emitente or 'Não informado',
            'formatted_document': self._format_document(cnpj, document_type),
            'document_length': len(cnpj),
            'is_valid_format': self._validate_document_format(cnpj, document_type)
        }
    
    def _normalize_destinatario_data(self, nfe: NFe) -> Dict[str, Any]:
        """
        Normaliza dados do destinatário
        
        Args:
            nfe: Objeto NFe
        
        Returns:
            Dict com dados normalizados do destinatário
        """
        cnpj = nfe.cnpj_destinatario
        document_type = self._identify_document_type(cnpj)
        
        return {
            'cnpj': cnpj,
            'document_type': document_type,
            'is_cpf': document_type == 'cpf',
            'is_cnpj': document_type == 'cnpj',
            'razao_social': nfe.razao_social_destinatario or 'Não informado',
            'formatted_document': self._format_document(cnpj, document_type),
            'document_length': len(cnpj),
            'is_valid_format': self._validate_document_format(cnpj, document_type)
        }
    
    def _process_items(self, itens: list, doc_type: str) -> Dict[str, Any]:
        """
        Processa itens do documento
        
        Args:
            itens: Lista de itens
            doc_type: Tipo do documento
        
        Returns:
            Dict com dados processados dos itens
        """
        processed_items = []
        
        for item in itens:
            item_data = {
                'numero_item': item.numero_item,
                'descricao': item.descricao,
                'ncm_declarado': item.ncm_declarado,
                'ncm_predito': item.ncm_predito,
                'cfop': item.cfop,
                'quantidade': item.quantidade,
                'valor_unitario': item.valor_unitario,
                'valor_total': item.valor_total,
                'unidade': item.unidade,
                'codigo_produto': item.codigo_produto,
                'ean': item.ean,
                'ncm_confianca': item.ncm_confianca
            }
            
            # Identificar tipo do item
            item_data['item_type'] = self._identify_item_type(item, doc_type)
            item_data['is_service'] = item_data['item_type'] == 'service'
            item_data['is_merchandise'] = item_data['item_type'] == 'merchandise'
            
            processed_items.append(item_data)
        
        return {
            'items': processed_items,
            'total_items': len(processed_items),
            'total_value': sum(item.valor_total for item in itens),
            'average_value': sum(item.valor_total for item in itens) / len(itens) if itens else 0,
            'has_services': any(self._identify_item_type(item, doc_type) == 'service' for item in itens),
            'has_merchandise': any(self._identify_item_type(item, doc_type) == 'merchandise' for item in itens)
        }
    
    def _calculate_fiscal_metrics(self, nfe: NFe, doc_type: str) -> Dict[str, Any]:
        """
        Calcula métricas fiscais do documento
        
        Args:
            nfe: Objeto NFe
            doc_type: Tipo do documento
        
        Returns:
            Dict com métricas fiscais
        """
        metrics = {
            'total_value': nfe.valor_total,
            'product_value': nfe.valor_produtos,
            'tax_value': nfe.valor_impostos or 0,
            'tax_percentage': (nfe.valor_impostos / nfe.valor_total * 100) if nfe.valor_impostos and nfe.valor_total > 0 else 0,
            'item_count': len(nfe.itens),
            'average_item_value': nfe.valor_total / len(nfe.itens) if nfe.itens else 0,
            'document_type': doc_type,
            'processing_date': nfe.data_emissao,
            'key_access': nfe.chave_acesso
        }
        
        # Métricas específicas por tipo
        if doc_type == 'nfse':
            metrics['service_metrics'] = {
                'service_count': len(nfe.itens),
                'total_service_value': nfe.valor_total,
                'average_service_value': nfe.valor_total / len(nfe.itens) if nfe.itens else 0
            }
        elif doc_type == 'nfe':
            metrics['merchandise_metrics'] = {
                'item_count': len(nfe.itens),
                'total_merchandise_value': nfe.valor_produtos,
                'average_item_value': nfe.valor_produtos / len(nfe.itens) if nfe.itens else 0
            }
        
        return metrics
    
    def _identify_document_type(self, document: str) -> str:
        """
        Identifica se o documento é CPF ou CNPJ
        
        Args:
            document: Número do documento
        
        Returns:
            'cpf' ou 'cnpj'
        """
        # Limpar documento
        clean_doc = re.sub(r'[^\d]', '', document)
        
        if len(clean_doc) == 11:
            return 'cpf'
        elif len(clean_doc) == 14:
            return 'cnpj'
        else:
            # Tentar identificar pelo contexto
            if len(clean_doc) < 14:
                return 'cpf'
            else:
                return 'cnpj'
    
    def _format_document(self, document: str, doc_type: str) -> str:
        """
        Formata documento (CPF ou CNPJ)
        
        Args:
            document: Número do documento
            doc_type: Tipo do documento
        
        Returns:
            Documento formatado
        """
        clean_doc = re.sub(r'[^\d]', '', document)
        
        if doc_type == 'cpf' and len(clean_doc) == 11:
            return f"{clean_doc[:3]}.{clean_doc[3:6]}.{clean_doc[6:9]}-{clean_doc[9:]}"
        elif doc_type == 'cnpj' and len(clean_doc) == 14:
            return f"{clean_doc[:2]}.{clean_doc[2:5]}.{clean_doc[5:8]}/{clean_doc[8:12]}-{clean_doc[12:]}"
        else:
            return clean_doc
    
    def _validate_document_format(self, document: str, doc_type: str) -> bool:
        """
        Valida formato do documento
        
        Args:
            document: Número do documento
            doc_type: Tipo do documento
        
        Returns:
            True se formato válido
        """
        clean_doc = re.sub(r'[^\d]', '', document)
        
        if doc_type == 'cpf':
            return len(clean_doc) == 11 and clean_doc.isdigit()
        elif doc_type == 'cnpj':
            return len(clean_doc) == 14 and clean_doc.isdigit()
        else:
            return False
    
    def _identify_item_type(self, item: ItemNFe, doc_type: str) -> str:
        """
        Identifica tipo do item (serviço ou mercadoria)
        
        Args:
            item: Item da NF-e
            doc_type: Tipo do documento
        
        Returns:
            'service' ou 'merchandise'
        """
        if doc_type == 'nfse':
            return 'service'
        elif doc_type == 'nfe':
            # Verificar se NCM indica serviço (códigos que começam com 00)
            if item.ncm_declarado.startswith('00'):
                return 'service'
            else:
                return 'merchandise'
        else:
            return 'unknown'
    
    def _validate_and_enrich(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e enriquece dados processados
        
        Args:
            data: Dados processados
        
        Returns:
            Dados validados e enriquecidos
        """
        # Validar dados críticos
        validation_results = {
            'emitente_valid': data['emitente']['is_valid_format'],
            'destinatario_valid': data['destinatario']['is_valid_format'],
            'values_consistent': abs(data['nfe'].valor_total - (data['nfe'].valor_produtos + (data['nfe'].valor_impostos or 0))) < 0.01,
            'has_items': len(data['nfe'].itens) > 0,
            'items_valid': all(item.valor_total > 0 for item in data['nfe'].itens)
        }
        
        # Enriquecer com informações adicionais
        enrichment = {
            'risk_indicators': self._calculate_risk_indicators(data),
            'compliance_checks': self._perform_compliance_checks(data),
            'data_quality_score': self._calculate_data_quality_score(validation_results)
        }
        
        return {
            **data,
            'validation': validation_results,
            'enrichment': enrichment
        }
    
    def _calculate_risk_indicators(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula indicadores de risco
        
        Args:
            data: Dados processados
        
        Returns:
            Dict com indicadores de risco
        """
        risk_indicators = {
            'high_value_transaction': data['nfe'].valor_total > 10000,
            'unusual_item_count': len(data['nfe'].itens) > 50,
            'missing_document_info': not data['emitente']['razao_social'] or data['emitente']['razao_social'] == 'Não informado',
            'cpf_destinatario': data['destinatario']['is_cpf'],
            'service_without_tax': data['fiscal_type']['is_service'] and (data['nfe'].valor_impostos or 0) == 0,
            'risk_score': 0
        }
        
        # Calcular score de risco
        risk_score = 0
        if risk_indicators['high_value_transaction']:
            risk_score += 20
        if risk_indicators['unusual_item_count']:
            risk_score += 15
        if risk_indicators['missing_document_info']:
            risk_score += 25
        if risk_indicators['cpf_destinatario']:
            risk_score += 10
        if risk_indicators['service_without_tax']:
            risk_score += 30
        
        risk_indicators['risk_score'] = min(risk_score, 100)
        
        return risk_indicators
    
    def _perform_compliance_checks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza verificações de conformidade
        
        Args:
            data: Dados processados
        
        Returns:
            Dict com verificações de conformidade
        """
        compliance = {
            'document_format_valid': data['emitente']['is_valid_format'] and data['destinatario']['is_valid_format'],
            'values_consistent': abs(data['nfe'].valor_total - (data['nfe'].valor_produtos + (data['nfe'].valor_impostos or 0))) < 0.01,
            'has_required_fields': bool(data['nfe'].chave_acesso and data['nfe'].numero and data['nfe'].data_emissao),
            'items_have_codes': all(item.ncm_declarado for item in data['nfe'].itens),
            'compliance_score': 0
        }
        
        # Calcular score de conformidade
        compliance_score = 0
        if compliance['document_format_valid']:
            compliance_score += 30
        if compliance['values_consistent']:
            compliance_score += 25
        if compliance['has_required_fields']:
            compliance_score += 25
        if compliance['items_have_codes']:
            compliance_score += 20
        
        compliance['compliance_score'] = compliance_score
        
        return compliance
    
    def _calculate_data_quality_score(self, validation: Dict[str, bool]) -> int:
        """
        Calcula score de qualidade dos dados
        
        Args:
            validation: Resultados de validação
        
        Returns:
            Score de qualidade (0-100)
        """
        total_checks = len(validation)
        passed_checks = sum(1 for v in validation.values() if v)
        return int((passed_checks / total_checks) * 100) if total_checks > 0 else 0
    
    def _generate_smart_metadata(self, data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """
        Gera metadados inteligentes
        
        Args:
            data: Dados processados
            doc_type: Tipo do documento
        
        Returns:
            Dict com metadados inteligentes
        """
        return {
            'document_summary': f"{data['fiscal_type']['description']} - {data['emitente']['razao_social']} → {data['destinatario']['razao_social']}",
            'fiscal_category': data['fiscal_type']['category'],
            'transaction_type': 'service' if data['fiscal_type']['is_service'] else 'merchandise',
            'participants': {
                'emitente_type': data['emitente']['document_type'],
                'destinatario_type': data['destinatario']['document_type'],
                'is_b2b': data['emitente']['is_cnpj'] and data['destinatario']['is_cnpj'],
                'is_b2c': data['emitente']['is_cnpj'] and data['destinatario']['is_cpf']
            },
            'financial_summary': {
                'total_value': data['nfe'].valor_total,
                'tax_percentage': data['metrics']['tax_percentage'],
                'item_count': data['metrics']['item_count']
            },
            'quality_indicators': {
                'data_quality_score': data['enrichment']['data_quality_score'],
                'compliance_score': data['enrichment']['compliance_checks']['compliance_score'],
                'risk_score': data['enrichment']['risk_indicators']['risk_score']
            },
            'processing_flags': {
                'requires_attention': data['enrichment']['risk_indicators']['risk_score'] > 50,
                'high_quality': data['enrichment']['data_quality_score'] > 80,
                'compliant': data['enrichment']['compliance_checks']['compliance_score'] > 70
            }
        }


# Função de conveniência
def parse_fiscal_document_smart(xml_path: str) -> Dict[str, Any]:
    """
    Função de conveniência para processamento inteligente de documento fiscal
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Dict com dados processados e metadados
    """
    parser = SmartFiscalParser()
    return parser.parse_document(xml_path)
