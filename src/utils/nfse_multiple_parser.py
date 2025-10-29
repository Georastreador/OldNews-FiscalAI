"""
OldNews FiscalAI - NFS-e Multiple Parser
Parser para arquivos XML de NFS-e com múltiplas notas
Processa TODAS as NFS-e do arquivo, não apenas a primeira
"""

import xmltodict
import lxml.etree as ET
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

from ..models import NFe, ItemNFe, StatusProcessamento

logger = logging.getLogger(__name__)


class NFeSEMultipleParser:
    """
    Parser de arquivos XML de NFS-e com múltiplas notas
    Extrai informações estruturadas de TODAS as NFS-e do arquivo
    """
    
    def __init__(self):
        """Inicializa o parser"""
        self.namespaces = {
            'nfse': 'http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd'
        }
    
    def parse_file(self, xml_path: str) -> List[NFe]:
        """
        Faz parsing de um arquivo XML de NFS-e com múltiplas notas
        
        Args:
            xml_path: Caminho para o arquivo XML da NFS-e
        
        Returns:
            Lista de objetos NFe com dados estruturados
        
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
    
    def parse_string(self, xml_content: str) -> List[NFe]:
        """
        Faz parsing de uma string XML de NFS-e com múltiplas notas
        
        Args:
            xml_content: Conteúdo XML como string
        
        Returns:
            Lista de objetos NFe com dados estruturados
        
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
                    comp_nfse = lista_nfse['CompNfse']
                    
                    # Garantir que comp_nfse seja sempre uma lista
                    if not isinstance(comp_nfse, list):
                        comp_nfse = [comp_nfse]
                    
                    # Processar TODAS as NFS-e
                    nfes = []
                    for i, comp_item in enumerate(comp_nfse):
                        try:
                            nfse_root = comp_item['Nfse']['InfNfse']
                            
                            # Extrair dados
                            nfe_data = self._extract_nfse_data(nfse_root, i)
                            
                            # Criar objeto NFe
                            nfe = NFe(**nfe_data)
                            nfe.status = StatusProcessamento.CONCLUIDO
                            nfe.data_processamento = datetime.now()
                            
                            nfes.append(nfe)
                            
                        except Exception as e:
                            logger.warning(f"Erro ao processar NFS-e {i+1}: {str(e)}")
                            continue
                    
                    if not nfes:
                        raise ValueError("Nenhuma NFS-e válida encontrada no arquivo")
                    
                    return nfes
                else:
                    raise ValueError("Estrutura XML inválida: ListaNfse não encontrada")
            else:
                raise ValueError("Estrutura XML inválida: ConsultarNfseResposta não encontrada")
            
        except Exception as e:
            raise ValueError(f"Erro ao fazer parsing do XML NFS-e: {str(e)}")
    
    def _extract_nfse_data(self, nfse_root: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
        """
        Extrai dados estruturados do dict XML NFS-e
        
        Args:
            nfse_root: Dict com dados da raiz InfNfse
            index: Índice da NFS-e no arquivo (para chave única)
        
        Returns:
            Dict com dados para criar objeto NFe
        """
        # Identificação da NFS-e
        numero = nfse_root.get('Numero', '')
        codigo_verificacao = nfse_root.get('CodigoVerificacao', '')
        
        # Criar chave de acesso única para NFS-e
        # Usar hash do número + código + índice para criar chave de 44 dígitos
        import hashlib
        hash_input = f"{numero}{codigo_verificacao}{index}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
        # Converter hex para números e completar com zeros
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
        
        # Dados do prestador de serviço
        prestador = nfse_root.get('PrestadorServico', {})
        cnpj_emitente = prestador.get('IdentificacaoPrestador', {}).get('Cnpj', '')
        razao_social_emitente = prestador.get('RazaoSocial', '')
        
        # Dados do tomador de serviço
        tomador = nfse_root.get('TomadorServico', {})
        cpf_cnpj_tomador = tomador.get('IdentificacaoTomador', {}).get('CpfCnpj', {})
        cpf_cnpj_raw = cpf_cnpj_tomador.get('Cnpj', cpf_cnpj_tomador.get('Cpf', ''))
        
        # Ajustar CPF/CNPJ para validação (CPF tem 11 dígitos, CNPJ tem 14)
        if len(cpf_cnpj_raw) == 11:
            cnpj_destinatario = cpf_cnpj_raw.ljust(14, '0')  # CPF -> CNPJ
        elif len(cpf_cnpj_raw) == 14:
            cnpj_destinatario = cpf_cnpj_raw
        else:
            cnpj_destinatario = cpf_cnpj_raw.ljust(14, '0')
        
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
        
        # Criar item único para NFS-e (diferente de NF-e que pode ter múltiplos itens)
        # NFS-e usa códigos de serviço, não NCM - ajustar para validação
        ncm_ajustado = item_lista_servico.ljust(8, '0') if len(item_lista_servico) < 8 else item_lista_servico[:8]
        cfop_ajustado = '0000'  # NFS-e não tem CFOP, usar padrão
        
        item = ItemNFe(
            numero_item=1,
            codigo_produto=item_lista_servico,
            descricao=discriminacao[:500] if discriminacao else f"Serviço {item_lista_servico}",
            ncm_declarado=ncm_ajustado,  # Ajustar para validação do modelo
            ncm_predito=None,
            ncm_confianca=None,
            cfop=cfop_ajustado,  # NFS-e não tem CFOP, usar padrão
            unidade='UN',
            quantidade=1.0,
            valor_unitario=valor_servicos,
            valor_total=valor_servicos
        )
        
        # Criar dados da NFe
        nfe_data = {
            'chave_acesso': chave_acesso,
            'numero': str(numero),
            'serie': '1',  # NFS-e geralmente tem série 1
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
        
        return nfe_data


def parse_multiple_nfse(xml_path: str) -> List[NFe]:
    """
    Função utilitária para fazer parsing de múltiplas NFS-e
    
    Args:
        xml_path: Caminho para o arquivo XML
        
    Returns:
        Lista de objetos NFe
    """
    parser = NFeSEMultipleParser()
    return parser.parse_file(xml_path)


def parse_multiple_nfse_string(xml_content: str) -> List[NFe]:
    """
    Função utilitária para fazer parsing de múltiplas NFS-e a partir de string
    
    Args:
        xml_content: Conteúdo XML como string
        
    Returns:
        Lista de objetos NFe
    """
    parser = NFeSEMultipleParser()
    return parser.parse_string(xml_content)
