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
    
    def executar_csv(self, df, filename: str) -> Dict[str, Any]:
        """
        Executa extração de dados de CSV usando IA
        
        Args:
            df: DataFrame com dados CSV
            filename: Nome do arquivo CSV
        
        Returns:
            Dict com dados extraídos e NFe criada
        """
        try:
            # Usar LLM para analisar e estruturar dados do CSV
            if self.llm:
                prompt = f"""
                Analise os dados do arquivo CSV '{filename}' e extraia informações fiscais relevantes.
                
                Dados disponíveis:
                - Colunas: {list(df.columns)}
                - Total de linhas: {len(df)}
                - Primeiras 3 linhas:
                {df.head(3).to_string()}
                
                Extraia e estruture os seguintes dados:
                1. Informações do emitente (CNPJ, razão social)
                2. Informações do destinatário (CNPJ, razão social)
                3. Dados dos produtos (código, descrição, NCM, CFOP, quantidade, valores)
                4. Valores totais
                5. Data de emissão (se disponível)
                
                Retorne em formato JSON estruturado.
                """
                
                response = self.llm.invoke(prompt)
                # Log removido para evitar poluição do terminal
                
                # Processar resposta do LLM
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                # Tentar extrair JSON da resposta
                import json
                import re
                
                # Procurar por JSON na resposta
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    dados_extraidos = json.loads(json_str)
                else:
                    # Se não encontrar JSON, criar estrutura básica
                    dados_extraidos = {
                        "status": "parcial",
                        "observacao": "Dados extraídos parcialmente - estrutura CSV analisada",
                        "colunas_identificadas": list(df.columns),
                        "total_linhas": len(df)
                    }
            else:
                # Fallback: análise básica sem LLM
                dados_extraidos = {
                    "status": "basico",
                    "observacao": "Análise básica sem LLM",
                    "colunas_identificadas": list(df.columns),
                    "total_linhas": len(df)
                }
            
            # Criar NFe a partir dos dados extraídos
            from ..models import NFe, ItemNFe
            from datetime import datetime
            
            itens = []
            for index, row in df.iterrows():
                item = ItemNFe(
                    numero_item=index + 1,
                    codigo_produto=str(row.get('codigo_produto', f'ITEM_{index+1}')),
                    descricao=str(row.get('descricao', f'Produto {index+1}')),
                    ncm_declarado=str(row.get('ncm', '00000000')),
                    ncm_predito=None,
                    ncm_confianca=None,
                    cfop=str(row.get('cfop', '5102')),
                    unidade=str(row.get('unidade', 'UN')),
                    quantidade=float(row.get('quantidade', 1.0)),
                    valor_unitario=float(row.get('valor_unitario', 0.0)),
                    valor_total=float(row.get('valor_total', 0.0))
                )
                itens.append(item)
            
            # Criar NFe
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            chave_acesso = f"{timestamp}{'0' * (44 - len(timestamp))}"[:44]
            
            nfe = NFe(
                chave_acesso=chave_acesso,
                numero="1",
                serie="1",
                data_emissao=datetime.now(),
                cnpj_emitente=str(df.get('cnpj_emitente', '00000000000000').iloc[0] if 'cnpj_emitente' in df.columns else '00000000000000'),
                razao_social_emitente=str(df.get('razao_social_emitente', 'Empresa CSV').iloc[0] if 'razao_social_emitente' in df.columns else 'Empresa CSV'),
                cnpj_destinatario=str(df.get('cnpj_destinatario', '00000000000000').iloc[0] if 'cnpj_destinatario' in df.columns else '00000000000000'),
                razao_social_destinatario=str(df.get('razao_social_destinatario', 'Cliente CSV').iloc[0] if 'razao_social_destinatario' in df.columns else 'Cliente CSV'),
                valor_total=float(df['valor_total'].sum() if 'valor_total' in df.columns else 0.0),
                valor_produtos=float(df['valor_total'].sum() if 'valor_total' in df.columns else 0.0),
                valor_impostos=0.0,
                tipo_documento="nfe",
                descricao_documento="Nota Fiscal Eletrônica",
                itens=itens
            )
            
            return {
                "status": "concluido",
                "dados_extraidos": dados_extraidos,
                "nfe": nfe,
                "itens": itens,
                "total_itens": len(itens)
            }
            
        except Exception as e:
            return {
                "erro": f"Erro ao processar CSV: {str(e)}",
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

