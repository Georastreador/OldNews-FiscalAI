"""
OldNews FiscalAI - Agente 5: Interface Conversacional
Chatbot para interação com usuário sobre análise fiscal
"""

from crewai import Agent, Task
from typing import Dict, Any, List, Optional
import json
import hashlib
import time
from datetime import datetime, timedelta

from ..models.schemas import NivelRisco, RelatorioFiscal


class Agente5Interface:
    """
    Agente 5: Interface Conversacional
    
    Papel: Assistente Fiscal Inteligente
    Responsabilidades:
    - Responder perguntas sobre o relatório
    - Explicar termos técnicos
    - Fornecer detalhes sobre fraudes detectadas
    - Sugerir próximos passos
    - Manter contexto da conversa
    """
    
    def __init__(self, llm: Any):
        """
        Inicializa o agente
        
        Args:
            llm: Instância do LLM
        """
        self.llm = llm
        self.relatorio: Optional[RelatorioFiscal] = None
        self.historico_conversa: List[Dict[str, str]] = []
        
        # Cache de respostas para otimização
        self.cache_respostas: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 3600  # 1 hora em segundos
        self.cache_max_size = 100  # Máximo de 100 respostas em cache
        
        # Inicialização lazy do agente CrewAI
        self._agent = None
        self._agent_initialized = False
    
    @property
    def agent(self):
        """Propriedade lazy para inicializar o agente apenas quando necessário"""
        if not self._agent_initialized:
            self._agent = Agent(
                role="Assistente Fiscal Inteligente e Educador",
                goal="Ajudar usuários a entender análises fiscais complexas de forma clara e acessível",
                backstory="""Você é um assistente fiscal virtual com excelente didática e paciência. 
                Você tem 10 anos de experiência explicando conceitos fiscais complexos para pessoas 
                de diferentes níveis de conhecimento. Você sempre responde de forma clara, objetiva 
                e amigável. Você usa exemplos práticos, evita jargões desnecessários e sempre confirma 
                se o usuário entendeu. Você é proativo em sugerir próximos passos e ações.""",
                llm=self.llm,
                verbose=False,  # Reduzido para melhor performance
                allow_delegation=False,
                max_iter=3,  # Limite de iterações para respostas mais rápidas
                max_execution_time=30,  # Timeout de 30 segundos
            )
            self._agent_initialized = True
        return self._agent
    
    def carregar_relatorio(self, relatorio: RelatorioFiscal):
        """
        Carrega relatório fiscal para contexto
        
        Args:
            relatorio: Relatório fiscal completo
        """
        self.relatorio = relatorio
        self.historico_conversa = []
        
        # Mensagem inicial
        mensagem_inicial = self._gerar_mensagem_inicial()
        self.historico_conversa.append({
            "role": "assistant",
            "content": mensagem_inicial
        })
    
    def conversar(self, mensagem_usuario: str) -> str:
        """
        Processa mensagem do usuário e retorna resposta
        
        Args:
            mensagem_usuario: Pergunta ou comando do usuário
        
        Returns:
            Resposta do assistente
        """
        # Verificar se há dados no session_state mesmo sem relatório
        import streamlit as st
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        if not self.relatorio and not multiple_nfes:
            return "❌ Nenhum relatório carregado. Por favor, analise uma NF-e primeiro."
        
        # Verificar cache primeiro
        cache_key = self._gerar_cache_key(mensagem_usuario)
        resposta_cache = self._verificar_cache(cache_key)
        if resposta_cache:
            # Adicionar ao histórico
            self.historico_conversa.append({
                "role": "user",
                "content": mensagem_usuario
            })
            self.historico_conversa.append({
                "role": "assistant",
                "content": resposta_cache
            })
            return resposta_cache
        
        # Adicionar mensagem do usuário ao histórico
        self.historico_conversa.append({
            "role": "user",
            "content": mensagem_usuario
        })
        
        # Criar prompt com contexto
        prompt = self._criar_prompt_conversa(mensagem_usuario)
        
        try:
            # Invocar LLM
            start_time = time.time()
            response = self.llm.invoke(prompt)
            response_time = time.time() - start_time
            
            # Extrair resposta
            if hasattr(response, 'content'):
                resposta = response.content
            else:
                resposta = str(response)
            
            # Adicionar ao cache
            self._adicionar_ao_cache(cache_key, resposta, response_time)
            
            # Adicionar resposta ao histórico
            self.historico_conversa.append({
                "role": "assistant",
                "content": resposta
            })
            
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao processar pergunta: {str(e)}"
    
    def _gerar_mensagem_inicial(self) -> str:
        """Gera mensagem inicial de boas-vindas"""
        if not self.relatorio:
            return "Olá! Sou seu assistente fiscal. Carregue um relatório para começar."
        
        # Usar dados do relatório diretamente
        resultado = self.relatorio
        
        # Emoji baseado no nível de risco
        emoji_status = {
            NivelRisco.BAIXO: "✅",
            NivelRisco.MEDIO: "⚡",
            NivelRisco.ALTO: "⚠️",
            NivelRisco.CRITICO: "🚨"
        }
        
        # Verificar se nivel_risco existe
        nivel_risco = getattr(resultado, 'nivel_risco', NivelRisco.BAIXO)
        emoji = emoji_status.get(nivel_risco, "📊")
        
        # Buscar dados das NFs do session_state
        import streamlit as st
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        if multiple_nfes and multiple_resultados:
            # Múltiplas NFs processadas
            total_valor = sum(nfe.valor_total for nfe in multiple_nfes)
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            score_medio = sum(resultado.score_risco_geral for resultado in multiple_resultados) / len(multiple_resultados)
            
            nfe_info = f"**Total de NFs:** {len(multiple_nfes)}\n**Valor Total:** R$ {total_valor:,.2f}\n**Total de Itens:** {total_itens}\n"
            score_risco = score_medio
        else:
            # NF única
            nfe_data = st.session_state.get('nfe_data')
            
            if nfe_data:
                nfe_info = f"**NF-e:** {nfe_data.numero}/{nfe_data.serie}\n**Valor:** R$ {nfe_data.valor_total:,.2f}\n"
            else:
                nfe_info = f"**Chave de Acesso:** {getattr(resultado, 'chave_acesso', 'N/A')}\n"
            
            score_risco = getattr(resultado, 'score_risco_geral', 0)
        
        mensagem = f"""{emoji} **Análise Fiscal Concluída!**

{nfe_info}**Status:** {nivel_risco.value.upper()}
**Score de Risco:** {score_risco:.1f}/100

"""
        
        # Verificar se fraudes_detectadas existe
        fraudes = getattr(resultado, 'fraudes_detectadas', [])
        if fraudes:
            mensagem += f"⚠️ **{len(fraudes)} fraude(s) detectada(s)**\n\n"
        else:
            mensagem += "✅ **Nenhuma fraude detectada**\n\n"
        
        mensagem += """**Como posso ajudar?**

Você pode me perguntar sobre:
- 📋 Detalhes das fraudes detectadas
- 🏷️ Classificações NCM dos produtos
- 💰 Valores e cálculos
- 📊 Explicação do score de risco
- 🎯 Próximos passos recomendados
- ❓ Qualquer dúvida sobre a análise

Digite sua pergunta abaixo! 👇"""
        
        return mensagem
    
    def _criar_prompt_conversa(self, mensagem_usuario: str) -> str:
        """Cria prompt para o LLM com contexto otimizado para janela limitada"""
        
        # Resumo conciso do relatório (máximo 200 caracteres)
        resumo_relatorio = self._resumir_relatorio_conciso()
        
        # Histórico recente (últimas 2 mensagens apenas)
        historico_recente = self.historico_conversa[-2:]
        historico_str = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in historico_recente
        ])
        
        # Prompt otimizado para contexto limitado
        prompt = f"""Você é um assistente fiscal especializado. Responda de forma clara e concisa.

CONTEXTO: {resumo_relatorio}

PERGUNTA: {mensagem_usuario}

INSTRUÇÕES:
1. Responda APENAS à pergunta feita
2. Seja direto e objetivo (máximo 3 parágrafos)
3. Use dados específicos do relatório quando disponível
4. Se não souber, diga "Não tenho essa informação no relatório"
5. Use **negrito** para destacar informações importantes
6. Termine a resposta com um ponto final

RESPOSTA:"""
        
        return prompt
    
    def _resumir_relatorio(self) -> str:
        """Cria resumo estruturado do relatório para o LLM"""
        if not self.relatorio:
            return "Nenhum relatório disponível"
        
        # Usar dados do relatório diretamente
        resultado = self.relatorio
        
        # Buscar dados das NFs do session_state
        import streamlit as st
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        if multiple_nfes and multiple_resultados:
            # Múltiplas NFs processadas
            total_valor = sum(nfe.valor_total for nfe in multiple_nfes)
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            score_medio = sum(resultado.score_risco_geral for resultado in multiple_resultados) / len(multiple_resultados)
            
            resumo = f"""
MÚLTIPLAS NFs ANALISADAS:
- Total de NFs: {len(multiple_nfes)}
- Valor Total: R$ {total_valor:,.2f}
- Total de Itens: {total_itens}
- Score Médio de Risco: {score_medio:.1f}/100
- Total de Fraudes: {total_fraudes}

RESUMO POR NF:
"""
            for i, (nfe, resultado_nf) in enumerate(zip(multiple_nfes[:5], multiple_resultados[:5]), 1):
                resumo += f"NF {i}: {nfe.numero}/{nfe.serie} - R$ {nfe.valor_total:,.2f} - Risco: {resultado_nf.score_risco_geral}/100 - Fraudes: {len(resultado_nf.fraudes_detectadas)}\n"
            
            if len(multiple_nfes) > 5:
                resumo += f"... e mais {len(multiple_nfes) - 5} NFs\n"
        else:
            # NF única
            nfe_data = st.session_state.get('nfe_data')
            
            if nfe_data:
                nfe_info = f"- Número: {nfe_data.numero}/{nfe_data.serie}\n- Chave: {nfe_data.chave_acesso}"
                valor_total_str = f"{nfe_data.valor_total:,.2f}"
            else:
                nfe_info = f"- Chave: {getattr(resultado, 'chave_acesso', 'N/A')}"
                valor_total_str = "0,00"
            
            resumo = f"""
NF-E ANALISADA:
{nfe_info}
- Data: {nfe_data.data_emissao.strftime('%d/%m/%Y') if nfe_data else 'N/A'}
- Emitente: {nfe_data.razao_social_emitente or nfe_data.cnpj_emitente if nfe_data else 'N/A'}
- Destinatário: {nfe_data.razao_social_destinatario or nfe_data.cnpj_destinatario if nfe_data else 'N/A'}
- Valor Total: R$ {valor_total_str}
- Número de Itens: {len(nfe_data.itens) if nfe_data else 0}

RESULTADO DA ANÁLISE:
- Score de Risco: {getattr(resultado, 'score_risco_geral', 0)}/100
- Nível de Risco: {getattr(resultado, 'nivel_risco', NivelRisco.BAIXO).value.upper()}
- Fraudes Detectadas: {len(getattr(resultado, 'fraudes_detectadas', []))}
- Itens Suspeitos: {len(getattr(resultado, 'itens_suspeitos', []))}

"""
        
        fraudes = getattr(resultado, 'fraudes_detectadas', [])
        if fraudes:
            resumo += "FRAUDES DETECTADAS:\n"
            for i, fraude in enumerate(fraudes, 1):
                resumo += f"{i}. {fraude.tipo_fraude.value.upper()} (Score: {fraude.score}/100)\n"
                resumo += f"   Item: {fraude.item_numero or 'NF-e completa'}\n"
                resumo += f"   Confiança: {fraude.confianca:.0%}\n"
                resumo += f"   Evidências: {', '.join(fraude.evidencias[:2])}\n"
                resumo += f"   Justificativa: {fraude.justificativa[:200]}...\n\n"
        
        # Buscar classificações do session_state se disponível
        classificacoes = st.session_state.get('classificacoes', [])
        if classificacoes:
            resumo += "CLASSIFICAÇÕES NCM:\n"
            # Tratar classificacoes como dicionário (numero_item -> ClassificacaoNCM)
            if isinstance(classificacoes, dict):
                for i, (numero_item, class_ncm) in enumerate(list(classificacoes.items())[:5], 1):
                    diverge = "DIVERGE" if class_ncm.diverge else "OK"
                    resumo += f"- Item {numero_item}: {class_ncm.descricao_produto[:50]}...\n"
                    resumo += f"  NCM Declarado: {class_ncm.ncm_declarado or 'N/A'} | NCM Predito: {class_ncm.ncm_predito} ({diverge})\n"
            else:
                # Fallback para lista (caso antigo)
                for class_ncm in classificacoes[:5]:  # Primeiros 5
                    diverge = "DIVERGE" if class_ncm.ncm_declarado != class_ncm.ncm_predito else "OK"
                    resumo += f"- Item {class_ncm.numero_item}: {class_ncm.descricao_produto[:50]}...\n"
                    resumo += f"  NCM Declarado: {class_ncm.ncm_declarado or 'N/A'} | NCM Predito: {class_ncm.ncm_predito} ({diverge})\n"
        
        resumo += f"\nAÇÕES RECOMENDADAS:\n"
        acoes = getattr(resultado, 'acoes_recomendadas', [])
        for acao in acoes[:5]:
            resumo += f"- {acao}\n"
        
        return resumo
    
    def _resumir_relatorio_conciso(self) -> str:
        """Cria resumo ultra-conciso do relatório (máximo 200 caracteres)"""
        # Buscar dados das NFs do session_state primeiro
        import streamlit as st
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        # Log removido para evitar poluição do terminal
        
        if multiple_nfes and multiple_resultados:
            # Múltiplas NFs processadas
            total_valor = sum(nfe.valor_total for nfe in multiple_nfes)
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            score_medio = sum(resultado.score_risco_geral for resultado in multiple_resultados) / len(multiple_resultados)
            
            resumo = f"{len(multiple_nfes)} NFs, R${total_valor:,.0f}, {total_itens} itens, risco {score_medio:.0f}/100, {total_fraudes} fraudes"
        else:
            # NF única ou sem dados
            if not self.relatorio:
                return "Sem relatório disponível"
            
            resultado = self.relatorio
            nfe_data = st.session_state.get('nfe_data')
            valor_total = f"{nfe_data.valor_total:,.0f}" if nfe_data else "0"
            num_itens = len(nfe_data.itens) if nfe_data else 0
            score_risco = getattr(resultado, 'score_risco_geral', 0)
            num_fraudes = len(getattr(resultado, 'fraudes_detectadas', []))
            
            resumo = f"NF-e R${valor_total}, {num_itens} itens, risco {score_risco}/100, {num_fraudes} fraudes"
        
        return resumo[:200]  # Garantir limite de 200 caracteres
    
    def limpar_historico(self):
        """Limpa histórico de conversa"""
        self.historico_conversa = []
        if self.relatorio:
            mensagem_inicial = self._gerar_mensagem_inicial()
            self.historico_conversa.append({
                "role": "assistant",
                "content": mensagem_inicial
            })
    
    def obter_historico(self) -> List[Dict[str, str]]:
        """
        Retorna histórico completo da conversa
        
        Returns:
            Lista de mensagens
        """
        return self.historico_conversa.copy()
    
    def sugerir_perguntas(self) -> List[str]:
        """
        Sugere perguntas relevantes baseadas no relatório
        
        Returns:
            Lista de perguntas sugeridas
        """
        if not self.relatorio:
            return []
        
        # Usar dados do relatório diretamente
        resultado = self.relatorio
        perguntas = []
        
        # Perguntas baseadas no contexto
        fraudes = getattr(resultado, 'fraudes_detectadas', [])
        if fraudes:
            perguntas.append("Quais fraudes foram detectadas e qual a gravidade?")
            perguntas.append("Quais são as evidências das fraudes?")
            perguntas.append("O que devo fazer com as fraudes detectadas?")
        
        itens_suspeitos = getattr(resultado, 'itens_suspeitos', [])
        if len(itens_suspeitos) > 0:
            perguntas.append(f"Por que os itens {', '.join(map(str, itens_suspeitos[:3]))} são suspeitos?")
        
        nivel_risco = getattr(resultado, 'nivel_risco', NivelRisco.BAIXO)
        if nivel_risco in [NivelRisco.ALTO, NivelRisco.CRITICO]:
            perguntas.append("Devo bloquear esta NF-e?")
            perguntas.append("Quais são os próximos passos urgentes?")
        
        # Perguntas gerais sempre disponíveis
        perguntas.extend([
            "Explique o score de risco",
            "Como foi feita a classificação NCM?",
            "Posso aprovar esta NF-e?",
        ])
        
        return perguntas[:6]  # Máximo 6 sugestões
    
    def _gerar_cache_key(self, mensagem: str) -> str:
        """Gera chave única para cache baseada na mensagem e contexto"""
        # Incluir contexto do relatório na chave
        contexto = ""
        if self.relatorio:
            resultado = self.relatorio
            contexto = f"{getattr(resultado, 'chave_acesso', '')}_{getattr(resultado, 'score_risco_geral', 0)}"
        
        # Criar hash da mensagem + contexto
        texto_completo = f"{mensagem.lower().strip()}_{contexto}"
        return hashlib.md5(texto_completo.encode()).hexdigest()
    
    def _verificar_cache(self, cache_key: str) -> Optional[str]:
        """Verifica se existe resposta em cache válida"""
        if cache_key not in self.cache_respostas:
            return None
        
        cache_entry = self.cache_respostas[cache_key]
        
        # Verificar se não expirou
        if time.time() - cache_entry['timestamp'] > self.cache_ttl:
            del self.cache_respostas[cache_key]
            return None
        
        return cache_entry['resposta']
    
    def _adicionar_ao_cache(self, cache_key: str, resposta: str, response_time: float):
        """Adiciona resposta ao cache"""
        # Limpar cache se estiver muito grande
        if len(self.cache_respostas) >= self.cache_max_size:
            # Remover entrada mais antiga
            oldest_key = min(self.cache_respostas.keys(), 
                           key=lambda k: self.cache_respostas[k]['timestamp'])
            del self.cache_respostas[oldest_key]
        
        # Adicionar nova entrada
        self.cache_respostas[cache_key] = {
            'resposta': resposta,
            'timestamp': time.time(),
            'response_time': response_time
        }
    
    def obter_estatisticas_cache(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache para monitoramento"""
        if not self.cache_respostas:
            return {
                'total_entradas': 0,
                'hit_rate': 0.0,
                'tempo_medio_resposta': 0.0
            }
        
        total_entradas = len(self.cache_respostas)
        tempos_resposta = [entry['response_time'] for entry in self.cache_respostas.values()]
        tempo_medio = sum(tempos_resposta) / len(tempos_resposta) if tempos_resposta else 0.0
        
        return {
            'total_entradas': total_entradas,
            'tempo_medio_resposta': round(tempo_medio, 3),
            'cache_ttl': self.cache_ttl,
            'cache_max_size': self.cache_max_size
        }
    
    def limpar_cache(self):
        """Limpa todo o cache"""
        self.cache_respostas.clear()

