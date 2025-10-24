"""
FiscalAI MVP - Configuração de Chaves de API
Sistema amigável para configuração de chaves de API para usuários não-técnicos
"""

import os
import streamlit as st
from pathlib import Path
from typing import Dict, Optional, List
import json
from datetime import datetime
import base64
from cryptography.fernet import Fernet
import hashlib

class APIConfigManager:
    """
    Gerenciador de configuração de chaves de API
    Interface amigável para usuários não-técnicos
    """
    
    def __init__(self):
        """Inicializa o gerenciador de configuração"""
        self.config_dir = Path.home() / ".fiscalai"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "api_config.json"
        self.encryption_key_file = self.config_dir / ".fiscalai_key"
        
        # Inicializar chave de criptografia
        self._init_encryption_key()
    
    def _init_encryption_key(self):
        """Inicializa ou carrega chave de criptografia"""
        if not self.encryption_key_file.exists():
            key = Fernet.generate_key()
            with open(self.encryption_key_file, 'wb') as f:
                f.write(key)
            # Tornar arquivo oculto e com permissões restritas
            os.chmod(self.encryption_key_file, 0o600)
        
        with open(self.encryption_key_file, 'rb') as f:
            self.fernet = Fernet(f.read())
    
    def _encrypt_value(self, value: str) -> str:
        """Criptografa um valor"""
        if not value:
            return ""
        return self.fernet.encrypt(value.encode()).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Descriptografa um valor"""
        if not encrypted_value:
            return ""
        try:
            return self.fernet.decrypt(encrypted_value.encode()).decode()
        except:
            return ""
    
    def get_config(self) -> Dict[str, str]:
        """Obtém configuração atual"""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                encrypted_config = json.load(f)
            
            config = {}
            for key, encrypted_value in encrypted_config.items():
                config[key] = self._decrypt_value(encrypted_value)
            
            return config
        except Exception as e:
            st.error(f"Erro ao carregar configuração: {e}")
            return {}
    
    def save_config(self, config: Dict[str, str]) -> bool:
        """Salva configuração criptografada"""
        try:
            encrypted_config = {}
            for key, value in config.items():
                encrypted_config[key] = self._encrypt_value(value)
            
            with open(self.config_file, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            # Tornar arquivo com permissões restritas
            os.chmod(self.config_file, 0o600)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar configuração: {e}")
            return False
    
    def get_providers_info(self) -> List[Dict[str, str]]:
        """Obtém informações sobre provedores de API"""
        return [
            {
                "name": "OpenAI",
                "description": "GPT-4, GPT-3.5 Turbo - Análise avançada de texto",
                "website": "https://platform.openai.com/api-keys",
                "icon": "🤖",
                "required": False,
                "config_key": "OPENAI_API_KEY"
            },
            {
                "name": "Anthropic (Claude)",
                "description": "Claude 3 - Análise contextual avançada",
                "website": "https://console.anthropic.com/",
                "icon": "🧠",
                "required": False,
                "config_key": "ANTHROPIC_API_KEY"
            },
            {
                "name": "Google (Gemini)",
                "description": "Gemini Pro - Análise multimodal",
                "website": "https://makersuite.google.com/app/apikey",
                "icon": "🔍",
                "required": False,
                "config_key": "GOOGLE_API_KEY"
            },
            {
                "name": "Groq",
                "description": "Llama 2, Mixtral - Processamento rápido",
                "website": "https://console.groq.com/keys",
                "icon": "⚡",
                "required": False,
                "config_key": "GROQ_API_KEY"
            }
        ]


def show_api_config_page():
    """Mostra página de configuração de API"""
    st.header("🔑 Configuração de Chaves de API")
    
    # Explicação para usuários não-técnicos
    st.markdown("""
    ### 📋 O que são chaves de API?
    
    As chaves de API são como "senhas especiais" que permitem ao FiscalAI usar serviços de inteligência artificial 
    para analisar suas notas fiscais com mais precisão.
    
    **🎯 Por que usar?**
    - ✅ **Análise mais precisa** de NCMs e CFOPs
    - ✅ **Detecção avançada** de fraudes
    - ✅ **Classificação inteligente** de produtos
    - ✅ **Relatórios mais detalhados**
    
    **🔒 É seguro?**
    - ✅ Suas chaves são **criptografadas** e armazenadas localmente
    - ✅ **Nunca são enviadas** para servidores externos
    - ✅ Você pode **remover** a qualquer momento
    """)
    
    # Inicializar gerenciador
    config_manager = APIConfigManager()
    current_config = config_manager.get_config()
    providers = config_manager.get_providers_info()
    
    # Tabs para diferentes provedores
    tabs = st.tabs([f"{provider['icon']} {provider['name']}" for provider in providers])
    
    for i, (tab, provider) in enumerate(zip(tabs, providers)):
        with tab:
            st.subheader(f"{provider['icon']} {provider['name']}")
            st.write(provider['description'])
            
            # Status atual
            current_key = current_config.get(provider['config_key'], '')
            if current_key:
                st.success("✅ Chave configurada")
                # Mostrar últimos 4 caracteres para confirmação
                masked_key = "*" * (len(current_key) - 4) + current_key[-4:] if len(current_key) > 4 else "*" * len(current_key)
                st.code(f"Chave: {masked_key}")
            else:
                st.warning("⚠️ Chave não configurada")
            
            # Formulário de configuração
            with st.form(f"config_{provider['name'].lower()}"):
                st.markdown(f"**Como obter sua chave:**")
                st.markdown(f"1. Acesse: [{provider['website']}]({provider['website']})")
                st.markdown("2. Crie uma conta (se necessário)")
                st.markdown("3. Gere uma nova chave de API")
                st.markdown("4. Cole a chave abaixo:")
                
                new_key = st.text_input(
                    f"Chave de API {provider['name']}",
                    value="",
                    type="password",
                    help=f"Cole sua chave de API do {provider['name']} aqui"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("💾 Salvar Chave", use_container_width=True):
                        if new_key:
                            # Validar formato básico da chave
                            if validate_api_key(new_key, provider['name']):
                                config = current_config.copy()
                                config[provider['config_key']] = new_key
                                
                                if config_manager.save_config(config):
                                    st.success(f"✅ Chave {provider['name']} salva com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao salvar chave")
                            else:
                                st.error("❌ Formato de chave inválido")
                        else:
                            st.error("❌ Por favor, insira uma chave válida")
                
                with col2:
                    if st.form_submit_button("🗑️ Remover Chave", use_container_width=True):
                        config = current_config.copy()
                        config.pop(provider['config_key'], None)
                        
                        if config_manager.save_config(config):
                            st.success(f"✅ Chave {provider['name']} removida!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao remover chave")
    
    # Seção de informações adicionais
    st.markdown("---")
    
    with st.expander("ℹ️ Informações Importantes"):
        st.markdown("""
        **🔐 Segurança:**
        - Suas chaves são armazenadas de forma criptografada no seu computador
        - Elas nunca são compartilhadas ou enviadas para servidores externos
        - Você pode remover as chaves a qualquer momento
        
        **💰 Custos:**
        - Alguns provedores cobram por uso (geralmente centavos por análise)
        - O FiscalAI usa as chaves apenas quando necessário
        - Você pode configurar limites de uso nos provedores
        
        **🚀 Sem chaves:**
        - O FiscalAI funciona sem chaves, mas com funcionalidades limitadas
        - Análises básicas são sempre gratuitas
        - Chaves melhoram a precisão e velocidade
        
        **🆘 Precisa de ajuda?**
        - Consulte a documentação de cada provedor
        - Verifique se sua conta tem créditos disponíveis
        - Teste com uma análise simples primeiro
        """)


def validate_api_key(key: str, provider: str) -> bool:
    """Valida formato básico da chave de API"""
    if not key or len(key) < 10:
        return False
    
    # Validações específicas por provedor
    if provider.lower() == "openai":
        return key.startswith("sk-") and len(key) > 20
    elif provider.lower() == "anthropic":
        return key.startswith("sk-ant-") and len(key) > 20
    elif provider.lower() == "google":
        return len(key) > 20  # Google keys são mais variadas
    elif provider.lower() == "groq":
        return key.startswith("gsk_") and len(key) > 20
    
    return len(key) > 10  # Validação genérica


def show_api_status():
    """Mostra status das chaves de API configuradas"""
    config_manager = APIConfigManager()
    config = config_manager.get_config()
    providers = config_manager.get_providers_info()
    
    configured_count = sum(1 for provider in providers if config.get(provider['config_key']))
    total_count = len(providers)
    
    # Criar layout com colunas para as mensagens
    col1, col2 = st.columns([1, 1])
    
    if configured_count == 0:
        with col1:
            st.markdown("""
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 12px; margin: 8px 0;">
                <p style="margin: 0; color: #856404; font-weight: 500;">⚠️ Nenhuma chave de API configurada</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 12px; margin: 8px 0;">
                <p style="margin: 0; color: #0c5460; font-weight: 500;">💡 Configure chaves de API para melhorar a análise</p>
            </div>
            """, unsafe_allow_html=True)
    elif configured_count < total_count:
        st.markdown(f"""
        <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 12px; margin: 8px 0; text-align: center;">
            <p style="margin: 0; color: #155724; font-weight: 500;">✅ {configured_count}/{total_count} chaves configuradas</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 12px; margin: 8px 0; text-align: center;">
            <p style="margin: 0; color: #0c5460; font-weight: 500;">🎉 Todas as {total_count} chaves configuradas!</p>
        </div>
        """, unsafe_allow_html=True)
    
    return configured_count > 0


def get_api_config_for_env() -> Dict[str, str]:
    """Obtém configuração de API para variáveis de ambiente"""
    config_manager = APIConfigManager()
    return config_manager.get_config()


# Função de conveniência para usar na aplicação principal
def setup_api_environment():
    """Configura variáveis de ambiente com as chaves salvas"""
    config = get_api_config_for_env()
    for key, value in config.items():
        if value:
            os.environ[key] = value
    return config
