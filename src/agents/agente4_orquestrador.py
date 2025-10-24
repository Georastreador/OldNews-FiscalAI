"""
OldNews FiscalAI - Agente 4: Orquestrador e Coordenador
Gerencia o fluxo de trabalho e gera relatório consolidado
"""

from crewai import Agent, Task, Crew, Process
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from ..models import NFe, ClassificacaoNCM, ResultadoAnalise, RelatorioFiscal
from .agente1_extrator import Agente1Extrator
from .agente2_classificador import Agente2Classificador
from .agente3_validador import Agente3Validador
from ..utils.pdf_exporter import PDFExporter


class Agente4Orquestrador:
    """
    Agente 4: Orquestrador e Coordenador
    
    Papel: Gerente de Projeto e Analista Estratégico
    Responsabilidades:
    - Coordenar fluxo entre Agentes 1, 2 e 3
    - Consolidar resultados de todos os agentes
    - Gerar resumo executivo
    - Criar relatório final em PDF
    - Calcular métricas e KPIs
    """
    
    def __init__(self, llm: Any):
        """
        Inicializa o agente
        
        Args:
            llm: Instância do LLM
        """
        self.llm = llm
        
        # Criar agente CrewAI
        self.agent = Agent(
            role="Gerente de Projeto e Analista Estratégico Fiscal",
            goal="Coordenar análise fiscal completa e gerar relatórios executivos claros e acionáveis",
            backstory="""Você é um gerente de projetos fiscais com MBA e 20 anos de experiência. 
            Você coordena equipes de auditores, entende profundamente os processos fiscais e 
            sabe comunicar resultados complexos de forma clara para diferentes públicos (técnicos 
            e executivos). Você é estratégico, identifica padrões e sempre fornece recomendações 
            práticas e acionáveis.""",
            llm=llm,
            verbose=True,
            allow_delegation=True,
        )
    
    def criar_crew(self,
                   agente1: Agente1Extrator,
                   agente2: Agente2Classificador,
                   agente3: Agente3Validador,
                   xml_path: str) -> Crew:
        """
        Cria Crew completa com todos os agentes
        
        Args:
            agente1: Agente Extrator
            agente2: Agente Classificador
            agente3: Agente Validador
            xml_path: Caminho do arquivo XML
        
        Returns:
            Crew configurada
        """
        # Criar tarefas
        tarefa1 = agente1.criar_tarefa(xml_path)
        
        # Tarefa 2 depende de tarefa 1
        tarefa2 = Task(
            description="""Usando os dados extraídos da NF-e, classifique todos os produtos com NCM.
            Use o resultado da tarefa anterior como entrada.""",
            agent=agente2.agent,
            expected_output="Classificações NCM em formato JSON",
            context=[tarefa1],
        )
        
        # Tarefa 3 depende de tarefas 1 e 2
        tarefa3 = Task(
            description="""Usando os dados da NF-e e as classificações NCM, execute validação 
            fiscal completa e detecção de fraudes. Use os resultados das tarefas anteriores.""",
            agent=agente3.agent,
            expected_output="Relatório de validação em formato JSON",
            context=[tarefa1, tarefa2],
        )
        
        # Tarefa 4: Consolidação (este agente)
        tarefa4 = Task(
            description="""Consolide todos os resultados das análises anteriores e gere um 
            relatório executivo final.
            
            TAREFAS:
            1. Revisar dados extraídos (Agente 1)
            2. Revisar classificações NCM (Agente 2)
            3. Revisar validações e fraudes (Agente 3)
            4. Gerar resumo executivo claro e objetivo
            5. Destacar principais problemas e riscos
            6. Fornecer recomendações estratégicas
            
            FORMATO DE SAÍDA (JSON):
            {
                "resumo_executivo": "texto claro e objetivo",
                "status_geral": "aprovado/atenção/bloqueado",
                "principais_problemas": ["lista"],
                "principais_riscos": ["lista"],
                "recomendacoes_estrategicas": ["lista"],
                "metricas": {
                    "num_itens": 0,
                    "valor_total": 0.0,
                    "num_divergencias_ncm": 0,
                    "num_fraudes_detectadas": 0,
                    "score_risco": 0.0
                }
            }
            """,
            agent=self.agent,
            expected_output="Relatório executivo consolidado em JSON",
            context=[tarefa1, tarefa2, tarefa3],
        )
        
        # Criar Crew
        crew = Crew(
            agents=[agente1.agent, agente2.agent, agente3.agent, self.agent],
            tasks=[tarefa1, tarefa2, tarefa3, tarefa4],
            process=Process.sequential,
            verbose=True,
        )
        
        return crew
    
    def executar_fluxo_completo(self,
                                xml_path: str,
                                agente1: Agente1Extrator,
                                agente2: Agente2Classificador,
                                agente3: Agente3Validador) -> RelatorioFiscal:
        """
        Executa fluxo completo de análise (sem CrewAI, direto)
        
        Args:
            xml_path: Caminho do XML
            agente1: Agente Extrator
            agente2: Agente Classificador
            agente3: Agente Validador
        
        Returns:
            RelatorioFiscal completo
        """
        print("🔄 Iniciando análise fiscal completa...")
        
        # Passo 1: Extração
        print("📄 Passo 1/4: Extraindo dados da NF-e...")
        nfe_data = agente1.executar(xml_path)
        if nfe_data.get('status') == 'erro':
            raise ValueError(f"Erro na extração: {nfe_data.get('erro')}")
        
        # Converter para NFe
        from datetime import datetime
        from ..models import ItemNFe
        
        itens = [
            ItemNFe(**item_data)
            for item_data in nfe_data['itens']
        ]
        
        nfe = NFe(
            chave_acesso=nfe_data['chave_acesso'],
            numero=nfe_data['numero'],
            serie=nfe_data['serie'],
            data_emissao=datetime.fromisoformat(nfe_data['data_emissao']),
            cnpj_emitente=nfe_data['cnpj_emitente'],
            razao_social_emitente=nfe_data.get('razao_social_emitente'),
            cnpj_destinatario=nfe_data['cnpj_destinatario'],
            razao_social_destinatario=nfe_data.get('razao_social_destinatario'),
            valor_total=nfe_data['valor_total'],
            valor_produtos=nfe_data['valor_produtos'],
            itens=itens,
        )
        
        # Passo 2: Classificação NCM
        print("🏷️  Passo 2/4: Classificando produtos com NCM...")
        classificacoes = agente2.executar(itens)
        
        # Passo 3: Validação e Detecção de Fraudes
        print("🔍 Passo 3/4: Validando e detectando fraudes...")
        resultado_analise = agente3.executar(nfe, classificacoes)
        
        # Passo 4: Consolidação e Relatório
        print("📊 Passo 4/4: Gerando relatório consolidado...")
        resumo_executivo = self._gerar_resumo_executivo(
            nfe, classificacoes, resultado_analise
        )
        
        recomendacoes_finais = self._gerar_recomendacoes_finais(resultado_analise)
        
        relatorio = RelatorioFiscal(
            nfe=nfe,
            resultado_analise=resultado_analise,
            classificacoes_ncm=list(classificacoes.values()),
            resumo_executivo=resumo_executivo,
            recomendacoes_finais=recomendacoes_finais,
        )
        
        print("✅ Análise concluída!")
        return relatorio
    
    def exportar_relatorio_pdf(self, 
                              nfe: NFe, 
                              classificacoes: Dict[int, ClassificacaoNCM],
                              resultado: ResultadoAnalise,
                              output_path: str = None) -> str:
        """
        Exporta relatório executivo em PDF
        
        Args:
            nfe: Dados da NF-e
            classificacoes: Classificações NCM dos itens
            resultado: Resultado da análise de fraudes
            output_path: Caminho opcional para salvar o PDF
            
        Returns:
            str: Caminho do arquivo PDF gerado
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"relatorio_fiscal_{timestamp}.pdf"
        
        exporter = PDFExporter()
        return exporter.export_relatorio_executivo(nfe, classificacoes, resultado, output_path)
    
    def _gerar_resumo_executivo(self,
                                nfe: NFe,
                                classificacoes: Dict[int, ClassificacaoNCM],
                                resultado: ResultadoAnalise) -> str:
        """Gera resumo executivo da análise"""
        
        # Calcular métricas
        num_itens = len(nfe.itens)
        num_divergencias = sum(1 for c in classificacoes.values() if c.diverge)
        num_fraudes = len(resultado.fraudes_detectadas)
        
        resumo = f"""# RESUMO EXECUTIVO - ANÁLISE FISCAL NF-e

