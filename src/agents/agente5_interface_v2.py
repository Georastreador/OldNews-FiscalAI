"""
Agente5Interface V2 - Acesso direto aos dados dos arquivos
Versão melhorada que acessa diretamente os dados carregados
"""

import time
import json
from typing import List, Dict, Optional
from datetime import datetime
import streamlit as st

from src.models.schemas import NivelRisco, RelatorioFiscal


class Agente5InterfaceV2:
    """
    Interface conversacional V2 para análise fiscal
    Acessa diretamente os dados dos arquivos carregados
    """
    
    def __init__(self, llm):
        """
        Inicializa o agente conversacional
        
        Args:
            llm: Modelo de linguagem para processamento
        """
        self.llm = llm
        self.historico_conversa = []
        self.relatorio = None
        
        # Adicionar mensagem inicial
        mensagem_inicial = self._gerar_mensagem_inicial()
        self.historico_conversa.append({
            "role": "assistant",
            "content": mensagem_inicial
        })
    
    def conversar(self, mensagem_usuario: str) -> str:
        """
        Processa mensagem do usuário e retorna resposta baseada nos dados carregados
        
        Args:
            mensagem_usuario: Pergunta ou comando do usuário
        
        Returns:
            Resposta do assistente baseada nos dados reais
        """
        # Verificar se há dados disponíveis
        dados_disponiveis = self._verificar_dados_disponiveis()
        if not dados_disponiveis:
            return "❌ Nenhum arquivo foi carregado. Por favor, faça upload de um arquivo XML ou CSV primeiro."
        
        # Adicionar mensagem do usuário ao histórico
        self.historico_conversa.append({
            "role": "user",
            "content": mensagem_usuario
        })
        
        # Criar prompt com dados reais
        prompt = self._criar_prompt_com_dados_reais(mensagem_usuario)
        
        # Debug: mostrar o prompt criado
        print(f"DEBUG prompt criado: {prompt[:500]}...")
        
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
            
            # Adicionar resposta ao histórico
            self.historico_conversa.append({
                "role": "assistant",
                "content": resposta
            })
            
            return resposta
            
        except Exception as e:
            return f"❌ Erro ao processar pergunta: {str(e)}"
    
    def _verificar_dados_disponiveis(self) -> bool:
        """Verifica se há dados de arquivos carregados"""
        # Verificar múltiplas NFs
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        # Verificar NF única
        nfe_data = st.session_state.get('nfe_data')
        relatorio = st.session_state.get('relatorio')
        
        # Verificar dados CSV
        csv_data = st.session_state.get('csv_data')
        
        # Debug: mostrar o que está disponível
        print(f"DEBUG Agente5V2: multiple_nfes={len(multiple_nfes) if multiple_nfes else 0}")
        print(f"DEBUG Agente5V2: multiple_resultados={len(multiple_resultados) if multiple_resultados else 0}")
        print(f"DEBUG Agente5V2: nfe_data={nfe_data is not None}")
        print(f"DEBUG Agente5V2: relatorio={relatorio is not None}")
        print(f"DEBUG Agente5V2: csv_data={csv_data is not None}")
        
        return bool(multiple_nfes or nfe_data or relatorio or csv_data)
    
    def _criar_prompt_com_dados_reais(self, mensagem_usuario: str) -> str:
        """Cria prompt com dados reais dos arquivos carregados"""
        
        # Coletar dados reais
        dados_info = self._coletar_dados_reais()
        
        # Histórico recente (últimas 2 mensagens)
        historico_recente = self.historico_conversa[-2:]
        historico_str = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in historico_recente
        ])
        
        # Prompt otimizado
        prompt = f"""Você é um assistente fiscal especializado. Responda baseado nos dados reais fornecidos.

DADOS DOS ARQUIVOS CARREGADOS:
{dados_info}

PERGUNTA: {mensagem_usuario}

HISTÓRICO RECENTE:
{historico_str}

INSTRUÇÕES:
1. Responda APENAS com base nos dados fornecidos acima
2. Seja direto e objetivo (máximo 3 parágrafos)
3. Use dados específicos dos arquivos quando disponível
4. Se a pergunta for sobre quantidade de NFs ou valores totais e você só tiver relatório consolidado, explique que essas informações específicas não estão disponíveis no relatório consolidado
5. Use **negrito** para destacar informações importantes
6. Termine a resposta com um ponto final

RESPOSTA:"""
        
        return prompt
    
    def _coletar_dados_reais(self) -> str:
        """Coleta dados reais dos arquivos carregados"""
        dados = []
        
        # Verificar múltiplas NFs (PRIORIDADE MÁXIMA)
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        print(f"DEBUG _coletar_dados_reais: multiple_nfes={len(multiple_nfes) if multiple_nfes else 0}")
        print(f"DEBUG _coletar_dados_reais: multiple_resultados={len(multiple_resultados) if multiple_resultados else 0}")
        print(f"DEBUG _coletar_dados_reais: session_state keys={list(st.session_state.keys())}")
        
        # Verificar se há dados de múltiplas NFs
        if multiple_nfes and len(multiple_nfes) > 0:
            # Dados de múltiplas NFs
            total_valor = sum(nfe.valor_total for nfe in multiple_nfes)
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            score_medio = sum(resultado.score_risco_geral for resultado in multiple_resultados) / len(multiple_resultados)
            
            dados.append(f"""
MÚLTIPLAS NOTAS FISCAIS (NFS-e):
- Total de NFs: {len(multiple_nfes)}
- Valor Total: R$ {total_valor:,.2f}
- Total de Itens: {total_itens}
- Score Médio de Risco: {score_medio:.1f}/100
- Total de Fraudes Detectadas: {total_fraudes}

DETALHES POR NF:
""")
            
            # Adicionar detalhes das primeiras 10 NFs
            for i, (nfe, resultado) in enumerate(zip(multiple_nfes[:10], multiple_resultados[:10]), 1):
                serie = getattr(nfe, 'serie', '1')  # Usar série padrão se não existir
                dados.append(f"NF {i}: {nfe.numero}/{serie} - R$ {nfe.valor_total:,.2f} - Risco: {resultado.score_risco_geral}/100 - Fraudes: {len(resultado.fraudes_detectadas)}")
            
            if len(multiple_nfes) > 10:
                dados.append(f"... e mais {len(multiple_nfes) - 10} NFs")
        
        # Verificar NF única
        nfe_data = st.session_state.get('nfe_data')
        if nfe_data and not multiple_nfes:
            dados.append(f"""
NOTA FISCAL ÚNICA:
- Número: {nfe_data.numero}/{nfe_data.serie}
- Chave: {nfe_data.chave_acesso}
- Data: {nfe_data.data_emissao.strftime('%d/%m/%Y') if hasattr(nfe_data, 'data_emissao') else 'N/A'}
- Emitente: {getattr(nfe_data, 'razao_social_emitente', getattr(nfe_data, 'cnpj_emitente', 'N/A'))}
- Destinatário: {getattr(nfe_data, 'razao_social_destinatario', getattr(nfe_data, 'cnpj_destinatario', 'N/A'))}
- Valor Total: R$ {nfe_data.valor_total:,.2f}
- Número de Itens: {len(nfe_data.itens)}
""")
        
        # Verificar dados CSV
        csv_data = st.session_state.get('csv_data')
        if csv_data is not None:
            dados.append(f"""
DADOS CSV:
- Total de Linhas: {len(csv_data)}
- Colunas: {', '.join(csv_data.columns.tolist())}
- Primeiras 5 linhas:
{csv_data.head().to_string()}
""")
        
        # Verificar relatório consolidado (fallback)
        relatorio = st.session_state.get('relatorio')
        if relatorio and not multiple_nfes:
            resultado = relatorio.resultado_analise if hasattr(relatorio, 'resultado_analise') else relatorio
            dados.append(f"""
RELATÓRIO CONSOLIDADO:
- Score de Risco: {getattr(resultado, 'score_risco_geral', 0)}/100
- Nível de Risco: {getattr(resultado, 'nivel_risco', NivelRisco.BAIXO).value.upper()}
- Fraudes Detectadas: {len(getattr(resultado, 'fraudes_detectadas', []))}
- Itens Suspeitos: {len(getattr(resultado, 'itens_suspeitos', []))}
""")
        
        # Se não há dados específicos, mas há relatório, usar informações básicas
        if not dados and relatorio:
            resultado = relatorio.resultado_analise if hasattr(relatorio, 'resultado_analise') else relatorio
            dados.append(f"""
DADOS DISPONÍVEIS:
- Score de Risco: {getattr(resultado, 'score_risco_geral', 0)}/100
- Nível de Risco: {getattr(resultado, 'nivel_risco', NivelRisco.BAIXO).value.upper()}
- Fraudes Detectadas: {len(getattr(resultado, 'fraudes_detectadas', []))}
- Itens Suspeitos: {len(getattr(resultado, 'itens_suspeitos', []))}

NOTA: Este é um relatório consolidado. Para informações específicas sobre quantidade de NFs e valores totais, 
é necessário que os dados das múltiplas NFs estejam disponíveis no session_state.
""")
        
        return "\n".join(dados) if dados else "Nenhum dado disponível"
    
    def _gerar_mensagem_inicial(self) -> str:
        """Gera mensagem inicial baseada nos dados disponíveis"""
        dados_disponiveis = self._verificar_dados_disponiveis()
        
        if not dados_disponiveis:
            return "Olá! Sou seu assistente fiscal. Carregue um arquivo XML ou CSV para começar a análise."
        
        # Coletar resumo dos dados
        dados_info = self._coletar_dados_reais()
        
        # Extrair informações principais
        if "MÚLTIPLAS NOTAS FISCAIS" in dados_info:
            # Extrair número de NFs
            import re
            match = re.search(r'Total de NFs: (\d+)', dados_info)
            num_nfs = match.group(1) if match else "várias"
            
            return f"""🎉 **Análise Fiscal Concluída!**

**{num_nfs} Notas Fiscais** foram processadas com sucesso!

Posso ajudá-lo com informações sobre:
- Quantidade de NFs analisadas
- Valores totais e por NF
- Detecção de fraudes
- Classificação NCM
- Validações fiscais
- E muito mais!

**Como posso ajudá-lo hoje?**"""
        
        elif "NOTA FISCAL ÚNICA" in dados_info:
            return f"""🎉 **Análise Fiscal Concluída!**

**1 Nota Fiscal** foi processada com sucesso!

Posso ajudá-lo com informações sobre:
- Detalhes da NF
- Validações fiscais
- Detecção de fraudes
- Classificação NCM
- E muito mais!

**Como posso ajudá-lo hoje?**"""
        
        else:
            return f"""🎉 **Análise Concluída!**

Dados carregados e processados com sucesso!

Posso ajudá-lo com informações sobre:
- Detalhes dos arquivos
- Análises realizadas
- Resultados e insights
- E muito mais!

**Como posso ajudá-lo hoje?**"""
    
    def obter_historico(self) -> List[Dict[str, str]]:
        """Retorna histórico completo da conversa"""
        return self.historico_conversa.copy()
    
    def limpar_historico(self):
        """Limpa histórico de conversa"""
        self.historico_conversa = []
        mensagem_inicial = self._gerar_mensagem_inicial()
        self.historico_conversa.append({
            "role": "assistant",
            "content": mensagem_inicial
        })
    
    def exportar_conversa(self) -> str:
        """Exporta conversa para formato de texto"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        header = f"""# CONVERSA FISCALAI - {timestamp}
