"""
OldNews FiscalAI - Agente 3: Validador Fiscal e Detector de Fraudes
Especialista em validação de conformidade fiscal e detecção de fraudes
"""

from crewai import Agent, Task
from typing import Dict, Any, Optional
import json

from ..models import NFe, ClassificacaoNCM, ResultadoAnalise
from ..detectors import OrquestradorDeteccaoFraudes


class Agente3Validador:
    """
    Agente 3: Validador Fiscal e Detector de Fraudes
    
    Papel: Auditor de Conformidade e Segurança Fiscal
    Responsabilidades:
    - Validar NCM declarado vs predito
    - Verificar consistência NCM vs CFOP
    - Executar detectores de fraude
    - Analisar padrões suspeitos
    - Gerar alertas de inconsistências
    """
    
    def __init__(self, 
                 llm: Any,
                 orquestrador_fraudes: Optional[OrquestradorDeteccaoFraudes] = None):
        """
        Inicializa o agente
        
        Args:
            llm: Instância do LLM
            orquestrador_fraudes: Orquestrador de detecção de fraudes
        """
        self.llm = llm
        self.orquestrador_fraudes = orquestrador_fraudes or OrquestradorDeteccaoFraudes()
        
        # Criar agente CrewAI
        self.agent = Agent(
            role="Auditor Fiscal e Detector de Fraudes",
            goal="Validar conformidade fiscal e detectar padrões de fraude em NF-e com precisão",
            backstory="""Você é um auditor fiscal experiente com 15 anos de experiência em 
            detecção de fraudes fiscais. Você conhece profundamente a legislação tributária 
            brasileira e os padrões mais comuns de sonegação e fraude. Você é meticuloso na 
            análise de inconsistências e sempre fornece evidências claras para suas conclusões. 
            Você sabe diferenciar erros honestos de tentativas intencionais de fraude.""",
            llm=llm,
            verbose=True,
            allow_delegation=False,
        )
    
    def criar_tarefa(self, 
                     nfe_data: Dict[str, Any],
                     classificacoes: Dict[int, ClassificacaoNCM]) -> Task:
        """
        Cria tarefa de validação e detecção de fraudes
        
        Args:
            nfe_data: Dados da NF-e (dict)
            classificacoes: Classificações NCM dos itens
        
        Returns:
            Task do CrewAI
        """
        # Executar análise de fraudes
        resultado_fraudes = self._executar_analise_fraudes(nfe_data, classificacoes)
        
        # Formatar para o prompt
        fraudes_str = self._formatar_fraudes(resultado_fraudes)
        nfe_str = json.dumps(nfe_data, indent=2, ensure_ascii=False)
        class_str = self._formatar_classificacoes(classificacoes)
        
        descricao = f"""Analise a NF-e abaixo e valide a conformidade fiscal.

DADOS DA NF-E:
{nfe_str}

CLASSIFICAÇÕES NCM:
{class_str}

ANÁLISE AUTOMÁTICA DE FRAUDES:
{fraudes_str}

TAREFAS:
1. VALIDAÇÕES BÁSICAS:
   - Compare NCM declarado vs NCM predito para cada item
   - Verifique consistência entre NCM e CFOP
   - Valide cálculos de valores e impostos
   - Identifique campos faltantes ou inconsistentes

2. ANÁLISE DE FRAUDES:
   - Revise as fraudes detectadas automaticamente
   - Valide se as evidências são sólidas
   - Identifique possíveis falsos positivos
   - Sugira investigações adicionais se necessário

3. AVALIAÇÃO DE RISCO:
   - Score de risco: {resultado_fraudes.score_risco_geral}/100
   - Nível: {resultado_fraudes.nivel_risco.value.upper()}
   - Fraudes detectadas: {len(resultado_fraudes.fraudes_detectadas)}

4. PARECER FINAL:
   - Resuma os principais problemas encontrados
   - Classifique a gravidade (baixa, média, alta, crítica)
   - Recomende ações específicas
   - Indique se a NF-e deve ser aprovada, revisada ou bloqueada

FORMATO DE SAÍDA (JSON):
{{
    "validacoes_basicas": {{
        "ncm_consistente": true/false,
        "cfop_consistente": true/false,
        "valores_corretos": true/false,
        "problemas": ["lista de problemas encontrados"]
    }},
    "analise_fraudes": {{
        "fraudes_confirmadas": ["lista de fraudes confirmadas"],
        "falsos_positivos": ["lista de possíveis falsos positivos"],
        "investigacoes_adicionais": ["lista de pontos a investigar"]
    }},
    "parecer_final": {{
        "resumo": "resumo executivo dos problemas",
        "gravidade": "baixa/media/alta/critica",
        "recomendacao": "aprovar/revisar/bloquear",
        "acoes_especificas": ["lista de ações recomendadas"]
    }}
}}

Seja objetivo, técnico e baseie suas conclusões em evidências concretas.
"""
        
        return Task(
            description=descricao,
            agent=self.agent,
            expected_output="Relatório de validação fiscal em formato JSON"
        )
    
    def executar(self,
                 nfe: NFe,
                 classificacoes: Dict[int, ClassificacaoNCM]) -> ResultadoAnalise:
        """
        Executa validação e detecção de fraudes
        
        Args:
            nfe: NF-e a ser analisada
            classificacoes: Classificações NCM dos itens
        
        Returns:
            ResultadoAnalise com fraudes detectadas
        """
        # Executar orquestrador de fraudes
        resultado = self.orquestrador_fraudes.analisar_nfe(nfe, classificacoes)
        
        return resultado
    
    def _executar_analise_fraudes(self,
                                  nfe_data: Dict[str, Any],
                                  classificacoes: Dict[int, ClassificacaoNCM]) -> ResultadoAnalise:
        """Executa análise de fraudes a partir de dados dict"""
        # Converter dict para NFe
        from datetime import datetime
        from ..models import ItemNFe
        
        itens = [
            ItemNFe(
                numero_item=item['numero_item'],
                descricao=item['descricao'],
                ncm_declarado=item['ncm_declarado'],
                cfop=item['cfop'],
                quantidade=item['quantidade'],
                valor_unitario=item['valor_unitario'],
                valor_total=item['valor_total'],
                unidade=item['unidade'],
            )
            for item in nfe_data['itens']
        ]
        
        nfe = NFe(
            chave_acesso=nfe_data['chave_acesso'],
            numero=nfe_data['numero'],
            serie=nfe_data['serie'],
            data_emissao=datetime.fromisoformat(nfe_data['data_emissao']),
            cnpj_emitente=nfe_data['cnpj_emitente'],
            cnpj_destinatario=nfe_data['cnpj_destinatario'],
            valor_total=nfe_data['valor_total'],
            valor_produtos=nfe_data['valor_produtos'],
            itens=itens,
        )
        
        return self.orquestrador_fraudes.analisar_nfe(nfe, classificacoes)
    
    def _formatar_fraudes(self, resultado: ResultadoAnalise) -> str:
        """Formata resultado de fraudes para exibição"""
        if not resultado.fraudes_detectadas:
            return "✅ Nenhuma fraude detectada."
        
        texto = f"⚠️ SCORE DE RISCO: {resultado.score_risco_geral}/100 ({resultado.nivel_risco.value.upper()})\n"
        texto += f"📊 FRAUDES DETECTADAS: {len(resultado.fraudes_detectadas)}\n\n"
        
        for i, fraude in enumerate(resultado.fraudes_detectadas, 1):
            texto += f"{i}. {fraude.tipo_fraude.value.upper()} (Score: {fraude.score}/100)\n"
            texto += f"   Confiança: {fraude.confianca:.0%}\n"
            texto += f"   Item: {fraude.item_numero or 'NF-e completa'}\n"
            texto += f"   Evidências:\n"
            for ev in fraude.evidencias:
                texto += f"   - {ev}\n"
            texto += f"   Justificativa: {fraude.justificativa}\n\n"
        
        texto += f"AÇÕES RECOMENDADAS:\n"
        for acao in resultado.acoes_recomendadas:
            texto += f"- {acao}\n"
        
        return texto
    
    def _formatar_classificacoes(self, classificacoes: Dict[int, ClassificacaoNCM]) -> str:
        """Formata classificações NCM para exibição"""
        if not classificacoes:
            return "Nenhuma classificação disponível"
        
        texto = ""
        for num_item, class_ncm in classificacoes.items():
            diverge = "❌ DIVERGE" if class_ncm.diverge else "✅ OK"
            texto += f"Item {num_item}: {class_ncm.descricao_produto}\n"
            texto += f"  NCM Declarado: {class_ncm.ncm_declarado or 'N/A'}\n"
            texto += f"  NCM Predito: {class_ncm.ncm_predito} (confiança: {class_ncm.confianca:.0%}) {diverge}\n"
            if class_ncm.justificativa:
                texto += f"  Justificativa: {class_ncm.justificativa}\n"
            texto += "\n"
        
        return texto

