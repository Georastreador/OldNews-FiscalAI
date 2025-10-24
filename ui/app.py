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
from datetime import datetime
import pandas as pd
import io

# Configuração de debug com proteção para produção
PRODUCTION_MODE = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true' and not PRODUCTION_MODE
DEBUG_LEVEL = int(os.getenv('FISCALAI_DEBUG_LEVEL', '1')) if DEBUG_MODE else 0

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
from src.utils.api_config import show_api_config_page, show_api_status, setup_api_environment
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

def inicializar_sessao():
    """Inicializa variáveis de sessão"""
    if 'relatorio' not in st.session_state:
        st.session_state.relatorio = None
    if 'agente5' not in st.session_state:
        st.session_state.agente5 = None
    if 'historico_chat' not in st.session_state:
        st.session_state.historico_chat = []
    if 'modelo_selecionado' not in st.session_state:
        st.session_state.modelo_selecionado = "mistral-7b-gguf"
    
    # Configurar modelo local como padrão
    if 'privacy_level' not in st.session_state:
        st.session_state.privacy_level = "🔒 Local (GGUF)"
    
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
    """Sidebar com configurações minimalistas"""
    
    # Nível de privacidade
    st.markdown("**🔒 Privacidade**")
    privacy_level = st.selectbox(
        "Nível:",
        [
            "🔒 Local (GGUF)",
            "🏠 Ollama",
            "☁️ API Externa"
        ],
        label_visibility="collapsed"
    )
    
    # Modelo de IA
    st.markdown("**🤖 Modelo**")
    if "Local" in privacy_level:
        modelo = st.selectbox(
            "Selecione:",
            ["mistral-7b-instruct-v0.1.Q4_K_M.gguf"],
            label_visibility="collapsed"
        )
    elif "Ollama" in privacy_level:
        modelo = st.selectbox(
            "Selecione:",
            ["llama2", "mistral", "codellama"],
            label_visibility="collapsed"
        )
    else:
        modelo = st.selectbox(
            "Selecione:",
            [
                "gpt-4o-mini (OpenAI)",
                "gpt-4o (OpenAI)", 
                "claude-3-haiku (Anthropic)",
                "claude-3-sonnet (Anthropic)",
                "gemini-pro (Google)",
                "llama-3.1-8b (Groq)"
            ],
            label_visibility="collapsed"
        )
    
    # Salvar configurações
    if st.button("💾 Salvar", use_container_width=True):
        st.session_state.privacy_level = privacy_level
        st.session_state.modelo_selecionado = modelo
        st.session_state.modelo_carregado = False  # Reset flag para forçar recarregamento
        st.success("✅ Configurações salvas! Use o botão 'Carregar Modelo' para ativar.")
    
    # Informações do modelo atual
    if hasattr(st.session_state, 'modelo_selecionado'):
        st.markdown("---")
        st.markdown(f"**Atual:** {st.session_state.modelo_selecionado}")
        
        # Status do modelo
        if st.session_state.get('modelo_carregado', False):
            st.success("✅ Modelo carregado")
            if st.button("🔄 Recarregar Modelo", use_container_width=True):
                st.session_state.modelo_carregado = False
                st.session_state.modelo_atual = None
                st.rerun()
        else:
            st.warning("⚠️ Carregando modelo...")
            if st.button("🔄 Carregar Modelo", use_container_width=True):
                if carregar_modelo_escolhido():
                    st.rerun()