# Exportado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
# ================================================

"""
        
        conversa_texto = []
        for i, msg in enumerate(self.historico_conversa, 1):
            role = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
            conversa_texto.append(f"{i}. {role}: {msg['content']}")
        
        return header + "\n\n".join(conversa_texto)
    
    def sugerir_perguntas(self) -> List[str]:
        """Sugere perguntas relevantes baseadas nos dados carregados"""
        dados_disponiveis = self._verificar_dados_disponiveis()
        
        if not dados_disponiveis:
            return []
        
        # Verificar tipo de dados
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        csv_data = st.session_state.get('csv_data')
        
        if multiple_nfes:
            return [
                "Quantas NFs foram analisadas?",
                "Qual o valor total das NFs?",
                "Quantas fraudes foram detectadas?",
                "Qual o score de risco médio?",
                "Quais NFs têm maior risco?",
                "Quantos itens foram processados?",
                "Qual NF tem o maior valor?",
                "Há padrões suspeitos nas NFs?"
            ]
        elif csv_data is not None:
            return [
                "Quantas linhas foram processadas?",
                "Quais são as colunas disponíveis?",
                "Há dados faltantes no arquivo?",
                "Qual o resumo dos dados?",
                "Há inconsistências nos dados?"
            ]
        else:
            return [
                "Quais são os principais resultados?",
                "Há fraudes detectadas?",
                "Qual o nível de risco?",
                "Quais validações foram feitas?"
            ]