**NF-e:** {nfe.numero}/{nfe.serie} | **Chave:** {nfe.chave_acesso}
**Data:** {nfe.data_emissao.strftime('%d/%m/%Y')} | **Valor Total:** R$ {nfe.valor_total:,.2f}

**Emitente:** {nfe.razao_social_emitente or nfe.cnpj_emitente}
**Destinatário:** {nfe.razao_social_destinatario or nfe.cnpj_destinatario}

## STATUS GERAL: {resultado.nivel_risco.value.upper()}

**Score de Risco:** {resultado.score_risco_geral}/100

## MÉTRICAS PRINCIPAIS

- **Itens Analisados:** {num_itens}
- **Divergências NCM:** {num_divergencias} ({num_divergencias/num_itens*100:.1f}%)
- **Fraudes Detectadas:** {num_fraudes}
- **Itens Suspeitos:** {len(resultado.itens_suspeitos)}

## PRINCIPAIS PROBLEMAS

"""
        
        if num_fraudes > 0:
            resumo += "### Fraudes Detectadas:\n"
            for fraude in resultado.fraudes_detectadas[:3]:  # Top 3
                resumo += f"- **{fraude.tipo_fraude.value.upper()}** (Score: {fraude.score}/100)\n"
                resumo += f"  {fraude.justificativa[:150]}...\n\n"
        else:
            resumo += "✅ Nenhuma fraude detectada.\n\n"
        
        if num_divergencias > 0:
            resumo += f"### Divergências de Classificação NCM:\n"
            resumo += f"{num_divergencias} item(ns) com NCM declarado diferente do predito.\n\n"
        
        return resumo
    
    def _gerar_recomendacoes_finais(self, resultado: ResultadoAnalise) -> List[str]:
        """Gera recomendações estratégicas finais"""
        recomendacoes = []
        
        if resultado.nivel_risco == "critico":
            recomendacoes.append("🚨 BLOQUEIO IMEDIATO: Não processar esta NF-e até investigação completa")
            recomendacoes.append("Acionar departamento jurídico e compliance")
            recomendacoes.append("Considerar auditoria completa do fornecedor")
        
        elif resultado.nivel_risco == "alto":
            recomendacoes.append("⚠️ REVISÃO OBRIGATÓRIA: Análise manual por especialista fiscal")
            recomendacoes.append("Solicitar esclarecimentos formais do fornecedor")
            recomendacoes.append("Registrar ocorrência para monitoramento futuro")
        
        elif resultado.nivel_risco == "medio":
            recomendacoes.append("⚡ ATENÇÃO: Verificar pontos destacados antes de aprovar")
            recomendacoes.append("Manter registro para análise de tendências")
        
        else:
            recomendacoes.append("✅ APROVADO: Processar normalmente")
            recomendacoes.append("Manter monitoramento de rotina")
        
        # Recomendações específicas
        if len(resultado.fraudes_detectadas) > 0:
            tipos_fraude = set(f.tipo_fraude.value for f in resultado.fraudes_detectadas)
            if "subfaturamento" in tipos_fraude:
                recomendacoes.append("💰 Validar preços com pesquisa de mercado")
            if "ncm_incorreto" in tipos_fraude:
                recomendacoes.append("📋 Solicitar reclassificação NCM do fornecedor")
            if "triangulacao" in tipos_fraude:
                recomendacoes.append("🔄 Investigar cadeia completa de transações")
        
        return recomendacoes

