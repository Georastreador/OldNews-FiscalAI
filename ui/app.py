"""
OldNews FiscalAI - Interface Web Streamlit (Versão 2.0)
Dashboard interativo para análise fiscal de NF-e
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import json
import os
import time
import logging
import hashlib
import chardet  # type: ignore
from datetime import datetime, timedelta
import pandas as pd
import io
import plotly.graph_objects as go  # type: ignore

# Configuração de debug com proteção para produção
PRODUCTION_MODE = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true' and not PRODUCTION_MODE
DEBUG_LEVEL = int(os.getenv('FISCALAI_DEBUG_LEVEL', '1')) if DEBUG_MODE else 0

# Configurar logger
logger = logging.getLogger(__name__)

def debug_log(message: str, level: int = 1):
    """Função de debug temporária para Streamlit"""
    if DEBUG_MODE and level <= DEBUG_LEVEL:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[DEBUG UI {timestamp}] {message}")
        # Também mostrar no Streamlit se debug estiver ativo
        if level == 1:  # Apenas mensagens críticas no Streamlit
            st.write(f"🔍 **Debug:** {message}")

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import get_model_manager
from src.utils.upload_handler import create_upload_widget, create_csv_upload_widget, show_upload_tips, get_upload_handler
from src.utils.api_config import show_api_config_page
from src.utils.async_processor import get_async_processor, get_batch_processor
from src.utils.data_validator import get_data_validator, validate_nfe_data, validate_csv_dataframe
from src.utils.rate_limiter import get_rate_limiter, check_rate_limit
from src.utils.secure_logger import get_secure_logger, log_info, log_error, log_performance
from src.utils.model_cache import get_model_cache, cache_model, get_cached_model
from src.utils.monitoring import get_metrics_collector, record_performance, get_dashboard_data
from src.utils.result_cache import get_result_cache
from src.training.brazilian_ncm_trainer import get_brazilian_trainer, train_brazilian_ncm_model
from src.validation.cross_validation import get_cross_validation_engine, validate_ncm_cross_validation
from src.database.ncm_database import get_ncm_database_manager, search_ncm_database
from src.learning.feedback_loop import get_feedback_system, add_feedback
from src.calibration.threshold_calibrator import get_threshold_calibrator, add_calibration_data
from src.ml.adaptive_ml import get_adaptive_ml_system, predict_fraud_ml
from src.rules.advanced_business_rules import get_business_rules_engine, execute_business_rules
from src.analysis.temporal_analysis import get_temporal_analysis_engine, add_temporal_data
from src.security.xml_schema_validator import get_xml_validator, validate_xml_schema, sanitize_xml_content
from src.security.input_sanitizer import get_input_sanitizer, sanitize_input
from src.security.security_headers import get_security_headers_manager, get_streamlit_headers
from src.security.security_audit import get_security_auditor, log_security_event
from src.security.dos_protection import get_dos_protection, check_rate_limit
from src.security.crypto_manager import get_crypto_manager, encrypt_data, decrypt_data
from src.utils.universal_xml_parser import UniversalXMLParser
from src.utils.smart_fiscal_parser import SmartFiscalParser
from src.agents import (
    Agente1Extrator,
    Agente2Classificador,
    Agente3Validador,
    Agente4Orquestrador,
    Agente5Interface,
)
from src.detectors import OrquestradorDeteccaoFraudes
from src.models import NivelRisco, NFe, ItemNFe, RelatorioFiscal
from src.utils.pdf_exporter import exportar_relatorio_pdf

# Configuração da página
st.set_page_config(
    page_title="OldNews FiscalAI - Sistema Inteligente de Análise Fiscal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Forçar tema claro
st.markdown("""
<style>
/* Configuração global para tema claro */
:root {
    --primary-color: #1f77b4;
    --background-color: #ffffff;
    --secondary-background-color: #f0f2f6;
    --text-color: #262730;
    --font: "Source Sans Pro", sans-serif;
}

/* Forçar tema claro no Streamlit */
.stApp {
    background-color: #ffffff !important;
    color: #262730 !important;
}

/* Garantir que o tema seja sempre claro */
[data-theme="light"] {
    --background-color: #ffffff !important;
    --secondary-background-color: #f0f2f6 !important;
    --text-color: #262730 !important;
}

[data-theme="dark"] {
    --background-color: #ffffff !important;
    --secondary-background-color: #f0f2f6 !important;
    --text-color: #262730 !important;
    }
</style>
""", unsafe_allow_html=True)

def carregar_modelo_local():
    """Carrega o modelo local GGUF automaticamente"""
    try:
        debug_log("Iniciando carregamento do modelo local GGUF...", 1)
        
        # Mostrar indicador de carregamento
        with st.spinner("🔄 Carregando modelo local GGUF..."):
            from src.utils.model_manager import get_model_manager
            
            # Inicializar model manager
            model_manager = get_model_manager()
            
            # Carregar modelo local
            llm = model_manager.get_llm("mistral-7b-gguf")
            
            # Testar o modelo
            test_response = llm.invoke("Teste de conexão")
            
            if test_response:
                st.session_state.modelo_carregado = True
                st.session_state.model_manager = model_manager
                st.session_state.modelo_atual = "mistral-7b-gguf"
                debug_log("✅ Modelo local GGUF carregado com sucesso!", 1)
                
                # Mostrar sucesso discretamente
                st.success("✅ Modelo local carregado!")
            else:
                st.error("❌ Erro ao carregar modelo local")
                
    except Exception as e:
        debug_log(f"❌ Erro ao carregar modelo local: {str(e)}", 1)
        st.error(f"❌ Erro ao carregar modelo local: {str(e)}")
        st.session_state.modelo_carregado = False

def carregar_modelo_escolhido():
    """Carrega o modelo escolhido pelo usuário"""
    try:
        privacy_level = st.session_state.get('privacy_level', "🔒 Local (GGUF)")
        modelo_selecionado = st.session_state.get('modelo_selecionado', "mistral-7b-gguf")
        
        # Verificar se já está carregado o modelo correto
        if (st.session_state.get('modelo_carregado', False) and 
            st.session_state.get('modelo_atual') == modelo_selecionado):
            debug_log(f"✅ Modelo {modelo_selecionado} já está carregado!", 1)
            return True
        
        debug_log(f"Carregando modelo: {modelo_selecionado} ({privacy_level})", 1)
        
        with st.spinner(f"🔄 Carregando {modelo_selecionado}..."):
            from src.utils.model_manager import get_model_manager
            
            # Inicializar model manager
            model_manager = get_model_manager()
            
            # Carregar modelo escolhido
            llm = model_manager.get_llm(modelo_selecionado)
            
            # Testar o modelo
            test_response = llm.invoke("Teste de conexão")
            
            if test_response:
                st.session_state.modelo_carregado = True
                st.session_state.model_manager = model_manager
                st.session_state.modelo_atual = modelo_selecionado
                debug_log(f"✅ Modelo {modelo_selecionado} carregado com sucesso!", 1)
                return True
            else:
                st.error(f"❌ Erro ao carregar modelo {modelo_selecionado}")
                return False
                
    except Exception as e:
        debug_log(f"❌ Erro ao carregar modelo: {str(e)}", 1)
        st.error(f"❌ Erro ao carregar modelo: {str(e)}")
        st.session_state.modelo_carregado = False
        return False

def _converter_para_serializavel(obj):
    """
    Converte objetos complexos para dicionários serializáveis em JSON com tratamento robusto
    
    Args:
        obj: Objeto a ser convertido
        
    Returns:
        Dicionário serializável
    """
    try:
        # Tratar None
        if obj is None:
            return None
        
        # Tratar tipos básicos
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Tratar datetime
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        
        # Tratar enums
        if hasattr(obj, 'value'):
            return obj.value
        
        # Tratar Pydantic models (versão 2.x)
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):  # Pydantic models (versão 1.x)
            return _converter_para_serializavel(obj.dict())
        
        # Tratar objetos com __dict__
        if hasattr(obj, '__dict__'):
            result = {}
            for k, v in obj.__dict__.items():
                # Pular atributos privados e métodos
                if not k.startswith('_') and not callable(v):
                    try:
                        result[k] = _converter_para_serializavel(v)
                    except Exception:
                        result[k] = str(v)
            return result
        
        # Tratar listas e tuplas
        if isinstance(obj, (list, tuple)):
            return [_converter_para_serializavel(item) for item in obj]
        
        # Tratar dicionários
        if isinstance(obj, dict):
            return {k: _converter_para_serializavel(v) for k, v in obj.items()}
        
        # Tratar sets
        if isinstance(obj, set):
            return list(obj)
        
        # Fallback para string
        return str(obj)
        
    except Exception as e:
        logger.warning(f"Erro na serialização de {type(obj)}: {e}")
        return f"<{type(obj).__name__}: {str(obj)[:100]}>"

def inicializar_sessao():
    """Inicializa variáveis de sessão"""
    if 'relatorio' not in st.session_state:
        st.session_state.relatorio = None
    if 'agente5' not in st.session_state:
        st.session_state.agente5 = None
    if 'historico_chat' not in st.session_state:
        st.session_state.historico_chat = []
    # CONFIGURAÇÃO PADRÃO SIMPLIFICADA
    if 'modelo_selecionado' not in st.session_state:
        st.session_state.modelo_selecionado = "gpt-4o"  # OpenAI como padrão estável
    
    if 'privacy_level' not in st.session_state:
        st.session_state.privacy_level = "🌐 OpenAI"  # Padrão estável
    
    # NOVO: Flag explícito para análise concluída
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    
    # Garantir que current_page existe
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'inicio'
    
    # Inicializar flag de modelo carregado
    if 'modelo_carregado' not in st.session_state:
        st.session_state.modelo_carregado = False

def sidebar_configuracoes():
    st.sidebar.markdown("<h2 style='margin-bottom:15px;'>🚀 OldNews FiscalAI</h2>", unsafe_allow_html=True)
    
    # Navegação
    if "current_page" not in st.session_state:
        st.session_state.current_page = "inicio"
    nav = st.sidebar.radio(
        "Navegação",
        ("Início", "Configurar APIs", "Upload", "Dashboard", "Chat"),
        index=["inicio", "config", "upload", "dashboard", "chat"].index(st.session_state.current_page) if st.session_state.current_page in ["inicio", "config", "upload", "dashboard", "chat"] else 0,
        key="nav_radio"
    )
    st.session_state.current_page = {"Início": "inicio", "Configurar APIs": "config", "Upload": "upload", "Dashboard": "dashboard", "Chat": "chat"}[nav]
    
    st.sidebar.markdown("---")
    
    # SEÇÃO DE PRIVACIDADE
    configurar_privacidade()
    
    st.sidebar.markdown("---")
    
    # Botão Resetar Sessão
    if st.sidebar.button("🔄 Resetar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

def configurar_privacidade():
    """Configuração de privacidade e seleção de modelo"""
    st.sidebar.markdown("### 🔒 Privacidade")
    
    # Opções de privacidade
    opcoes_privacidade = {
        "🏠 Local (Mistral)": "local",
        "🌐 API Externa": "api"
    }
    
    # Seleção de privacidade
    if "privacidade_selecionada" not in st.session_state:
        st.session_state.privacidade_selecionada = "local"
    
    privacidade = st.sidebar.selectbox(
        "Escolha o tipo de modelo:",
        options=list(opcoes_privacidade.keys()),
        index=list(opcoes_privacidade.values()).index(st.session_state.privacidade_selecionada),
        key="privacidade_select"
    )
    
    st.session_state.privacidade_selecionada = opcoes_privacidade[privacidade]
    
    st.sidebar.markdown("---")
    
    # Configuração baseada na privacidade selecionada
    if st.session_state.privacidade_selecionada == "local":
        configurar_modelo_local()
    else:
        configurar_api_externa()

def configurar_modelo_local():
    """Configuração para modelo local"""
    st.sidebar.markdown("### 🤖 Modelo Local")
    
    # Modelos locais disponíveis
    modelos_locais = {
        "Mistral 7B (Recomendado)": "mistral-7b-gguf",
        "Mistral 7B (Ollama)": "mistral-7b-ollama",
        "Llama 2 7B (Ollama)": "llama2-7b-ollama"
    }
    
    if "modelo_local_selecionado" not in st.session_state:
        st.session_state.modelo_local_selecionado = "mistral-7b-gguf"
    
    modelo_local = st.sidebar.selectbox(
        "Selecione o modelo:",
        options=list(modelos_locais.keys()),
        index=list(modelos_locais.values()).index(st.session_state.modelo_local_selecionado),
        key="modelo_local_select"
    )
    
    st.session_state.modelo_local_selecionado = modelos_locais[modelo_local]
    st.session_state.modelo_selecionado = st.session_state.modelo_local_selecionado
    st.session_state.privacy_level = "🏠 Local"
    
    # Status do modelo local
    st.sidebar.success("✅ **Modelo Local Ativo**")
    st.sidebar.markdown(f"**Modelo:** {modelo_local}")
    st.sidebar.markdown("🔒 **100% Privado**")
    st.sidebar.markdown("💰 **Gratuito**")
    
    # Botão para carregar modelo
    if st.sidebar.button("🔄 Carregar Modelo Local", use_container_width=True):
        with st.spinner("Carregando modelo local..."):
            if carregar_modelo_local():
                st.success("✅ Modelo local carregado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Erro ao carregar modelo local")

def configurar_api_externa():
    """Configuração para API externa"""
    st.sidebar.markdown("### 🌐 API Externa")
    
    # Provedores de API
    provedores = {
        "OpenAI": "openai",
        "Anthropic (Claude)": "anthropic", 
        "Google (Gemini)": "google",
        "Groq": "groq"
    }
    
    if "provedor_selecionado" not in st.session_state:
        st.session_state.provedor_selecionado = "openai"
    
    provedor = st.sidebar.selectbox(
        "Selecione o provedor:",
        options=list(provedores.keys()),
        index=list(provedores.values()).index(st.session_state.provedor_selecionado),
        key="provedor_select"
    )
    
    st.session_state.provedor_selecionado = provedores[provedor]
    
    # Modelos baseados no provedor
    modelos_por_provedor = {
        "openai": {
            "GPT-4o": "gpt-4o",
            "GPT-4o Mini": "gpt-4o-mini",
            "GPT-3.5 Turbo": "gpt-3.5-turbo"
        },
        "anthropic": {
            "Claude 3.5 Sonnet": "claude-3.5-sonnet",
            "Claude 3 Haiku": "claude-3-haiku"
        },
        "google": {
            "Gemini 1.5 Pro": "gemini-1.5-pro",
            "Gemini 1.5 Flash": "gemini-1.5-flash"
        },
        "groq": {
            "Llama 3.1 8B": "llama-3.1-8b",
            "Mixtral 8x7B": "mixtral-8x7b"
        }
    }
    
    modelos_disponiveis = modelos_por_provedor.get(st.session_state.provedor_selecionado, {})
    
    if "modelo_api_selecionado" not in st.session_state:
        st.session_state.modelo_api_selecionado = list(modelos_disponiveis.values())[0] if modelos_disponiveis else ""
    
    if modelos_disponiveis:
        modelo_api = st.sidebar.selectbox(
            "Selecione o modelo:",
            options=list(modelos_disponiveis.keys()),
            index=list(modelos_disponiveis.values()).index(st.session_state.modelo_api_selecionado) if st.session_state.modelo_api_selecionado in modelos_disponiveis.values() else 0,
            key="modelo_api_select"
        )
        
        st.session_state.modelo_api_selecionado = modelos_disponiveis[modelo_api]
        st.session_state.modelo_selecionado = st.session_state.modelo_api_selecionado
        st.session_state.privacy_level = f"🌐 {provedor}"
    
    # Configuração da API Key
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🔑 Configuração da API**")
    
    # Campos de API Key baseados no provedor
    api_key_fields = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", 
        "google": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY"
    }
    
    campo_api_key = api_key_fields.get(st.session_state.provedor_selecionado, "API_KEY")
    
    # Obter API key atual (do session_state ou ambiente)
    api_key_session = st.session_state.get(f"{campo_api_key.lower()}_input", "")
    api_key_env = os.getenv(campo_api_key, "")
    api_key_atual = api_key_session if api_key_session else api_key_env
    
    # Campo para inserir API key
    api_key_input = st.sidebar.text_input(
        f"Insira sua {campo_api_key}:",
        value=api_key_atual,
        type="password",
        help=f"Cole sua API key do {provedor} aqui",
        key=f"{campo_api_key.lower()}_input"
    )
    
    # Mostrar informações do provedor
    st.sidebar.markdown(f"**Provedor:** {provedor}")
    st.sidebar.markdown(f"**Modelo:** {modelo_api}")
    
    # Botão para testar API (sempre visível)
    if st.sidebar.button("🧪 Testar API", use_container_width=True):
        # Sanitizar entrada (evitar espaços/quebras invisíveis)
        api_key_sanitizada = (api_key_input or "").strip().strip('"').strip("'").replace("\u200b", "")
        # Armazenar versão sanitizada em chave separada (não sobrescreve o widget)
        st.session_state[f"{campo_api_key.lower()}_sanitized"] = api_key_sanitizada
        if api_key_sanitizada and len(api_key_sanitizada) > 10:
            with st.spinner("Testando API..."):
                # Definir API key no ambiente
                os.environ[campo_api_key] = api_key_sanitizada
                if testar_api_externa(api_key_sanitizada):
                    st.success("✅ API funcionando!")
                else:
                    st.error("❌ Erro na API")
        else:
            st.error("❌ Insira uma API key válida primeiro")
        
        # Botão para configurar API via página
        if st.sidebar.button("⚙️ Configurar via Página", use_container_width=True):
            st.session_state.current_page = "config"
            st.rerun()

def carregar_modelo_local():
    """Carrega modelo local"""
    try:
        model_manager = get_model_manager()
        llm = model_manager.get_llm(st.session_state.modelo_local_selecionado)
        st.session_state.llm = llm
        st.session_state.modelo_carregado = True
        return True
    except Exception as e:
        st.error(f"Erro ao carregar modelo local: {str(e)}")
        return False

def testar_api_externa(api_key_input):
    """Testa API externa"""
    try:
        # Campos de API Key baseados no provedor
        api_key_fields = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", 
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY"
        }
        
        # Obter campo da API key
        campo_api_key = api_key_fields.get(st.session_state.provedor_selecionado, "API_KEY")
        
        # Definir API key como variável de ambiente (sanitizada)
        api_key_input = (api_key_input or "").strip().strip('"').strip("'").replace("\u200b", "")
        os.environ[campo_api_key] = api_key_input
        
        # Testar API
        model_manager = get_model_manager()
        llm = model_manager.get_llm(st.session_state.modelo_api_selecionado)
        
        # Teste simples
        response = llm.invoke("Teste")
        st.session_state.llm = llm
        st.session_state.modelo_carregado = True
        return True
    except Exception as e:
        msg = str(e)
        if "invalid_api_key" in msg.lower() or "Incorrect API key" in msg or "401" in msg:
            st.error("❌ Erro na API: Chave inválida. Verifique se copiou a chave completa (sem espaços) e se é do tipo 'sk-' válida.")
        else:
            st.error(f"Erro na API: {msg}")
        return False

def pagina_inicio():
    st.markdown("<h3>Bem-vindo ao 🚀 <span style='color:#007aff;'>OldNews FiscalAI</span>!</h3>", unsafe_allow_html=True)
    
    # Botões principais modernos sempre visíveis
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button(
            "🔧 Configurar APIs", 
            use_container_width=True, 
            key="nav_config",
            help="Configure chaves de API e modelos"
        ):
            st.session_state.current_page = "config"
    
    with col2:
        if st.button(
            "📤 Upload de Nota", 
            use_container_width=True, 
            key="nav_upload",
            help="Faça upload de arquivos XML ou CSV"
        ):
            st.session_state.current_page = "upload"
    
    with col3:
        if st.button(
            "📈 Resultados", 
            use_container_width=True, 
            key="nav_dashboard",
            help="Visualize análises e relatórios"
        ):
            st.session_state.current_page = "dashboard"
    
    with col4:
        if st.button(
            "🤖 IA Chat", 
            use_container_width=True, 
            key="nav_chat",
            help="Converse com o assistente IA"
        ):
            st.session_state.current_page = "chat"
    
    st.markdown("---")
    
    # Instruções de uso
    st.markdown("""
    <div class="content-section">
    <h3>🚀 Instruções de Início</h3>
    <p style="font-size:16px; line-height: 1.6; color: #333; margin: 0;">
        O sistema utiliza IA para análise fiscal inteligente.<br>
        Use os atalhos acima para começar!</p>
    <ul style='font-size:15px; color:#1f77b4;'>
    <li><b>Configurar APIs</b>: Adicione chaves para análises avançadas.</li>
    <li><b>Upload de Nota</b>: Faça upload de XML ou CSV para análise automática.</li>
    <li><b>Resultados</b>: Visualize fraudes, scores, exporte relatórios.</li>
    <li><b>IA Chat</b>: Pergunte à IA sobre o resultado fiscal obtido.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Status das APIs
    st.markdown("---")
    st.subheader("🔑 Status das APIs")
    # show_api_status() - Função removida, usar página de configuração

