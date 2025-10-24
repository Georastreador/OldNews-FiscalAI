"""
OldNews FiscalAI - Agente 1: Extrator de Dados
Especialista em extração e estruturação de dados de NF-e XML
"""

from crewai import Agent, Task
from typing import Dict, Any, Optional
from pathlib import Path

from ..models import NFe, StatusProcessamento
from ..utils import NFeXMLParser
from ..utils.xml_parser_robusto import NFeXMLParserRobusto


class Agente1Extrator:
    """
    Agente 1: Extrator de Dados
    
    Papel: Analista de Dados Estruturados
    Responsabilidades:
    - Receber arquivo XML de NF-e
    - Fazer parsing e validação do XML
    - Extrair campos essenciais
    - Estruturar dados em formato JSON
    - Passar dados para próximos agentes
    """
    
    def __init__(self, llm: Optional[Any] = None):
        """
        Inicializa o agente
        
        Args:
            llm: Instância do LLM (opcional, não usado diretamente por este agente)
        """
        self.llm = llm
        self.parser = NFeXMLParser()
        self.parser_robusto = NFeXMLParserRobusto()
        
        # Criar agente CrewAI
        self.agent = Agent(
            role="Analista de Dados Estruturados de NF-e",
            goal="Extrair e estruturar dados de Notas Fiscais Eletrônicas com precisão e confiabilidade",
            backstory="""Você é um especialista em processamento de documentos fiscais eletrônicos 
            com 10 anos de experiência. Você conhece profundamente a estrutura XML da NF-e brasileira 
            e é meticuloso na extração de dados, garantindo que nenhuma informação importante seja perdida. 
            Você valida cada campo extraído e identifica inconsistências estruturais no XML.""",
            verbose=True,
            allow_delegation=False,
        )
    
    def criar_tarefa(self, xml_path: str) -> Task:
        """
        Cria tarefa de extração de dados
        
        Args:
            xml_path: Caminho para o arquivo XML da NF-e
        
        Returns:
            Task do CrewAI
        """
        descricao = f"""Extraia e estruture os dados da NF-e do arquivo XML: {xml_path}

INSTRUÇÕES:
1. Faça o parsing do arquivo XML
2. Valide a estrutura do XML
3. Extraia os seguintes campos obrigatórios:
   - Chave de acesso (44 dígitos)
   - Número e série da NF-e
   - Data de emissão
   - CNPJ e razão social do emitente
   - CNPJ e razão social do destinatário
   - Valor total da NF-e
   - Lista completa de itens (produtos)
   
4. Para cada item, extraia:
   - Número do item
   - Descrição do produto
   - NCM (8 dígitos)
   - CFOP (4 dígitos)
   - Quantidade e unidade
   - Valor unitário e valor total
   
5. Valide:
   - Formato da chave de acesso
   - Formato dos CNPJs
   - Consistência entre valores (quantidade * valor unitário = valor total)
   - Presença de todos os campos obrigatórios

6. Retorne os dados estruturados em formato JSON

FORMATO DE SAÍDA ESPERADO:
{{
    "chave_acesso": "...",
    "numero": "...",
    "serie": "...",
    "data_emissao": "...",
    "cnpj_emitente": "...",
    "razao_social_emitente": "...",
    "cnpj_destinatario": "...",
    "razao_social_destinatario": "...",
    "valor_total": 0.00,
    "valor_produtos": 0.00,
    "itens": [
        {{
            "numero_item": 1,
            "descricao": "...",
            "ncm_declarado": "...",
            "cfop": "...",
            "quantidade": 0.0,
            "valor_unitario": 0.0,
            "valor_total": 0.0,
            "unidade": "..."
        }}
    ],
    "status": "concluido"
}}

Se houver erros na extração, retorne em formato JSON:
{{
    "erro": "descrição do erro",
    "status": "erro"
}}
"""
        
        return Task(
            description=descricao,
            agent=self.agent,
            expected_output="Dados estruturados da NF-e em formato JSON válido"
        )
    
    def executar(self, xml_path: str) -> Dict[str, Any]:
        """
        Executa extração de dados diretamente (sem CrewAI)
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Dict com dados extraídos ou erro
        """
        try:
            # Validar arquivo
            xml_path_obj = Path(xml_path)
            if not xml_path_obj.exists():
                return {
                    "erro": f"Arquivo não encontrado: {xml_path}",
                    "status": "erro"
                }
            
            # Usar parser robusto diretamente (mais confiável)
            nfe = self.parser_robusto.parse_file(str(xml_path_obj))
            print("✅ Parser robusto funcionou!")
            
            # Converter para dict
            nfe_dict = self._nfe_to_dict(nfe)
            nfe_dict["status"] = "concluido"
            
            return nfe_dict
            
        except Exception as e:
            return {
                "erro": f"Erro ao processar XML: {str(e)}",
                "status": "erro"
            }
    
    def _nfe_to_dict(self, nfe: NFe) -> Dict[str, Any]:
        """
        Converte objeto NFe para dict
        
        Args:
            nfe: Objeto NFe
        
        Returns:
            Dict com dados da NF-e
        """
        return {
            "chave_acesso": nfe.chave_acesso,
            "numero": nfe.numero,
            "serie": nfe.serie,
            "data_emissao": nfe.data_emissao.isoformat(),
            "cnpj_emitente": nfe.cnpj_emitente,
            "razao_social_emitente": nfe.razao_social_emitente,
            "cnpj_destinatario": nfe.cnpj_destinatario,
            "razao_social_destinatario": nfe.razao_social_destinatario,
            "valor_total": nfe.valor_total,
            "valor_produtos": nfe.valor_produtos,
            "valor_impostos": nfe.valor_impostos,
            "itens": [
                {
                    "numero_item": item.numero_item,
                    "descricao": item.descricao,
                    "ncm_declarado": item.ncm_declarado,
                    "cfop": item.cfop,
                    "quantidade": item.quantidade,
                    "valor_unitario": item.valor_unitario,
                    "valor_total": item.valor_total,
                    "unidade": item.unidade,
                    "codigo_produto": item.codigo_produto,
                    "ean": item.ean,
                }
                for item in nfe.itens
            ]
        }

