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
        
        # Primeiro, tentar responder com consultas específicas aos dados
        resposta_consulta = self._processar_consulta_dados(mensagem_usuario)
        if resposta_consulta:
            self.historico_conversa.append({
                "role": "assistant",
                "content": resposta_consulta
            })
            return resposta_consulta
        
        # Criar prompt com dados reais
        prompt = self._criar_prompt_com_dados_reais(mensagem_usuario)
        
        # Evitar logs de debug visíveis ao usuário final
        # (mantido em silêncio para experiência limpa)
        
        try:
            # Verificar se o LLM está disponível
            if not self.llm:
                return "❌ Modelo de linguagem não disponível. Por favor, recarregue a página."
            
            # Invocar LLM
            start_time = time.time()
            response = self.llm.invoke(prompt)
            response_time = time.time() - start_time
            
            # Extrair resposta
            if hasattr(response, 'content'):
                resposta = response.content
            else:
                resposta = str(response)
            
            # Limpar resposta de possíveis prefixos indesejados
            resposta = self._limpar_resposta(resposta)
            
            # Adicionar resposta ao histórico
            self.historico_conversa.append({
                "role": "assistant",
                "content": resposta
            })
            
            return resposta
            
        except Exception as e:
            error_msg = str(e)
            # Se for erro de API key, sugerir usar modelo local
            if "api key" in error_msg.lower() or "401" in error_msg:
                return "❌ Erro de API key. O sistema está tentando usar o modelo local. Por favor, recarregue a página para reinicializar o chat."
            # Se for erro de contexto muito longo
            elif "contexto" in error_msg.lower() or "muito longo" in error_msg.lower() or "prompt" in error_msg.lower():
                return "❌ O contexto é muito longo para o modelo. Tente fazer uma pergunta mais específica ou use o botão 'Reinicializar' para limpar o histórico."
            return f"❌ Erro ao processar pergunta: {error_msg}"
    
    def _processar_consulta_dados(self, mensagem: str) -> Optional[str]:
        """
        Processa consultas específicas aos dados carregados
        Retorna resposta direta se for uma consulta específica, None caso contrário
        """
        mensagem_lower = mensagem.lower().strip()
        
        # Consultas sobre quantidade de NFs
        if any(palavra in mensagem_lower for palavra in ['quantas nf', 'quantas nota', 'quantas fiscal', 'total de nf', 'número de nf']):
            return self._consultar_quantidade_nfs()
        
        # Consultas sobre valores
        if any(palavra in mensagem_lower for palavra in ['valor', 'preço', 'total', 'reais', 'r$']):
            return self._consultar_valores(mensagem_lower)
        
        # Consultas sobre itens
        if any(palavra in mensagem_lower for palavra in ['itens', 'produtos', 'mercadorias', 'quantidade de itens']):
            return self._consultar_itens()
        
        # Consultas sobre fraudes
        if any(palavra in mensagem_lower for palavra in ['fraude', 'fraudes', 'risco', 'problema', 'irregularidade']):
            return self._consultar_fraudes()
        
        # Consultas sobre datas
        if any(palavra in mensagem_lower for palavra in ['data', 'período', 'ano', 'mês', 'quando']):
            return self._consultar_datas()
        
        # Consultas sobre CNPJ/CPF
        if any(palavra in mensagem_lower for palavra in ['cnpj', 'cpf', 'documento', 'emitente', 'destinatário']):
            return self._consultar_documentos()
        
        # Consultas sobre NCM
        if any(palavra in mensagem_lower for palavra in ['ncm', 'código', 'classificação']):
            return self._consultar_ncm()
        
        return None
    
    def _consultar_quantidade_nfs(self) -> str:
        """Consulta quantidade de NFs carregadas"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        relatorio = st.session_state.get('relatorio')
        
        # Sem saída de debug para usuários finais
        
        if multiple_nfes:
            return f"📊 **Total de NFs analisadas: {len(multiple_nfes)}**\n\nDetalhes:\n- NFs carregadas: {len(multiple_nfes)}\n- Análise individual de cada NF realizada"
        elif nfe_data:
            return "📊 **Total de NFs analisadas: 1**\n\nDetalhes:\n- 1 NF carregada e analisada"
        elif relatorio and hasattr(relatorio, 'resultado_analise'):
            resultado = relatorio.resultado_analise
            # Quando só temos o relatório consolidado, o número de notas pode estar em
            # resultado.total_notas OU em resultado.resultado_analise['total_notas']
            if isinstance(resultado, dict):
                total_notas = resultado.get('total_notas')
            else:
                total_notas = getattr(resultado, 'total_notas', None)
                if total_notas is None and hasattr(resultado, 'resultado_analise'):
                    inner = getattr(resultado, 'resultado_analise')
                    if isinstance(inner, dict):
                        total_notas = inner.get('total_notas')
            if total_notas:
                try:
                    total = int(total_notas)
                    if total > 1:
                        return f"📊 **Total de NFs analisadas: {total}**\n\nDetalhes:\n- Resultado consolidado carregado\n- Dados agregados disponíveis"
                except Exception:
                    pass
        else:
            return "❌ Nenhuma NF encontrada nos dados carregados."
    
    def _consultar_valores(self, mensagem: str) -> str:
        """Consulta valores das NFs"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        relatorio = st.session_state.get('relatorio')
        
        if multiple_nfes:
            valores = [nfe.valor_total for nfe in multiple_nfes]
            valor_total = sum(valores)
            valor_medio = valor_total / len(valores)
            valor_min = min(valores)
            valor_max = max(valores)
            
            # Verificar se há filtro de faixa de valores
            if 'entre' in mensagem and ('reais' in mensagem or 'r$' in mensagem):
                # Extrair valores da mensagem (exemplo: "entre 500 e 1000")
                import re
                numeros = re.findall(r'\d+', mensagem)
                if len(numeros) >= 2:
                    min_valor = float(numeros[0])
                    max_valor = float(numeros[1])
                    nfs_filtradas = [nfe for nfe in multiple_nfes if min_valor <= nfe.valor_total <= max_valor]
                    
                    return f"💰 **NFs entre R$ {min_valor:,.2f} e R$ {max_valor:,.2f}:**\n\n- Quantidade: {len(nfs_filtradas)} NFs\n- Percentual: {(len(nfs_filtradas)/len(multiple_nfes)*100):.1f}% do total"
            
            return f"💰 **Análise de Valores:**\n\n- Valor total: R$ {valor_total:,.2f}\n- Valor médio: R$ {valor_medio:,.2f}\n- Menor valor: R$ {valor_min:,.2f}\n- Maior valor: R$ {valor_max:,.2f}\n- Total de NFs: {len(multiple_nfes)}"
        
        elif nfe_data:
            return f"💰 **Valor da NF:**\n\n- Valor total: R$ {nfe_data.valor_total:,.2f}"
        elif relatorio and hasattr(relatorio, 'resultado_analise'):
            resultado = relatorio.resultado_analise
            inner = getattr(resultado, 'resultado_analise', None) if not isinstance(resultado, dict) else resultado
            if isinstance(inner, dict) and 'total_valor' in inner:
                return f"💰 **Valor Total (Consolidado):**\n\n- Valor somado das NFs: R$ {inner['total_valor']:,.2f}"
        
        return "❌ Nenhuma NF encontrada para análise de valores."
    
    def _consultar_itens(self) -> str:
        """Consulta informações sobre itens"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        
        if multiple_nfes:
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            itens_por_nf = [len(nfe.itens) for nfe in multiple_nfes]
            media_itens = total_itens / len(multiple_nfes)
            
            return f"📦 **Análise de Itens:**\n\n- Total de itens: {total_itens}\n- Média de itens por NF: {media_itens:.1f}\n- Menor quantidade: {min(itens_por_nf)}\n- Maior quantidade: {max(itens_por_nf)}\n- Total de NFs: {len(multiple_nfes)}"
        
        elif nfe_data:
            return f"📦 **Itens da NF:**\n\n- Total de itens: {len(nfe_data.itens)}"
        
        return "❌ Nenhuma NF encontrada para análise de itens."
    
    def _consultar_fraudes(self) -> str:
        """Consulta informações sobre fraudes detectadas"""
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        relatorio = st.session_state.get('relatorio')
        
        if multiple_resultados:
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            nfs_com_fraude = sum(1 for resultado in multiple_resultados if resultado.fraudes_detectadas)
            
            if total_fraudes > 0:
                fraudes_detalhadas = []
                for i, resultado in enumerate(multiple_resultados):
                    if resultado.fraudes_detectadas:
                        for fraude in resultado.fraudes_detectadas:
                            fraudes_detalhadas.append(f"NF {i+1}: {fraude.tipo_fraude} - {fraude.descricao}")
                
                return f"🚨 **Fraudes Detectadas:**\n\n- Total de fraudes: {total_fraudes}\n- NFs com fraude: {nfs_com_fraude}\n- Percentual: {(nfs_com_fraude/len(multiple_resultados)*100):.1f}%\n\n**Detalhes:**\n" + "\n".join(fraudes_detalhadas[:10])  # Limitar a 10 fraudes
            else:
                return "✅ **Nenhuma fraude detectada**\n\nTodas as NFs analisadas estão em conformidade."
        
        elif relatorio and hasattr(relatorio, 'resultado_analise'):
            resultado = relatorio.resultado_analise
            if resultado.fraudes_detectadas:
                fraudes_detalhadas = [f"- {fraude.tipo_fraude}: {fraude.descricao}" for fraude in resultado.fraudes_detectadas]
                return f"🚨 **Fraudes Detectadas:**\n\n- Total: {len(resultado.fraudes_detectadas)}\n\n**Detalhes:**\n" + "\n".join(fraudes_detalhadas)
            else:
                return "✅ **Nenhuma fraude detectada**\n\nA NF analisada está em conformidade."
        
        return "❌ Nenhuma análise de fraude disponível."
    
    def _consultar_datas(self) -> str:
        """Consulta informações sobre datas"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        
        if multiple_nfes:
            datas = []
            for nfe in multiple_nfes:
                if hasattr(nfe, 'data_emissao'):
                    datas.append(nfe.data_emissao)
            
            if datas:
                from datetime import datetime
                datas_ordenadas = sorted(datas)
                data_mais_antiga = datas_ordenadas[0]
                data_mais_recente = datas_ordenadas[-1]
                
                return f"📅 **Período das NFs:**\n\n- Data mais antiga: {data_mais_antiga}\n- Data mais recente: {data_mais_recente}\n- Total de NFs: {len(multiple_nfes)}"
        
        elif nfe_data and hasattr(nfe_data, 'data_emissao'):
            return f"📅 **Data da NF:**\n\n- Data de emissão: {nfe_data.data_emissao}"
        
        return "❌ Informações de data não disponíveis."
    
    def _consultar_documentos(self) -> str:
        """Consulta informações sobre CNPJ/CPF"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        
        if multiple_nfes:
            cnpjs_emitentes = set()
            cnpjs_destinatarios = set()
            
            for nfe in multiple_nfes:
                if hasattr(nfe, 'cnpj_emitente'):
                    cnpjs_emitentes.add(nfe.cnpj_emitente)
                if hasattr(nfe, 'cnpj_destinatario'):
                    cnpjs_destinatarios.add(nfe.cnpj_destinatario)
            
            return f"📄 **Documentos Encontrados:**\n\n- CNPJs únicos (emitentes): {len(cnpjs_emitentes)}\n- CNPJs únicos (destinatários): {len(cnpjs_destinatarios)}\n- Total de NFs: {len(multiple_nfes)}"
        
        elif nfe_data:
            info = []
            if hasattr(nfe_data, 'cnpj_emitente'):
                info.append(f"- CNPJ Emitente: {nfe_data.cnpj_emitente}")
            if hasattr(nfe_data, 'cnpj_destinatario'):
                info.append(f"- CNPJ Destinatário: {nfe_data.cnpj_destinatario}")
            
            if info:
                return f"📄 **Documentos da NF:**\n\n" + "\n".join(info)
        
        return "❌ Informações de documentos não disponíveis."
    
    def _consultar_ncm(self) -> str:
        """Consulta informações sobre códigos NCM"""
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        nfe_data = st.session_state.get('nfe_data')
        
        if multiple_nfes:
            ncms = set()
            for nfe in multiple_nfes:
                for item in nfe.itens:
                    if hasattr(item, 'ncm'):
                        ncms.add(item.ncm)
            
            return f"🏷️ **Códigos NCM:**\n\n- NCMs únicos: {len(ncms)}\n- Total de itens: {sum(len(nfe.itens) for nfe in multiple_nfes)}\n- Total de NFs: {len(multiple_nfes)}"
        
        elif nfe_data:
            ncms = set()
            for item in nfe_data.itens:
                if hasattr(item, 'ncm'):
                    ncms.add(item.ncm)
            
            return f"🏷️ **Códigos NCM da NF:**\n\n- NCMs únicos: {len(ncms)}\n- Total de itens: {len(nfe_data.itens)}"
        
        return "❌ Informações de NCM não disponíveis."

    def _limpar_resposta(self, resposta: str) -> str:
        """Limpa a resposta de prefixos indesejados"""
        if not resposta:
            return resposta
        
        # Remover prefixos comuns
        prefixes_to_remove = [
            "ASSISTENTE:",
            "ASSISTANT:",
            "RESPOSTA:",
            "RESPONSE:",
            "ANSWER:",
            "Você é um assistente fiscal especializado.",
        ]
        
        resposta_limpa = resposta.strip()
        for prefix in prefixes_to_remove:
            if resposta_limpa.startswith(prefix):
                resposta_limpa = resposta_limpa[len(prefix):].strip()
        
        return resposta_limpa
    
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
        
        # Coletar dados reais com truncamento inteligente
        dados_info = self._coletar_dados_reais_otimizado()
        
        # Incluir referência do arquivo, se disponível
        xml_path = st.session_state.get('uploaded_xml_path')
        origem_arquivo = f"\nARQUIVO: {xml_path}\n" if xml_path else "\n"
        
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
{origem_arquivo}

PERGUNTA: {mensagem_usuario}

HISTÓRICO RECENTE:
{historico_str}

INSTRUÇÕES:
1. Responda APENAS com base nos dados fornecidos acima
2. Seja direto e objetivo (máximo 3 parágrafos)
3. Use dados específicos dos arquivos quando disponível
4. Se a pergunta mencionar NFs específicas, responda considerando TODAS as NFs do arquivo quando disponíveis; se só houver relatório consolidado, explique claramente qualquer limitação.
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
            # Se o relatório for consolidado, campos podem estar em um dict interno
            inner = None
            if not isinstance(resultado, dict) and hasattr(resultado, 'resultado_analise'):
                inner = getattr(resultado, 'resultado_analise')
            base = inner if isinstance(inner, dict) else (resultado if isinstance(resultado, dict) else {})
            total_notas = base.get('total_notas')
            if total_notas and total_notas > 1:
                total_valor = base.get('total_valor', 0)
                total_itens = base.get('total_itens', 0)
                total_fraudes = base.get('total_fraudes', 0)
                dados.append(f"""