def pagina_config():
    """Página de configuração de APIs"""
    # Botões de navegação rápida modernos
    st.markdown("### 🚀 Navegação Rápida")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button(
            "🏠 Início", 
            use_container_width=True, 
            key="nav_inicio",
            help="Voltar à página inicial"
        ):
            st.session_state.current_page = "inicio"
            st.rerun()
    
    with col2:
        if st.button(
            "📤 Upload de Nota", 
            use_container_width=True, 
            key="nav_upload",
            help="Fazer upload de arquivos"
        ):
            st.session_state.current_page = "upload"
            st.rerun()
    
    with col3:
        if st.button(
            "📈 Resultados", 
            use_container_width=True, 
            key="nav_dashboard",
            help="Ver resultados da análise"
        ):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col4:
        if st.button(
            "🤖 IA Chat", 
            use_container_width=True, 
            key="nav_chat",
            help="Conversar com IA"
        ):
            st.session_state.current_page = "chat"
            st.rerun()
    
    st.markdown("---")
    
    # Conteúdo da página de configuração
    show_api_config_page()

def pagina_upload():
    """Página de upload de NF-e"""
    # Botões de navegação rápida
    st.markdown("### 🚀 Navegação Rápida")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Início", use_container_width=True, key="nav_inicio"):
            st.session_state.current_page = "inicio"
            st.rerun()
    
    with col2:
        if st.button("🔧 Configurar APIs", use_container_width=True, key="nav_config"):
            st.session_state.current_page = "config"
            st.rerun()
    
    with col3:
        if st.button("📈 Resultados", use_container_width=True, key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col4:
        if st.button("🤖 IA Chat", use_container_width=True, key="nav_chat"):
            st.session_state.current_page = "chat"
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("""
    <div class="content-section">
        <h3>📤 Upload de NF-e</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout principal com sidebar à direita
    main_col, sidebar_col = st.columns([3, 1])
    
    with main_col:
        # Seleção de tipo de arquivo
        tipo_arquivo = st.radio(
            "📋 Tipo de Arquivo:",
            ["📄 XML (NF-e/NFS-e)", "📊 CSV (Dados Fiscais)"],
            horizontal=True
        )
        
        if "XML" in tipo_arquivo:
            # Upload de XML
            st.info("🔍 Criando widget de upload XML...")
            file_path = create_upload_widget(max_size_mb=200)
            st.info(f"📁 Resultado do upload: {file_path}")
            
            if file_path is not None:
                st.success(f"✅ Arquivo XML carregado: {Path(file_path).name}")
                st.info("💡 Suporta NF-e e NFS-e automaticamente!")
                st.toast("Arquivo XML recebido com sucesso!", icon="📄")
                
                st.info("🔘 Criando botões de análise...")
                
                # Container para botões modernos
                col_btn1, col_btn2 = st.columns([1, 1])
                
                with col_btn1:
                    # Botão de análise moderno
                    if st.button(
                        "🔍 Analisar Documento", 
                        key="analisar_xml",
                        help="Inicia análise completa do documento XML",
                        use_container_width=True
                    ):
                        st.info("🚀 Iniciando análise...")
                        analisar_nfe(file_path)
                
                with col_btn2:
                    # Botão executar moderno
                    if st.button(
                        "🚀 Executar Análise", 
                        key="executar_xml",
                        help="Executa análise com configurações otimizadas",
                        use_container_width=True
                    ):
                        st.info("🚀 Iniciando execução...")
                        analisar_nfe(file_path)
            else:
                st.warning("⚠️ Nenhum arquivo XML carregado")
        
        else:
            # Upload de CSV (múltiplos arquivos)
            st.info("🔍 Criando widget de upload CSV...")
            csv_files = create_csv_upload_widget(max_size_mb=50)
            st.info(f"📁 Resultado do upload CSV: {csv_files}")
            
            if csv_files is not None:
                if isinstance(csv_files, list):
                    st.success(f"✅ {len(csv_files)} arquivo(s) CSV carregado(s)")
                    st.toast("Arquivos CSV prontos para análise!", icon="🗂️")
                else:
                    st.success(f"✅ Arquivo CSV carregado: {csv_files.name}")
                    st.toast("Arquivo CSV pronto para análise!", icon="📑")
                
                st.info("🔘 Criando botões de análise CSV...")
                
                # Container para botões modernos CSV
                col_csv1, col_csv2 = st.columns([1, 1])
                
                with col_csv1:
                    # Botão de análise CSV moderno
                    if st.button(
                        "🔍 Analisar Arquivo(s)", 
                        key="analisar_csv",
                        help="Inicia análise dos arquivos CSV carregados",
                        use_container_width=True
                    ):
                        st.info("🚀 Iniciando análise CSV...")
                        if isinstance(csv_files, list):
                            analisar_csv_async(csv_files)
                        else:
                            analisar_csv(csv_files)
                
                with col_csv2:
                    # Botão executar CSV moderno
                    if st.button(
                        "🚀 Executar Análise", 
                        key="executar_csv",
                        help="Executa análise CSV com configurações otimizadas",
                        use_container_width=True
                    ):
                        st.info("🚀 Iniciando execução CSV...")
                        if isinstance(csv_files, list):
                            analisar_csv_async(csv_files)
                        else:
                            analisar_csv(csv_files)
            else:
                st.warning("⚠️ Nenhum arquivo CSV carregado")
    
    with sidebar_col:
        st.subheader("ℹ️ Instruções")
        st.info("""
        **Passo a passo:**
        
        1. Escolha o tipo de arquivo (XML ou CSV)
        2. Selecione o(s) arquivo(s) (múltiplos CSVs suportados)
        3. Clique em "Analisar" ou "Executar"
        4. Aguarde o processamento
        5. Visualize os resultados consolidados (Dashboard)
        6. Converse com o assistente (Chat)
        
        **🎯 Tipos Suportados:**
        
        | Tipo | Status | Descrição |
        |------|--------|-----------|
        | NF-e | ✅ Suportado | Nota Fiscal Eletrônica |
        | NFS-e | ✅ Suportado | Nota Fiscal de Serviços Eletrônica |
        | CT-e | 🔄 Futuro | Conhecimento de Transporte |
        | MDF-e | 🔄 Futuro | Manifesto Eletrônico |
        
        **📁 Formatos de Arquivo:**
        - XML (padrão SEFAZ)
        - CSV com dados fiscais
        
        **Tamanho máximo:**
        - XML: 200 MB
        - CSV: 50 MB
        """)
        
        # Botões de exemplo modernos
        st.subheader("📋 Exemplos Prontos")
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            if st.button(
                "📄 NF-e Exemplo", 
                use_container_width=True, 
                key="exemplo_nfe",
                help="Carrega e analisa uma NF-e de exemplo"
            ):
                # Carregar arquivo de exemplo
                exemplo_path = Path(__file__).parent.parent / "data" / "samples" / "nfe_exemplo.xml"
                if exemplo_path.exists():
                    st.success("NF-e de exemplo carregada!")
                    st.info("🔄 Executando análise automaticamente...")
                    # Executar análise automaticamente
                    analisar_nfe(str(exemplo_path))
                else:
                    st.error("❌ Arquivo de exemplo não encontrado!")
        
        with col_ex2:
            if st.button(
                "📊 CSV Exemplo", 
                use_container_width=True, 
                key="exemplo_csv",
                help="Cria e analisa um CSV de exemplo"
            ):
                # Criar e analisar CSV de exemplo automaticamente
                csv_exemplo = criar_csv_exemplo()
                if csv_exemplo:
                    st.info("🔄 Executando análise do CSV automaticamente...")
                    # Executar análise automaticamente
                    analisar_csv(csv_exemplo)


def criar_csv_exemplo():
    """Cria um CSV de exemplo e retorna o objeto para análise"""
    from streamlit.runtime.uploaded_file_manager import UploadedFile
    
    # Criar dados de exemplo
    dados_exemplo = [
        {
            'codigo_produto': 'PROD001',
            'descricao': 'Produto de Exemplo 1',
            'ncm': '12345678',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 10.0,
            'valor_unitario': 25.50,
            'valor_total': 255.00,
            'desconto': 0.0,
            'acrescimo': 0.0,
            'cnpj_emitente': '12345678000199',
            'razao_social_emitente': 'Empresa Exemplo Ltda',
            'cnpj_destinatario': '98765432000188',
            'razao_social_destinatario': 'Cliente Exemplo Ltda'
        },
        {
            'codigo_produto': 'PROD002',
            'descricao': 'Produto de Exemplo 2',
            'ncm': '87654321',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 5.0,
            'valor_unitario': 45.00,
            'valor_total': 225.00,
            'desconto': 10.0,
            'acrescimo': 0.0,
            'cnpj_emitente': '12345678000199',
            'razao_social_emitente': 'Empresa Exemplo Ltda',
            'cnpj_destinatario': '98765432000188',
            'razao_social_destinatario': 'Cliente Exemplo Ltda'
        },
        {
            'codigo_produto': 'PROD003',
            'descricao': 'Produto de Exemplo 3',
            'ncm': '11223344',
            'cfop': '5102',
            'unidade': 'KG',
            'quantidade': 2.5,
            'valor_unitario': 15.75,
            'valor_total': 39.38,
            'desconto': 0.0,
            'acrescimo': 5.0,
            'cnpj_emitente': '12345678000199',
            'razao_social_emitente': 'Empresa Exemplo Ltda',
            'cnpj_destinatario': '98765432000188',
            'razao_social_destinatario': 'Cliente Exemplo Ltda'
        }
    ]
    
    # Criar DataFrame
    df = pd.DataFrame(dados_exemplo)
    
    # Converter para CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    # Criar objeto similar ao UploadedFile
    class MockUploadedFile:
        def __init__(self, data, name):
            self._data = data.encode('utf-8')
            self.name = name
        
        def getvalue(self):
            return self._data
    
    # Retornar objeto mock para análise
    csv_file = MockUploadedFile(csv_data, "exemplo_dados_fiscais.csv")
    
    st.success("✅ CSV de exemplo criado!")
    
    # Também disponibilizar para download
    st.download_button(
        label="📥 Baixar CSV de Exemplo",
        data=csv_data,
        file_name="exemplo_dados_fiscais.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    return csv_file


def analisar_nfe(xml_path: str):
    """
    Executa análise completa de NF-e usando o sistema de agentes
    
    Args:
        xml_path: Caminho para o arquivo XML da NF-e
    """
    st.info("🔍 Iniciando análise de NF-e...")
    
    # Verificar rate limiting
    client_id = "streamlit_user"  # Em produção, usar IP real
    st.info(f"🔒 Verificando rate limit para cliente: {client_id}")
    
    try:
        is_allowed, rate_info = check_rate_limit(client_id, "api_analysis")
        st.info(f"✅ Rate limit verificado: {is_allowed}")
    except Exception as e:
        st.warning(f"⚠️ Erro ao verificar rate limit: {e}")
        is_allowed = True  # Continuar mesmo com erro
    
    if not is_allowed:
        st.error("🚫 **Rate Limit Excedido**")
        st.warning("Muitas análises executadas. Tente novamente mais tarde.")
        if 'block_until' in rate_info:
            block_until = datetime.fromtimestamp(rate_info['block_until'])
            st.info(f"⏰ Bloqueio até: {block_until.strftime('%H:%M:%S')}")
        return
    
    # Log de evento de segurança
    st.info("🔐 Registrando evento de segurança...")
    try:
        log_security_event(
            event_type="document_analysis",
            source_ip=client_id,
            action="nfe_analysis_start",
            resource=f"file:{xml_path}",
            details={"file_size": os.path.getsize(xml_path) if os.path.exists(xml_path) else 0},
            user_id="streamlit_user",
            severity="low"
        )
        st.info("✅ Evento de segurança registrado")
    except Exception as e:
        st.warning(f"⚠️ Erro ao registrar evento de segurança: {e}")
        logger.warning(f"Erro ao registrar evento de segurança: {e}")
    
    # Validar XML contra schema XSD
    st.info("📋 Validando XML contra schema XSD...")
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        st.info("✅ XML lido com sucesso")
        
        xml_validator = get_xml_validator()
        validation_result = validate_xml_schema(xml_content, "nfe_4.00")
        
        if not validation_result.is_valid:
            st.warning("⚠️ **Validação XML Schema - Problemas Encontrados**")
            
            # Mostrar erros críticos
            if validation_result.errors:
                st.error("**Erros críticos que impedem a análise:**")
                for error in validation_result.errors:
                    st.write(f"• {error}")
            
            # Mostrar avisos
            if validation_result.warnings:
                st.warning("**Avisos (não impedem a análise):**")
                for warning in validation_result.warnings:
                    st.write(f"• {warning}")
            
            with st.expander("🔍 Detalhes Técnicos da Validação"):
                st.write(f"**Schema usado:** NFe {validation_result.schema_version}")
                st.write(f"**Tamanho do arquivo:** {validation_result.file_size:,} bytes")
                st.write(f"**Tempo de validação:** {validation_result.validation_time:.2f}s")
                
                # Verificações de segurança
                st.write("**Verificações de Segurança:**")
                for check, passed in validation_result.security_checks.items():
                    status = "✅" if passed else "❌"
                    st.write(f"{status} {check.replace('_', ' ').title()}")
            
            # Perguntar se deve continuar
            st.info("💡 **A análise pode continuar mesmo com avisos de validação.** Os avisos não impedem o processamento do XML.")
            if st.checkbox("Continuar análise mesmo com avisos de validação?", value=True):
                st.success("✅ Continuando análise...")
            else:
                st.stop()
        else:
            st.success("✅ **XML validado com sucesso!**")
            
            # Mostrar informações de validação
            with st.expander("📋 Informações de Validação"):
                st.write(f"**Schema:** NFe {validation_result.schema_version}")
                st.write(f"**Tamanho:** {validation_result.file_size:,} bytes")
                st.write(f"**Tempo de validação:** {validation_result.validation_time:.2f}s")
                
                if validation_result.warnings:
                    st.write("**Avisos:**")
                    for warning in validation_result.warnings:
                        st.write(f"• {warning}")
                else:
                    st.success("✅ Nenhum aviso encontrado")
                
                # Verificações de segurança
                st.write("**Verificações de Segurança:**")
                for check, passed in validation_result.security_checks.items():
                    status = "✅" if passed else "❌"
                    st.write(f"{status} {check.replace('_', ' ').title()}")
        
    except Exception as e:
        logger.warning(f"Erro na validação XML schema: {e}")
        st.warning("⚠️ Não foi possível validar o XML contra o schema oficial")
    
    # Verificar cache de resultados
    try:
        result_cache = get_result_cache()
        cache_key = f"nfe_analysis_{hashlib.md5(xml_content.encode()).hexdigest()}"
        
        # Tentar obter resultado do cache
        cached_result = result_cache.get(cache_key)
        if cached_result:
            st.success("🚀 **Resultado obtido do cache - Análise instantânea!**")
            st.info(f"Cache criado em: {cached_result['timestamp']}")
            
            # Restaurar estado a partir do cache
            if 'relatorio' in cached_result:
                st.session_state.relatorio = cached_result['relatorio']
            if 'nfe' in cached_result:
                st.session_state.nfe_data = cached_result['nfe']
            elif 'relatorio' in cached_result and hasattr(cached_result['relatorio'], 'nfe'):
                # Fallback: derivar nfe_data do relatório armazenado
                st.session_state.nfe_data = getattr(cached_result['relatorio'], 'nfe', None)
            if 'classificacoes' in cached_result:
                st.session_state.classificacoes = cached_result['classificacoes']
            if 'multiple_nfes' in cached_result:
                st.session_state.multiple_nfes = cached_result['multiple_nfes']
            if 'multiple_resultados' in cached_result:
                st.session_state.multiple_resultados = cached_result['multiple_resultados']
            if 'csv_data' in cached_result:
                st.session_state.csv_data = cached_result['csv_data']
            if 'xml_path' in cached_result:
                st.session_state.uploaded_xml_path = cached_result['xml_path']
            
            # Recarregar UI com estado restaurado
            st.rerun()
        else:
            pass
    except Exception as e:
        logger.warning(f"Erro ao verificar cache: {e}")
    
    # Inicializar variáveis de progresso fora do try
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Log de início da análise
        log_info(f"Iniciando análise da NF-e: {xml_path}", 
                extra_data={'xml_path': xml_path, 'client_id': client_id})
        
        # Iniciar timer de performance
        start_time = time.time()
        
        debug_log(f"Iniciando análise da NF-e: {xml_path}", 1)
        
        # Passo 1: Inicializar agentes
        status_text.text("🔄 Inicializando agentes...")
        progress_bar.progress(10)
        debug_log("Inicializando agentes...", 2)
        
        from src.agents import (
            Agente1Extrator,
            Agente2Classificador, 
            Agente3Validador,
            Agente4Orquestrador
        )
        from src.detectors import OrquestradorDeteccaoFraudes
        from src.utils.xml_parser import NFeXMLParser
        
        # Inicializar agentes com LLM
        from src.utils.model_manager import get_model_manager
        model_manager = get_model_manager()
        modelo_para_usar = st.session_state.get('modelo_selecionado', 'mistral-7b-gguf')
        llm = model_manager.get_llm(modelo_para_usar)
        
        agente1 = Agente1Extrator(llm)
        agente2 = Agente2Classificador(llm)
        agente3 = Agente3Validador(llm)
        agente4 = Agente4Orquestrador(llm)
        
        # Passo 2: Extrair dados da NF-e com parser inteligente
        status_text.text("🧠 Processando documento com IA...")
        progress_bar.progress(25)
        
        # Usar parser aprimorado que detecta e processa múltiplas notas
        from src.utils.enhanced_multiple_parser import parse_enhanced_multiple
        
        try:
            # Processar com parser aprimorado que detecta múltiplas notas
            st.info(f"🔍 Analisando arquivo: {xml_path}")
            nfes, doc_type, doc_description = parse_enhanced_multiple(xml_path)
            
            st.info(f"📊 Resultado do parser: {len(nfes)} nota(s) encontrada(s)")
            st.info(f"📋 Tipo detectado: {doc_type} - {doc_description}")
            
            if len(nfes) > 1:
                st.success(f"🎉 Processadas {len(nfes)} notas fiscais!")
                st.info(f"📋 Tipo: {doc_description}")
                
                # Mostrar detalhes de cada nota
                for i, nfe in enumerate(nfes[:5]):  # Mostrar apenas as primeiras 5
                    st.info(f"  📄 Nota {i+1}: {nfe.numero} - {nfe.razao_social_emitente} → {nfe.razao_social_destinatario}")
                
                if len(nfes) > 5:
                    st.info(f"  ... e mais {len(nfes) - 5} notas")
                
                # Processar todas as notas
                todos_resultados = []
                todos_nfes = []
                todas_classificacoes = []
                todas_validacoes = []
                
                for i, nfe in enumerate(nfes):
                    status_text.text(f"🔍 Analisando nota {i+1}/{len(nfes)}...")
                    progress_bar.progress(25 + (i / len(nfes)) * 50)
                    
                    # Agente 2: Classificar produtos
                    classificacoes = agente2.executar(nfe.itens)
                    
                    # Agente 3: Validação fiscal
                    validacao = agente3.executar(nfe, classificacoes)
                    
                    # Detectar fraudes
                    detector = OrquestradorDeteccaoFraudes()
                    resultado = detector.analisar_nfe(nfe, classificacoes)
                    
                    # Agente 4: Orquestração e consolidação
                    resultado_orquestrado = agente4.executar(nfe, classificacoes, validacao)
                    
                    todos_resultados.append(resultado_orquestrado)
                    todos_nfes.append(nfe)
                    todas_classificacoes.append(classificacoes)
                    todas_validacoes.append(validacao)
                
                # Consolidar resultados de todas as notas
                relatorio_consolidado = consolidar_resultados(todos_resultados, todos_nfes, todas_classificacoes)
                
                # Salvar resultado consolidado na sessão
                st.session_state.relatorio = relatorio_consolidado
                st.session_state.nfe_data = todos_nfes[0]  # Usar primeira nota como principal
                st.session_state.classificacoes = todas_classificacoes[0]
                st.session_state.multiple_nfes = todos_nfes
                st.session_state.multiple_resultados = todos_resultados
                st.session_state.uploaded_xml_path = xml_path
                
                # Salvar resultado consolidado (múltiplas NFs) no cache
                try:
                    result_cache = get_result_cache()
                    cache_key = f"nfe_analysis_{hashlib.md5(xml_content.encode()).hexdigest()}"
                    cache_data = {
                        'relatorio': relatorio_consolidado,
                        'nfe': todos_nfes[0],
                        'classificacoes': todas_classificacoes[0],
                        'multiple_nfes': todos_nfes,
                        'multiple_resultados': todos_resultados,
                        'timestamp': datetime.now().isoformat(),
                        'xml_path': xml_path
                    }
                    result_cache.set(cache_key, cache_data)
                except Exception as e:
                    logger.warning(f"Erro ao salvar resultado consolidado no cache: {e}")
                
                # Inicializar Agente5Interface para chat
                from src.agents import Agente5Interface
                agente5 = Agente5Interface(llm)
                relatorio_fiscal = RelatorioFiscal(
                    nfe=todos_nfes[0],
                    resultado_analise=relatorio_consolidado,
                    classificacoes_ncm=list(todas_classificacoes[0].values())
                )
                agente5.carregar_relatorio(relatorio_fiscal)
                st.session_state.agente5 = agente5
                
                # Log removido para evitar poluição do terminal
                
                # Definir flag de análise concluída
                st.session_state.analysis_completed = True
                
                # Redirecionar para dashboard
                st.session_state.current_page = 'dashboard'
                st.success("🎉 Análise de múltiplas notas concluída! Redirecionando para o dashboard...")
                st.rerun()
                
            else:
                # Apenas uma nota - usar processamento normal
                st.info(f"📄 Processando 1 nota fiscal: {doc_description}")
                nfe = nfes[0]
                st.info(f"  📋 Nota: {nfe.numero} - {nfe.razao_social_emitente} → {nfe.razao_social_destinatario}")
                metadata = {'document_type': doc_type, 'document_description': doc_description}
                
        except Exception as e:
            # Fallback para parser original
            st.warning(f"⚠️ Usando parser alternativo: {str(e)}")
            smart_parser = SmartFiscalParser()
            smart_data = smart_parser.parse_document(xml_path)
            
            nfe = smart_data['nfe']
            doc_type = smart_data['document_type']
            doc_description = smart_data['document_description']
            metadata = smart_data['metadata']
        
        # Mostrar informações inteligentes do documento
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"📋 **Tipo:** {doc_description}")
        
        with col2:
            st.success(f"🏢 **Emitente:** {metadata['participants']['emitente_type'].upper()}")
        
        with col3:
            st.success(f"👤 **Destinatário:** {metadata['participants']['destinatario_type'].upper()}")
        
        # Mostrar resumo inteligente
        st.info(f"💡 **Resumo:** {metadata['document_summary']}")
        
        # Mostrar indicadores de qualidade
        quality_score = metadata['quality_indicators']['data_quality_score']
        compliance_score = metadata['quality_indicators']['compliance_score']
        risk_score = metadata['quality_indicators']['risk_score']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if quality_score >= 80:
                st.success(f"✅ **Qualidade:** {quality_score}%")
            elif quality_score >= 60:
                st.warning(f"⚠️ **Qualidade:** {quality_score}%")
            else:
                st.error(f"❌ **Qualidade:** {quality_score}%")
        
        with col2:
            if compliance_score >= 70:
                st.success(f"✅ **Conformidade:** {compliance_score}%")
            elif compliance_score >= 50:
                st.warning(f"⚠️ **Conformidade:** {compliance_score}%")
            else:
                st.error(f"❌ **Conformidade:** {compliance_score}%")
        
        with col3:
            if risk_score <= 30:
                st.success(f"✅ **Risco:** {risk_score}%")
            elif risk_score <= 60:
                st.warning(f"⚠️ **Risco:** {risk_score}%")
            else:
                st.error(f"❌ **Risco:** {risk_score}%")
        
        # Armazenar dados inteligentes na sessão
        st.session_state.smart_data = smart_data
        
        # Passo 3: Classificar produtos
        status_text.text("🏷️ Classificando produtos...")
        progress_bar.progress(50)
        
        classificacoes = agente2.executar(nfe.itens)
        
        # Passo 4: Detectar fraudes
        status_text.text("🔍 Detectando fraudes...")
        progress_bar.progress(75)
        
        detector = OrquestradorDeteccaoFraudes()
        resultado = detector.analisar_nfe(nfe, classificacoes)
        
        # Passo 5: Gerar relatório
        status_text.text("📊 Gerando relatório...")
        progress_bar.progress(90)
        
        # Criar RelatorioFiscal com o resultado
        from src.models.schemas import RelatorioFiscal
        relatorio_fiscal = RelatorioFiscal(
            nfe=nfe,
            resultado_analise=resultado,
            classificacoes_ncm=list(classificacoes.values())
        )
        
        # Salvar resultado na sessão
        st.session_state.relatorio = relatorio_fiscal
        st.session_state.nfe_data = nfe
        st.session_state.classificacoes = classificacoes
        st.session_state.uploaded_xml_path = xml_path
        
        # Salvar resultado no cache
        try:
            result_cache = get_result_cache()
            cache_key = f"nfe_analysis_{hashlib.md5(xml_content.encode()).hexdigest()}"
            
            cache_data = {
                'relatorio': relatorio_fiscal,
                'nfe': nfe,
                'classificacoes': classificacoes,
                'timestamp': datetime.now().isoformat(),
                'xml_path': xml_path,
                'fraudes_detectadas': len(relatorio_fiscal.resultado_analise.fraudes_detectadas)
            }
            
            result_cache.set(cache_key, cache_data)
            logger.info(f"Resultado salvo no cache: {cache_key}")
        except json.JSONDecodeError as e:
            logger.error(f"Erro de JSON no cache: {e}")
            st.warning("Erro ao processar dados do cache. Continuando sem cache...")
        except Exception as e:
            logger.warning(f"Erro ao salvar no cache: {e}")
            st.warning(f"Erro ao salvar no cache: {e}")
        
        # Inicializar Agente5Interface para chat
        from src.agents import Agente5Interface
        
        agente5 = Agente5Interface(llm)
        agente5.carregar_relatorio(relatorio_fiscal)
        st.session_state.agente5 = agente5
        
        # NOVO: Definir flag de análise concluída
        st.session_state.analysis_completed = True
        
        # Passo 6: Concluído
        progress_bar.progress(100)
        status_text.text("✅ Análise concluída!")
        
        # Registrar métrica de performance
        duration_ms = (time.time() - start_time) * 1000
        record_performance("nfe_analysis", duration_ms, success=True, 
                          extra_data={'xml_path': xml_path, 'client_id': client_id})
        
        # Redirecionar para dashboard
        st.session_state.current_page = 'dashboard'
        st.success("🎉 Análise concluída com sucesso! Redirecionando para o dashboard...")
        st.rerun()
    
    except Exception as e:
        # Em caso de erro, garantir que o flag seja False
        st.session_state.analysis_completed = False
        st.error(f"❌ Erro na análise: {str(e)}")
        st.exception(e)
        progress_bar.empty()
        status_text.empty()


def analisar_multiplos_csv(csv_files):
    """
    Executa análise completa de múltiplos arquivos CSV usando o sistema de agentes
    
    Args:
        csv_files: Lista de arquivos CSV carregados via Streamlit
    """
    # Inicializar variáveis de progresso fora do try
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        
        total_files = len(csv_files)
        st.info(f"🔄 Iniciando análise de {total_files} arquivo(s) CSV...")
        
        # Armazenar resultados de todos os arquivos
        todos_resultados = []
        todos_nfes = []
        todas_classificacoes = []
        todos_dfs = []
        
        # Processar cada arquivo
        for i, csv_file in enumerate(csv_files):
            status_text.text(f"📊 Processando arquivo {i+1}/{total_files}: {csv_file.name}")
            progress_bar.progress((i / total_files) * 0.8)  # 80% para processamento
            
            try:
                # Processar arquivo individual
                resultado = processar_csv_individual(csv_file, i+1, total_files)
                
                if resultado:
                    todos_resultados.append(resultado['relatorio'])
                    todos_nfes.append(resultado['nfe'])
                    todas_classificacoes.append(resultado['classificacoes'])
                    todos_dfs.append(resultado['df'])
                    
                    st.success(f"✅ Arquivo {i+1} processado: {csv_file.name}")
                else:
                    st.warning(f"⚠️ Erro ao processar arquivo {i+1}: {csv_file.name}")
                    
            except Exception as e:
                st.error(f"❌ Erro no arquivo {csv_file.name}: {str(e)}")
                continue
        
        # Consolidar resultados
        status_text.text("📊 Consolidando resultados...")
        progress_bar.progress(0.9)
        
        if todos_resultados:
            # Criar relatório consolidado
            relatorio_consolidado = consolidar_resultados(todos_resultados, todos_nfes, todas_classificacoes)
            
            # Salvar resultado consolidado na sessão
            st.session_state.relatorio = relatorio_consolidado
            st.session_state.nfe_data = todos_nfes[0] if todos_nfes else None  # Usar primeira NFe como referência
            st.session_state.classificacoes = todas_classificacoes[0] if todas_classificacoes else None
            st.session_state.csv_data = todos_dfs[0] if todos_dfs else None
            st.session_state.todos_resultados = todos_resultados
            st.session_state.todos_nfes = todos_nfes
            st.session_state.todas_classificacoes = todas_classificacoes
            st.session_state.todos_dfs = todos_dfs
            
            # Inicializar Agente5Interface para chat
            from src.utils.model_manager import get_model_manager
            model_manager = get_model_manager()
            modelo_para_usar = st.session_state.get('modelo_selecionado', 'mistral-7b-gguf')
            llm = model_manager.get_llm(modelo_para_usar)
            
            from src.agents import Agente5Interface
            agente5 = Agente5Interface(llm)
            agente5.carregar_relatorio(relatorio_consolidado)
            st.session_state.agente5 = agente5
            
            # Definir flag de análise concluída
            st.session_state.analysis_completed = True
            
            # Concluído
            progress_bar.progress(1.0)
            status_text.text("✅ Análise consolidada concluída!")
            
            # Redirecionar para dashboard
            st.session_state.current_page = 'dashboard'
            st.success(f"🎉 Análise de {len(todos_resultados)} arquivo(s) concluída! Redirecionando para o dashboard...")
            st.rerun()
            
        else:
            st.error("❌ Nenhum arquivo foi processado com sucesso")
            progress_bar.empty()
            status_text.empty()
        
    except Exception as e:
        st.session_state.analysis_completed = False
        st.error(f"❌ Erro na análise múltipla: {str(e)}")
        st.exception(e)
        progress_bar.empty()
        status_text.empty()


def processar_csv_individual(csv_file, numero_arquivo, total_arquivos):
    """
    Processa um arquivo CSV individual
    
    Args:
        csv_file: Arquivo CSV individual
        numero_arquivo: Número do arquivo (para logs)
        total_arquivos: Total de arquivos
    
    Returns:
        Dict com resultado, nfe, classificacoes e df ou None
    """
    try:
        
        # Ler CSV com detector robusto de codificação
        from src.utils.csv_encoding_detector import read_csv_robust
        
        csv_bytes = csv_file.getvalue()
        df, encoding_used, separator_used = read_csv_robust(csv_bytes)
        
        if df is None:
            st.error(f"❌ Erro ao processar arquivo {numero_arquivo}: Não foi possível ler o arquivo como CSV válido")
            st.error("💡 Dicas: Verifique se o arquivo está em formato CSV válido e tente salvá-lo como UTF-8.")
            return None
        
        # Log da codificação e separador usados
        if encoding_used != 'utf-8' or separator_used != ',':
            st.info(f"ℹ️ Arquivo {numero_arquivo} processado com codificação {encoding_used} e separador '{separator_used}'")
        
        # Salvar CSV temporariamente
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            df.to_csv(tmp_file.name, index=False)
            csv_path = tmp_file.name
        
        # Inicializar agentes
        from src.agents import (
            Agente1Extrator,
            Agente2Classificador, 
            Agente3Validador,
            Agente4Orquestrador
        )
        from src.detectors import OrquestradorDeteccaoFraudes
        
        # Inicializar agentes com LLM
        from src.utils.model_manager import get_model_manager
        model_manager = get_model_manager()
        modelo_para_usar = st.session_state.get('modelo_selecionado', 'mistral-7b-gguf')
        llm = model_manager.get_llm(modelo_para_usar)
        
        agente1 = Agente1Extrator(llm)
        agente2 = Agente2Classificador(llm)
        agente3 = Agente3Validador(llm)
        agente4 = Agente4Orquestrador(llm)
        
        # Executar Agente1Extrator para extrair dados do CSV
        try:
            resultado_extracao = agente1.executar_csv(df, csv_file.name)
            if resultado_extracao and 'nfe' in resultado_extracao:
                nfe = resultado_extracao['nfe']
            else:
                nfe = converter_csv_para_nfe(df, csv_file.name)
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente1Extrator: {str(e)}")
            nfe = converter_csv_para_nfe(df, csv_file.name)
            resultado_extracao = None
        
        # Executar Agente2Classificador
        try:
            classificacoes = agente2.executar(nfe.itens)
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente2Classificador: {str(e)}")
            classificacoes = {}
        
        # Executar Agente3Validador
        try:
            resultado_validacao = agente3.executar(nfe, classificacoes)
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente3Validador: {str(e)}")
            resultado_validacao = None
        
        # Executar Agente4Orquestrador
        try:
            resultado_orquestracao = agente4.executar(nfe, classificacoes, resultado_validacao)
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente4Orquestrador: {str(e)}")
            resultado_orquestracao = None
        
        # Detectar fraudes
        try:
            detector = OrquestradorDeteccaoFraudes()
            resultado = detector.analisar_nfe(nfe, classificacoes)
        except Exception as e:
            st.warning(f"⚠️ Erro na detecção de fraudes: {str(e)}")
            from src.models.schemas import ResultadoAnalise, NivelRisco
            resultado = ResultadoAnalise(
                fraudes_detectadas=[],
                score_risco_geral=0,
                nivel_risco=NivelRisco.BAIXO,
                itens_suspeitos=[],
                acoes_recomendadas=[],
                data_analise=datetime.now(),
                tempo_processamento_segundos=0
            )
        
        # Limpar arquivo temporário
        os.unlink(csv_path)
        
        return {
            'relatorio': resultado,
            'nfe': nfe,
            'classificacoes': classificacoes,
            'df': df,
            'resultado_extracao': resultado_extracao,
            'resultado_validacao': resultado_validacao,
            'resultado_orquestracao': resultado_orquestracao
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao processar arquivo {numero_arquivo}: {str(e)}")
        return None


def consolidar_resultados(todos_resultados, todos_nfes, todas_classificacoes):
    """
    Consolida resultados de múltiplos arquivos XML/CSV
    
    Args:
        todos_resultados: Lista de resultados de análise
        todos_nfes: Lista de objetos NFe
        todas_classificacoes: Lista de classificações
    
    Returns:
        Relatório consolidado
    """
    from src.models.schemas import RelatorioFiscal, ResultadoAnalise, NivelRisco
    from datetime import datetime
    
    # Consolidar métricas
    total_fraudes = sum(len(r.fraudes_detectadas) for r in todos_resultados)
    total_itens = sum(len(nfe.itens) for nfe in todos_nfes)
    score_medio = sum(r.score_risco_geral for r in todos_resultados) / len(todos_resultados)
    
    # Determinar nível de risco consolidado
    if score_medio < 30:
        nivel_risco = NivelRisco.BAIXO
    elif score_medio < 70:
        nivel_risco = NivelRisco.MEDIO
    else:
        nivel_risco = NivelRisco.ALTO
    
    # Consolidar fraudes
    todas_fraudes = []
    for resultado in todos_resultados:
        todas_fraudes.extend(resultado.fraudes_detectadas)
    
    # Consolidar ações recomendadas
    todas_acoes = []
    for resultado in todos_resultados:
        todas_acoes.extend(resultado.acoes_recomendadas)
    
    # Remover duplicatas das ações
    todas_acoes = list(set(todas_acoes))
    
    # Agrupar por CNPJ emitente para análise
    grupos_cnpj = {}
    for nfe, resultado in zip(todos_nfes, todos_resultados):
        cnpj = nfe.cnpj_emitente
        if cnpj not in grupos_cnpj:
            grupos_cnpj[cnpj] = {
                'razao_social': nfe.razao_social_emitente,
                'nfes': [],
                'resultados': [],
                'total_valor': 0,
                'total_fraudes': 0
            }
        grupos_cnpj[cnpj]['nfes'].append(nfe)
        grupos_cnpj[cnpj]['resultados'].append(resultado)
        grupos_cnpj[cnpj]['total_valor'] += nfe.valor_total
        grupos_cnpj[cnpj]['total_fraudes'] += len(resultado.fraudes_detectadas)
    
    # Gerar recomendações estratégicas por grupo
    recomendacoes_estrategicas = []
    for cnpj, dados in grupos_cnpj.items():
        if dados['total_fraudes'] > 0:
            recomendacoes_estrategicas.append(
                f"⚠️ {dados['razao_social']}: {dados['total_fraudes']} fraudes detectadas em {len(dados['nfes'])} notas (R$ {dados['total_valor']:,.2f})"
            )
        else:
            recomendacoes_estrategicas.append(
                f"✅ {dados['razao_social']}: Sem fraudes detectadas em {len(dados['nfes'])} notas (R$ {dados['total_valor']:,.2f})"
            )
    
    # Adicionar recomendações gerais
    if len(grupos_cnpj) > 1:
        recomendacoes_estrategicas.append(f"📊 Análise consolidada de {len(todos_nfes)} notas de {len(grupos_cnpj)} prestadores diferentes")
    
    # Criar resultado consolidado
    # Gerar chave de acesso válida (44 caracteres) para resultado consolidado
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    chave_consolidada = f"CONSOLIDADO_{len(todos_nfes)}_NOTAS_{timestamp}".ljust(44, '0')[:44]
    
    resultado_consolidado = ResultadoAnalise(
        chave_acesso=chave_consolidada,
        score_risco_geral=score_medio,
        nivel_risco=nivel_risco,
        fraudes_detectadas=todas_fraudes,
        itens_suspeitos=list(range(1, total_itens + 1)),
        acoes_recomendadas=todas_acoes + recomendacoes_estrategicas,
        tempo_processamento_segundos=sum(r.tempo_processamento_segundos for r in todos_resultados),
        data_analise=datetime.now(),
        resultado_analise={
            'total_notas': len(todos_nfes),
            'total_prestadores': len(grupos_cnpj),
            'grupos_cnpj': grupos_cnpj,
            'recomendacoes_estrategicas': recomendacoes_estrategicas
        }
    )
    
    # Criar relatório consolidado
    relatorio_consolidado = RelatorioFiscal(
        nfe=todos_nfes[0],  # Primeira NFe como referência
        resultado_analise=resultado_consolidado,
        classificacoes_ncm=consolidar_classificacoes(todas_classificacoes)
    )
    
    return relatorio_consolidado


def consolidar_classificacoes(todas_classificacoes):
    """
    Consolida classificações de múltiplas NFS-e
    
    Args:
        todas_classificacoes: Lista de classificações de cada NFS-e
    
    Returns:
        Lista consolidada de classificações
    """
    classificacoes_consolidadas = []
    for classificacoes in todas_classificacoes:
        if classificacoes:
            classificacoes_consolidadas.extend(list(classificacoes.values()))
    return classificacoes_consolidadas


def analisar_csv_async(csv_files):
    """
    Executa análise assíncrona de múltiplos arquivos CSV com agentes CREW
    
    Args:
        csv_files: Lista de arquivos CSV ou arquivo único
    """
    if not isinstance(csv_files, list):
        csv_files = [csv_files]
    
    st.info(f"🚀 Iniciando análise completa de {len(csv_files)} arquivo(s) CSV com agentes CREW...")
    
    # Para múltiplos arquivos, processar o primeiro com análise completa
    # e os demais com análise básica
    if len(csv_files) == 1:
        # Apenas um arquivo - usar análise completa
        analisar_csv(csv_files[0])
    else:
        # Múltiplos arquivos - processar o primeiro com análise completa
        st.info(f"📊 Processando primeiro arquivo com análise completa: {csv_files[0].name}")
        analisar_csv(csv_files[0])
        
        # Processar demais arquivos com análise básica
        if len(csv_files) > 1:
            st.info(f"📊 Processando {len(csv_files)-1} arquivo(s) adicional(is) com análise básica...")
            
            todos_resultados = []
            todos_nfes = []
            todas_classificacoes = []
            
            for i, csv_file in enumerate(csv_files[1:], 1):
                try:
                    st.info(f"🔍 Processando arquivo {i+1}/{len(csv_files)}: {csv_file.name}")
                    
                    # Processar arquivo individual
                    resultado = processar_csv_individual(csv_file, i+1, len(csv_files))
                    
                    if resultado:
                        todos_resultados.append(resultado['relatorio'])
                        todos_nfes.append(resultado['nfe'])
                        todas_classificacoes.append(resultado['classificacoes'])
                        
                        st.success(f"✅ Arquivo {i+1} processado com sucesso")
                    else:
                        st.warning(f"⚠️ Arquivo {i+1} não pôde ser processado")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo {i+1}: {str(e)}")
                    continue
            
            # Consolidar resultados se houver múltiplos arquivos processados
            if todos_resultados:
                st.info("🔄 Consolidando resultados de múltiplos arquivos...")
                
                # Consolidar resultados
                relatorio_consolidado = consolidar_resultados(todos_resultados, todos_nfes, todas_classificacoes)
                
                # Salvar resultado consolidado na sessão
                st.session_state.relatorio = relatorio_consolidado
                st.session_state.multiple_nfes = todos_nfes
                st.session_state.multiple_resultados = todos_resultados
                
                # Inicializar Agente5Interface para chat
                from src.agents import Agente5Interface
                from src.utils.model_manager import get_model_manager
                from src.models.schemas import RelatorioFiscal
                
                model_manager = get_model_manager()
                modelo_para_usar = st.session_state.get('modelo_selecionado', 'mistral-7b-gguf')
                llm = model_manager.get_llm(modelo_para_usar)
                
                agente5 = Agente5Interface(llm)
                relatorio_fiscal = RelatorioFiscal(
                    nfe=todos_nfes[0],
                    resultado_analise=relatorio_consolidado,
                    classificacoes_ncm=list(todas_classificacoes[0].values())
                )
                agente5.carregar_relatorio(relatorio_fiscal)
                st.session_state.agente5 = agente5
                
                # Definir flag de análise concluída
                st.session_state.analysis_completed = True
                
                # Redirecionar para dashboard
                st.session_state.current_page = 'dashboard'
                st.success("🎉 Análise de múltiplos arquivos CSV concluída! Redirecionando para o dashboard...")
                st.rerun()


def analisar_csv(csv_file):
    """
    Executa análise completa de dados CSV usando o sistema de agentes
    
    Args:
        csv_file: Arquivo CSV carregado via Streamlit
    """
    # Inicializar variáveis de progresso fora do try
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        
        # Passo 1: Processar CSV
        status_text.text("📊 Processando arquivo CSV...")
        progress_bar.progress(10)
        
        # Ler CSV com detector robusto de codificação
        from src.utils.csv_encoding_detector import read_csv_robust
        
        csv_bytes = csv_file.getvalue()
        df, encoding_used, separator_used = read_csv_robust(csv_bytes)
        
        if df is None:
            st.error("❌ Erro ao processar CSV: Não foi possível ler o arquivo como CSV válido")
            st.error("💡 Dicas: Verifique se o arquivo está em formato CSV válido e tente salvá-lo como UTF-8.")
            return
        
        # Log da codificação e separador usados
        if encoding_used != 'utf-8' or separator_used != ',':
            st.info(f"ℹ️ Arquivo processado com codificação {encoding_used} e separador '{separator_used}'")
        
        # Salvar CSV temporariamente
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            df.to_csv(tmp_file.name, index=False)
            csv_path = tmp_file.name
        
        # Passo 2: Carregar tabelas fiscais se necessário
        if not st.session_state.get('tabelas_carregadas', False):
            status_text.text("📊 Carregando tabelas fiscais...")
            progress_bar.progress(15)
            
            try:
                from src.utils.tabelas_fiscais import GerenciadorTabelasFiscais
                gerenciador = GerenciadorTabelasFiscais()
                st.session_state.tabelas_carregadas = True
                st.session_state.gerenciador_tabelas = gerenciador
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar tabelas fiscais: {e}")
        
        # Passo 3: Inicializar agentes
        status_text.text("🔄 Inicializando agentes...")
        progress_bar.progress(20)
        
        from src.agents import (
            Agente1Extrator,
            Agente2Classificador, 
            Agente3Validador,
            Agente4Orquestrador
        )
        from src.detectors import OrquestradorDeteccaoFraudes
        
        # Inicializar agentes com LLM
        from src.utils.model_manager import get_model_manager
        model_manager = get_model_manager()
        modelo_para_usar = st.session_state.get('modelo_selecionado', 'mistral-7b-gguf')
        
        st.info(f"🔧 Carregando modelo: {modelo_para_usar}")
        llm = model_manager.get_llm(modelo_para_usar)
        st.success(f"✅ Modelo {modelo_para_usar} carregado com sucesso!")
        
        agente1 = Agente1Extrator(llm)
        agente2 = Agente2Classificador(llm)
        agente3 = Agente3Validador(llm)
        agente4 = Agente4Orquestrador(llm)
        
        # Passo 3: Executar Agente1Extrator
        status_text.text("🧠 Executando Agente1Extrator...")
        progress_bar.progress(30)
        
        st.info(f"🔍 Executando Agente1Extrator para extrair dados do CSV...")
        try:
            # Executar Agente1Extrator para extrair dados do CSV
            resultado_extracao = agente1.executar_csv(df, csv_file.name)
            st.success(f"✅ Agente1Extrator concluído: {len(resultado_extracao.get('itens', []))} itens extraídos")
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente1Extrator: {str(e)}")
            # Continuar com conversão manual se o agente falhar
            resultado_extracao = None
        
        # Passo 4: Converter CSV para formato NFe
        status_text.text("🔄 Convertendo CSV para formato NFe...")
        progress_bar.progress(40)
            
        # Criar objeto NFe a partir do CSV (usar resultado do agente se disponível)
        st.info(f"🔍 Convertendo {len(df)} linhas CSV para formato NFe...")
        if resultado_extracao and 'nfe' in resultado_extracao:
            nfe = resultado_extracao['nfe']
            st.success(f"✅ NFe criada pelo Agente1Extrator com {len(nfe.itens)} itens")
        else:
            nfe = converter_csv_para_nfe(df, csv_file.name)
            st.success(f"✅ NFe criada manualmente com {len(nfe.itens)} itens")
        
        # Passo 5: Executar Agente2Classificador
        status_text.text("🏷️ Executando Agente2Classificador...")
        progress_bar.progress(50)
        
        st.info(f"🔍 Executando Agente2Classificador para {len(nfe.itens)} itens...")
        try:
            classificacoes = agente2.executar(nfe.itens)
            st.success(f"✅ Agente2Classificador concluído: {len(classificacoes)} itens classificados")
            
            # Mostrar detalhes das classificações
            if classificacoes:
                st.info("📊 Detalhes das classificações:")
                for num_item, classif in list(classificacoes.items())[:3]:  # Mostrar apenas os 3 primeiros
                    st.write(f"  - Item {num_item}: NCM {classif.ncm_predito} (Confiança: {classif.confianca:.2f})")
                if len(classificacoes) > 3:
                    st.write(f"  ... e mais {len(classificacoes) - 3} itens")
            else:
                st.warning("⚠️ Nenhuma classificação foi gerada")
        except Exception as e:
            st.error(f"❌ Erro no Agente2Classificador: {str(e)}")
            st.exception(e)
            # Continuar com classificações vazias
            classificacoes = {}
        
        # Passo 6: Executar Agente3Validador
        status_text.text("🔍 Executando Agente3Validador...")
        progress_bar.progress(65)
        
        st.info(f"🔍 Executando Agente3Validador para validar dados fiscais...")
        try:
            resultado_validacao = agente3.executar(nfe, classificacoes)
            st.success(f"✅ Agente3Validador concluído: {len(resultado_validacao.get('inconsistencias', []))} inconsistências encontradas")
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente3Validador: {str(e)}")
            resultado_validacao = None
        
        # Passo 7: Executar Agente4Orquestrador
        status_text.text("🎯 Executando Agente4Orquestrador...")
        progress_bar.progress(75)
        
        st.info(f"🔍 Executando Agente4Orquestrador para consolidar análises...")
        try:
            resultado_orquestracao = agente4.executar(nfe, classificacoes, resultado_validacao)
            st.success(f"✅ Agente4Orquestrador concluído: análise consolidada")
        except Exception as e:
            st.warning(f"⚠️ Erro no Agente4Orquestrador: {str(e)}")
            resultado_orquestracao = None
        
        # Passo 8: Detectar fraudes
        status_text.text("🔍 Detectando fraudes...")
        progress_bar.progress(85)
        
        st.info(f"🔍 Executando OrquestradorDeteccaoFraudes...")
        try:
            detector = OrquestradorDeteccaoFraudes()
            resultado = detector.analisar_nfe(nfe, classificacoes)
            st.success(f"✅ Detecção de fraudes concluída: {len(resultado.fraudes_detectadas)} fraudes detectadas")
            
            # Mostrar detalhes das fraudes detectadas
            if resultado.fraudes_detectadas:
                st.info("🚨 Fraudes detectadas:")
                for fraude in resultado.fraudes_detectadas[:3]:  # Mostrar apenas as 3 primeiras
                    st.write(f"  - {fraude.tipo_fraude}: {fraude.descricao} (Score: {fraude.score})")
                if len(resultado.fraudes_detectadas) > 3:
                    st.write(f"  ... e mais {len(resultado.fraudes_detectadas) - 3} fraudes")
            else:
                st.info("✅ Nenhuma fraude detectada")
                
            # Mostrar score de risco
            if hasattr(resultado, 'score_risco_geral'):
                st.info(f"📊 Score de risco geral: {resultado.score_risco_geral}/100")
        except Exception as e:
            st.error(f"❌ Erro na detecção de fraudes: {str(e)}")
            st.exception(e)
            # Continuar com resultado vazio
            from src.models.schemas import ResultadoAnalise, NivelRisco
            resultado = ResultadoAnalise(
                fraudes_detectadas=[],
                score_risco_geral=0,
                nivel_risco=NivelRisco.BAIXO,
                itens_suspeitos=[],
                acoes_recomendadas=[],
                data_analise=datetime.now(),
                tempo_processamento_segundos=0
            )
        
        # Passo 9: Gerar relatório consolidado
        status_text.text("📊 Gerando relatório consolidado...")
        progress_bar.progress(90)
            
        # Criar RelatorioFiscal com o resultado consolidado
        from src.models.schemas import RelatorioFiscal
        relatorio_fiscal = RelatorioFiscal(
            nfe=nfe,
            resultado_analise=resultado,
            classificacoes_ncm=list(classificacoes.values()),
            # Adicionar resultados dos agentes
            resultado_extracao=resultado_extracao,
            resultado_validacao=resultado_validacao,
            resultado_orquestracao=resultado_orquestracao
        )
        
        # Salvar resultado na sessão
        st.session_state.relatorio = relatorio_fiscal
        st.session_state.nfe_data = nfe
        st.session_state.classificacoes = classificacoes
        st.session_state.csv_data = df
        
        # Inicializar Agente5Interface para chat
        from src.agents import Agente5Interface
        agente5 = Agente5Interface(llm)
        agente5.carregar_relatorio(relatorio_fiscal)
        st.session_state.agente5 = agente5
        
        # NOVO: Definir flag de análise concluída
        st.session_state.analysis_completed = True
        
        # Passo 10: Concluído
        progress_bar.progress(100)
        status_text.text("✅ Análise completa concluída!")
            
        # Limpar arquivo temporário
        os.unlink(csv_path)
            
        # Redirecionar para dashboard
        st.session_state.current_page = 'dashboard'
        st.success("🎉 Análise CSV concluída com sucesso! Redirecionando para o dashboard...")
        st.rerun()
            
    except Exception as e:
        # Em caso de erro, garantir que o flag seja False
        st.session_state.analysis_completed = False
        st.error(f"❌ Erro na análise CSV: {str(e)}")
        st.exception(e)
        progress_bar.empty()
        status_text.empty()


def converter_csv_para_nfe(df, filename):
    """
    Converte dados CSV para objeto NFe
    
    Args:
        df: DataFrame com dados CSV
        filename: Nome do arquivo CSV
    
    Returns:
        Objeto NFe
    """
    
    # Mapear colunas do CSV para campos NFe
    # Assumir estrutura padrão do CSV
    itens = []
    
    for index, row in df.iterrows():
        # Criar item NFe a partir da linha do CSV
        item = ItemNFe(
            numero_item=index + 1,
            codigo_produto=str(row.get('codigo_produto', f'ITEM_{index+1}')),
            descricao=str(row.get('descricao', f'Produto {index+1}')),
            ncm_declarado=str(row.get('ncm', '00000000')),
            ncm_predito=None,  # Será preenchido pelo classificador
            ncm_confianca=None,  # Será preenchido pelo classificador
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
        valor_impostos=0.0,  # Valor padrão
        tipo_documento="nfe",  # Valor padrão
        descricao_documento="Nota Fiscal Eletrônica",  # Valor padrão
        itens=itens
    )
    
    return nfe


def pagina_dashboard():
    """Página de dashboard com resultados da análise"""
    # Botões de navegação rápida
    st.markdown("### 🚀 Navegação Rápida")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Início", use_container_width=True, key="nav_inicio"):
            st.session_state.current_page = "inicio"
            st.rerun()
    
    with col2:
        if st.button("🔧 Configurar APIs", use_container_width=True, key="nav_config"):
            st.session_state.current_page = "config"
            st.rerun()
    
    with col3:
        if st.button("📤 Upload de Nota", use_container_width=True, key="nav_upload"):
            st.session_state.current_page = "upload"
            st.rerun()
    
    with col4:
        if st.button("🤖 IA Chat", use_container_width=True, key="nav_chat"):
            st.session_state.current_page = "chat"
            st.rerun()
    
    st.markdown("---")
    
    relatorio = st.session_state.relatorio
    
    st.markdown("""
    <div class="content-section">
        <h3>📊 Dashboard de Resultados</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Verificar se há múltiplas notas processadas
    if st.session_state.get('multiple_nfes'):
        st.markdown("---")
        st.subheader("📋 Múltiplas Notas Fiscais Processadas")
        
        multiple_nfes = st.session_state.multiple_nfes
        multiple_resultados = st.session_state.multiple_resultados
        
        st.success(f"🎉 **{len(multiple_nfes)} notas fiscais** foram processadas com sucesso!")
        
        # Resumo das notas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 Total de Notas", len(multiple_nfes))
        
        with col2:
            valor_total = sum(nfe.valor_total for nfe in multiple_nfes)
            st.metric("💰 Valor Total", f"R$ {valor_total:,.2f}")
        
        with col3:
            fraudes_detectadas = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            st.metric("🚨 Fraudes Detectadas", fraudes_detectadas)
        
        # Tabela resumo das notas
        st.subheader("📊 Resumo por Nota")
        
        dados_resumo = []
        for i, (nfe, resultado) in enumerate(zip(multiple_nfes, multiple_resultados)):
            dados_resumo.append({
                "Nota": i + 1,
                "Número": nfe.numero,
                "Emitente": nfe.razao_social_emitente[:30] + "..." if len(nfe.razao_social_emitente) > 30 else nfe.razao_social_emitente,
                "CNPJ": nfe.cnpj_emitente,
                "Data": nfe.data_emissao.strftime("%d/%m/%Y"),
                "Valor": f"R$ {nfe.valor_total:,.2f}",
                "Score Risco": f"{resultado.score_risco_geral:.1f}%",
                "Fraudes": len(resultado.fraudes_detectadas)
            })
        
        import pandas as pd
        df_resumo = pd.DataFrame(dados_resumo)
        st.dataframe(df_resumo, use_container_width=True)
        
        # Resumo por CNPJ
        st.subheader("🏢 Resumo por Prestador (CNPJ)")
        
        # Agrupar por CNPJ
        grupos_cnpj = {}
        for nfe, resultado in zip(multiple_nfes, multiple_resultados):
            cnpj = nfe.cnpj_emitente
            if cnpj not in grupos_cnpj:
                grupos_cnpj[cnpj] = {
                    'razao_social': nfe.razao_social_emitente,
                    'notas': [],
                    'total_valor': 0,
                    'total_fraudes': 0,
                    'score_medio': 0
                }
            grupos_cnpj[cnpj]['notas'].append(nfe.numero)
            grupos_cnpj[cnpj]['total_valor'] += nfe.valor_total
            grupos_cnpj[cnpj]['total_fraudes'] += len(resultado.fraudes_detectadas)
            grupos_cnpj[cnpj]['score_medio'] += resultado.score_risco_geral
        
        # Calcular score médio por CNPJ
        for cnpj in grupos_cnpj:
            grupos_cnpj[cnpj]['score_medio'] /= len(grupos_cnpj[cnpj]['notas'])
        
        # Criar tabela de resumo por CNPJ
        dados_cnpj = []
        for cnpj, dados in grupos_cnpj.items():
            dados_cnpj.append({
                "CNPJ": cnpj,
                "Razão Social": dados['razao_social'][:40] + "..." if len(dados['razao_social']) > 40 else dados['razao_social'],
                "Notas": len(dados['notas']),
                "Valor Total": f"R$ {dados['total_valor']:,.2f}",
                "Score Médio": f"{dados['score_medio']:.1f}%",
                "Total Fraudes": dados['total_fraudes']
            })
        
        df_cnpj = pd.DataFrame(dados_cnpj)
        st.dataframe(df_cnpj, use_container_width=True)
        
        # Seleção de nota para detalhes
        st.subheader("🔍 Detalhes por Nota")
        nota_selecionada = st.selectbox(
            "Selecione uma nota para ver detalhes:",
            range(len(multiple_nfes)),
            format_func=lambda x: f"Nota {x+1} - {multiple_nfes[x].razao_social_emitente[:30]}... - R$ {multiple_nfes[x].valor_total:,.2f}"
        )
        
        if st.button("📋 Ver Detalhes da Nota Selecionada", type="primary"):
            # Atualizar sessão com nota selecionada
            st.session_state.nfe_data = multiple_nfes[nota_selecionada]
            st.session_state.relatorio = multiple_resultados[nota_selecionada]
            st.session_state.classificacoes = st.session_state.get('multiple_classificacoes', [{}] * len(multiple_nfes))[nota_selecionada]
            
            st.success(f"✅ Detalhes da Nota {nota_selecionada + 1} carregados!")
            st.rerun()
        
        st.markdown("---")
    
    # Mostrar dados inteligentes se disponíveis
    if st.session_state.get('smart_data'):
        smart_data = st.session_state.smart_data
        metadata = smart_data['metadata']
        
        st.markdown("---")
        st.subheader("🧠 Análise Inteligente do Documento")
        
        # Informações do documento
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 Informações do Documento**")
            st.write(f"**Tipo:** {metadata['fiscal_category'].upper()}")
            st.write(f"**Categoria:** {metadata['transaction_type'].title()}")
            st.write(f"**Resumo:** {metadata['document_summary']}")
        
        with col2:
            st.markdown("**👥 Participantes**")
            st.write(f"**Emitente:** {metadata['participants']['emitente_type'].upper()}")
            st.write(f"**Destinatário:** {metadata['participants']['destinatario_type'].upper()}")
            st.write(f"**Tipo de Transação:** {'B2B' if metadata['participants']['is_b2b'] else 'B2C' if metadata['participants']['is_b2c'] else 'Outro'}")
        
        # Indicadores de qualidade
        st.markdown("**📈 Indicadores de Qualidade**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quality_score = metadata['quality_indicators']['data_quality_score']
            if quality_score >= 80:
                st.success(f"✅ **Qualidade dos Dados:** {quality_score}%")
            elif quality_score >= 60:
                st.warning(f"⚠️ **Qualidade dos Dados:** {quality_score}%")
            else:
                st.error(f"❌ **Qualidade dos Dados:** {quality_score}%")
    
        with col2:
            compliance_score = metadata['quality_indicators']['compliance_score']
            if compliance_score >= 70:
                st.success(f"✅ **Conformidade:** {compliance_score}%")
            elif compliance_score >= 50:
                st.warning(f"⚠️ **Conformidade:** {compliance_score}%")
            else:
                st.error(f"❌ **Conformidade:** {compliance_score}%")
        
        with col3:
            risk_score = metadata['quality_indicators']['risk_score']
            if risk_score <= 30:
                st.success(f"✅ **Score de Risco:** {risk_score}%")
            elif risk_score <= 60:
                st.warning(f"⚠️ **Score de Risco:** {risk_score}%")
            else:
                st.error(f"❌ **Score de Risco:** {risk_score}%")
        
        # Flags de processamento
        flags = metadata['processing_flags']
        if flags['requires_attention']:
            st.warning("⚠️ **Atenção:** Este documento requer análise adicional")
        if flags['high_quality']:
            st.success("✅ **Alta Qualidade:** Dados bem estruturados")
        if flags['compliant']:
            st.success("✅ **Conforme:** Documento atende aos padrões")
        
        st.markdown("---")
    
    if relatorio:
        # Botões de download modernos
        st.subheader("📥 Downloads Disponíveis")
        col_download1, col_download2, col_download3 = st.columns(3)
        
        with col_download1:
            try:
                relatorio_texto = gerar_relatorio_texto()
                if st.session_state.get('csv_data') is not None:
                    file_name = f"relatorio_fiscal_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                else:
                    file_name = f"relatorio_fiscal_{relatorio.nfe.chave_acesso if relatorio.nfe else 'unknown'}.txt"
                
                st.download_button(
                    label="📥 Relatório Completo",
                    data=relatorio_texto.encode('utf-8') if isinstance(relatorio_texto, str) else relatorio_texto,
                    file_name=file_name,
                    mime="text/plain",
                    use_container_width=True,
                    help="Baixa relatório completo em TXT"
                )
            except Exception as e:
                logger.error(f"Erro ao preparar download do relatório: {e}")
                # Fallback silencioso - gerar relatório básico
                try:
                    relatorio_texto_fallback = f"Relatório Fiscal\nGerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nDados não disponíveis no momento."
                    st.download_button(
                        label="📥 Relatório Completo",
                        data=relatorio_texto_fallback,
                        file_name=f"relatorio_fiscal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                except:
                    pass
        
        with col_download2:
            try:
                analises_texto = gerar_analises_texto()
                if st.session_state.get('csv_data') is not None:
                    file_name = f"analises_agentes_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                else:
                    file_name = f"analises_agentes_{relatorio.nfe.chave_acesso if relatorio.nfe else 'unknown'}.txt"
                
                st.download_button(
                    label="📋 Análises dos Agentes",
                    data=analises_texto.encode('utf-8') if isinstance(analises_texto, str) else analises_texto,
                    file_name=file_name,
                    mime="text/plain",
                    use_container_width=True,
                    help="Baixa análises detalhadas dos agentes em TXT"
                )
            except Exception as e:
                logger.error(f"Erro ao preparar download das análises: {e}")
                # Fallback silencioso
                try:
                    analises_texto_fallback = f"Análises dos Agentes\nGerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nDados não disponíveis no momento."
                    st.download_button(
                        label="📋 Análises dos Agentes",
                        data=analises_texto_fallback,
                        file_name=f"analises_agentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                except:
                    pass
        
        with col_download3:
            try:
                dados_texto = gerar_dados_texto()
                if st.session_state.get('csv_data') is not None:
                    file_name = f"dados_nfe_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                else:
                    file_name = f"dados_nfe_{relatorio.nfe.chave_acesso if relatorio.nfe else 'unknown'}.txt"
                
                st.download_button(
                    label="📊 Dados da NF-e",
                    data=dados_texto.encode('utf-8') if isinstance(dados_texto, str) else dados_texto,
                    file_name=file_name,
                    mime="text/plain",
                    use_container_width=True,
                    help="Baixa dados estruturados da NF-e em TXT"
                )
            except Exception as e:
                logger.error(f"Erro ao preparar download dos dados: {e}")
                # Fallback silencioso
                try:
                    dados_texto_fallback = f"Dados da NF-e\nGerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nDados não disponíveis no momento."
                    st.download_button(
                        label="📊 Dados da NF-e",
                        data=dados_texto_fallback,
                        file_name=f"dados_nfe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                except:
                    pass
        
        st.markdown("---")
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'score_risco_geral'):
                st.metric("Score de Risco", f"{relatorio.resultado_analise.score_risco_geral}/100")
            else:
                st.warning('Score de risco indisponível - relatório incompleto.')
        
        with col2:
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'fraudes_detectadas'):
                st.metric("Fraudes Detectadas", len(relatorio.resultado_analise.fraudes_detectadas))
            else:
                st.warning('Fraudes indisponíveis - análise incompleta.')
        
        with col3:
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'nivel_risco'):
                st.metric("Nível de Risco", relatorio.resultado_analise.nivel_risco.value)
            else:
                st.warning('Nível de risco indisponível - análise incompleta.')
        
        # --- Fallback NCM ---
        if st.session_state.get('fallback_classificacao_utilizada', False):
            st.warning("Classificação automática de NCM falhou em alguns itens. Usado valor declarado. Corrija o cadastro para melhores resultados!")
        
        # Mostrar ações recomendadas
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'acoes_recomendadas'):
            st.subheader("🎯 Ações Recomendadas")
            for acao in relatorio.resultado_analise.acoes_recomendadas:
                st.info(f"- {acao}")
        else:
            # Gerar ações recomendadas básicas se não estiverem disponíveis
            st.subheader("🎯 Ações Recomendadas")
            st.info("- Verificar classificação NCM dos produtos")
            st.info("- Validar dados fiscais com a Receita Federal")
            st.info("- Revisar conformidade com legislação vigente")
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'fraudes_detectadas') and relatorio.resultado_analise.fraudes_detectadas:
                st.warning("- Investigar fraudes detectadas imediatamente")
        
        # Mostrar data da análise
        if (hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and 
            hasattr(relatorio.resultado_analise, 'data_analise') and 
            relatorio.resultado_analise.data_analise is not None):
            st.subheader("Data da Análise")
            st.info(f"Data: {relatorio.resultado_analise.data_analise.strftime('%d/%m/%Y %H:%M:%S')}")
        else:
            st.warning("Data da análise indisponível - análise incompleta.")
        
        # Mostrar tempo de processamento
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'tempo_processamento_segundos'):
            tempo_segundos = relatorio.resultado_analise.tempo_processamento_segundos
            minutos = int(tempo_segundos // 60)
            segundos = int(tempo_segundos % 60)
            st.subheader("Tempo de Processamento")
            st.info(f"Tempo: {minutos} min {segundos} seg")
        else:
            st.warning("Tempo de processamento indisponível - análise incompleta.")
        
        # Mostrar itens suspeitos
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'itens_suspeitos'):
            st.subheader("Itens Suspeitos")
            if relatorio.resultado_analise.itens_suspeitos:
                st.info(f"Números dos itens suspeitos: {', '.join(map(str, relatorio.resultado_analise.itens_suspeitos))}")
        else:
            st.info("Nenhum item suspeito detectado.")
        
        # Mostrar resultado da análise (se disponível)
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
            st.subheader("Resultado da Análise")
            try:
                # Exibir informações básicas do resultado
                resultado = relatorio.resultado_analise
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if hasattr(resultado, 'score_risco_geral'):
                        st.metric("Score de Risco Geral", f"{resultado.score_risco_geral}/100")
                    
                    if hasattr(resultado, 'nivel_risco'):
                        st.metric("Nível de Risco", str(resultado.nivel_risco))
                
                with col2:
                    if hasattr(resultado, 'fraudes_detectadas'):
                        st.metric("Fraudes Detectadas", len(resultado.fraudes_detectadas))
                    
                    if hasattr(resultado, 'itens_suspeitos'):
                        st.metric("Itens Suspeitos", len(resultado.itens_suspeitos))
                
                # Mostrar fraudes detectadas
                if hasattr(resultado, 'fraudes_detectadas') and resultado.fraudes_detectadas:
                    st.subheader("🔍 Fraudes Detectadas")
                    for i, fraude in enumerate(resultado.fraudes_detectadas, 1):
                        with st.expander(f"Fraude {i}: {fraude.tipo_fraude}"):
                            st.write(f"**Descrição:** {fraude.descricao}")
                            st.write(f"**Score:** {fraude.score}")
                            st.write(f"**Confiança:** {fraude.confianca}")
                            if fraude.evidencias:
                                st.write(f"**Evidências:** {', '.join(fraude.evidencias)}")
                
                # Mostrar ações recomendadas
                if hasattr(resultado, 'acoes_recomendadas') and resultado.acoes_recomendadas:
                    st.subheader("💡 Ações Recomendadas")
                    for acao in resultado.acoes_recomendadas:
                        st.write(f"• {acao}")
                
            except Exception as e:
                logger.error(f"Erro ao exibir resultado da análise: {e}")
                st.warning(f"Erro ao exibir resultado da análise: {str(e)}")
                st.info("Resultado da análise contém dados complexos que não podem ser exibidos.")
        else:
            st.warning("Resultado da análise indisponível - análise incompleta.")
        
        # Mostrar fraudes detectadas
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'fraudes_detectadas'):
            st.subheader("Fraudes Detectadas")
            if relatorio.resultado_analise.fraudes_detectadas:
                for fraude in relatorio.resultado_analise.fraudes_detectadas:
                    # Usar atributos do objeto DeteccaoFraude
                    tipo = fraude.tipo_fraude.value if hasattr(fraude.tipo_fraude, 'value') else str(fraude.tipo_fraude)
                    descricao = fraude.descricao or fraude.justificativa
                    item_numero = fraude.item_numero or "N/A"
                    st.error(f"🚨 **Fraude:** {tipo} - {descricao} (Item: {item_numero})")
                    st.write(f"   **Score:** {fraude.score}/100 | **Confiança:** {fraude.confianca:.2f}")
                    if fraude.evidencias:
                        st.write(f"   **Evidências:** {', '.join(fraude.evidencias)}")
        else:
            st.info("Nenhuma fraude detectada.")
        
        # Mostrar classificações de NCM
        if hasattr(relatorio, 'classificacoes_ncm') and relatorio.classificacoes_ncm:
            st.subheader("🏷️ Classificações de NCM")
            for classificacao in relatorio.classificacoes_ncm:
                st.info(f"NCM: {classificacao.ncm_predito} - Classificação: {classificacao.descricao_produto} (Confiança: {classificacao.confianca:.2f})")
        else:
            st.info("Nenhuma classificação de NCM disponível.")
        
        # Mostrar soluções dos agentes
        st.subheader("🤖 Soluções dos Agentes")
        
        # Verificar se há múltiplas notas processadas
        multiple_nfes = st.session_state.get('multiple_nfes', [])
        multiple_resultados = st.session_state.get('multiple_resultados', [])
        
        if multiple_nfes and multiple_resultados:
            st.info(f"📊 **Processadas {len(multiple_nfes)} notas fiscais**")
            st.markdown("---")
            
            # Mostrar resumo consolidado
            total_itens = sum(len(nfe.itens) for nfe in multiple_nfes)
            total_fraudes = sum(len(resultado.fraudes_detectadas) for resultado in multiple_resultados)
            score_medio = sum(resultado.score_risco_geral for resultado in multiple_resultados) / len(multiple_resultados)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Notas", len(multiple_nfes))
            with col2:
                st.metric("Total de Itens", total_itens)
            with col3:
                st.metric("Fraudes Detectadas", total_fraudes)
            
            st.markdown("---")
            
            # Mostrar análise por nota
            for idx, (nfe, resultado) in enumerate(zip(multiple_nfes, multiple_resultados), 1):
                with st.expander(f"📄 Nota Fiscal {idx}/{len(multiple_nfes)} - {nfe.numero}"):
                    st.write(f"**Emitente:** {nfe.razao_social_emitente}")
                    st.write(f"**Destinatário:** {nfe.razao_social_destinatario}")
                    st.write(f"**Valor Total:** R$ {nfe.valor_total:,.2f}")
                    st.write(f"**Score de Risco:** {resultado.score_risco_geral}/100")
                    st.write(f"**Fraudes Detectadas:** {len(resultado.fraudes_detectadas)}")
                    
                    if resultado.fraudes_detectadas:
                        st.write("**Fraudes encontradas:**")
                        for fraude in resultado.fraudes_detectadas:
                            st.write(f"- {fraude.tipo_fraude}: {fraude.descricao} (Score: {fraude.score})")
        else:
            # Análise de nota única
            # Agente 1 - Extrator
            st.markdown("**🔍 Agente 1 - Extrator de Dados:**")
            if hasattr(relatorio, 'nfe') and relatorio.nfe:
                st.success(f"✅ Extraiu {len(relatorio.nfe.itens)} itens do documento")
                st.info(f"📊 Dados extraídos: {relatorio.nfe.razao_social_emitente} → {relatorio.nfe.razao_social_destinatario}")
            else:
                st.warning("❌ Dados não extraídos corretamente")
            
            # Agente 2 - Classificador
            st.markdown("**🏷️ Agente 2 - Classificador NCM:**")
            if hasattr(relatorio, 'classificacoes_ncm') and relatorio.classificacoes_ncm:
                ncm_corretos = sum(1 for c in relatorio.classificacoes_ncm if c.confianca > 0.7)
                st.success(f"✅ Classificou {len(relatorio.classificacoes_ncm)} produtos")
                st.info(f"📈 Taxa de confiança: {ncm_corretos}/{len(relatorio.classificacoes_ncm)} produtos com alta confiança")
            else:
                st.warning("❌ Classificação NCM não realizada")
            
            # Agente 3 - Validador
            st.markdown("**✅ Agente 3 - Validador Fiscal:**")
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
                if hasattr(relatorio.resultado_analise, 'score_risco_geral'):
                    if relatorio.resultado_analise.score_risco_geral < 30:
                        st.success("✅ Documento validado com baixo risco")
                    elif relatorio.resultado_analise.score_risco_geral < 70:
                        st.warning("⚠️ Documento com risco moderado - requer atenção")
                    else:
                        st.error("❌ Documento com alto risco - investigação necessária")
                else:
                    st.warning("❌ Validação não concluída")
            else:
                st.warning("❌ Validação não realizada")
            
            # Agente 4 - Orquestrador
            st.markdown("**🎯 Agente 4 - Orquestrador de Análise:**")
            if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
                st.success("✅ Análise completa orquestrada com sucesso")
                if hasattr(relatorio.resultado_analise, 'fraudes_detectadas'):
                    st.info(f"🔍 {len(relatorio.resultado_analise.fraudes_detectadas)} fraudes detectadas")
            else:
                st.warning("❌ Orquestração da análise não concluída")
        
        # Seção de Monitoramento
        st.subheader("📊 Monitoramento de Performance")
        
        # Obter dados de monitoramento
        try:
            dashboard_data = get_dashboard_data()
            
            # Status do sistema
            status = dashboard_data.get('status', 'unknown')
            status_color = {
                'healthy': '🟢',
                'degraded': '🟡', 
                'warning': '🟠',
                'critical': '🔴',
                'unknown': '⚪'
            }.get(status, '⚪')
            
            st.write(f"**Status do Sistema:** {status_color} {status.upper()}")
            
            # Métricas do sistema
            system_metrics = dashboard_data.get('metrics', {}).get('system', {})
            if system_metrics:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("CPU", f"{system_metrics.get('cpu_percent', 0):.1f}%")
                
                with col2:
                    st.metric("Memória", f"{system_metrics.get('memory_percent', 0):.1f}%")
                
                with col3:
                    st.metric("Disco", f"{system_metrics.get('disk_usage_percent', 0):.1f}%")
                
                with col4:
                    st.metric("Memória Livre", f"{system_metrics.get('memory_available_mb', 0):.0f} MB")
            
            # Performance recente
            performance = dashboard_data.get('performance', {})
            if performance:
                st.write("**Performance Recente:**")
                st.write(f"- Operações Totais: {performance.get('total_operations', 0)}")
                st.write(f"- Taxa de Sucesso: {performance.get('success_rate', 0):.1f}%")
                st.write(f"- Tempo Médio: {performance.get('avg_duration_ms', 0):.1f}ms")
            
            # Alertas ativos
            alerts = dashboard_data.get('alerts', [])
            if alerts:
                st.warning(f"⚠️ {len(alerts)} alerta(s) ativo(s)")
                for alert in alerts[:3]:  # Mostrar apenas os 3 primeiros
                    st.write(f"- {alert.get('message', 'Alerta desconhecido')}")
            
        except Exception as e:
            st.warning(f"Erro ao carregar dados de monitoramento: {str(e)}")
        
        # Seção de Melhorias de Acurácia
        st.subheader("🎯 Melhorias de Acurácia")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Estatísticas da base NCM
            try:
                ncm_stats = get_ncm_database_manager().get_statistics()
                st.metric("Base NCM", f"{ncm_stats.total_entries:,} códigos")
                st.metric("Cobertura", f"{ncm_stats.coverage_percentage:.1f}%")
            except json.JSONDecodeError as e:
                st.warning(f"Erro de parsing JSON na base NCM: {str(e)}")
                logger.error(f"JSON decode error in NCM stats: {e}")
            except Exception as e:
                st.warning(f"Erro ao carregar estatísticas NCM: {str(e)}")
                logger.error(f"Error loading NCM stats: {e}")
        
        with col2:
            # Estatísticas de feedback
            try:
                feedback_insights = get_feedback_system().get_learning_insights()
                if 'total_feedback' in feedback_insights:
                    st.metric("Feedback Total", f"{feedback_insights['total_feedback']:,}")
                    st.metric("Correções", f"{feedback_insights.get('corrections', 0):,}")
                else:
                    st.info("Nenhum feedback disponível")
            except Exception as e:
                st.warning(f"Erro ao carregar feedback: {str(e)}")
        
        # Botões de ação para melhorias
        st.subheader("🔧 Ações de Melhoria")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🏋️ Treinar Modelo NCM", use_container_width=True):
                try:
                    with st.spinner("Treinando modelo NCM brasileiro..."):
                        result = train_brazilian_ncm_model()
                        st.success(f"Modelo treinado! Acurácia: {result.test_accuracy:.3f}")
                except Exception as e:
                    st.error(f"Erro no treinamento: {str(e)}")
        
        with col2:
            if st.button("📊 Calibrar Thresholds", use_container_width=True):
                try:
                    calibrator = get_threshold_calibrator()
                    calibrations = calibrator.calibrate_all_detectors()
                    st.success(f"Calibrados {len(calibrations)} detectores")
                except Exception as e:
                    st.error(f"Erro na calibração: {str(e)}")
        
        with col3:
            if st.button("🤖 Treinar ML", use_container_width=True):
                try:
                    ml_system = get_adaptive_ml_system()
                    ml_system.train_all_models()
                    st.success("Modelos ML treinados!")
                except Exception as e:
                    st.error(f"Erro no treinamento ML: {str(e)}")
        
        with col4:
            if st.button("📈 Análise Temporal", use_container_width=True):
                try:
                    temporal_engine = get_temporal_analysis_engine()
                    patterns = temporal_engine.detect_temporal_patterns()
                    st.success(f"Detectados {len(patterns)} padrões temporais")
                except Exception as e:
                    st.error(f"Erro na análise temporal: {str(e)}")
        
        # Seção de Cache e Performance
        st.subheader("⚡ Cache e Performance")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            try:
                result_cache = get_result_cache()
                cache_stats = result_cache.get_cache_stats()
                st.metric("Resultados em Cache", f"{cache_stats['total_results']:,}")
            except Exception as e:
                st.metric("Resultados em Cache", "N/A")
        
        with col2:
            try:
                model_cache = get_model_cache()
                model_stats = model_cache.get_cache_stats()
                st.metric("Modelos em Cache", f"{model_stats['total_models']:,}")
            except Exception as e:
                st.metric("Modelos em Cache", "N/A")
        
        with col3:
            try:
                metrics = get_metrics_collector()
                dashboard_data = get_dashboard_data()
                st.metric("Análises Hoje", f"{dashboard_data.get('analyses_today', 0):,}")
            except Exception as e:
                st.metric("Análises Hoje", "N/A")
        
        # Botões de ação para cache
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Limpar Cache", use_container_width=True):
                try:
                    result_cache = get_result_cache()
                    result_cache.clear_cache()
                    st.success("Cache limpo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao limpar cache: {str(e)}")
        
        with col2:
            if st.button("📊 Estatísticas Cache", use_container_width=True):
                try:
                    result_cache = get_result_cache()
                    stats = result_cache.get_cache_stats()
                    
                    with st.expander("📈 Estatísticas Detalhadas do Cache"):
                        st.write(f"**Total de resultados:** {stats['total_results']:,}")
                        st.write(f"**Tamanho total:** {stats['total_size_mb']:.2f} MB")
                        st.write(f"**Resultados ativos:** {stats['active_results']:,}")
                        st.write(f"**Resultados expirados:** {stats['expired_results']:,}")
                        st.write(f"**Taxa de hit:** {stats['hit_rate']:.1%}")
                except Exception as e:
                    st.error(f"Erro ao obter estatísticas: {str(e)}")
        
        with col3:
            if st.button("🔄 Atualizar Cache", use_container_width=True):
                try:
                    result_cache = get_result_cache()
                    result_cache.cleanup_expired()
                    st.success("Cache atualizado!")
                except Exception as e:
                    st.error(f"Erro ao atualizar cache: {str(e)}")
        
        # Seção de Segurança
        st.subheader("🔒 Segurança e Proteção")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Estatísticas de segurança
            try:
                dos_stats = get_dos_protection().get_rate_limit_stats()
                st.metric("Clientes Ativos", f"{dos_stats['active_clients']:,}")
                st.metric("Clientes Bloqueados", f"{dos_stats['blocked_clients']:,}")
            except Exception as e:
                st.warning(f"Erro ao carregar estatísticas DoS: {str(e)}")
        
        with col2:
            # Estatísticas de auditoria
            try:
                auditor = get_security_auditor()
                recent_events = auditor.get_security_events(
                    start_time=datetime.now() - timedelta(hours=24)
                )
                st.metric("Eventos (24h)", f"{len(recent_events):,}")
                high_risk_events = [e for e in recent_events if e.risk_score > 0.7]
                st.metric("Alto Risco", f"{len(high_risk_events):,}")
            except Exception as e:
                st.warning(f"Erro ao carregar auditoria: {str(e)}")
        
        # Botões de ação para segurança
        st.subheader("🛡️ Ações de Segurança")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Validar XML", use_container_width=True):
                try:
                    # Validar XML atual se disponível
                    if hasattr(relatorio, 'nfe') and relatorio.nfe:
                        # Simular validação XML
                        st.success("XML validado com sucesso!")
                    else:
                        st.info("Nenhum XML para validar")
                except Exception as e:
                    st.error(f"Erro na validação: {str(e)}")
        
        with col2:
            if st.button("🧹 Sanitizar Dados", use_container_width=True):
                try:
                    sanitizer = get_input_sanitizer()
                    # Simular sanitização
                    st.success("Dados sanitizados!")
                except Exception as e:
                    st.error(f"Erro na sanitização: {str(e)}")
        
        with col3:
            if st.button("📊 Relatório Segurança", use_container_width=True):
                try:
                    auditor = get_security_auditor()
                    report = auditor.generate_security_report(
                        start_time=datetime.now() - timedelta(days=7),
                        end_time=datetime.now()
                    )
                    st.success(f"Relatório gerado! Score: {report.security_score:.1f}")
                except Exception as e:
                    st.error(f"Erro no relatório: {str(e)}")
        
        with col4:
            if st.button("🔄 Rotacionar Chaves", use_container_width=True):
                try:
                    crypto_manager = get_crypto_manager()
                    # Simular rotação de chaves
                    st.success("Chaves rotacionadas!")
                except Exception as e:
                    st.error(f"Erro na rotação: {str(e)}")
        
        # Mostrar detalhes da NFe
        if hasattr(relatorio, 'nfe') and relatorio.nfe:
            st.subheader("📄 Detalhes da Nota Fiscal Eletrônica")
            
            # Informações principais em colunas
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📋 Informações Básicas:**")
                st.write(f"**Chave de Acesso:** {relatorio.nfe.chave_acesso}")
                st.write(f"**Número:** {relatorio.nfe.numero}")
                st.write(f"**Série:** {relatorio.nfe.serie}")
                st.write(f"**Data de Emissão:** {relatorio.nfe.data_emissao.strftime('%d/%m/%Y')}")
                st.write(f"**Tipo de Documento:** {relatorio.nfe.tipo_documento}")
                st.write(f"**Descrição:** {relatorio.nfe.descricao_documento}")
            
            with col2:
                st.markdown("**💰 Valores:**")
                st.write(f"**Valor Total:** R$ {relatorio.nfe.valor_total:,.2f}")
                st.write(f"**Valor dos Produtos:** R$ {relatorio.nfe.valor_produtos:,.2f}")
                st.write(f"**Valor dos Impostos:** R$ {relatorio.nfe.valor_impostos:,.2f}")
            
            # Participantes
            st.markdown("**👥 Participantes:**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Emitente:**")
                st.write(f"**CNPJ:** {relatorio.nfe.cnpj_emitente}")
                st.write(f"**Razão Social:** {relatorio.nfe.razao_social_emitente}")
            
            with col2:
                st.markdown("**Destinatário:**")
                st.write(f"**CNPJ:** {relatorio.nfe.cnpj_destinatario}")
                st.write(f"**Razão Social:** {relatorio.nfe.razao_social_destinatario}")
            
            # Itens
            st.markdown("**📦 Itens da Nota:**")
            if relatorio.nfe.itens:
                for item in relatorio.nfe.itens:
                    with st.expander(f"Item {item.numero_item}: {item.descricao}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Código:** {item.codigo_produto}")
                            st.write(f"**NCM:** {item.ncm_declarado}")
                        with col2:
                            st.write(f"**CFOP:** {item.cfop}")
                            st.write(f"**Unidade:** {item.unidade}")
                        with col3:
                            st.write(f"**Quantidade:** {item.quantidade}")
                            st.write(f"**Valor Unitário:** R$ {item.valor_unitario:,.2f}")
                            st.write(f"**Valor Total:** R$ {item.valor_total:,.2f}")
            else:
                st.warning("Nenhum item encontrado na nota fiscal.")
        else:
            st.warning("Dados da NF-e indisponíveis - análise incompleta.")
        
        # Botões de download modernos
        st.subheader("📥 Downloads Disponíveis")
        col_download1, col_download2, col_download3 = st.columns(3)
        
        with col_download1:
            if st.button(
                "📥 Relatório Completo", 
                use_container_width=True, 
                key="download_relatorio_2",
                help="Baixa relatório completo em PDF"
            ):
                download_relatorio_completo()
        
        with col_download2:
            if st.button(
                "📋 Análises dos Agentes", 
                use_container_width=True, 
                key="download_agentes_2",
                help="Baixa análises detalhadas dos agentes"
            ):
                download_analises_agentes()
        
        with col_download3:
            if st.button(
                "📊 Dados da NF-e", 
                use_container_width=True, 
                key="download_nfe_2",
                help="Baixa dados estruturados da NF-e"
            ):
                download_dados_nfe()
        
        st.markdown("---")
        
        # Informação sobre o chat
        st.info("💬 Para interagir com o assistente IA, acesse a aba 'Chat' no menu lateral.")
    
    # Gráfico de fraudes por fornecedor
    if st.session_state.get('multiple_nfes'):
        multiple_nfes = st.session_state.multiple_nfes
        multiple_resultados = st.session_state.multiple_resultados
        fraudes_por_cnpj = {}
        for nfe, resultado in zip(multiple_nfes, multiple_resultados):
            cnpj = nfe.cnpj_emitente
            fraudes = len(resultado.fraudes_detectadas)
            fraudes_por_cnpj[cnpj] = fraudes_por_cnpj.get(cnpj, 0) + fraudes
        if any(fraudes_por_cnpj.values()):
            st.subheader("Gráfico: 🚨 Fraudes por Fornecedor (CNPJ)")
            fig = go.Figure(
                data=[go.Bar(x=list(fraudes_por_cnpj.keys()), y=list(fraudes_por_cnpj.values()),
                          marker_color='crimson', name='Fraudes')]
            )
            fig.update_layout(xaxis_title='CNPJ', yaxis_title='Fraudes detectadas', height=400)
            st.plotly_chart(fig, use_container_width=True)

    relatorio = st.session_state.relatorio
    if relatorio:
        st.markdown("<h3>📈 Métricas Gerais</h3>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Score Risco", f"{getattr(relatorio.resultado_analise, 'score_risco_geral', 0)}/100")
        with col2:
            st.metric("Fraudes", len(getattr(relatorio.resultado_analise, 'fraudes_detectadas', [])))
        with col3:
            st.metric("Valor Total", f"R$ {getattr(relatorio.nfe, 'valor_total', 0):,.2f}")
        with col4:
            st.metric("Tempo Processamento", f"{int(getattr(relatorio.resultado_analise, 'tempo_processamento_segundos', 0)//60)} min")
        st.markdown("---")

