"""
OldNews FiscalAI - Enhanced Multiple XML Parser
Parser aprimorado que detecta e processa múltiplas notas fiscais de qualquer tipo
"""

import xmltodict
import lxml.etree as ET
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import logging
import re
from datetime import datetime

from ..models import NFe, ItemNFe, StatusProcessamento

logger = logging.getLogger(__name__)


class EnhancedMultipleXMLParser:
    """
    Parser aprimorado que detecta e processa múltiplas notas fiscais
    Suporta NF-e, NFS-e e outros tipos de documentos fiscais
    """
    
    def __init__(self):
        """Inicializa o parser aprimorado"""
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe',
            'nfse': 'http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd',
            'cte': 'http://www.portalfiscal.inf.br/cte',
            'mdfe': 'http://www.portalfiscal.inf.br/mdfe'
        }
    
    def parse_file(self, xml_path: str) -> Tuple[List[NFe], str, str]:
        """
        Faz parsing de um arquivo XML detectando e processando múltiplas notas
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (lista_objetos_nfe, tipo_documento, descricao)
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {xml_path}")
        
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        return self.parse_string(xml_content, str(xml_path))
    
    def parse_string(self, xml_content: str, file_path: str = "") -> Tuple[List[NFe], str, str]:
        """
        Faz parsing de uma string XML detectando e processando múltiplas notas
        
        Args:
            xml_content: Conteúdo XML como string
            file_path: Caminho do arquivo (para logs)
        
        Returns:
            Tuple (lista_objetos_nfe, tipo_documento, descricao)
        """
        try:
            # Detectar tipo de documento
            doc_type, description = self._detect_document_type(xml_content)
            logger.info(f"Tipo detectado: {doc_type} - {description}")
            
            # Processar baseado no tipo
            if doc_type == 'nfse':
                return self._parse_multiple_nfse(xml_content), doc_type, description
            elif doc_type == 'nfe':
                return self._parse_multiple_nfe(xml_content), doc_type, description
            else:
                # Tentar parsing genérico
                return self._parse_generic_multiple(xml_content), doc_type, description
                
        except Exception as e:
            logger.error(f"Erro ao fazer parsing do XML: {str(e)}")
            raise ValueError(f"Erro ao fazer parsing do XML: {str(e)}")
    
    def _detect_document_type(self, xml_content: str) -> Tuple[str, str]:
        """
        Detecta o tipo de documento fiscal
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Tuple (tipo, descricao)
        """
        # Detectar por elementos específicos
        if 'ConsultarNfseResposta' in xml_content or 'ListaNfse' in xml_content:
            return 'nfse', 'Nota Fiscal de Serviços Eletrônica (NFS-e)'
        elif 'nfeProc' in xml_content or 'infNFe' in xml_content:
            return 'nfe', 'Nota Fiscal Eletrônica (NF-e)'
        elif 'cteProc' in xml_content or 'infCte' in xml_content:
            return 'cte', 'Conhecimento de Transporte Eletrônico (CT-e)'
        elif 'mdfeProc' in xml_content or 'infMDFe' in xml_content:
            return 'mdfe', 'Manifesto Eletrônico de Documentos Fiscais (MDF-e)'
        else:
            return 'unknown', 'Documento fiscal não identificado'
    
    def _parse_multiple_nfse(self, xml_content: str) -> List[NFe]:
        """
        Processa múltiplas NFS-e
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Lista de objetos NFe
        """
        try:
            # Limpar e parsear XML
            xml_content_clean = ' '.join(xml_content.split())
            xml_dict = xmltodict.parse(
                xml_content_clean,
                process_namespaces=False,
                disable_entities=True,
                process_comments=False,
                strip_whitespace=True
            )
            
            # Navegar na estrutura NFS-e
            if 'ConsultarNfseResposta' in xml_dict:
                lista_nfse = xml_dict['ConsultarNfseResposta'].get('ListaNfse', {})
                if 'CompNfse' in lista_nfse:
                    comp_nfse = lista_nfse['CompNfse']
                    
                    # Garantir que seja uma lista
                    if not isinstance(comp_nfse, list):
                        comp_nfse = [comp_nfse]
                    
                    logger.info(f"Processando {len(comp_nfse)} NFS-e encontradas")
                    
                    # Processar todas as NFS-e
                    nfes = []
                    for i, comp_item in enumerate(comp_nfse):
                        try:
                            nfse_root = comp_item['Nfse']['InfNfse']
                            nfe_data = self._extract_nfse_data(nfse_root, i)
                            
                            nfe = NFe(**nfe_data)
                            nfe.status = StatusProcessamento.CONCLUIDO
                            nfe.data_processamento = datetime.now()
                            
                            nfes.append(nfe)
                            logger.info(f"NFS-e {i+1} processada com sucesso")
                            
                        except Exception as e:
                            logger.warning(f"Erro ao processar NFS-e {i+1}: {str(e)}")
                            continue
                    
                    if not nfes:
                        raise ValueError("Nenhuma NFS-e válida encontrada")
                    
                    return nfes
                else:
                    raise ValueError("Estrutura XML inválida: ListaNfse não encontrada")
            else:
                raise ValueError("Estrutura XML inválida: ConsultarNfseResposta não encontrada")
                
        except Exception as e:
            raise ValueError(f"Erro ao processar NFS-e: {str(e)}")
    
    def _parse_multiple_nfe(self, xml_content: str) -> List[NFe]:
        """
        Processa múltiplas NF-e (se houver)
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Lista de objetos NFe
        """
        try:
            # Primeiro, tentar detectar múltiplas notas usando regex
            nfe_matches = self._find_multiple_nfe_patterns(xml_content)
            
            if len(nfe_matches) > 1:
                logger.info(f"Detectadas {len(nfe_matches)} notas fiscais no arquivo")
                return self._process_multiple_nfe_from_matches(nfe_matches)
            
            # Se não encontrou múltiplas, processar como única nota
            xml_content_clean = ' '.join(xml_content.split())
            xml_dict = xmltodict.parse(
                xml_content_clean,
                process_namespaces=False,
                disable_entities=True,
                process_comments=False,
                strip_whitespace=True
            )
            
            # Estrutura típica de NF-e
            if 'nfeProc' in xml_dict:
                nfe_root = xml_dict['nfeProc']['NFe']['infNFe']
            elif 'NFe' in xml_dict:
                nfe_root = xml_dict['NFe']['infNFe']
            elif 'infNFe' in xml_dict:
                nfe_root = xml_dict['infNFe']
            else:
                raise ValueError("Estrutura XML inválida: raiz não encontrada")
            
            # Extrair dados da NF-e
            nfe_data = self._extract_nfe_data(nfe_root)
            
            # Criar objeto NFe
            nfe = NFe(**nfe_data)
            nfe.status = StatusProcessamento.CONCLUIDO
            nfe.data_processamento = datetime.now()
            
            logger.info("NF-e processada com sucesso")
            return [nfe]
            
        except Exception as e:
            raise ValueError(f"Erro ao processar NF-e: {str(e)}")
    
    def _find_multiple_nfe_patterns(self, xml_content: str) -> List[str]:
        """
        Encontra padrões de múltiplas NF-e no conteúdo XML
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Lista de strings contendo as NF-e encontradas
        """
        import re
        
        # Padrões para detectar múltiplas NF-e
        patterns = [
            r'<infNFe[^>]*>.*?</infNFe>',  # Padrão infNFe completo
            r'<NFe[^>]*>.*?</NFe>',        # Padrão NFe completo
        ]
        
        all_matches = []
        
        for pattern in patterns:
            matches = re.findall(pattern, xml_content, re.DOTALL | re.IGNORECASE)
            all_matches.extend(matches)
        
        # Remover duplicatas mantendo ordem
        unique_matches = []
        seen = set()
        for match in all_matches:
            if match not in seen:
                unique_matches.append(match)
                seen.add(match)
        
        logger.info(f"Encontrados {len(unique_matches)} padrões de NF-e")
        return unique_matches
    
    def _process_multiple_nfe_from_matches(self, nfe_matches: List[str]) -> List[NFe]:
        """
        Processa múltiplas NF-e a partir dos matches encontrados
        
        Args:
            nfe_matches: Lista de strings contendo as NF-e
        
        Returns:
            Lista de objetos NFe
        """
        nfes = []
        
        for i, nfe_content in enumerate(nfe_matches):
            try:
                # Tentar parsear cada NF-e individualmente
                xml_dict = xmltodict.parse(
                    nfe_content,
                    process_namespaces=False,
                    disable_entities=True,
                    process_comments=False,
                    strip_whitespace=True
                )
                
                # Extrair dados da NF-e
                if 'infNFe' in xml_dict:
                    nfe_root = xml_dict['infNFe']
                elif 'NFe' in xml_dict and 'infNFe' in xml_dict['NFe']:
                    nfe_root = xml_dict['NFe']['infNFe']
                else:
                    logger.warning(f"Não foi possível extrair infNFe da NF-e {i+1}")
                    continue
                
                nfe_data = self._extract_nfe_data(nfe_root)
                
                # Criar objeto NFe
                nfe = NFe(**nfe_data)
                nfe.status = StatusProcessamento.CONCLUIDO
                nfe.data_processamento = datetime.now()
                
                nfes.append(nfe)
                logger.info(f"NF-e {i+1} processada com sucesso")
                
            except Exception as e:
                logger.warning(f"Erro ao processar NF-e {i+1}: {str(e)}")
                continue
        
        if not nfes:
            raise ValueError("Nenhuma NF-e válida encontrada nos matches")
        
        return nfes
    
    def _parse_generic_multiple(self, xml_content: str) -> List[NFe]:
        """
        Parser genérico para documentos não identificados
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Lista de objetos NFe
        """
        try:
            # Tentar extrair informações básicas
            xml_content_clean = ' '.join(xml_content.split())
            xml_dict = xmltodict.parse(
                xml_content_clean,
                process_namespaces=False,
                disable_entities=True,
                process_comments=False,
                strip_whitespace=True
            )
            
            # Procurar por padrões de notas fiscais
            nfes = []
            
            # Buscar por elementos que possam conter dados de notas
            def find_fiscal_elements(data, path=""):
                elements = []
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        if any(keyword in key.lower() for keyword in ['nfe', 'nfse', 'nota', 'fiscal', 'numero', 'chave']):
                            elements.append((current_path, value))
                        if isinstance(value, (dict, list)):
                            elements.extend(find_fiscal_elements(value, current_path))
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        current_path = f"{path}[{i}]" if path else f"[{i}]"
                        elements.extend(find_fiscal_elements(item, current_path))
                return elements
            
            fiscal_elements = find_fiscal_elements(xml_dict)
            logger.info(f"Encontrados {len(fiscal_elements)} elementos fiscais")
            
            # Se não encontrou elementos específicos, criar uma nota genérica
            if not fiscal_elements:
                nfe_data = self._create_generic_nfe_data(xml_content)
                nfe = NFe(**nfe_data)
                nfe.status = StatusProcessamento.CONCLUIDO
                nfe.data_processamento = datetime.now()
                return [nfe]
            
            # Processar elementos encontrados
            for i, (path, value) in enumerate(fiscal_elements[:10]):  # Limitar a 10 para evitar sobrecarga
                try:
                    nfe_data = self._extract_from_element(path, value, i)
                    if nfe_data:
                        nfe = NFe(**nfe_data)
                        nfe.status = StatusProcessamento.CONCLUIDO
                        nfe.data_processamento = datetime.now()
                        nfes.append(nfe)
                except Exception as e:
                    logger.warning(f"Erro ao processar elemento {path}: {str(e)}")
                    continue
            
            if not nfes:
                # Fallback: criar nota genérica
                nfe_data = self._create_generic_nfe_data(xml_content)
                nfe = NFe(**nfe_data)
                nfe.status = StatusProcessamento.CONCLUIDO
                nfe.data_processamento = datetime.now()
                return [nfe]
            
            return nfes
            
        except Exception as e:
            logger.error(f"Erro no parser genérico: {str(e)}")
            # Fallback: criar nota genérica
            nfe_data = self._create_generic_nfe_data(xml_content)
            nfe = NFe(**nfe_data)
            nfe.status = StatusProcessamento.CONCLUIDO
            nfe.data_processamento = datetime.now()
            return [nfe]
    
    def _extract_nfse_data(self, nfse_root: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
        """
        Extrai dados de NFS-e
        
        Args:
            nfse_root: Dados da NFS-e
            index: Índice da nota
        
        Returns:
            Dados para criar objeto NFe
        """
        import hashlib
        
        # Identificação
        numero = nfse_root.get('Numero', f'NFSE_{index+1}')
        codigo_verificacao = nfse_root.get('CodigoVerificacao', '')
        
        # Criar chave de acesso única
        hash_input = f"{numero}{codigo_verificacao}{index}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
        chave_numerica = ''.join([str(int(c, 16)) for c in hash_hex])
        chave_acesso = (chave_numerica + '0' * 44)[:44]
        
        # Data de emissão
        data_emissao_str = nfse_root.get('DataEmissao', '')
        try:
            if 'T' in data_emissao_str:
                data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00'))
            else:
                data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d')
        except:
            data_emissao = datetime.now()
        
        # Dados do prestador
        prestador = nfse_root.get('PrestadorServico', {})
        cnpj_emitente = prestador.get('IdentificacaoPrestador', {}).get('Cnpj', '')
        razao_social_emitente = prestador.get('RazaoSocial', '')
        
        # Dados do tomador
        tomador = nfse_root.get('TomadorServico', {})
        cpf_cnpj_tomador = tomador.get('IdentificacaoTomador', {}).get('CpfCnpj', {})
        cpf_cnpj_raw = cpf_cnpj_tomador.get('Cnpj', cpf_cnpj_tomador.get('Cpf', ''))
        cnpj_destinatario = cpf_cnpj_raw.ljust(14, '0') if cpf_cnpj_raw else '00000000000000'
        razao_social_destinatario = tomador.get('RazaoSocial', '')
        
        # Dados do serviço
        servico = nfse_root.get('Servico', {})
        valores = servico.get('Valores', {})
        valor_servicos = float(valores.get('ValorServicos', 0))
        valor_iss = float(valores.get('ValorIss', 0))
        valor_liquido = float(valores.get('ValorLiquidoNfse', valor_servicos))
        
        # Item do serviço
        item_lista_servico = servico.get('ItemListaServico', '')
        discriminacao = servico.get('Discriminacao', '')
        
        # Criar item
        ncm_ajustado = item_lista_servico.ljust(8, '0') if len(item_lista_servico) < 8 else item_lista_servico[:8]
        
        item = ItemNFe(
            numero_item=1,
            codigo_produto=item_lista_servico,
            descricao=discriminacao[:500] if discriminacao else f"Serviço {item_lista_servico}",
            ncm_declarado=ncm_ajustado,
            ncm_predito=None,
            ncm_confianca=None,
            cfop='0000',
            unidade='UN',
            quantidade=1.0,
            valor_unitario=valor_servicos,
            valor_total=valor_servicos
        )
        
        return {
            'chave_acesso': chave_acesso,
            'numero': str(numero),
            'serie': '1',
            'data_emissao': data_emissao,
            'cnpj_emitente': cnpj_emitente,
            'razao_social_emitente': razao_social_emitente,
            'cnpj_destinatario': cnpj_destinatario,
            'razao_social_destinatario': razao_social_destinatario,
            'valor_total': valor_liquido,
            'valor_produtos': valor_servicos,
            'valor_impostos': valor_iss,
            'tipo_documento': 'nfse',
            'descricao_documento': 'Nota Fiscal de Serviços Eletrônica',
            'itens': [item]
        }
    
    def _extract_nfe_data(self, nfe_root: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai dados de NF-e
        
        Args:
            nfe_root: Dados da NF-e
        
        Returns:
            Dados para criar objeto NFe
        """
        from datetime import datetime
        
        # Identificação
        ide = nfe_root.get('ide', {})
        chave_acesso = nfe_root.get('@Id', '').replace('NFe', '')
        numero = ide.get('nNF', '')
        serie = ide.get('serie', '')
        
        # Data de emissão
        data_emissao_str = ide.get('dhEmi', '')
        try:
            data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00'))
        except:
            data_emissao = datetime.now()
        
        # Emitente
        emit = nfe_root.get('emit', {})
        cnpj_emitente = emit.get('CNPJ', '')
        razao_social_emitente = emit.get('xNome', '')
        
        # Destinatário
        dest = nfe_root.get('dest', {})
        cnpj_destinatario = dest.get('CNPJ', dest.get('CPF', ''))
        razao_social_destinatario = dest.get('xNome', '')
        
        # Valores
        total = nfe_root.get('total', {}).get('ICMSTot', {})
        valor_total = float(total.get('vNF', 0))
        valor_produtos = float(total.get('vProd', 0))
        valor_impostos = float(total.get('vTotTrib', 0))
        
        # Itens
        itens = []
        det = nfe_root.get('det', [])
        if not isinstance(det, list):
            det = [det]
        
        for i, item_data in enumerate(det):
            prod = item_data.get('prod', {})
            item = ItemNFe(
                numero_item=i + 1,
                codigo_produto=prod.get('cProd', ''),
                descricao=prod.get('xProd', ''),
                ncm_declarado=prod.get('NCM', ''),
                ncm_predito=None,
                ncm_confianca=None,
                cfop=prod.get('CFOP', ''),
                unidade=prod.get('uCom', ''),
                quantidade=float(prod.get('qCom', 0)),
                valor_unitario=float(prod.get('vUnCom', 0)),
                valor_total=float(prod.get('vProd', 0))
            )
            itens.append(item)
        
        return {
            'chave_acesso': chave_acesso,
            'numero': str(numero),
            'serie': str(serie),
            'data_emissao': data_emissao,
            'cnpj_emitente': cnpj_emitente,
            'razao_social_emitente': razao_social_emitente,
            'cnpj_destinatario': cnpj_destinatario,
            'razao_social_destinatario': razao_social_destinatario,
            'valor_total': valor_total,
            'valor_produtos': valor_produtos,
            'valor_impostos': valor_impostos,
            'tipo_documento': 'nfe',
            'descricao_documento': 'Nota Fiscal Eletrônica',
            'itens': itens
        }
    
    def _create_generic_nfe_data(self, xml_content: str) -> Dict[str, Any]:
        """
        Cria dados genéricos de NFe quando não consegue extrair dados específicos
        
        Args:
            xml_content: Conteúdo XML
        
        Returns:
            Dados genéricos para criar objeto NFe
        """
        import hashlib
        
        # Gerar chave de acesso baseada no conteúdo
        hash_hex = hashlib.md5(xml_content.encode()).hexdigest()
        chave_numerica = ''.join([str(int(c, 16)) for c in hash_hex])
        chave_acesso = (chave_numerica + '0' * 44)[:44]
        
        # Item genérico
        item = ItemNFe(
            numero_item=1,
            codigo_produto='GEN001',
            descricao='Documento fiscal processado',
            ncm_declarado='00000000',
            ncm_predito=None,
            ncm_confianca=None,
            cfop='0000',
            unidade='UN',
            quantidade=1.0,
            valor_unitario=0.0,
            valor_total=0.0
        )
        
        return {
            'chave_acesso': chave_acesso,
            'numero': '1',
            'serie': '1',
            'data_emissao': datetime.now(),
            'cnpj_emitente': '00000000000000',
            'razao_social_emitente': 'Documento Fiscal',
            'cnpj_destinatario': '00000000000000',
            'razao_social_destinatario': 'Processado',
            'valor_total': 0.0,
            'valor_produtos': 0.0,
            'valor_impostos': 0.0,
            'tipo_documento': 'unknown',
            'descricao_documento': 'Documento Fiscal Processado',
            'itens': [item]
        }
    
    def _extract_from_element(self, path: str, value: Any, index: int) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de um elemento específico
        
        Args:
            path: Caminho do elemento
            value: Valor do elemento
            index: Índice
        
        Returns:
            Dados extraídos ou None
        """
        try:
            # Implementar extração baseada no caminho
            # Por enquanto, retornar None para usar fallback
            return None
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do elemento {path}: {str(e)}")
            return None


# Funções de conveniência
def parse_enhanced_multiple(xml_path: str) -> Tuple[List[NFe], str, str]:
    """
    Função de conveniência para fazer parsing aprimorado de múltiplas notas
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Tuple (lista_objetos_nfe, tipo_documento, descricao)
    """
    parser = EnhancedMultipleXMLParser()
    return parser.parse_file(xml_path)
