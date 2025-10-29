"""
FiscalAI MVP - NFS-e Parser
Parser para arquivos XML de Nota Fiscal de Serviços Eletrônica (NFS-e)
"""

import xmltodict
import lxml.etree as ET
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

from ..models import NFe, ItemNFe, StatusProcessamento

logger = logging.getLogger(__name__)


class NFeSEXMLParser:
    """
    Parser de arquivos XML de NFS-e (Nota Fiscal de Serviços Eletrônica)
    Extrai informações estruturadas do XML da NFS-e
    """
    
    def __init__(self):
        """Inicializa o parser"""
        self.namespaces = {
            'nfse': 'http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd'
        }
    
    def parse_file(self, xml_path: str) -> NFe:
        """
        Faz parsing de um arquivo XML de NFS-e
        
        Args:
            xml_path: Caminho para o arquivo XML da NFS-e
        
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
        Faz parsing de uma string XML de NFS-e
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Objeto NFe com dados estruturados
        
        Raises:
            ValueError: Se XML for inválido ou incompleto
        """
        try:
            # Limpar quebras de linha e espaços extras
            xml_content_clean = ' '.join(xml_content.split())
            
            # Converter XML para dict com proteção contra XXE
            xml_dict = xmltodict.parse(
                xml_content_clean,
                process_namespaces=False,
                disable_entities=True,
                process_comments=False,
                strip_whitespace=True
            )
            
            # Navegar na estrutura do XML NFS-e
            # Estrutura: ConsultarNfseResposta -> ListaNfse -> CompNfse -> Nfse -> InfNfse
            if 'ConsultarNfseResposta' in xml_dict:
                lista_nfse = xml_dict['ConsultarNfseResposta'].get('ListaNfse', {})
                if 'CompNfse' in lista_nfse:
                    # Pode ser uma lista ou um único item
                    comp_nfse = lista_nfse['CompNfse']
                    if isinstance(comp_nfse, list):
                        # Múltiplas NFS-e - usar a primeira
                        nfse_root = comp_nfse[0]['Nfse']['InfNfse']
                    else:
                        # Uma única NFS-e
                        nfse_root = comp_nfse['Nfse']['InfNfse']
                else:
                    raise ValueError("Estrutura XML inválida: ListaNfse não encontrada")
            else:
                raise ValueError("Estrutura XML inválida: ConsultarNfseResposta não encontrada")
            
            # Extrair dados
            nfe_data = self._extract_nfse_data(nfse_root)
            
            # Criar objeto NFe
            nfe = NFe(**nfe_data)
            nfe.status = StatusProcessamento.CONCLUIDO
            nfe.data_processamento = datetime.now()
            
            return nfe
            
        except Exception as e:
            raise ValueError(f"Erro ao fazer parsing do XML NFS-e: {str(e)}")
    
    def _extract_nfse_data(self, nfse_root: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai dados estruturados do dict XML NFS-e
        
        Args:
            nfse_root: Dict com dados da raiz InfNfse
        
        Returns:
            Dict com dados para criar objeto NFe
        """
        # Identificação da NFS-e
        numero = nfse_root.get('Numero', '')
        codigo_verificacao = nfse_root.get('CodigoVerificacao', '')
        # NFS-e não tem chave de acesso de 44 dígitos, criar uma chave numérica única
        # Usar hash do número + código para criar chave de 44 dígitos
        import hashlib
        hash_input = f"{numero}{codigo_verificacao}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
        # Converter hex para números e completar com zeros
        chave_numerica = ''.join([str(int(c, 16)) for c in hash_hex])
        chave_acesso = chave_numerica.ljust(44, '0')[:44]
        
        # Data de emissão
        data_emissao_str = nfse_root.get('DataEmissao', '')
        data_emissao = self._parse_datetime(data_emissao_str)
        
        # Prestador de serviço (emitente)
        prestador = nfse_root.get('PrestadorServico', {})
        identificacao_prestador = prestador.get('IdentificacaoPrestador', {})
        cnpj_emitente = identificacao_prestador.get('Cnpj', '')
        razao_social_emitente = prestador.get('RazaoSocial', 'Prestador não informado')
        
        # Tomador de serviço (destinatário)
        tomador = nfse_root.get('TomadorServico', {})
        identificacao_tomador = tomador.get('IdentificacaoTomador', {})
        cpf_cnpj_tomador = identificacao_tomador.get('CpfCnpj', {})
        
        # Pode ser CPF ou CNPJ - normalizar para 14 dígitos
        cnpj_destinatario = ''
        if isinstance(cpf_cnpj_tomador, dict):
            cpf = cpf_cnpj_tomador.get('Cpf', '')
            cnpj = cpf_cnpj_tomador.get('Cnpj', '')
            if cnpj:
                cnpj_destinatario = cnpj
            elif cpf:
                # CPF tem 11 dígitos, adicionar zeros à esquerda para 14
                cnpj_destinatario = cpf.zfill(14)
        else:
            doc = str(cpf_cnpj_tomador) if cpf_cnpj_tomador else ''
            if len(doc) == 11:  # CPF
                cnpj_destinatario = doc.zfill(14)
            elif len(doc) == 14:  # CNPJ
                cnpj_destinatario = doc
            else:
                cnpj_destinatario = doc.zfill(14)
        
        razao_social_destinatario = tomador.get('RazaoSocial', 'Tomador não informado')
        
        # Serviço (equivalente aos itens da NF-e)
        servico = nfse_root.get('Servico', {})
        valores = servico.get('Valores', {})
        
        valor_total = float(valores.get('ValorServicos', 0))
        valor_produtos = valor_total  # NFS-e não tem separação entre produtos e impostos
        valor_impostos = float(valores.get('ValorIss', 0))
        
        # Criar item único para o serviço
        item_servico = self._create_service_item(servico, nfse_root)
        
        return {
            'chave_acesso': chave_acesso,
            'numero': str(numero),
            'serie': '1',  # NFS-e não tem série
            'data_emissao': data_emissao,
            'cnpj_emitente': cnpj_emitente,
            'razao_social_emitente': razao_social_emitente,
            'cnpj_destinatario': cnpj_destinatario,
            'razao_social_destinatario': razao_social_destinatario,
            'valor_total': valor_total,
            'valor_produtos': valor_produtos,
            'valor_impostos': valor_impostos,
            'itens': [item_servico],
        }
    
    def _create_service_item(self, servico: Dict[str, Any], nfse_root: Dict[str, Any]) -> ItemNFe:
        """
        Cria um item baseado no serviço da NFS-e
        
        Args:
            servico: Dict com dados do serviço
            nfse_root: Dict com dados completos da NFS-e
        
        Returns:
            Objeto ItemNFe
        """
        valores = servico.get('Valores', {})
        
        # Descrição do serviço
        discriminacao = servico.get('Discriminacao', 'Serviço não especificado')
        
        # Código do serviço (equivalente ao NCM)
        item_lista_servico = servico.get('ItemListaServico', '00000000')
        codigo_tributacao = servico.get('CodigoTributacaoMunicipio', '00000000')
        
        # Garantir que o código tenha 8 dígitos (padrão NCM)
        if len(item_lista_servico) < 8:
            item_lista_servico = item_lista_servico.zfill(8)
        if len(codigo_tributacao) < 8:
            codigo_tributacao = codigo_tributacao.zfill(8)
        
        # Valores
        valor_total = float(valores.get('ValorServicos', 0))
        base_calculo = float(valores.get('BaseCalculo', valor_total))
        aliquota = float(valores.get('Aliquota', 0))
        
        # Calcular valor unitário (assumir quantidade 1)
        quantidade = 1.0
        valor_unitario = valor_total / quantidade if quantidade > 0 else valor_total
        
        return ItemNFe(
            numero_item=1,
            descricao=discriminacao,
            ncm_declarado=item_lista_servico,  # Usar código do serviço como NCM
            cfop="0000",  # NFS-e não tem CFOP
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            unidade="UN",
            codigo_produto=codigo_tributacao,
        )
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Faz parsing de string de data/hora do XML NFS-e
        
        Args:
            dt_str: String de data no formato ISO
        
        Returns:
            Objeto datetime
        """
        if not dt_str:
            return datetime.now()
        
        # Tentar formatos comuns para NFS-e
        formats = [
            '%Y-%m-%dT%H:%M:%S',     # ISO sem timezone
            '%Y-%m-%dT%H:%M:%S.%f',  # ISO com microsegundos
            '%Y-%m-%d',               # Apenas data
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        # Fallback
        return datetime.now()
    
    def validate_xml(self, xml_path: str) -> tuple[bool, Optional[str]]:
        """
        Valida estrutura básica do XML de NFS-e
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (is_valid, error_message)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Verificar elementos obrigatórios para NFS-e
            required_elements = ['ConsultarNfseResposta', 'ListaNfse']
            
            for elem in required_elements:
                if root.find(f'.//{elem}') is None:
                    return False, f"Elemento obrigatório não encontrado: {elem}"
            
            return True, None
            
        except ET.XMLSyntaxError as e:
            return False, f"Erro de sintaxe XML: {str(e)}"
        except Exception as e:
            return False, f"Erro ao validar XML: {str(e)}"


# Função de conveniência
def parse_nfse_xml(xml_path: str) -> NFe:
    """
    Função de conveniência para fazer parsing de NFS-e XML
    
    Args:
        xml_path: Caminho para o arquivo XML
    
    Returns:
        Objeto NFe
    """
    parser = NFeSEXMLParser()
    return parser.parse_file(xml_path)