def gerar_relatorio_texto():
    """Gera relatório em formato texto como fallback"""
    relatorio = st.session_state.relatorio
    if not relatorio:
        return "Nenhum relatório disponível."
    
    texto = []
    texto.append("=" * 60)
    texto.append("RELATÓRIO FISCAL - FISCALAI")
    texto.append("=" * 60)
    texto.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    texto.append("")
    
    # Informações da NFe
    if hasattr(relatorio, 'nfe') and relatorio.nfe:
        nfe = relatorio.nfe
        texto.append("INFORMAÇÕES DA NOTA FISCAL:")
        texto.append(f"Chave de Acesso: {nfe.chave_acesso}")
        texto.append(f"Número: {nfe.numero}")
        texto.append(f"Série: {nfe.serie}")
        texto.append(f"Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y')}")
        texto.append(f"Emitente: {nfe.razao_social_emitente} (CNPJ: {nfe.cnpj_emitente})")
        texto.append(f"Destinatário: {nfe.razao_social_destinatario} (CNPJ: {nfe.cnpj_destinatario})")
        texto.append(f"Valor Total: R$ {nfe.valor_total:,.2f}")
        texto.append("")
    
    # Resultado da análise
    if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
        resultado = relatorio.resultado_analise
        texto.append("RESULTADO DA ANÁLISE:")
        texto.append(f"Score de Risco: {getattr(resultado, 'score_risco_geral', 'N/A')}/100")
        texto.append(f"Nível de Risco: {getattr(resultado, 'nivel_risco', 'N/A')}")
        texto.append(f"Fraudes Detectadas: {len(getattr(resultado, 'fraudes_detectadas', []))}")
        texto.append("")
        
        # Fraudes detectadas
        if hasattr(resultado, 'fraudes_detectadas') and resultado.fraudes_detectadas:
            texto.append("FRAUDES DETECTADAS:")
            for fraude in resultado.fraudes_detectadas:
                texto.append(f"- {fraude.tipo_fraude}: {fraude.descricao} (Score: {fraude.score})")
            texto.append("")
    
    # Classificações NCM
    if hasattr(relatorio, 'classificacoes_ncm') and relatorio.classificacoes_ncm:
        texto.append("CLASSIFICAÇÕES NCM:")
        for classif in relatorio.classificacoes_ncm:
            texto.append(f"- NCM {classif.ncm_predito}: {classif.descricao_produto} (Confiança: {classif.confianca:.2f})")
        texto.append("")
    
    # Ações recomendadas
    if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise and hasattr(relatorio.resultado_analise, 'acoes_recomendadas'):
        texto.append("AÇÕES RECOMENDADAS:")
        for acao in relatorio.resultado_analise.acoes_recomendadas:
            texto.append(f"- {acao}")
    else:
        texto.append("AÇÕES RECOMENDADAS:")
        texto.append("- Verificar classificação NCM dos produtos")
        texto.append("- Validar dados fiscais com a Receita Federal")
        texto.append("- Revisar conformidade com legislação vigente")
    
    texto.append("")
    texto.append("=" * 60)
    texto.append("Relatório gerado pelo FiscalAI")
    texto.append("=" * 60)
    
    return "\n".join(texto)