MÚLTIPLAS NOTAS FISCAIS (Consolidado):
- Total de NFs: {int(total_notas)}
- Valor Total: R$ {total_valor:,.2f}
- Itens: {int(total_itens)}
- Fraudes: {int(total_fraudes)}
""")
            else:
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
    
    def _coletar_dados_reais_otimizado(self) -> str:
        """Coleta dados reais com truncamento inteligente para evitar prompts muito longos"""
        
        # Limite de caracteres para o contexto (ajustado para modelo local)
        MAX_CONTEXT_CHARS = 2000  # Reduzido para modelo local
        
        # Coletar dados básicos primeiro
        dados_basicos = self._coletar_dados_basicos()
        
        # Se os dados básicos já são suficientes, usar apenas eles
        if len(dados_basicos) <= MAX_CONTEXT_CHARS:
            return dados_basicos
        
        # Se muito longo, truncar inteligentemente
        return self._truncar_dados_inteligentemente(dados_basicos, MAX_CONTEXT_CHARS)
    
    def _coletar_dados_basicos(self) -> str:
        """Coleta apenas dados essenciais para o contexto"""
        dados = []
        
        # Verificar múltiplas NFs
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        if multiple_nfes and multiple_resultados:
            # Calcular estatísticas básicas
            total_valor = sum(nfe.valor_total for nfe in multiple_nfes)
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            scores = [r.score_risco_geral for r in multiple_resultados if hasattr(r, 'score_risco_geral')]
            score_medio = sum(scores) / len(scores) if scores else 0
            total_fraudes = sum(len(r.fraudes_detectadas) for r in multiple_resultados if hasattr(r, 'fraudes_detectadas'))
            
            dados.append(f"""MÚLTIPLAS NOTAS FISCAIS:
- Total: {len(multiple_nfes)} NFs
- Valor Total: R$ {total_valor:,.2f}
- Itens: {total_itens}
- Risco Médio: {score_medio:.1f}/100
- Fraudes: {total_fraudes}""")
            
            # Adicionar apenas as primeiras 3 NFs como exemplo
            for i, (nfe, resultado) in enumerate(zip(multiple_nfes[:3], multiple_resultados[:3]), 1):
                serie = getattr(nfe, 'serie', '1')
                score = getattr(resultado, 'score_risco_geral', 0)
                fraudes = len(getattr(resultado, 'fraudes_detectadas', []))
                dados.append(f"NF {i}: {nfe.numero}/{serie} - R$ {nfe.valor_total:,.2f} - Risco: {score}/100 - Fraudes: {fraudes}")
            
            if len(multiple_nfes) > 3:
                dados.append(f"... e mais {len(multiple_nfes) - 3} NFs")
        
        # Verificar NF única
        nfe_data = st.session_state.get('nfe_data')
        if nfe_data and not multiple_nfes:
            dados.append(f"""NOTA FISCAL ÚNICA:
- Número: {nfe_data.numero}/{getattr(nfe_data, 'serie', '1')}
- Valor: R$ {nfe_data.valor_total:,.2f}
- Itens: {len(nfe_data.itens)}""")
        
        # Verificar dados CSV
        csv_data = st.session_state.get('csv_data')
        if csv_data is not None:
            dados.append(f"""DADOS CSV:
- Linhas: {len(csv_data)}
- Colunas: {', '.join(csv_data.columns.tolist()[:5])}{'...' if len(csv_data.columns) > 5 else ''}""")
        
        # Verificar relatório consolidado
        relatorio = st.session_state.get('relatorio')
        if relatorio and not multiple_nfes:
            resultado = relatorio.resultado_analise if hasattr(relatorio, 'resultado_analise') else relatorio
            score = getattr(resultado, 'score_risco_geral', 0)
            nivel = getattr(resultado, 'nivel_risco', NivelRisco.BAIXO).value.upper()
            fraudes = len(getattr(resultado, 'fraudes_detectadas', []))
            dados.append(f"""RELATÓRIO:
- Risco: {score}/100 ({nivel})
- Fraudes: {fraudes}""")
        
        return "\n".join(dados) if dados else "Nenhum dado disponível"
    
    def _truncar_dados_inteligentemente(self, dados: str, max_chars: int) -> str:
        """Trunca dados de forma inteligente mantendo informações essenciais"""
        if len(dados) <= max_chars:
            return dados
        
        # Dividir em seções
        secoes = dados.split('\n\n')
        resultado = []
        chars_usados = 0
        
        for secao in secoes:
            if chars_usados + len(secao) + 2 <= max_chars:
                resultado.append(secao)
                chars_usados += len(secao) + 2
            else:
                # Adicionar resumo da seção restante
                if "MÚLTIPLAS NOTAS" in secao:
                    resultado.append("... (dados adicionais truncados para economizar contexto)")
                break
        
        return '\n\n'.join(resultado)
    
    def _truncar_prompt_se_necessario(self, prompt: str) -> str:
        """Trunca o prompt se for muito longo para o modelo"""
        # Limite conservador para modelo local (aproximadamente 2000 tokens)
        MAX_PROMPT_CHARS = 4000
        
        if len(prompt) <= MAX_PROMPT_CHARS:
            return prompt
        
        # Dividir o prompt em seções
        linhas = prompt.split('\n')
        
        # Manter sempre: instruções, pergunta, histórico
        secoes_essenciais = []
        secoes_dados = []
        
        em_dados = False
        for linha in linhas:
            if linha.startswith('DADOS:'):
                em_dados = True
                secoes_dados.append(linha)
            elif linha.startswith('PERGUNTA:'):
                em_dados = False
                secoes_essenciais.append(linha)
            elif em_dados:
                secoes_dados.append(linha)
            else:
                secoes_essenciais.append(linha)
        
        # Construir prompt truncado
        prompt_truncado = '\n'.join(secoes_essenciais)
        
        # Adicionar dados truncados se houver espaço
        if secoes_dados:
            dados_truncados = '\n'.join(secoes_dados)
            if len(prompt_truncado) + len(dados_truncados) <= MAX_PROMPT_CHARS:
                # Inserir dados antes da pergunta
                linhas_finais = prompt_truncado.split('\n')
                pergunta_idx = next(i for i, linha in enumerate(linhas_finais) if linha.startswith('PERGUNTA:'))
                linhas_finais.insert(pergunta_idx, dados_truncados)
                prompt_truncado = '\n'.join(linhas_finais)
            else:
                # Adicionar apenas resumo dos dados
                prompt_truncado = prompt_truncado.replace('DADOS:', 'DADOS: (dados truncados - contexto muito longo)')
        
        return prompt_truncado
    
    def _gerar_mensagem_inicial(self) -> str:
        """Gera mensagem inicial baseada nos dados disponíveis"""
        dados_disponiveis = self._verificar_dados_disponiveis()
        
        if not dados_disponiveis:
            return """👋 **Olá! Sou seu assistente fiscal inteligente.**

Carregue um arquivo XML ou CSV para começar a análise e consultas.

**Exemplos de perguntas que posso responder:**
• Quantas NFs foram analisadas?
• Qual o valor total das NFs?
• Quantas NFs estão entre R$ 500 e R$ 1000?
• Quais fraudes foram detectadas?
• Quantos itens tem cada NF?
• Quais CNPJs estão nas NFs?
• Qual o período das NFs?"""
        
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

**Agora posso responder suas consultas sobre os dados:**
• Quantas NFs foram analisadas?
• Qual o valor total das NFs?
• Quantas NFs estão entre R$ 500 e R$ 1000?
• Quais fraudes foram detectadas?
• Quantos itens tem cada NF?
• Quais CNPJs estão nas NFs?
• Qual o período das NFs?

**Faça sua pergunta!** 💬

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