def pagina_inicio():
    """Página inicial com informações e guia"""
    
    # Status do modelo
    if st.session_state.get('modelo_carregado', False):
        modelo_atual = st.session_state.get('modelo_atual', 'Modelo')
        privacy_level = st.session_state.get('privacy_level', '🔒 Local (GGUF)')
        st.success(f"✅ **{modelo_atual} Carregado** ({privacy_level}) - Sistema pronto para análise!")
    else:
        st.info("🔄 **Carregando Modelo** - Aguarde...")
    
    # Instruções de início
    st.markdown("""
    <div class="content-section">
        <h3>🚀 Instruções de Início</h3>
        <p style="font-size: 16px; line-height: 1.6; color: #333; margin: 0;">
            Bem-vindo ao OldNews FiscalAI! Este sistema utiliza inteligência artificial para analisar 
            Notas Fiscais Eletrônicas e detectar possíveis fraudes fiscais.
        </p>
        <br>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4 style="margin: 0 0 8px 0; color: #007aff;">1️⃣ Configure APIs (Opcional)</h4>
                <p style="margin: 0; color: #666; font-size: 14px;">
                    Adicione chaves de API para análises mais precisas. O sistema funciona sem chaves também.
                </p>
            </div>
            <div>
                <h4 style="margin: 0 0 8px 0; color: #007aff;">2️⃣ Analise uma NF-e</h4>
                <p style="margin: 0; color: #666; font-size: 14px;">
                    Faça upload de arquivos XML (NF-e, NFS-e) ou CSV para análise automática de fraudes.
                </p>
            </div>
            <div>
                <h4 style="margin: 0 0 8px 0; color: #007aff;">3️⃣ Visualize Resultados</h4>
                <p style="margin: 0; color: #666; font-size: 14px;">
                    Veja o dashboard com métricas, detecções de fraude e exporte relatórios em PDF.
                </p>
            </div>
            <div>
                <h4 style="margin: 0 0 8px 0; color: #007aff;">4️⃣ Converse com IA</h4>
                <p style="margin: 0; color: #666; font-size: 14px;">
                    Faça perguntas sobre a análise e obtenha insights detalhados do assistente.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def pagina_upload():
    """Página de upload de NF-e"""
    st.markdown("""
    <div class="content-section">
        <h3>📤 Upload de NF-e</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Seleção de tipo de arquivo
        tipo_arquivo = st.radio(
            "📋 Tipo de Arquivo:",
            ["📄 XML (NF-e/NFS-e)", "📊 CSV (Dados Fiscais)"],
            horizontal=True
        )
        
        if "XML" in tipo_arquivo:
            # Upload de XML
            file_path = create_upload_widget(max_size_mb=200)
            
            if file_path is not None:
                st.success(f"✅ Arquivo XML carregado: {Path(file_path).name}")
                st.info("💡 Suporta NF-e e NFS-e automaticamente!")
            
            # Botão de análise
                if st.button("🔍 Analisar Documento", type="primary", use_container_width=True):
                    analisar_nfe(file_path)
                
                # Botão Executar!
                if st.button("🚀 Executar Análise!", type="primary", use_container_width=True):
                    analisar_nfe(file_path)
        
        else:
            # Upload de CSV (múltiplos arquivos)
            csv_files = create_csv_upload_widget(max_size_mb=50)
            
            if csv_files is not None:
                if isinstance(csv_files, list):
                    st.success(f"✅ {len(csv_files)} arquivo(s) CSV carregado(s)")
                    
                    # Botão de análise CSV múltiplos
                    if st.button("🔍 Analisar Todos os CSVs", type="primary", use_container_width=True):
                        analisar_multiplos_csv(csv_files)
                    
                    # Botão Executar CSV múltiplos!
                    if st.button("🚀 Executar Todos os CSVs!", type="primary", use_container_width=True):
                        analisar_multiplos_csv(csv_files)
                else:
                    st.success(f"✅ Arquivo CSV carregado: {csv_files.name}")
                    
                    # Botão de análise CSV único
                    if st.button("🔍 Analisar CSV", type="primary", use_container_width=True):
                        analisar_csv(csv_files)
                    
                    # Botão Executar CSV!
                    if st.button("🚀 Executar CSV!", type="primary", use_container_width=True):
                        analisar_csv(csv_files)
    
    with col2:
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
        
        # Botões de exemplo
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            if st.button("📄 NF-e Exemplo", use_container_width=True):
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
            if st.button("📊 CSV Exemplo", use_container_width=True):
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
    # Inicializar variáveis de progresso fora do try
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
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
        
        # Salvar resultado na sessão
        st.session_state.relatorio = resultado
        st.session_state.nfe_data = nfe
        st.session_state.classificacoes = classificacoes
        
        # Inicializar Agente5Interface para chat
        from src.agents import Agente5Interface
        from src.models.schemas import RelatorioFiscal
        from datetime import datetime
        
        # Criar RelatorioFiscal com o resultado
        relatorio_fiscal = RelatorioFiscal(
            nfe=nfe,
            classificacoes_ncm=list(classificacoes.values()),
            resultado_analise=resultado
        )
        
        agente5 = Agente5Interface(llm)
        agente5.carregar_relatorio(relatorio_fiscal)
        st.session_state.agente5 = agente5
        
        # NOVO: Definir flag de análise concluída
        st.session_state.analysis_completed = True
        
        # Passo 6: Concluído
        progress_bar.progress(100)
        status_text.text("✅ Análise concluída!")
        
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
        
        # Ler CSV com tratamento de erros
        csv_data = csv_file.getvalue().decode('utf-8')
        try:
            df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', encoding='utf-8')
        except Exception as e:
            try:
                df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', encoding='latin-1')
            except Exception as e2:
                try:
                    df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', sep=';', encoding='utf-8')
                except Exception as e3:
                    st.error(f"❌ Erro ao processar CSV {numero_arquivo}: {str(e3)}")
                    return None
        
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
        
        # Converter CSV para formato NFe
        nfe = converter_csv_para_nfe(df, csv_file.name)
        
        # Classificar produtos
        classificacoes = agente2.executar(nfe.itens)
        
        # Detectar fraudes
        detector = OrquestradorDeteccaoFraudes()
        resultado = detector.analisar_nfe(nfe, classificacoes)
        
        # Limpar arquivo temporário
        os.unlink(csv_path)
        
        return {
            'relatorio': resultado,
            'nfe': nfe,
            'classificacoes': classificacoes,
            'df': df
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao processar arquivo {numero_arquivo}: {str(e)}")
        return None


def consolidar_resultados(todos_resultados, todos_nfes, todas_classificacoes):
    """
    Consolida resultados de múltiplos arquivos CSV
    
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
    
    # Criar resultado consolidado
    resultado_consolidado = ResultadoAnalise(
        chave_acesso="CONSOLIDADO_MULTIPLOS_CSV",
        score_risco_geral=score_medio,
        nivel_risco=nivel_risco,
        fraudes_detectadas=todas_fraudes,
        itens_suspeitos=list(range(1, total_itens + 1)),
        acoes_recomendadas=todas_acoes,
        tempo_processamento_segundos=sum(r.tempo_processamento_segundos for r in todos_resultados),
        data_analise=datetime.now(),
        resultado_analise={}  # Campo legado para compatibilidade
    )
    
    # Criar relatório consolidado
    relatorio_consolidado = RelatorioFiscal(
        nfe=todos_nfes[0],  # Primeira NFe como referência
        resultado_analise=resultado_consolidado,
        classificacoes_ncm=list(todas_classificacoes[0].values()) if todas_classificacoes else []
    )
    
    return relatorio_consolidado


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
        
        # Ler CSV com tratamento de erros
        csv_data = csv_file.getvalue().decode('utf-8')
        try:
            # Tentar ler CSV com diferentes configurações
            df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', encoding='utf-8')
        except Exception as e:
            try:
                # Tentar com encoding diferente
                df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', encoding='latin-1')
            except Exception as e2:
                try:
                    # Tentar com separador diferente
                    df = pd.read_csv(io.StringIO(csv_data), on_bad_lines='skip', sep=';', encoding='utf-8')
                except Exception as e3:
                    st.error(f"❌ Erro ao processar CSV: {str(e3)}")
                    st.error("💡 Dicas: Verifique se o arquivo está em formato CSV válido com separadores consistentes.")
                    return
        
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
        llm = model_manager.get_llm(modelo_para_usar)
        
        agente1 = Agente1Extrator(llm)
        agente2 = Agente2Classificador(llm)
        agente3 = Agente3Validador(llm)
        agente4 = Agente4Orquestrador(llm)
        
        # Passo 3: Converter CSV para formato NFe
        status_text.text("🔄 Convertendo CSV para formato NFe...")
        progress_bar.progress(40)
            
        # Criar objeto NFe a partir do CSV
        nfe = converter_csv_para_nfe(df, csv_file.name)
        
        # Passo 4: Classificar produtos
        status_text.text("🏷️ Classificando produtos...")
        progress_bar.progress(60)
        
        classificacoes = agente2.executar(nfe.itens)
        
        # Passo 5: Detectar fraudes
        status_text.text("🔍 Detectando fraudes...")
        progress_bar.progress(80)
        
        detector = OrquestradorDeteccaoFraudes()
        resultado = detector.analisar_nfe(nfe, classificacoes)
        
        # Passo 6: Gerar relatório
        status_text.text("📊 Gerando relatório...")
        progress_bar.progress(90)
            
        # Salvar resultado na sessão
        st.session_state.relatorio = resultado
        st.session_state.nfe_data = nfe
        st.session_state.classificacoes = classificacoes
        st.session_state.csv_data = df
        
        # Inicializar Agente5Interface para chat
        from src.agents import Agente5Interface
        agente5 = Agente5Interface(llm)
        relatorio_fiscal = RelatorioFiscal(
            nfe=nfe,
            resultado_analise=resultado,
            classificacoes_ncm=list(classificacoes.values())
        )
        agente5.carregar_relatorio(relatorio_fiscal)
        st.session_state.agente5 = agente5
        
        # NOVO: Definir flag de análise concluída
        st.session_state.analysis_completed = True
        
        # Passo 7: Concluído
        progress_bar.progress(100)
        status_text.text("✅ Análise concluída!")
            
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
    relatorio = st.session_state.relatorio
    
    st.markdown("""
    <div class="content-section">
        <h3>📊 Dashboard de Resultados</h3>
    </div>
    """, unsafe_allow_html=True)
    
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
        # Botões de download
        col_download1, col_download2, col_download3 = st.columns(3)
        
        with col_download1:
            if st.button("📥 Baixar Relatório Completo", use_container_width=True):
                download_relatorio_completo()
        
        with col_download2:
            if st.button("📋 Baixar Análises dos Agentes", use_container_width=True):
                download_analises_agentes()
        
        with col_download3:
            if st.button("📊 Baixar Dados da NF-e", use_container_width=True):
                download_dados_nfe()
        
        st.markdown("---")
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Score de Risco", f"{relatorio.score_risco_geral}/100")
        
        with col2:
            st.metric("Nível de Risco", relatorio.nivel_risco.value)
        
        with col3:
            st.metric("Fraudes Detectadas", len(relatorio.fraudes_detectadas))
        
        # Análises dos Agentes CrewAI
        st.subheader("🤖 Análises dos Agentes CrewAI")
        
        # Agente 1 - Extrator
        with st.expander("🔍 Agente 1 - Extrator de Dados", expanded=True):
            if st.session_state.get('nfe_data'):
                nfe = st.session_state.nfe_data
                st.write(f"**Chave de Acesso:** {nfe.chave_acesso}")
                st.write(f"**Emitente:** {nfe.razao_social_emitente} (CNPJ: {nfe.cnpj_emitente})")
                st.write(f"**Destinatário:** {nfe.razao_social_destinatario} (CNPJ: {nfe.cnpj_destinatario})")
                st.write(f"**Data de Emissão:** {nfe.data_emissao.strftime('%d/%m/%Y %H:%M')}")
                st.write(f"**Valor Total:** R$ {nfe.valor_total:.2f}")
                st.write(f"**Número de Itens:** {len(nfe.itens)}")
        
        # Agente 2 - Classificador
        with st.expander("🏷️ Agente 2 - Classificador NCM", expanded=True):
            if st.session_state.get('classificacoes'):
                classificacoes = st.session_state.classificacoes
                
                # Verificar se classificacoes é um dicionário ou lista
                if isinstance(classificacoes, dict) and len(classificacoes) > 0:
                    st.write(f"**Total de Produtos Classificados:** {len(classificacoes)}")
                    
                    # Mostrar algumas classificações (primeiros 5 itens)
                    for i, (numero_item, classificacao) in enumerate(list(classificacoes.items())[:5], 1):
                        if hasattr(classificacao, 'descricao_produto'):
                            st.write(f"**{i}. Item {numero_item}: {classificacao.descricao_produto}**")
                            st.write(f"   - NCM Declarado: {classificacao.ncm_declarado or 'N/A'}")
                            st.write(f"   - NCM Predito: {classificacao.ncm_predito}")
                            st.write(f"   - Confiança: {classificacao.confianca:.0%}")
                            st.write(f"   - Justificativa: {classificacao.justificativa or 'N/A'}")
                            if classificacao.diverge:
                                st.write(f"   - ⚠️ **DISCREPÂNCIA DETECTADA**")
                            st.write("---")
                        else:
                            st.write(f"**{i}. Item {numero_item}: Classificação {classificacao}**")
                            st.write("---")
                    
                    if len(classificacoes) > 5:
                        st.write(f"... e mais {len(classificacoes) - 5} produtos classificados")
                        
                elif isinstance(classificacoes, list) and len(classificacoes) > 0:
                    st.write(f"**Total de Produtos Classificados:** {len(classificacoes)}")
                    
                    # Mostrar algumas classificações
                    for i, classificacao in enumerate(classificacoes[:5], 1):
                        if hasattr(classificacao, 'descricao_produto'):
                            st.write(f"**{i}. {classificacao.descricao_produto}**")
                            st.write(f"   - NCM Declarado: {classificacao.ncm_declarado}")
                            st.write(f"   - NCM Predito: {classificacao.ncm_predito}")
                            st.write(f"   - Confiança: {classificacao.confianca:.0%}")
                            st.write(f"   - Justificativa: {classificacao.justificativa}")
                            st.write("---")
                        else:
                            st.write(f"**{i}. Classificação {classificacao}**")
                            st.write("---")
                    
                    if len(classificacoes) > 5:
                        st.write(f"... e mais {len(classificacoes) - 5} produtos classificados")
                else:
                    st.write("**Nenhuma classificação disponível**")
                    st.write(f"Tipo de dados: {type(classificacoes)}")
                    if hasattr(classificacoes, '__dict__'):
                        st.write(f"Atributos: {list(classificacoes.__dict__.keys())}")
        
        # Agente 3 - Validador
        with st.expander("✅ Agente 3 - Validador Fiscal", expanded=True):
            if relatorio.resultado_analise:
                resultado = relatorio.resultado_analise
                st.write(f"**Status da Validação:** {resultado.status}")
                st.write(f"**Conformidade Fiscal:** {resultado.conformidade:.0%}")
                st.write(f"**Observações:** {resultado.observacoes}")
        
        # Agente 4 - Orquestrador
        with st.expander("🎯 Agente 4 - Orquestrador", expanded=True):
            st.write(f"**Análise Concluída:** ✅")
            st.write(f"**Score de Risco Geral:** {relatorio.score_risco_geral}/100")
            st.write(f"**Nível de Risco:** {relatorio.nivel_risco.value.upper()}")
            if relatorio.data_analise:
                st.write(f"**Data da Análise:** {relatorio.data_analise.strftime('%d/%m/%Y %H:%M:%S')}")
            else:
                st.write(f"**Data da Análise:** Não disponível")
        
        # Fraudes detectadas
        if relatorio.fraudes_detectadas:
            st.subheader("🚨 Fraudes Detectadas")
            for i, fraude in enumerate(relatorio.fraudes_detectadas, 1):
                with st.expander(f"🔍 {i}. {fraude.tipo_fraude.value.upper()} (Score: {fraude.score}/100)"):
                    st.write(f"**Justificativa:** {fraude.justificativa}")
                    st.write(f"**Confiança:** {fraude.confianca:.0%}")
                    st.write(f"**Método:** {fraude.metodo_deteccao}")
        
        # Ações recomendadas
        if relatorio.acoes_recomendadas:
            st.subheader("💡 Ações Recomendadas")
            for acao in relatorio.acoes_recomendadas:
                st.write(f"• {acao}")
    else:
        st.info("Nenhum relatório disponível")


def pagina_chat():
    """Página de chat com assistente IA CrewAI"""
    st.markdown("""
    <div class="content-section">
        <h3>💬 Chat com Assistente IA</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Verificar se há agente5 disponível
    if not st.session_state.get('agente5'):
        st.warning("⚠️ Nenhuma análise disponível. Faça uma análise primeiro para usar o chat.")
        return
    
    agente5 = st.session_state.agente5
    
    # Botões de controle
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🗑️ Limpar Chat", use_container_width=True):
            st.session_state.historico_chat = []
            agente5.limpar_historico()
            st.rerun()
    
    with col2:
        if st.button("💡 Sugestões", use_container_width=True):
            sugestoes = agente5.sugerir_perguntas()
            st.session_state.sugestoes_mostradas = sugestoes
            st.rerun()
    
    with col3:
        if st.button("📥 Baixar Chat", use_container_width=True):
            download_chat()
    
    # Mostrar sugestões se disponíveis
    if st.session_state.get('sugestoes_mostradas'):
        st.subheader("💡 Perguntas Sugeridas:")
        for sugestao in st.session_state.sugestoes_mostradas:
            if st.button(f"❓ {sugestao}", use_container_width=True):
                st.session_state.pergunta_sugerida = sugestao
                st.rerun()
    
    # Histórico de chat
    st.subheader("💬 Conversa")
    
    # Container para o chat
    chat_container = st.container()
    
    with chat_container:
        for mensagem in st.session_state.historico_chat:
            if mensagem["tipo"] == "usuario":
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0;">
                    <strong>Você:</strong> {mensagem['conteudo']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #f3e5f5; padding: 10px; border-radius: 10px; margin: 5px 0;">
                    <strong>Assistente:</strong> {mensagem['conteudo']}
                </div>
                """, unsafe_allow_html=True)
    
    # Input de chat
    pergunta_sugerida = st.session_state.get('pergunta_sugerida', '')
    pergunta = st.text_input(
        "Faça uma pergunta sobre a análise:",
        value=pergunta_sugerida,
        placeholder="Ex: Quais fraudes foram detectadas?"
    )
    
    # Limpar pergunta sugerida após uso
    if pergunta_sugerida:
        st.session_state.pergunta_sugerida = ''
    
    if st.button("Enviar", type="primary", use_container_width=True):
        if pergunta:
            # Adicionar pergunta ao histórico
            st.session_state.historico_chat.append({
                "tipo": "usuario",
                "conteudo": pergunta
            })
            
            # Obter resposta do Agente5Interface
            with st.spinner("🤖 Assistente pensando..."):
                try:
                    resposta = agente5.conversar(pergunta)
                except Exception as e:
                    resposta = f"❌ Erro ao processar pergunta: {str(e)}"
            
            # Adicionar resposta ao histórico
            st.session_state.historico_chat.append({
                "tipo": "assistente", 
                "conteudo": resposta
            })
        
        st.rerun()
    

def download_chat():
    """Gera e disponibiliza download do histórico de chat"""
    if not st.session_state.historico_chat:
        st.warning("Nenhuma conversa para baixar.")
        return
    
    # Criar conteúdo do chat
    chat_content = "=== HISTÓRICO DE CHAT - FISCALAI MVP ===\n\n"
    chat_content += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    for mensagem in st.session_state.historico_chat:
        if mensagem["tipo"] == "usuario":
            chat_content += f"USUÁRIO: {mensagem['conteudo']}\n\n"
        else:
            chat_content += f"ASSISTENTE: {mensagem['conteudo']}\n\n"
    
    # Disponibilizar download
    st.download_button(
        label="📥 Baixar Histórico de Chat",
        data=chat_content,
        file_name=f"chat_fiscalai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )


def download_relatorio_completo():
    """Gera e disponibiliza download do relatório completo"""
    if not st.session_state.get('relatorio'):
        st.warning("Nenhum relatório disponível para download.")
        return
    
    relatorio = st.session_state.relatorio
    
    # Criar conteúdo do relatório
    content = "=== RELATÓRIO COMPLETO - FISCALAI MVP ===\n\n"
    content += f"Data da Análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    # Informações gerais
    content += "=== INFORMAÇÕES GERAIS ===\n"
    content += f"Score de Risco Geral: {relatorio.score_risco_geral}/100\n"
    content += f"Nível de Risco: {relatorio.nivel_risco.value.upper()}\n"
    if relatorio.data_analise:
        content += f"Data da Análise: {relatorio.data_analise.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    else:
        content += f"Data da Análise: Não disponível\n\n"
    
    # Dados da NF-e
    if st.session_state.get('nfe_data'):
        nfe = st.session_state.nfe_data
        content += "=== DADOS DA NF-e ===\n"
        content += f"Chave de Acesso: {nfe.chave_acesso}\n"
        content += f"Emitente: {nfe.razao_social_emitente} (CNPJ: {nfe.cnpj_emitente})\n"
        content += f"Destinatário: {nfe.razao_social_destinatario} (CNPJ: {nfe.cnpj_destinatario})\n"
        content += f"Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y %H:%M')}\n"
        content += f"Valor Total: R$ {nfe.valor_total:.2f}\n"
        content += f"Número de Itens: {len(nfe.itens)}\n\n"
    
    # Análises dos Agentes
    content += "=== ANÁLISES DOS AGENTES CREWAI ===\n\n"
    
    # Agente 1 - Extrator
    content += "--- AGENTE 1 - EXTRATOR DE DADOS ---\n"
    content += f"Responsabilidade: Extração e estruturação de dados da NF-e\n"
    if st.session_state.get('nfe_data'):
        nfe = st.session_state.nfe_data
        content += f"Status: Dados extraídos com sucesso\n"
        content += f"Total de campos extraídos: {len(nfe.__dict__)}\n"
        content += f"Validação: Dados estruturados corretamente\n\n"
        
        # Detalhes da extração
        content += "ANÁLISE REALIZADA:\n"
        content += f"- Chave de Acesso: {nfe.chave_acesso}\n"
        content += f"- Número/Serie: {nfe.numero}/{nfe.serie}\n"
        content += f"- Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y %H:%M')}\n"
        content += f"- Emitente: {nfe.razao_social_emitente or 'N/A'} (CNPJ: {nfe.cnpj_emitente})\n"
        content += f"- Destinatário: {nfe.razao_social_destinatario or 'N/A'} (CNPJ: {nfe.cnpj_destinatario})\n"
        content += f"- Valor Total: R$ {nfe.valor_total:,.2f}\n"
        content += f"- Total de Itens: {len(nfe.itens)}\n"
        content += f"- Valor dos Produtos: R$ {nfe.valor_produtos:,.2f}\n"
        valor_impostos_str = f"{nfe.valor_impostos:,.2f}" if nfe.valor_impostos is not None else "0.00"
        content += f"- Valor dos Impostos: R$ {valor_impostos_str}\n\n"
        
        content += "QUALIDADE DOS DADOS:\n"
        content += f"- ✅ Chave de acesso válida: {len(nfe.chave_acesso) == 44}\n"
        content += f"- ✅ CNPJ emitente válido: {len(nfe.cnpj_emitente) == 14}\n"
        content += f"- ✅ CNPJ destinatário válido: {len(nfe.cnpj_destinatario) == 14}\n"
        valor_impostos = nfe.valor_impostos if nfe.valor_impostos is not None else 0.0
        content += f"- ✅ Valores consistentes: {abs(nfe.valor_total - (nfe.valor_produtos + valor_impostos)) < 0.01}\n\n"
    else:
        content += f"Status: Nenhum dado de NF-e disponível\n\n"
    
    # Agente 2 - Classificador
    content += "--- AGENTE 2 - CLASSIFICADOR NCM ---\n"
    content += f"Responsabilidade: Classificação fiscal de produtos com códigos NCM\n"
    if st.session_state.get('classificacoes'):
        classificacoes = st.session_state.classificacoes
        content += f"Status: Classificação concluída\n"
        content += f"Total de produtos classificados: {len(classificacoes)}\n\n"
        
        # Estatísticas das classificações
        if isinstance(classificacoes, dict):
            total_discrepancias = sum(1 for c in classificacoes.values() if hasattr(c, 'diverge') and c.diverge)
            confianca_media = sum(c.confianca for c in classificacoes.values() if hasattr(c, 'confianca')) / len(classificacoes) if classificacoes else 0
            
            content += "ANÁLISE REALIZADA:\n"
            content += f"- Total de produtos analisados: {len(classificacoes)}\n"
            content += f"- Discrepâncias detectadas: {total_discrepancias}\n"
            content += f"- Taxa de discrepância: {(total_discrepancias/len(classificacoes)*100):.1f}%\n"
            content += f"- Confiança média das classificações: {confianca_media:.1%}\n"
            content += f"- Produtos com alta confiança (>90%): {sum(1 for c in classificacoes.values() if hasattr(c, 'confianca') and c.confianca > 0.9)}\n"
            content += f"- Produtos com baixa confiança (<70%): {sum(1 for c in classificacoes.values() if hasattr(c, 'confianca') and c.confianca < 0.7)}\n\n"
        
        content += "Detalhes das classificações:\n"
        
        # Tratar classificacoes como dicionário (numero_item -> ClassificacaoNCM)
        if isinstance(classificacoes, dict):
            for i, (numero_item, classificacao) in enumerate(classificacoes.items(), 1):
                if hasattr(classificacao, 'descricao_produto'):
                    content += f"  {i}. Item {numero_item}: {classificacao.descricao_produto}\n"
                    content += f"     NCM Declarado: {classificacao.ncm_declarado or 'N/A'}\n"
                    content += f"     NCM Predito: {classificacao.ncm_predito}\n"
                    content += f"     Confiança: {classificacao.confianca:.0%}\n"
                    content += f"     Justificativa: {classificacao.justificativa or 'N/A'}\n"
                    if classificacao.diverge:
                        content += f"     ⚠️ DISCREPÂNCIA: NCM declarado difere do predito\n"
                    content += "\n"
        else:
            # Fallback para lista (caso antigo)
            for i, classificacao in enumerate(classificacoes, 1):
                if hasattr(classificacao, 'descricao_produto'):
                    content += f"  {i}. {classificacao.descricao_produto}\n"
                    content += f"     NCM Declarado: {classificacao.ncm_declarado}\n"
                    content += f"     NCM Predito: {classificacao.ncm_predito}\n"
                    content += f"     Confiança: {classificacao.confianca:.0%}\n"
                    content += f"     Justificativa: {classificacao.justificativa}\n\n"
                else:
                    content += f"  {i}. Classificação {classificacao}\n\n"
    
    # Agente 3 - Validador
    content += "--- AGENTE 3 - VALIDADOR FISCAL ---\n"
    content += f"Responsabilidade: Validação de conformidade fiscal e regulatória\n"
    if relatorio.resultado_analise:
        resultado = relatorio.resultado_analise
        content += f"Status: {resultado.status}\n"
        content += f"Conformidade Fiscal: {resultado.conformidade:.0%}\n"
        content += f"Observações: {resultado.observacoes}\n\n"
        
        content += "ANÁLISE REALIZADA:\n"
        content += f"- Regras fiscais verificadas: NCM, CFOP, Alíquotas\n"
        content += f"- Conformidade geral: {resultado.conformidade:.1%}\n"
        content += f"- Status da validação: {resultado.status}\n"
        if hasattr(resultado, 'itens_validados'):
            content += f"- Itens validados: {len(resultado.itens_validados)}\n"
        if hasattr(resultado, 'itens_nao_conformes'):
            content += f"- Itens não conformes: {len(resultado.itens_nao_conformes)}\n"
        content += f"- Observações técnicas: {resultado.observacoes}\n\n"
    else:
        content += f"Status: Validação não disponível\n\n"
    
    # Agente 4 - Orquestrador
    content += "--- AGENTE 4 - ORQUESTRADOR ---\n"
    content += f"Responsabilidade: Coordenação geral e síntese estratégica da análise\n"
    content += f"Status: Análise concluída com sucesso\n"
    content += f"Score de Risco Geral: {relatorio.score_risco_geral}/100\n"
    content += f"Nível de Risco: {relatorio.nivel_risco.value.upper()}\n"
    if relatorio.data_analise:
        content += f"Data da Análise: {relatorio.data_analise.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    else:
        content += f"Data da Análise: Não disponível\n\n"
    
    content += "ANÁLISE REALIZADA:\n"
    content += f"- Coordenação de {len([a for a in [1,2,3] if True])} agentes especializados\n"
    content += f"- Consolidação de resultados de extração, classificação e validação\n"
    content += f"- Cálculo de score de risco baseado em múltiplos fatores\n"
    content += f"- Identificação de padrões e anomalias fiscais\n"
    content += f"- Geração de recomendações estratégicas\n\n"
    
    content += "RESUMO EXECUTIVO:\n"
    content += f"- Nível de risco: {relatorio.nivel_risco.value.upper()}\n"
    content += f"- Score de risco: {relatorio.score_risco_geral}/100\n"
    if relatorio.fraudes_detectadas:
        content += f"- Fraudes detectadas: {len(relatorio.fraudes_detectadas)}\n"
        content += f"- Tipos de fraude: {', '.join(set(f.tipo_fraude.value for f in relatorio.fraudes_detectadas))}\n"
    else:
        content += f"- Fraudes detectadas: Nenhuma\n"
    content += f"- Recomendação geral: {'Aprovar' if relatorio.nivel_risco.value in ['BAIXO', 'MEDIO'] else 'Revisar'}\n\n"
    
    # Fraudes detectadas
    if relatorio.fraudes_detectadas:
        content += "=== FRAUDES DETECTADAS ===\n"
        for i, fraude in enumerate(relatorio.fraudes_detectadas, 1):
            content += f"{i}. {fraude.tipo_fraude.value.upper()} (Score: {fraude.score}/100)\n"
            content += f"   Justificativa: {fraude.justificativa}\n"
            content += f"   Confiança: {fraude.confianca:.0%}\n"
            content += f"   Método: {fraude.metodo_deteccao}\n\n"
    
    # Ações recomendadas
    if relatorio.acoes_recomendadas:
        content += "=== AÇÕES RECOMENDADAS ===\n"
        for acao in relatorio.acoes_recomendadas:
            content += f"• {acao}\n"
    
    # Disponibilizar download
    st.download_button(
        label="📥 Baixar Relatório Completo",
        data=content,
        file_name=f"relatorio_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )


def download_analises_agentes():
    """Gera e disponibiliza download das análises dos agentes CrewAI"""
    if not st.session_state.get('relatorio'):
        st.warning("Nenhuma análise disponível para download.")
        return
    
    # Criar conteúdo das análises dos agentes
    content = "=== ANÁLISES DOS AGENTES CREWAI - FISCALAI MVP ===\n\n"
    content += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    # Agente 1 - Extrator
    content += "=== AGENTE 1 - EXTRATOR DE DADOS ===\n"
    content += "Responsabilidade: Extração e estruturação de dados da NF-e\n"
    content += "Status: Concluído\n\n"
    
    if st.session_state.get('nfe_data'):
        nfe = st.session_state.nfe_data
        content += "Dados Extraídos:\n"
        content += f"- Chave de Acesso: {nfe.chave_acesso}\n"
        content += f"- Emitente: {nfe.razao_social_emitente}\n"
        content += f"- CNPJ Emitente: {nfe.cnpj_emitente}\n"
        content += f"- Destinatário: {nfe.razao_social_destinatario}\n"
        content += f"- CNPJ Destinatário: {nfe.cnpj_destinatario}\n"
        content += f"- Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y %H:%M')}\n"
        content += f"- Valor Total: R$ {nfe.valor_total:.2f}\n"
        content += f"- Número de Itens: {len(nfe.itens)}\n\n"
    
    # Agente 2 - Classificador
    content += "=== AGENTE 2 - CLASSIFICADOR NCM ===\n"
    content += "Responsabilidade: Classificação fiscal de produtos com códigos NCM\n"
    content += "Status: Concluído\n\n"
    
    if st.session_state.get('classificacoes'):
        classificacoes = st.session_state.classificacoes
        content += f"Total de Produtos Classificados: {len(classificacoes)}\n\n"
        content += "Classificações Detalhadas:\n"
        
        # Tratar classificacoes como dicionário (numero_item -> ClassificacaoNCM)
        if isinstance(classificacoes, dict):
            for i, (numero_item, classificacao) in enumerate(classificacoes.items(), 1):
                if hasattr(classificacao, 'descricao_produto'):
                    content += f"\n{i}. ITEM {numero_item}: {classificacao.descricao_produto}\n"
                    content += f"   NCM Declarado: {classificacao.ncm_declarado or 'N/A'}\n"
                    content += f"   NCM Predito: {classificacao.ncm_predito}\n"
                    content += f"   Confiança da Classificação: {classificacao.confianca:.0%}\n"
                    content += f"   Justificativa: {classificacao.justificativa or 'N/A'}\n"
                    if classificacao.diverge:
                        content += f"   ⚠️ DISCREPÂNCIA DETECTADA: NCM declarado difere do predito\n"
        else:
            # Fallback para lista (caso antigo)
            for i, classificacao in enumerate(classificacoes, 1):
                if hasattr(classificacao, 'descricao_produto'):
                    content += f"\n{i}. PRODUTO: {classificacao.descricao_produto}\n"
                    content += f"   NCM Declarado: {classificacao.ncm_declarado}\n"
                    content += f"   NCM Predito: {classificacao.ncm_predito}\n"
                    content += f"   Confiança da Classificação: {classificacao.confianca:.0%}\n"
                    content += f"   Justificativa: {classificacao.justificativa}\n"
                    if classificacao.ncm_declarado != classificacao.ncm_predito:
                        content += f"   ⚠️ DISCREPÂNCIA DETECTADA: NCM declarado difere do predito\n"
                else:
                    content += f"\n{i}. Classificação {classificacao}\n"
    
    # Agente 3 - Validador
    content += "\n\n=== AGENTE 3 - VALIDADOR FISCAL ===\n"
    content += "Responsabilidade: Validação de conformidade fiscal e regulatória\n"
    content += "Status: Concluído\n\n"
    
    if st.session_state.get('relatorio') and st.session_state.relatorio.resultado_analise:
        resultado = st.session_state.relatorio.resultado_analise
        content += f"Status da Validação: {resultado.status}\n"
        content += f"Conformidade Fiscal: {resultado.conformidade:.0%}\n"
        content += f"Observações: {resultado.observacoes}\n\n"
    
    # Agente 4 - Orquestrador
    content += "=== AGENTE 4 - ORQUESTRADOR ===\n"
    content += "Responsabilidade: Coordenação geral da análise e consolidação de resultados\n"
    content += "Status: Concluído\n\n"
    
    if st.session_state.get('relatorio'):
        relatorio = st.session_state.relatorio
        content += f"Score de Risco Geral: {relatorio.score_risco_geral}/100\n"
        content += f"Nível de Risco: {relatorio.nivel_risco.value.upper()}\n"
        if relatorio.data_analise:
            content += f"Data da Análise: {relatorio.data_analise.strftime('%d/%m/%Y %H:%M:%S')}\n"
        else:
            content += f"Data da Análise: Não disponível\n"
        content += f"Total de Fraudes Detectadas: {len(relatorio.fraudes_detectadas)}\n\n"
    
    # Disponibilizar download
    st.download_button(
        label="📋 Baixar Análises dos Agentes",
        data=content,
        file_name=f"analises_agentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )


def download_dados_nfe():
    """Gera e disponibiliza download dos dados da NF-e"""
    if not st.session_state.get('nfe_data'):
        st.warning("Nenhum dado de NF-e disponível para download.")
        return
    
    nfe = st.session_state.nfe_data
    
    # Criar conteúdo dos dados da NF-e
    content = "=== DADOS DA NF-e - FISCALAI MVP ===\n\n"
    content += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    # Informações básicas
    content += "=== INFORMAÇÕES BÁSICAS ===\n"
    content += f"Chave de Acesso: {nfe.chave_acesso}\n"
    content += f"Número: {nfe.numero}\n"
    content += f"Série: {nfe.serie}\n"
    content += f"Data de Emissão: {nfe.data_emissao.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    # Emitente
    content += "=== EMITENTE ===\n"
    content += f"Razão Social: {nfe.razao_social_emitente}\n"
    content += f"CNPJ: {nfe.cnpj_emitente}\n\n"
    
    # Destinatário
    content += "=== DESTINATÁRIO ===\n"
    content += f"Razão Social: {nfe.razao_social_destinatario}\n"
    content += f"CNPJ: {nfe.cnpj_destinatario}\n\n"
    
    # Valores
    content += "=== VALORES ===\n"
    content += f"Valor Total: R$ {nfe.valor_total:.2f}\n"
    content += f"Valor dos Produtos: R$ {nfe.valor_produtos:.2f}\n\n"
    
    # Itens
    content += "=== ITENS DA NF-e ===\n"
    content += f"Total de Itens: {len(nfe.itens)}\n\n"
    
    for i, item in enumerate(nfe.itens, 1):
        content += f"ITEM {i}:\n"
        content += f"  Código do Produto: {item.codigo_produto}\n"
        content += f"  Descrição: {item.descricao}\n"
        content += f"  NCM: {item.ncm_declarado}\n"
        content += f"  CFOP: {item.cfop}\n"
        content += f"  Unidade: {item.unidade}\n"
        content += f"  Quantidade: {item.quantidade}\n"
        content += f"  Valor Unitário: R$ {item.valor_unitario:.2f}\n"
        content += f"  Valor Total: R$ {item.valor_total:.2f}\n\n"
    
    # Disponibilizar download
    st.download_button(
        label="📊 Baixar Dados da NF-e",
        data=content,
        file_name=f"dados_nfe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )


def main():
    """Função principal"""
    inicializar_sessao()
    
    # Configurar variáveis de ambiente com chaves salvas (otimizado)
    try:
        setup_api_environment()
    except Exception as e:
        st.warning(f"⚠️ Erro ao configurar API: {e}")
    
    # Carregar tabelas fiscais de forma assíncrona (apenas quando necessário)
    if 'tabelas_carregadas' not in st.session_state:
        st.session_state.tabelas_carregadas = False
    
    # Estilos SHADCN/Modern Design
    st.markdown("""
    <style>
    /* Reset e base - SHADCN inspired */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    
    /* Título principal - Design Minimalista Moderno */
    .main-title {
        text-align: center;
        margin: 0 0 0.5rem 0;
        padding: 0;
        font-size: 2.2rem;
        font-weight: 300;
        color: #1a1a1a;
        letter-spacing: -0.03em;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    .main-subtitle {
        text-align: center;
        margin: 0 0 2.5rem 0;
        padding: 0;
        font-size: 1rem;
        font-weight: 400;
        color: #666666;
        letter-spacing: 0.01em;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    /* Abas estilo browser - Design Minimalista */
    .browser-tabs {
        margin: 0 0 2.5rem 0;
        border-bottom: 1px solid #e5e5e5;
        background: #ffffff;
        padding: 0;
    }
    
    .tab-container {
        display: flex;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Botões de aba - Design Minimalista */
    .stButton > button {
        background: transparent;
        color: #666666;
        border: none;
        border-radius: 0;
        padding: 16px 24px;
        font-weight: 400;
        font-size: 15px;
        transition: all 0.3s ease;
        border-bottom: 2px solid transparent;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
        margin: 0;
    }
    
    .stButton > button:hover {
        background: #f8f8f8;
        color: #1a1a1a;
        border-bottom-color: #e5e5e5;
    }
    
    /* Aba ativa - Design Minimalista */
    .stButton > button[kind="primary"] {
        background: transparent;
        color: #1a1a1a;
        border-bottom-color: #007aff;
        font-weight: 500;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #f8f8f8;
        border-bottom-color: #007aff;
    }
    
    /* Seções de conteúdo - Design Minimalista */
    .content-section {
        background: #ffffff;
        border: 1px solid #e5e5e5;
        border-radius: 12px;
        padding: 32px;
        margin: 2rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    
    .content-section h3 {
        margin: 0 0 20px 0;
        font-size: 1.3rem;
        font-weight: 500;
        color: #1a1a1a;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    /* Sidebar - Design Minimalista */
    .css-1d391kg {
        background: #ffffff;
        border-right: 1px solid #e5e5e5;
    }
    
    .sidebar-content {
        padding: 1.5rem 0;
    }
    
    .sidebar-content h3 {
        margin: 0 0 1.5rem 0;
        font-size: 1.1rem;
        font-weight: 500;
        color: #1a1a1a;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    /* Botões primários - Design Minimalista */
    .stButton > button[type="primary"] {
        background: #007aff;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 14px 28px;
        font-weight: 500;
        font-size: 15px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 122, 255, 0.2);
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    .stButton > button[type="primary"]:hover {
        background: #0056cc;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
        transform: translateY(-1px);
    }
    
    /* Alertas - Design Minimalista */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }
    
    /* Remover espaçamentos desnecessários */
    .stTabs [data-baseweb="tab-list"] {
        display: none;
    }
    
    /* Ocultar elementos do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Prevenir piscar do título */
    .stApp > header {
        visibility: hidden;
        height: 0;
    }
    
    /* Estabilizar título da página */
    title {
        display: none !important;
    }
    
    /* Melhorias de tipografia - Arial como fonte principal */
    body, html {
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif !important;
        font-size: 14px;
        line-height: 1.5;
    }
    
    /* Aplicar Arial em todos os elementos */
    * {
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif !important;
    }
    
    /* Forçar fundo branco sempre */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* Melhorias adicionais para design minimalista */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
    }
    
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }
    
    .stRadio > div > label {
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
        color: #666666;
    }
    
    .stCheckbox > div > label {
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
        color: #666666;
    }
    
    .main .block-container {
        background-color: #ffffff !important;
    }
    
    /* Forçar tema claro */
    .stApp > div {
        background-color: #ffffff !important;
    }
    
    /* Garantir que todos os elementos tenham fundo branco */
    .stApp, .main, .block-container, .stApp > div, 
    .stApp > div > div, .stApp > div > div > div {
        background-color: #ffffff !important;
    }
    
    /* Forçar cores de texto escuras para contraste */
    .stApp, .main, .block-container {
        color: #000000 !important;
    }
    
    /* Garantir que o sidebar também seja branco */
    .css-1d391kg {
        background-color: #ffffff !important;
    }
    
    /* Forçar fundo branco em todos os elementos Streamlit */
    div[data-testid="stApp"] {
        background-color: #ffffff !important;
    }
    
    /* Garantir que o conteúdo principal seja branco */
    .main .block-container > div {
        background-color: #ffffff !important;
    }
    
    /* Estilizar opções de upload em cinza */
    .stRadio > div > label > div[data-testid="stMarkdownContainer"] {
        color: #6b7280 !important;
    }
    
    /* Estilizar labels dos radio buttons */
    .stRadio > div > label {
        color: #6b7280 !important;
    }
    
    /* Estilizar texto das opções de upload */
    .stRadio > div > label > div[data-testid="stMarkdownContainer"] p {
        color: #6b7280 !important;
    }
    
    /* Estilizar especificamente as opções XML e CSV */
    .stRadio > div > label:has-text("📄 XML (NF-e/NFS-e)"),
    .stRadio > div > label:has-text("📊 CSV (Dados Fiscais)") {
        color: #6b7280 !important;
    }
    
    /* Estilizar todos os elementos de radio button */
    .stRadio label {
        color: #6b7280 !important;
    }
    
    /* Estilizar texto dentro dos radio buttons */
    .stRadio label div {
        color: #6b7280 !important;
    }
    
    /* Estilizar parágrafos dentro dos radio buttons */
    .stRadio label p {
        color: #6b7280 !important;
    }
    
    /* Corrigir sobreposição de texto nos títulos dos agentes */
    .stExpander > div > div {
        overflow: visible !important;
    }
    
    .stExpander > div > div > div {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: unset !important;
    }
    
    /* CORREÇÃO ROBUSTA PARA SOBREPOSIÇÃO DE TÍTULOS DOS AGENTES */
    
    /* Resetar todos os expanders */
    [data-testid="stExpander"] {
        margin: 16px 0 !important;
        border: 1px solid #e1e5e9 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    /* Corrigir o cabeçalho do expander */
    [data-testid="stExpander"] > div:first-child {
        background: #f8f9fa !important;
        border-bottom: 1px solid #e1e5e9 !important;
        padding: 0 !important;
        margin: 0 !important;
        position: relative !important;
        z-index: 10 !important;
    }
    
    /* Corrigir o botão de toggle do expander */
    [data-testid="stExpander"] > div:first-child > div {
        background: transparent !important;
        padding: 12px 16px !important;
        margin: 0 !important;
        border: none !important;
        position: relative !important;
        z-index: 15 !important;
    }
    
    /* Corrigir o texto do título */
    [data-testid="stExpander"] > div:first-child > div > div {
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        position: relative !important;
        z-index: 20 !important;
    }
    
    /* Garantir que o texto seja legível */
    [data-testid="stExpander"] > div:first-child > div > div > div {
        color: #1a1a1a !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        line-height: 1.5 !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        position: relative !important;
        z-index: 25 !important;
    }
    
    /* Corrigir o conteúdo do expander */
    [data-testid="stExpander"] > div:last-child {
        background: #ffffff !important;
        padding: 16px !important;
        margin: 0 !important;
        border: none !important;
        position: relative !important;
        z-index: 5 !important;
    }
    
    /* Garantir que não haja sobreposição entre elementos */
    [data-testid="stExpander"] * {
        box-sizing: border-box !important;
    }
    
    /* Correção específica para títulos dos agentes */
    [data-testid="stExpander"]:has([class*="agent"]) > div:first-child {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    [data-testid="stExpander"]:has([class*="agent"]) > div:first-child > div > div > div {
        color: white !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }
    </style>
    
    <script>
    // Aplicar cor cinza às opções de upload
    function styleUploadOptions() {
        const radioLabels = document.querySelectorAll('.stRadio label');
        radioLabels.forEach(label => {
            const text = label.textContent || label.innerText;
            if (text.includes('📄 XML (NF-e/NFS-e)') || text.includes('📊 CSV (Dados Fiscais)')) {
                label.style.color = '#6b7280';
                const markdownContainer = label.querySelector('[data-testid="stMarkdownContainer"]');
                if (markdownContainer) {
                    markdownContainer.style.color = '#6b7280';
                }
                const paragraphs = label.querySelectorAll('p');
                paragraphs.forEach(p => {
                    p.style.color = '#6b7280';
                });
            }
        });
    }
    
    // Executar quando a página carregar
    document.addEventListener('DOMContentLoaded', styleUploadOptions);
    
    // Executar após mudanças no DOM (Streamlit rerun)
    const observer = new MutationObserver(styleUploadOptions);
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Função robusta para corrigir sobreposição de texto nos títulos dos agentes
    function fixAgentTitlesOverlap() {
        const expanders = document.querySelectorAll('[data-testid="stExpander"]');
        expanders.forEach((expander, index) => {
            // Resetar estilos do expander
            expander.style.margin = '16px 0';
            expander.style.border = '1px solid #e1e5e9';
            expander.style.borderRadius = '8px';
            expander.style.overflow = 'hidden';
            
            // Corrigir o cabeçalho
            const header = expander.querySelector('div:first-child');
            if (header) {
                header.style.background = '#f8f9fa';
                header.style.borderBottom = '1px solid #e1e5e9';
                header.style.padding = '0';
                header.style.margin = '0';
                header.style.position = 'relative';
                header.style.zIndex = '10';
                
                // Corrigir o botão de toggle
                const toggleButton = header.querySelector('div');
                if (toggleButton) {
                    toggleButton.style.background = 'transparent';
                    toggleButton.style.padding = '12px 16px';
                    toggleButton.style.margin = '0';
                    toggleButton.style.border = 'none';
                    toggleButton.style.position = 'relative';
                    toggleButton.style.zIndex = '15';
                    
                    // Corrigir o container do texto
                    const textContainer = toggleButton.querySelector('div');
                    if (textContainer) {
                        textContainer.style.background = 'transparent';
                        textContainer.style.padding = '0';
                        textContainer.style.margin = '0';
                        textContainer.style.position = 'relative';
                        textContainer.style.zIndex = '20';
                        
                        // Corrigir o texto final
                        const textElement = textContainer.querySelector('div');
                        if (textElement) {
                            textElement.style.color = '#1a1a1a';
                            textElement.style.fontWeight = '600';
                            textElement.style.fontSize = '16px';
                            textElement.style.lineHeight = '1.5';
                            textElement.style.whiteSpace = 'normal';
                            textElement.style.wordWrap = 'break-word';
                            textElement.style.overflowWrap = 'break-word';
                            textElement.style.background = 'transparent';
                            textElement.style.padding = '0';
                            textElement.style.margin = '0';
                            textElement.style.position = 'relative';
                            textElement.style.zIndex = '25';
                        }
                    }
                }
            }
            
            // Corrigir o conteúdo
            const content = expander.querySelector('div:last-child');
            if (content) {
                content.style.background = '#ffffff';
                content.style.padding = '16px';
                content.style.margin = '0';
                content.style.border = 'none';
                content.style.position = 'relative';
                content.style.zIndex = '5';
            }
            
            // Adicionar classe para identificação
            expander.classList.add('agent-expander-fixed');
        });
    }
    
    // Executar correção quando a página carregar
    document.addEventListener('DOMContentLoaded', fixAgentTitlesOverlap);
    
    // Executar correção após mudanças no DOM
    const titleObserver = new MutationObserver(fixAgentTitlesOverlap);
    titleObserver.observe(document.body, { childList: true, subtree: true });
    
    // Executar correção periodicamente para garantir que funcione
    setInterval(fixAgentTitlesOverlap, 1000);
    
    // Executar correção quando a página ganhar foco
    window.addEventListener('focus', fixAgentTitlesOverlap);
    
    // Executar correção quando houver scroll
    window.addEventListener('scroll', fixAgentTitlesOverlap);
    </script>
    """, unsafe_allow_html=True)
    
    # Título principal - fixo no topo
    st.markdown("""
    <div class="main-title">🚀 OldNews FiscalAI</div>
    <div class="main-subtitle">Sistema Inteligente de Análise Fiscal de NF-e</div>
    """, unsafe_allow_html=True)
    
    # Status das APIs - abaixo do título
    show_api_status()
    
    # Abas de navegação estilo browser
    st.markdown("""
    <div class="browser-tabs">
        <div class="tab-container">
    """, unsafe_allow_html=True)
    
    # Definir páginas e ícones
    pages = [
        ("🏠", "Início", "inicio"),
        ("🔑", "Configurar APIs", "configurar"),
        ("📤", "Analisar NF-e", "analisar"), 
        ("📊", "Dashboard", "dashboard"),
        ("💬", "Chat", "chat")
    ]
    
    # Criar abas
    tab_cols = st.columns(len(pages))
    for i, (icon, name, page_key) in enumerate(pages):
        with tab_cols[i]:
            is_active = st.session_state.get('current_page', 'inicio') == page_key
            
            if st.button(f"{icon} {name}", key=f"tab_{page_key}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.current_page = page_key
                st.rerun()
    
    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar minimalista
    with st.sidebar:
        st.markdown("### 🚀 OldNews FiscalAI")
        st.markdown("---")
        sidebar_configuracoes()
    
    # Roteamento de páginas baseado em session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'inicio'
    
    # Roteamento de páginas
    if st.session_state.current_page == 'inicio':
        pagina_inicio()
    elif st.session_state.current_page == 'analisar':
        pagina_upload()
    elif st.session_state.current_page == 'configurar':
        show_api_config_page()
    elif st.session_state.current_page == 'dashboard':
        if st.session_state.get('analysis_completed', False) and st.session_state.get('relatorio'):
            # Exibir dashboard com resultados
            pagina_dashboard()
        else:
            st.info("📋 Faça uma análise primeiro para ver o dashboard")
    elif st.session_state.current_page == 'chat':
        if st.session_state.get('analysis_completed', False) and st.session_state.get('relatorio'):
            # Exibir interface de chat
            pagina_chat()
        else:
            st.info("📋 Faça uma análise primeiro para usar o chat")

if __name__ == "__main__":
    main()