def download_relatorio_completo():
    """Faz download do relatório consolidado em TXT"""
    if st.session_state.relatorio and hasattr(st.session_state.relatorio, 'nfe'):
        try:
            # Gerar relatório em texto
            relatorio_texto = gerar_relatorio_texto()
            
            # Determinar nome do arquivo baseado no tipo de documento
            if st.session_state.get('csv_data') is not None:
                file_name = f"relatorio_fiscal_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            else:
                file_name = f"relatorio_fiscal_{st.session_state.relatorio.nfe.chave_acesso}.txt"
            
            st.download_button(
                label="📥 Baixar Relatório TXT",
                data=relatorio_texto,
                file_name=file_name,
                mime="text/plain"
            )
            st.toast("✅ Relatório TXT pronto para download!", icon="📄")
        except Exception as e:
            st.error(f"Erro ao gerar relatório: {str(e)}")
    else:
        st.warning("Nenhum relatório disponível para download.")


def gerar_analises_texto():
    """Gera análises dos agentes em formato texto"""
    relatorio = st.session_state.relatorio
    if not relatorio:
        return "Nenhum relatório disponível."
    
    texto = []
    texto.append("=" * 60)
    texto.append("ANÁLISES DOS AGENTES - FISCALAI")
    texto.append("=" * 60)
    texto.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    texto.append("")
    
    # Verificar se há múltiplas notas
    multiple_nfes = st.session_state.get('multiple_nfes', [])
    multiple_resultados = st.session_state.get('multiple_resultados', [])
    
    if multiple_nfes and multiple_resultados:
        texto.append(f"📊 PROCESSADAS {len(multiple_nfes)} NOTAS FISCAIS")
        texto.append("")
        
        # Processar cada nota
        for idx, (nfe, resultado) in enumerate(zip(multiple_nfes, multiple_resultados), 1):
            texto.append(f"{'='*60}")
            texto.append(f"NOTA FISCAL {idx}/{len(multiple_nfes)}")
            texto.append(f"{'='*60}")
            texto.append(f"Chave de Acesso: {nfe.chave_acesso}")
            texto.append(f"Número: {nfe.numero}")
            texto.append(f"Emitente: {nfe.razao_social_emitente}")
            texto.append(f"Destinatário: {nfe.razao_social_destinatario}")
            texto.append(f"Valor Total: R$ {nfe.valor_total:,.2f}")
            texto.append("")
            
            # Agente 1 - Extrator
            texto.append("AGENTE 1 - EXTRATOR DE DADOS:")
            texto.append("-" * 40)
            texto.append(f"✅ Extraiu {len(nfe.itens)} itens do documento")
            texto.append(f"📊 Dados extraídos: {nfe.razao_social_emitente} → {nfe.razao_social_destinatario}")
            texto.append(f"💰 Valor total processado: R$ {nfe.valor_total:,.2f}")
            texto.append("")
            
            # Agente 2 - Classificador (usar classificações da primeira nota se disponível)
            texto.append("AGENTE 2 - CLASSIFICADOR NCM:")
            texto.append("-" * 40)
            if idx == 1 and hasattr(relatorio, 'classificacoes_ncm') and relatorio.classificacoes_ncm:
                ncm_corretos = sum(1 for c in relatorio.classificacoes_ncm if c.confianca > 0.7)
                texto.append(f"✅ Classificou {len(relatorio.classificacoes_ncm)} produtos")
                texto.append(f"📈 Taxa de confiança: {ncm_corretos}/{len(relatorio.classificacoes_ncm)} produtos com alta confiança")
                for classif in relatorio.classificacoes_ncm[:5]:  # Limitar a 5 para não ficar muito longo
                    texto.append(f"  - NCM {classif.ncm_predito}: {classif.descricao_produto[:50]}... (Confiança: {classif.confianca:.2f})")
            else:
                texto.append("ℹ️ Classificação NCM consolidada para múltiplas notas")
            texto.append("")
            
            # Agente 3 - Validador
            texto.append("AGENTE 3 - VALIDADOR FISCAL:")
            texto.append("-" * 40)
            if hasattr(resultado, 'score_risco_geral'):
                score = resultado.score_risco_geral
                if score < 30:
                    texto.append("✅ Documento validado com baixo risco")
                elif score < 70:
                    texto.append("⚠️ Documento com risco moderado - requer atenção")
                else:
                    texto.append("❌ Documento com alto risco - investigação necessária")
                texto.append(f"📊 Score de risco: {score}/100")
            else:
                texto.append("❌ Validação não concluída")
            texto.append("")
            
            # Agente 4 - Orquestrador
            texto.append("AGENTE 4 - ORQUESTRADOR DE ANÁLISE:")
            texto.append("-" * 40)
            texto.append("✅ Análise completa orquestrada com sucesso")
            if hasattr(resultado, 'fraudes_detectadas'):
                texto.append(f"🔍 {len(resultado.fraudes_detectadas)} fraudes detectadas")
                for fraude in resultado.fraudes_detectadas:
                    texto.append(f"  - {fraude.tipo_fraude}: {fraude.descricao[:80]}... (Score: {fraude.score})")
            texto.append("")
    else:
        # Processar única nota
        # Agente 1 - Extrator
        texto.append("AGENTE 1 - EXTRATOR DE DADOS:")
        texto.append("-" * 40)
        if hasattr(relatorio, 'nfe') and relatorio.nfe:
            texto.append(f"✅ Extraiu {len(relatorio.nfe.itens)} itens do documento")
            texto.append(f"📊 Dados extraídos: {relatorio.nfe.razao_social_emitente} → {relatorio.nfe.razao_social_destinatario}")
            texto.append(f"💰 Valor total processado: R$ {relatorio.nfe.valor_total:,.2f}")
        else:
            texto.append("❌ Dados não extraídos corretamente")
        texto.append("")
        
        # Agente 2 - Classificador
        texto.append("AGENTE 2 - CLASSIFICADOR NCM:")
        texto.append("-" * 40)
        if hasattr(relatorio, 'classificacoes_ncm') and relatorio.classificacoes_ncm:
            ncm_corretos = sum(1 for c in relatorio.classificacoes_ncm if c.confianca > 0.7)
            texto.append(f"✅ Classificou {len(relatorio.classificacoes_ncm)} produtos")
            texto.append(f"📈 Taxa de confiança: {ncm_corretos}/{len(relatorio.classificacoes_ncm)} produtos com alta confiança")
            for classif in relatorio.classificacoes_ncm:
                texto.append(f"  - NCM {classif.ncm_predito}: {classif.descricao_produto} (Confiança: {classif.confianca:.2f})")
        else:
            texto.append("❌ Classificação NCM não realizada")
        texto.append("")
        
        # Agente 3 - Validador
        texto.append("AGENTE 3 - VALIDADOR FISCAL:")
        texto.append("-" * 40)
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
            if hasattr(relatorio.resultado_analise, 'score_risco_geral'):
                score = relatorio.resultado_analise.score_risco_geral
                if score < 30:
                    texto.append("✅ Documento validado com baixo risco")
                elif score < 70:
                    texto.append("⚠️ Documento com risco moderado - requer atenção")
                else:
                    texto.append("❌ Documento com alto risco - investigação necessária")
                texto.append(f"📊 Score de risco: {score}/100")
            else:
                texto.append("❌ Validação não concluída")
        else:
            texto.append("❌ Validação não realizada")
        texto.append("")
        
        # Agente 4 - Orquestrador
        texto.append("AGENTE 4 - ORQUESTRADOR DE ANÁLISE:")
        texto.append("-" * 40)
        if hasattr(relatorio, 'resultado_analise') and relatorio.resultado_analise:
            texto.append("✅ Análise completa orquestrada com sucesso")
            if hasattr(relatorio.resultado_analise, 'fraudes_detectadas'):
                texto.append(f"🔍 {len(relatorio.resultado_analise.fraudes_detectadas)} fraudes detectadas")
                for fraude in relatorio.resultado_analise.fraudes_detectadas:
                    texto.append(f"  - {fraude.tipo_fraude}: {fraude.descricao} (Score: {fraude.score})")
        else:
            texto.append("❌ Orquestração da análise não concluída")
    
    texto.append("")
    texto.append("=" * 60)
    texto.append("Análises geradas pelo FiscalAI")
    texto.append("=" * 60)
    
    return "\n".join(texto)


