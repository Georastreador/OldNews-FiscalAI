"""
OldNews FiscalAI - Agente 2: Classificador NCM
Especialista em classificação fiscal de produtos usando IA
"""

from crewai import Agent, Task
from typing import Dict, Any, List, Optional
import json
import pandas as pd

from ..models import ItemNFe, ClassificacaoNCM


class Agente2Classificador:
    """
    Agente 2: Classificador NCM
    
    Papel: Especialista em Classificação Fiscal
    Responsabilidades:
    - Receber descrições de produtos
    - Classificar produtos com código NCM
    - Fornecer justificativa da classificação
    - Calcular score de confiança
    - Sugerir NCMs alternativos quando ambíguo
    """
    
    def __init__(self, llm: Any, tabela_ncm: Optional[pd.DataFrame] = None):
        """
        Inicializa o agente
        
        Args:
            llm: Instância do LLM
            tabela_ncm: DataFrame com NCM e descrições oficiais
        """
        self.llm = llm
        self.tabela_ncm = tabela_ncm if tabela_ncm is not None else self._criar_tabela_ncm_mock()
        
        # Criar agente CrewAI
        self.agent = Agent(
            role="Especialista em Classificação Fiscal NCM",
            goal="Classificar produtos com código NCM correto e fornecer justificativas claras",
            backstory="""Você é um auditor fiscal certificado com 15 anos de experiência em 
            classificação NCM (Nomenclatura Comum do Mercosul). Você conhece profundamente a 
            estrutura hierárquica do NCM, as regras de classificação e os casos especiais. 
            Você sempre fornece justificativas técnicas para suas classificações e identifica 
            quando há ambiguidade, sugerindo alternativas quando necessário.""",
            llm=llm,
            verbose=True,
            allow_delegation=False,
        )
    
    def criar_tarefa(self, itens: List[Dict[str, Any]]) -> Task:
        """
        Cria tarefa de classificação NCM
        
        Args:
            itens: Lista de itens (dicts) a classificar
        
        Returns:
            Task do CrewAI
        """
        # Preparar contexto com exemplos de NCM
        exemplos_ncm = self._preparar_exemplos_ncm()
        
        itens_str = json.dumps(itens, indent=2, ensure_ascii=False)
        
        descricao = f"""Classifique os produtos abaixo com o código NCM mais adequado.

PRODUTOS A CLASSIFICAR:
{itens_str}

EXEMPLOS DE NCM PARA REFERÊNCIA:
{exemplos_ncm}

INSTRUÇÕES:
1. Para cada produto, analise cuidadosamente a descrição
2. Identifique a categoria principal do produto
3. Determine o código NCM de 8 dígitos mais adequado
4. Forneça uma justificativa técnica da classificação
5. Calcule um score de confiança (0.0 a 1.0)
6. Se houver ambiguidade, sugira NCMs alternativos

REGRAS DE CLASSIFICAÇÃO NCM:
- Primeiros 2 dígitos: Capítulo (categoria geral)
- Dígitos 3-4: Posição (subcategoria)
- Dígitos 5-6: Subposição (detalhamento)
- Dígitos 7-8: Item e subitem (especificação final)

FORMATO DE SAÍDA (JSON):
{{
    "classificacoes": [
        {{
            "numero_item": 1,
            "descricao_produto": "...",
            "ncm_predito": "12345678",
            "ncm_declarado": "87654321",
            "confianca": 0.95,
            "justificativa": "Explicação técnica da classificação...",
            "alternativas": [
                {{"ncm": "11111111", "descricao": "...", "score": 0.75}}
            ]
        }}
    ]
}}

IMPORTANTE:
- Seja preciso e técnico nas justificativas
- Confiança alta (>0.9) apenas quando tiver certeza absoluta
- Confiança média (0.7-0.9) para classificações prováveis
- Confiança baixa (<0.7) quando houver ambiguidade
- Sempre compare com o NCM declarado e indique se diverge
"""
        
        return Task(
            description=descricao,
            agent=self.agent,
            expected_output="Lista de classificações NCM em formato JSON"
        )
    
    def executar(self, itens: List[ItemNFe]) -> Dict[int, ClassificacaoNCM]:
        """
        Executa classificação NCM usando LLM
        
        Args:
            itens: Lista de itens da NF-e
        
        Returns:
            Dict {numero_item: ClassificacaoNCM}
        """
        # Preparar dados para o LLM
        itens_dict = [
            {
                "numero_item": item.numero_item,
                "descricao": item.descricao,
                "ncm_declarado": item.ncm_declarado,
                "quantidade": item.quantidade,
                "valor_unitario": item.valor_unitario,
            }
            for item in itens
        ]
        
        # Criar prompt
        prompt = self._criar_prompt_classificacao(itens_dict)
        
        try:
            # Invocar LLM
            response = self.llm.invoke(prompt)
            
            # Extrair conteúdo
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Verificar se a resposta não está vazia
            if not content or content.strip() == "":
                raise ValueError("Resposta vazia do LLM")
            
            # Verificar se contém JSON
            if not ('{' in content and '}' in content):
                raise ValueError("Resposta não contém JSON válido")
            
            # Parsear JSON
            content = self._limpar_json(content)
            
            # Verificar se ainda tem conteúdo após limpeza
            if not content or content.strip() == "":
                raise ValueError("Conteúdo vazio após limpeza")
            
            resultado = json.loads(content)
            
            # Verificar se tem a estrutura esperada
            if 'classificacoes' not in resultado:
                raise ValueError("JSON não contém 'classificacoes'")
            
            # Converter para ClassificacaoNCM
            classificacoes = {}
            for class_dict in resultado.get('classificacoes', []):
                if not isinstance(class_dict, dict):
                    continue
                    
                if 'numero_item' not in class_dict:
                    continue
                    
                try:
                    num_item = class_dict['numero_item']
                    classificacoes[num_item] = ClassificacaoNCM(**class_dict)
                except Exception as item_error:
                    continue
            
            # Se não conseguiu classificar nenhum item, usar fallback
            if not classificacoes:
                raise ValueError("Nenhuma classificação válida encontrada")
            
            return classificacoes
            
        except Exception as e:
            try:
                import streamlit as st
                st.session_state['fallback_classificacao_utilizada'] = True
            except Exception:
                pass
            # Log persistente
            try:
                from datetime import datetime
                with open('logs/fallback_warnings.log', 'a') as f:
                    f.write(f"[{datetime.now()}] Falha na classificação NCM. Erro: {e}\n")
            except Exception:
                pass
            # Fallback: usar NCM declarado
            return self._fallback_classificacao(itens)
    
    def _criar_prompt_classificacao(self, itens: List[Dict]) -> str:
        """Cria prompt para classificação NCM"""
        exemplos_ncm = self._preparar_exemplos_ncm()
        itens_str = json.dumps(itens, indent=2, ensure_ascii=False)
        
        return f"""Você é um especialista em classificação fiscal NCM. Classifique os produtos abaixo.

PRODUTOS:
{itens_str}

EXEMPLOS DE NCM:
{exemplos_ncm}

Retorne em formato JSON:
{{
    "classificacoes": [
        {{
            "numero_item": 1,
            "descricao_produto": "descrição",
            "ncm_predito": "12345678",
            "ncm_declarado": "87654321",
            "confianca": 0.95,
            "justificativa": "explicação técnica",
            "alternativas": []
        }}
    ]
}}

Seja preciso e técnico. Confiança alta (>0.9) apenas se tiver certeza."""
        
    def _preparar_exemplos_ncm(self) -> str:
        """Prepara exemplos de NCM para o prompt"""
        if self.tabela_ncm.empty:
            return "Nenhum exemplo disponível"
        
        exemplos = []
        for ncm, row in self.tabela_ncm.head(10).iterrows():
            exemplos.append(f"- {ncm}: {row['descricao']}")
        
        return "\n".join(exemplos)
    
    def _limpar_json(self, content: str) -> str:
        """Remove markdown e limpa JSON"""
        content = content.strip()
        if content.startswith('```json'):
            content = content.split('```json')[1].split('```')[0]
        elif content.startswith('```'):
            content = content.split('```')[1].split('```')[0]
        return content.strip()
    
    def _fallback_classificacao(self, itens: List[ItemNFe]) -> Dict[int, ClassificacaoNCM]:
        """Fallback: usar NCM declarado com baixa confiança"""
        classificacoes = {}
        for item in itens:
            classificacoes[item.numero_item] = ClassificacaoNCM(
                numero_item=item.numero_item,
                descricao_produto=item.descricao,
                ncm_predito=item.ncm_declarado,
                ncm_declarado=item.ncm_declarado,
                confianca=0.5,
                justificativa="Classificação automática falhou. Usando NCM declarado.",
            )
        return classificacoes
    
    def _criar_tabela_ncm_mock(self) -> pd.DataFrame:
        """Cria tabela NCM mock"""
        data = {
            'ncm': [
                '85171231', '84713012', '85176255', '85044090', '39202090',
                '84713011', '85171210', '85176262', '85044021', '73269090',
            ],
            'descricao': [
                'Telefones celulares (smartphones)',
                'Computadores portáteis (notebooks)',
                'Aparelhos para comutação de redes (roteadores)',
                'Carregadores de baterias',
                'Placas, folhas, películas de polímeros de propileno',
                'Computadores de mesa (desktops)',
                'Telefones celulares básicos',
                'Modems e roteadores WiFi',
                'Fontes de alimentação eletrônicas',
                'Outras obras de ferro ou aço',
            ]
        }
        
        df = pd.DataFrame(data)
        df.set_index('ncm', inplace=True)
        return df

