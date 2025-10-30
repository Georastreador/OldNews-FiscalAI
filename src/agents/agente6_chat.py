"""
Agente6Chat - Agente exclusivo do Chat
Intermedia perguntas do usuário com os dados carregados (NFs/CSV/Consolidado) e a LLM.
"""

from typing import List, Dict, Optional
import time
from datetime import datetime
import streamlit as st

from src.models.schemas import NivelRisco


class Agente6Chat:
    """Agente de conversa: pergunta → contexto de arquivo → LLM → resposta."""

    def __init__(self, llm):
        self.llm = llm
        self.historico: List[Dict[str, str]] = []
        self._add_system_greeting()

    def _add_system_greeting(self):
        self.historico.append({
            "role": "assistant",
            "content": "🎉 Análise pronta. Pergunte qualquer coisa sobre as NFs carregadas (valores, datas, CNPJs, NCM, fraudes, totais, etc.)."
        })

    def conversar(self, mensagem_usuario: str) -> str:
        if not mensagem_usuario or not mensagem_usuario.strip():
            return "❌ Pergunta vazia."

        if not self._tem_dados():
            return "❌ Nenhum arquivo carregado. Faça o upload e processe antes de perguntar."

        self.historico.append({"role": "user", "content": mensagem_usuario})

        # Contexto sempre disponível para a LLM
        prompt = self._montar_prompt(mensagem_usuario)

        try:
            inicio = time.time()
            resp = self.llm.invoke(prompt) if self.llm else None
            dur = time.time() - inicio

            conteudo = getattr(resp, "content", None) if resp is not None else None
            resposta = conteudo if conteudo else "❌ Modelo indisponível no momento."
            resposta = self._limpar_resposta(resposta)
            self.historico.append({"role": "assistant", "content": resposta})
            return resposta
        except Exception as e:
            return f"❌ Erro ao consultar o modelo: {str(e)}"

    def limpar_historico(self):
        self.historico = []
        self._add_system_greeting()

    def exportar_conversa(self) -> str:
        linhas = []
        for m in self.historico:
            linhas.append(f"{m['role'].upper()}: {m['content']}")
        return "\n\n".join(linhas)

    # Compat: usado pelo UI atual no expander de informações
    def _coletar_dados_reais(self) -> str:
        return self._coletar_contexto_compacto()

    def _tem_dados(self) -> bool:
        return any([
            bool(st.session_state.get('multiple_nfes')),
            bool(st.session_state.get('nfe_data')),
            bool(st.session_state.get('relatorio')),
            st.session_state.get('csv_data') is not None,
        ])

    def _montar_prompt(self, pergunta: str) -> str:
        contexto = self._coletar_contexto_compacto()
        xml_path = st.session_state.get('uploaded_xml_path')
        origem = f"\nARQUIVO: {xml_path}\n" if xml_path else "\n"

        historico_recente = self.historico[-2:]
        hist = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in historico_recente])

        return (
            "Você é um assistente fiscal. Responda APENAS com base no contexto abaixo.\n\n"
            "CONTEXTO (resumido e confiável):\n" + contexto + origem + "\n"
            f"PERGUNTA: {pergunta}\n\n"
            "HISTÓRICO RECENTE:\n" + hist + "\n\n"
            "INSTRUÇÕES:\n"
            "1. Seja objetivo (até 3 parágrafos).\n"
            "2. Use números e entidades do contexto.\n"
            "3. Se o detalhe solicitado não estiver no contexto, explique a limitação e diga o que falta.\n"
            "4. Termine com ponto final.\n\n"
            "RESPOSTA:"
        )

    def _coletar_contexto_compacto(self) -> str:
        partes: List[str] = []

        # Tentar obter consolidado primeiro (pode existir mesmo sem listas materializadas)
        consolidado = self._get_consolidado_dict()
        total_notas_consol = consolidado.get('total_notas') if isinstance(consolidado, dict) else None

        # Detecção rápida no XML (antes de montar blocos) para já informar o total
        detected_total = self._detectar_quantidade_por_xml()
        if isinstance(detected_total, int) and detected_total > 1:
            partes.append(f"TOTAL_NFS_DETECTADO: {detected_total}")

        # Múltiplas NFs
        nfs = st.session_state.get('multiple_nfes', [])
        resultados = st.session_state.get('multiple_resultados', [])
        if nfs and resultados:
            total_valor = sum(getattr(n, 'valor_total', 0) for n in nfs)
            total_itens = sum(len(getattr(n, 'itens', [])) for n in nfs)
            fraudes = sum(len(getattr(r, 'fraudes_detectadas', [])) for r in resultados)
            partes.append(
                f"MÚLTIPLAS NFS:\n- Total: {len(nfs)}\n- Valor Total: R$ {total_valor:,.2f}\n- Itens: {total_itens}\n- Fraudes: {fraudes}"
            )
            # Até 5 NFs para amostra
            for i, (n, r) in enumerate(list(zip(nfs, resultados))[:5], start=1):
                serie = getattr(n, 'serie', '1')
                score = getattr(r, 'score_risco_geral', 0)
                partes.append(
                    f"NF {i}: {getattr(n, 'numero', '—')}/{serie} - R$ {getattr(n, 'valor_total', 0):,.2f} - Risco: {score}/100"
                )

        # NF única (somente se não houver múltiplas detectadas por consolidado OU por detecção no XML)
        nfe = st.session_state.get('nfe_data')
        if nfe and not nfs and not (
            (isinstance(total_notas_consol, int) and total_notas_consol > 1) or
            (isinstance(detected_total, int) and detected_total > 1)
        ):
            partes.append(
                "NF ÚNICA:\n"
                f"- Número: {getattr(nfe, 'numero', '—')}/{getattr(nfe, 'serie', '1')}\n"
                f"- Valor: R$ {getattr(nfe, 'valor_total', 0):,.2f}\n"
                f"- Data: {getattr(nfe, 'data_emissao', '—')}\n"
                f"- Emitente: {getattr(nfe, 'razao_social_emitente', getattr(nfe, 'cnpj_emitente', '—'))}\n"
                f"- Destinatário: {getattr(nfe, 'razao_social_destinatario', getattr(nfe, 'cnpj_destinatario', '—'))}\n"
                f"- Itens: {len(getattr(nfe, 'itens', []))}"
            )

        # Consolidado
        if consolidado and not nfs:
            total_notas = consolidado.get('total_notas')
            total_valor = consolidado.get('total_valor')
            total_itens = consolidado.get('total_itens')
            total_fraudes = consolidado.get('total_fraudes')
            partes.append(
                "CONSOLIDADO:\n"
                f"- Total de NFs: {total_notas}\n- Valor Total: R$ {total_valor:,.2f}\n"
                f"- Itens: {total_itens}\n- Fraudes: {total_fraudes}"
            )
            # Amostra de até 5 NFs a partir dos grupos do consolidado (se disponível)
            grupos = consolidado.get('grupos_cnpj') or {}
            amostra = []
            for cnpj, dados in grupos.items():
                nfes_grupo = dados.get('nfes') or []
                for nfe_obj in nfes_grupo:
                    if hasattr(nfe_obj, 'numero'):
                        amostra.append(nfe_obj)
                    if len(amostra) >= 5:
                        break
                if len(amostra) >= 5:
                    break
            if amostra:
                partes.append("AMOSTRA (até 5 NFs):")
                for i, n in enumerate(amostra, start=1):
                    data_str = getattr(n, 'data_emissao', '')
                    try:
                        # suportar datetime
                        if hasattr(data_str, 'strftime'):
                            data_str = data_str.strftime('%Y-%m-%d')
                    except Exception:
                        pass
                    partes.append(
                        f"- NF {i}: {getattr(n, 'numero', '—')}/{getattr(n, 'serie', '1')} | R$ {getattr(n, 'valor_total', 0):,.2f} | Data: {data_str}"
                    )

        # CSV
        df = st.session_state.get('csv_data')
        if df is not None:
            cols = ", ".join(df.columns.tolist()[:6])
            partes.append(
                f"CSV:\n- Linhas: {len(df)}\n- Colunas: {cols}{'...' if len(df.columns) > 6 else ''}"
            )

        # Fallback extremo: se ainda não há múltiplas nem consolidado, anexar detecção simples
        if not partes or ("MÚLTIPLAS NFS:" not in "\n".join(partes) and "CONSOLIDADO:" not in "\n".join(partes)):
            if isinstance(detected_total, int):
                partes.append(f"DETECÇÃO RÁPIDA (XML):\n- Possível total de NFs: {detected_total}")

        return "\n".join(partes) if partes else "Sem dados no contexto."

    def _get_consolidado_dict(self) -> Dict:
        """Tenta extrair o dicionário consolidado de múltiplas NFs do session_state.
        Procura em: relatorio.resultado_analise.resultado_analise (dict) e variações.
        """
        rel = st.session_state.get('relatorio')
        if not rel:
            return {}
        res = getattr(rel, 'resultado_analise', rel)
        # Nível 1: se já for dict
        if isinstance(res, dict) and 'total_notas' in res:
            return res
        # Nível 2: atributo resultado_analise interno
        inner = getattr(res, 'resultado_analise', None)
        if isinstance(inner, dict) and 'total_notas' in inner:
            return inner
        # Nível 3: outro encapsulamento raro
        inner2 = getattr(inner, 'resultado_analise', None) if inner is not None else None
        if isinstance(inner2, dict) and 'total_notas' in inner2:
            return inner2
        return {}

    def _detectar_quantidade_por_xml(self) -> Optional[int]:
        """Conta rapidamente quantas NFs existem no arquivo XML carregado (sem processar tudo)."""
        try:
            xml_path = st.session_state.get('uploaded_xml_path')
            if not xml_path:
                return None
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                xml = f.read()
            import re
            # Padrões para NF-e e NFS-e
            nfe_matches = re.findall(r'<infNFe[\s\S]*?</infNFe>', xml, re.IGNORECASE)
            nfse_matches = re.findall(r'<CompNfse[\s\S]*?</CompNfse>', xml, re.IGNORECASE)
            total = len(nfe_matches) + len(nfse_matches)
            if total == 0:
                # fallback: conta <NFe> wrappers
                total = len(re.findall(r'<NFe[\s\S]*?</NFe>', xml, re.IGNORECASE))
            return total if total > 0 else None
        except Exception:
            return None

    def _limpar_resposta(self, texto: str) -> str:
        return texto.strip()