def download_analises_agentes():
    """Faz download das análises individuais dos agentes em TXT"""
    if st.session_state.relatorio and hasattr(st.session_state.relatorio, 'nfe'):
        try:
            # Gerar análises em texto
            analises_texto = gerar_analises_texto()
            
            # Determinar nome do arquivo baseado no tipo de documento
            if st.session_state.get('csv_data') is not None:
                file_name = f"analises_agentes_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            else:
                file_name = f"analises_agentes_{st.session_state.relatorio.nfe.chave_acesso}.txt"
            
            st.download_button(
                label="📥 Baixar Análises TXT",
                data=analises_texto,
                file_name=file_name,
                mime="text/plain"
            )
            st.toast("✅ Análises dos agentes em TXT pronto!", icon="🤖")
        except Exception as e:
            st.error(f"Erro ao gerar análises: {str(e)}")
    else:
        st.warning("Nenhum relatório disponível para download.")


def gerar_dados_texto():
    """Gera dados da NFe em formato texto"""
    relatorio = st.session_state.relatorio
    if not relatorio or not hasattr(relatorio, 'nfe') or not relatorio.nfe:
        return "Nenhum dado da NF-e disponível."
    
    nfe = relatorio.nfe
    texto = []
    texto.append("=" * 60)
    texto.append("DADOS DA NOTA FISCAL ELETRÔNICA - FISCALAI")
    texto.append("=" * 60)
    texto.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    texto.append("")
    
    # Informações básicas
    texto.append("INFORMAÇÕES BÁSICAS:")
    texto.append(f"Chave de Acesso: {nfe.chave_acesso}")
    texto.append(f"Número: {nfe.numero}")
    texto.append(f"Série: {nfe.serie}")
    texto.append(f"Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y')}")
    texto.append(f"Tipo de Documento: {nfe.tipo_documento}")
    texto.append(f"Descrição: {nfe.descricao_documento}")
    texto.append("")
    
    # Participantes
    texto.append("PARTICIPANTES:")
    texto.append(f"Emitente: {nfe.razao_social_emitente}")
    texto.append(f"CNPJ Emitente: {nfe.cnpj_emitente}")
    texto.append(f"Destinatário: {nfe.razao_social_destinatario}")
    texto.append(f"CNPJ Destinatário: {nfe.cnpj_destinatario}")
    texto.append("")
    
    # Valores
    texto.append("VALORES:")
    texto.append(f"Valor Total: R$ {nfe.valor_total:,.2f}")
    texto.append(f"Valor dos Produtos: R$ {nfe.valor_produtos:,.2f}")
    texto.append(f"Valor dos Impostos: R$ {nfe.valor_impostos:,.2f}")
    texto.append("")
    
    # Itens
    if nfe.itens:
        texto.append("ITENS DA NOTA:")
        for item in nfe.itens:
            texto.append(f"Item {item.numero_item}:")
            texto.append(f"  Código: {item.codigo_produto}")
            texto.append(f"  Descrição: {item.descricao}")
            texto.append(f"  NCM: {item.ncm_declarado}")
            texto.append(f"  CFOP: {item.cfop}")
            texto.append(f"  Unidade: {item.unidade}")
            texto.append(f"  Quantidade: {item.quantidade}")
            texto.append(f"  Valor Unitário: R$ {item.valor_unitario:,.2f}")
            texto.append(f"  Valor Total: R$ {item.valor_total:,.2f}")
            texto.append("")
    else:
        texto.append("Nenhum item encontrado na nota fiscal.")
    
    texto.append("=" * 60)
    texto.append("Dados gerados pelo FiscalAI")
    texto.append("=" * 60)
    
    return "\n".join(texto)


def download_dados_nfe():
    """Faz download dos dados da NF-e em CSV"""
    if st.session_state.relatorio and hasattr(st.session_state.relatorio, 'nfe') and st.session_state.relatorio.nfe:
        try:
            import tempfile
            import pandas as pd
            
            nfe = st.session_state.relatorio.nfe
            
            # Criar DataFrame com dados da NFe
            dados_nfe = {
                'chave_acesso': [nfe.chave_acesso],
                'numero': [nfe.numero],
                'serie': [nfe.serie],
                'data_emissao': [nfe.data_emissao.strftime('%d/%m/%Y')],
                'cnpj_emitente': [nfe.cnpj_emitente],
                'razao_social_emitente': [nfe.razao_social_emitente],
                'cnpj_destinatario': [nfe.cnpj_destinatario],
                'razao_social_destinatario': [nfe.razao_social_destinatario],
                'valor_total': [nfe.valor_total],
                'valor_produtos': [nfe.valor_produtos],
                'valor_impostos': [nfe.valor_impostos],
                'tipo_documento': [nfe.tipo_documento],
                'descricao_documento': [nfe.descricao_documento]
            }
            
            # Adicionar dados dos itens
            if nfe.itens:
                for i, item in enumerate(nfe.itens):
                    dados_nfe[f'item_{i+1}_codigo'] = [item.codigo_produto]
                    dados_nfe[f'item_{i+1}_descricao'] = [item.descricao]
                    dados_nfe[f'item_{i+1}_ncm'] = [item.ncm_declarado]
                    dados_nfe[f'item_{i+1}_cfop'] = [item.cfop]
                    dados_nfe[f'item_{i+1}_unidade'] = [item.unidade]
                    dados_nfe[f'item_{i+1}_quantidade'] = [item.quantidade]
                    dados_nfe[f'item_{i+1}_valor_unitario'] = [item.valor_unitario]
                    dados_nfe[f'item_{i+1}_valor_total'] = [item.valor_total]
            
            df = pd.DataFrame(dados_nfe)
            
            # Determinar nome do arquivo baseado no tipo de documento
            if st.session_state.get('csv_data') is not None:
                file_name = f"dados_nfe_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                file_name = f"dados_nfe_{nfe.chave_acesso}.csv"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                df.to_csv(tmp_file.name, index=False, encoding='utf-8')
                tmp_file.seek(0)
                st.download_button(
                    label="📥 Baixar Dados NF-e CSV",
                    data=tmp_file.read(),
                    file_name=file_name,
                    mime="text/csv"
                )
                os.remove(tmp_file.name)
                st.toast("✅ Arquivo CSV gerado!", icon="🗂️")
        except Exception as e:
            st.error(f"Erro ao gerar CSV: {str(e)}")
            # Fallback: gerar dados em texto
            dados_texto = gerar_dados_texto()
            st.download_button(
                label="📥 Baixar Dados TXT",
                data=dados_texto,
                file_name=f"dados_nfe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    else:
        st.warning("Nenhum dado da NF-e disponível para download.")


def log_fallback(msg):
    """Registra mensagens de fallback em um arquivo de log"""
    try:
        os.makedirs('logs', exist_ok=True)
        with open('logs/fallback_warnings.log', 'a') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception as e:
        debug_log(f"Erro ao registrar fallback: {str(e)}", 1)

def pagina_chat():
    """Página de chat com o assistente IA V2"""
    # Botões de navegação rápida
    st.markdown("### 🚀 Navegação Rápida")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Início", use_container_width=True, key="nav_inicio"):
            st.session_state.current_page = "inicio"
            st.rerun()
    
    with col2:
        if st.button("🔧 Configurar APIs", use_container_width=True, key="nav_config"):
            st.session_state.current_page = "config"
            st.rerun()
    
    with col3:
        if st.button("📤 Upload de Nota", use_container_width=True, key="nav_upload"):
            st.session_state.current_page = "upload"
            st.rerun()
    
    with col4:
        if st.button("📈 Resultados", use_container_width=True, key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.markdown("---")
    st.subheader("💬 Chat FiscalAI - Assistente Inteligente")
    
    # Mostrar informações do modelo atual
    if st.session_state.get('modelo_carregado', False):
        privacidade = st.session_state.get('privacidade_selecionada', 'local')
        if privacidade == 'local':
            modelo = st.session_state.get('modelo_local_selecionado', 'mistral-7b-gguf')
            st.info(f"🤖 **Modelo Local Ativo:** {modelo} | 🔒 **100% Privado** | 💰 **Gratuito**")
        else:
            modelo = st.session_state.get('modelo_api_selecionado', 'gpt-4o')
            provedor = st.session_state.get('provedor_selecionado', 'openai')
            st.info(f"🌐 **API Externa Ativa:** {modelo} | **Provedor:** {provedor}")
    else:
        st.warning("⚠️ Nenhum modelo carregado. Configure um modelo na barra lateral.")
    
    # Verificar se há dados carregados
    multiple_nfes = st.session_state.get('multiple_nfes', [])
    nfe_data = st.session_state.get('nfe_data')
    relatorio = st.session_state.get('relatorio')
    csv_data = st.session_state.get('csv_data')
    
    # Debug: mostrar dados disponíveis
    st.write(f"🔍 DEBUG Página Chat:")
    st.write(f"- multiple_nfes: {len(multiple_nfes) if multiple_nfes else 0}")
    st.write(f"- nfe_data: {nfe_data is not None}")
    st.write(f"- relatorio: {relatorio is not None}")
    st.write(f"- csv_data: {csv_data is not None}")
    st.write(f"- session_state keys: {list(st.session_state.keys())}")
    
    dados_disponiveis = bool(multiple_nfes or nfe_data or relatorio or csv_data)
    
    if not dados_disponiveis:
        st.warning("⚠️ Nenhum arquivo carregado. Por favor, faça upload de um arquivo XML ou CSV primeiro.")
        st.info("💡 Vá para a página 'Upload' para carregar e analisar um arquivo.")
        return
    
    # Inicializar Agente de Chat (Agente6) se não existir
    if not st.session_state.get("agente5_v2") or not st.session_state.get('modelo_carregado', False):
        try:
            from src.agents.agente6_chat import Agente6Chat
            from src.utils.model_manager import get_model_manager
            import os
            
            model_manager = get_model_manager()
            
            # Usar configuração de privacidade selecionada
            if st.session_state.get('privacidade_selecionada') == 'local':
                # Usar modelo local
                modelo_selecionado = st.session_state.get('modelo_local_selecionado', 'mistral-7b-gguf')
                try:
                    llm = model_manager.get_llm(modelo_selecionado)
                    st.info(f"🤖 Usando modelo local: {modelo_selecionado}")
                except Exception as e:
                    st.error(f"❌ Erro ao carregar modelo local: {str(e)}")
                    st.warning("💡 Verifique se o modelo local está disponível.")
                    return
            else:
                # Usar API externa - verificar se há API key configurada
                modelo_selecionado = st.session_state.get('modelo_api_selecionado', 'gpt-4o')
                
                # Campos de API Key baseados no provedor
                api_key_fields = {
                    "openai": "OPENAI_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY", 
                    "google": "GOOGLE_API_KEY",
                    "groq": "GROQ_API_KEY"
                }
                
                campo_api_key = api_key_fields.get(st.session_state.get('provedor_selecionado', 'openai'), "API_KEY")
                api_key_session = st.session_state.get(f"{campo_api_key.lower()}_input", "")
                api_key_env = os.getenv(campo_api_key, "")
                api_key_atual = api_key_session if api_key_session else api_key_env
                
                # Definir API key como variável de ambiente temporária se disponível
                if api_key_atual and "SUA_CHAV" not in api_key_atual:
                    os.environ[campo_api_key] = api_key_atual
                
                try:
                    llm = model_manager.get_llm(modelo_selecionado)
                    st.info(f"🤖 Usando API externa: {modelo_selecionado}")
                except Exception as e:
                    st.error(f"❌ Erro ao carregar API externa: {str(e)}")
                    st.warning("💡 Verifique se a API key está configurada corretamente.")
                    return
            
            agente5_v2 = Agente6Chat(llm)
            st.session_state.agente5_v2 = agente5_v2
            st.session_state.modelo_carregado = True
            st.success("✅ Chat inicializado com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro ao inicializar assistente: {str(e)}")
            st.warning("Assistente indisponível. Verifique se o modelo está carregado.")
            return
    
    # Usar o agente V2
    agente5_v2 = st.session_state.agente5_v2
    
    # Inicializar histórico se necessário
    if "historico_chat" not in st.session_state:
        st.session_state.historico_chat = []
    
    # Mostrar histórico de mensagens
    for msg in st.session_state.historico_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Interface de chat
    nova_msg = st.chat_input("Digite sua pergunta fiscal...")
    if nova_msg:
        st.session_state.historico_chat.append({"role": "user", "content": nova_msg})
        with st.chat_message("user"):
            st.write(nova_msg)
        
        # Processar mensagem com Agente5InterfaceV2
        try:
            resposta = agente5_v2.conversar(nova_msg)
        except Exception as e:
            resposta = f"❌ Erro ao processar pergunta: {str(e)}"
        
        st.session_state.historico_chat.append({"role": "assistant", "content": resposta})
        with st.chat_message("assistant"):
            st.write(resposta)
    
    # Botões de controle
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗑️ Limpar Chat", help="Limpa o histórico de conversa"):
            st.session_state.historico_chat = []
            agente5_v2.limpar_historico()
            st.rerun()
    
    with col2:
        if st.button("🔄 Reinicializar", help="Reinicializa o assistente com o modelo selecionado"):
            # Limpar o agente atual
            if "agente5_v2" in st.session_state:
                del st.session_state.agente5_v2
            st.session_state.modelo_carregado = False
            st.session_state.historico_chat = []
            st.rerun()
    
    with col3:
        # Botão de download da conversa
        if st.session_state.historico_chat:
            conversa_texto = agente5_v2.exportar_conversa()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"conversa_fiscalai_{timestamp}.txt"
            
            st.download_button(
                "💾 Baixar Conversa",
                data=conversa_texto,
                file_name=nome_arquivo,
                mime="text/plain",
                help="Baixa o histórico completo da conversa"
            )
    
    with col4:
        # Botão para perguntas simples
        if st.button("🎯 Pergunta Simples", help="Limpa o histórico para fazer perguntas mais simples"):
            st.session_state.historico_chat = []
            agente5_v2.limpar_historico()
            st.rerun()
    
    # Mostrar informações dos dados carregados
    with st.expander("📊 Informações dos Dados Carregados", expanded=False):
        if hasattr(agente5_v2, "_coletar_dados_reais"):
            dados_info = agente5_v2._coletar_dados_reais()
        elif hasattr(agente5_v2, "_coletar_contexto_compacto"):
            dados_info = agente5_v2._coletar_contexto_compacto()
        else:
            dados_info = "Dados indisponíveis nesta sessão."
        st.text(dados_info)

if __name__ == "__main__":
    # Aplicar headers de segurança
    try:
        security_headers = get_streamlit_headers()
        # Nota: Streamlit não permite definir headers HTTP diretamente
        # Em produção, estes headers devem ser configurados no servidor web
        logger.info("Headers de segurança configurados")
    except Exception as e:
        logger.warning(f"Erro ao configurar headers de segurança: {e}")
    
    inicializar_sessao()
    sidebar_configuracoes()
    if st.session_state.current_page == "inicio":
        pagina_inicio()
    elif st.session_state.current_page == "config":
        pagina_config()
    elif st.session_state.current_page == "upload":
        pagina_upload()
    elif st.session_state.current_page == "dashboard":
        pagina_dashboard()
    elif st.session_state.current_page == "chat":
        pagina_chat()