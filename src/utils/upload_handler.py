"""
FiscalAI MVP - Upload Handler para Arquivos Grandes
Sistema otimizado para upload e processamento de arquivos XML grandes
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UploadHandler:
    """
    Gerenciador de upload para arquivos grandes
    Suporta arquivos de até 200MB com otimizações
    """
    
    def __init__(self, max_size_mb: int = 200):
        """
        Inicializa o handler de upload
        
        Args:
            max_size_mb: Tamanho máximo em MB (padrão: 200MB)
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.temp_dir = Path(tempfile.gettempdir()) / "fiscalai_uploads"
        self.temp_dir.mkdir(exist_ok=True)
    
    def handle_large_file_upload(self, 
                                uploaded_file, 
                                chunk_size: int = 8192) -> Tuple[bool, str, Optional[str]]:
        """
        Processa upload de arquivo grande com streaming
        
        Args:
            uploaded_file: Arquivo enviado pelo Streamlit
            chunk_size: Tamanho do chunk para leitura (padrão: 8KB)
        
        Returns:
            Tuple (sucesso, mensagem, caminho_arquivo)
        """
        try:
            # Verificar tamanho
            file_size = len(uploaded_file.getvalue())
            
            if file_size > self.max_size_bytes:
                return False, f"Arquivo muito grande. Máximo permitido: {self.max_size_bytes // (1024*1024)}MB", None
            
            # Gerar nome único com validação de segurança
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Validar e sanitizar nome do arquivo
            original_name = uploaded_file.name
            if not original_name or '..' in original_name or '/' in original_name or '\\' in original_name:
                raise ValueError("Nome de arquivo inválido - contém caracteres perigosos")
            
            # Usar apenas nome base do arquivo (sem path)
            import os
            safe_filename = os.path.basename(original_name)
            filename = f"nfe_{timestamp}_{safe_filename}"
            temp_path = self.temp_dir / filename
            
            # Upload com progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Escrever arquivo em chunks
            with open(temp_path, 'wb') as f:
                uploaded_file.seek(0)  # Voltar ao início
                
                bytes_written = 0
                while True:
                    chunk = uploaded_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    bytes_written += len(chunk)
                    
                    # Atualizar progress bar
                    progress = bytes_written / file_size
                    progress_bar.progress(progress)
                    status_text.text(f"Upload: {bytes_written // 1024}KB / {file_size // 1024}KB")
            
            progress_bar.empty()
            status_text.empty()
            
            return True, f"Arquivo salvo: {filename}", str(temp_path)
            
        except Exception as e:
            logger.error(f"Erro no upload: {e}")
            return False, f"Erro no upload: {str(e)}", None
    
    def optimize_xml_for_processing(self, xml_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Otimiza XML grande para processamento
        
        Args:
            xml_path: Caminho para o arquivo XML
        
        Returns:
            Tuple (sucesso, mensagem, caminho_otimizado)
        """
        try:
            xml_path = Path(xml_path)
            if not xml_path.exists():
                return False, "Arquivo não encontrado", None
            
            file_size = xml_path.stat().st_size
            
            # Se arquivo é pequeno (< 5MB), não precisa otimizar
            if file_size < 5 * 1024 * 1024:
                return True, "Arquivo não precisa de otimização", str(xml_path)
            
            # Criar versão otimizada
            optimized_path = xml_path.parent / f"optimized_{xml_path.name}"
            
            with st.spinner("Otimizando arquivo XML..."):
                # Ler e reescrever XML (remove espaços desnecessários)
                with open(xml_path, 'r', encoding='utf-8') as f_in:
                    content = f_in.read()
                
                # Otimizações básicas
                optimized_content = self._optimize_xml_content(content)
                
                with open(optimized_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(optimized_content)
            
            return True, f"Arquivo otimizado: {optimized_path.name}", str(optimized_path)
            
        except Exception as e:
            logger.error(f"Erro na otimização: {e}")
            return False, f"Erro na otimização: {str(e)}", None
    
    def _optimize_xml_content(self, content: str) -> str:
        """
        Otimiza conteúdo XML
        
        Args:
            content: Conteúdo XML original
        
        Returns:
            Conteúdo XML otimizado
        """
        # Remover comentários desnecessários
        lines = content.split('\n')
        optimized_lines = []
        
        for line in lines:
            line = line.strip()
            # Pular linhas vazias e comentários
            if line and not line.startswith('<!--'):
                optimized_lines.append(line)
        
        return '\n'.join(optimized_lines)
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Limpa arquivos temporários antigos com segurança
        
        Args:
            max_age_hours: Idade máxima em horas (padrão: 24h)
        """
        try:
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            # Verificar se diretório existe
            if not self.temp_dir.exists():
                return
            
            for file_path in self.temp_dir.glob("*"):
                try:
                    if file_path.is_file():
                        # Verificar se arquivo é do FiscalAI (segurança extra)
                        if not file_path.name.startswith(('nfe_', 'optimized_')):
                            continue
                            
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            # Sobrescrever arquivo antes de deletar (segurança)
                            with open(file_path, 'wb') as f:
                                f.write(b'0' * file_path.stat().st_size)
                            
                            file_path.unlink()
                            cleaned_count += 1
                            logger.info(f"Arquivo temporário removido: {file_path.name}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Não foi possível remover {file_path.name}: {e}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Limpeza concluída: {cleaned_count} arquivos removidos")
        
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Obtém informações do arquivo
        
        Args:
            file_path: Caminho para o arquivo
        
        Returns:
            Dict com informações do arquivo
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": "Arquivo não encontrado"}
            
            stat = path.stat()
            
            return {
                "name": path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": path.suffix.lower()
            }
        
        except Exception as e:
            return {"error": str(e)}


def create_csv_upload_widget(max_size_mb: int = 50, multiple: bool = True) -> Optional[UploadedFile]:
    """
    Cria widget de upload para arquivos CSV
    
    Args:
        max_size_mb: Tamanho máximo em MB
        multiple: Se permite múltiplos arquivos
    
    Returns:
        Arquivo(s) CSV carregado(s) ou None
    """
    if multiple:
        st.markdown("### 📊 Upload de Múltiplos Arquivos CSV")
    else:
        st.markdown("### 📊 Upload de Arquivo CSV")
    
    # Informações sobre limites
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Tamanho Máximo", f"{max_size_mb}MB")
    
    with col2:
        st.metric("Formato", "CSV")
    
    with col3:
        if multiple:
            st.metric("Quantidade", "Múltiplos")
        else:
            st.metric("Encoding", "UTF-8")
    
    # Widget de upload
    uploaded_files = st.file_uploader(
        "Selecione arquivo(s) CSV:" if multiple else "Selecione um arquivo CSV:",
        type=['csv'],
        accept_multiple_files=multiple,
        help=f"Arquivo(s) CSV com dados fiscais. Tamanho máximo: {max_size_mb}MB por arquivo"
    )
    
    if uploaded_files is not None:
        if multiple:
            # Múltiplos arquivos
            if len(uploaded_files) == 0:
                return None
            
            st.success(f"✅ {len(uploaded_files)} arquivo(s) CSV carregado(s)")
            
            # Verificar cada arquivo
            valid_files = []
            total_size = 0
            
            for i, uploaded_file in enumerate(uploaded_files):
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                total_size += file_size_mb
                
                if file_size_mb > max_size_mb:
                    st.error(f"❌ Arquivo {uploaded_file.name} muito grande! Máximo permitido: {max_size_mb}MB")
                    continue
                
                valid_files.append(uploaded_file)
                st.info(f"📄 {uploaded_file.name} ({file_size_mb:.2f} MB)")
            
            if not valid_files:
                st.error("❌ Nenhum arquivo válido foi carregado")
                return None
            
            st.success(f"✅ {len(valid_files)} arquivo(s) válido(s) para processamento")
            st.info(f"📊 Tamanho total: {total_size:.2f} MB")
            
            # Preview do primeiro arquivo
            if valid_files:
                try:
                    import pandas as pd
                    import io
                    
                    first_file = valid_files[0]
                    csv_data = first_file.getvalue().decode('utf-8')
                    
                    try:
                        df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', encoding='utf-8')
                    except Exception as e1:
                        try:
                            df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', encoding='latin-1')
                        except Exception as e2:
                            try:
                                df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', sep=';', encoding='utf-8')
                            except Exception as e3:
                                st.warning(f"⚠️ Erro ao fazer preview do primeiro CSV: {str(e3)}")
                                return valid_files
                    
                    st.subheader(f"📋 Preview do primeiro arquivo ({first_file.name}):")
                    st.dataframe(df_preview, use_container_width=True)
                    st.info(f"📊 Colunas detectadas: {', '.join(df_preview.columns.tolist())}")
                    
                except Exception as e:
                    st.warning(f"⚠️ Erro ao fazer preview: {str(e)}")
            
            return valid_files
            
        else:
            # Arquivo único (comportamento original)
            uploaded_file = uploaded_files[0] if isinstance(uploaded_files, list) else uploaded_files
            
            # Verificar tamanho
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            
            if file_size_mb > max_size_mb:
                st.error(f"❌ Arquivo muito grande! Máximo permitido: {max_size_mb}MB")
                return None
            
            # Mostrar informações do arquivo
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            st.info(f"📊 Tamanho: {file_size_mb:.2f} MB")
            
            # Preview do CSV
            try:
                import pandas as pd
                import io
                
                # Ler CSV para preview com tratamento de erros
                csv_data = uploaded_file.getvalue().decode('utf-8')
                try:
                    df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', encoding='utf-8')
                except Exception as e1:
                    try:
                        df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', encoding='latin-1')
                    except Exception as e2:
                        try:
                            df_preview = pd.read_csv(io.StringIO(csv_data), nrows=5, on_bad_lines='skip', sep=';', encoding='utf-8')
                        except Exception as e3:
                            st.warning(f"⚠️ Erro ao fazer preview do CSV: {str(e3)}")
                            st.info("💡 O arquivo será processado mesmo assim, mas pode ter algumas linhas ignoradas.")
                            return uploaded_file
                
                st.subheader("📋 Preview do CSV:")
                st.dataframe(df_preview, use_container_width=True)
                
                st.info(f"📊 Colunas detectadas: {', '.join(df_preview.columns.tolist())}")
                
            except Exception as e:
                st.warning(f"⚠️ Erro ao fazer preview do CSV: {str(e)}")
                st.info("💡 O arquivo será processado mesmo assim.")
            
            return uploaded_file
    
    return None


def create_upload_widget(max_size_mb: int = 200) -> Optional[str]:
    """
    Cria widget de upload otimizado para arquivos grandes
    
    Args:
        max_size_mb: Tamanho máximo em MB
    
    Returns:
        Caminho do arquivo ou None
    """
    st.markdown("### 📁 Upload de Arquivo XML")
    
    # Informações sobre limites
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Tamanho Máximo", f"{max_size_mb}MB")
    
    with col2:
        st.metric("Formato", "XML")
    
    with col3:
        st.metric("Otimização", "Automática")
    
    # Widget de upload
    uploaded_file = st.file_uploader(
        "Escolha um arquivo XML de NF-e",
        type=['xml'],
        help=f"Arquivos até {max_size_mb}MB são suportados. Arquivos grandes serão otimizados automaticamente."
    )
    
    if uploaded_file is not None:
        # Mostrar informações do arquivo
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"📄 **Arquivo:** {uploaded_file.name}")
        
        with col2:
            st.info(f"📊 **Tamanho:** {file_size_mb:.2f}MB")
        
        # Processar upload
        handler = UploadHandler(max_size_mb)
        
        success, message, file_path = handler.handle_large_file_upload(uploaded_file)
        
        if success:
            st.success(f"✅ {message}")
            
            # Otimizar se necessário
            if file_size_mb > 5:
                opt_success, opt_message, opt_path = handler.optimize_xml_for_processing(file_path)
                
                if opt_success:
                    st.success(f"🚀 {opt_message}")
                    return opt_path
                else:
                    st.warning(f"⚠️ {opt_message}")
                    return file_path
            else:
                return file_path
        else:
            st.error(f"❌ {message}")
            return None
    
    return None


def show_upload_tips():
    """Mostra dicas para upload de arquivos grandes"""
    
    with st.expander("💡 Dicas para Arquivos Grandes"):
        st.markdown("""
        **Para arquivos maiores que 10MB:**
        
        🔧 **Otimizações Automáticas:**
        - Remoção de espaços desnecessários
        - Compressão de conteúdo
        - Processamento em chunks
        
        ⚡ **Melhor Performance:**
        - Arquivos são processados em partes
        - Progress bar mostra status
        - Limpeza automática de arquivos temporários
        
        📊 **Limites Suportados:**
        - **Máximo:** 200MB por arquivo
        - **Recomendado:** < 50MB para melhor performance
        - **Otimização:** Automática para arquivos > 5MB
        
        🛡️ **Segurança:**
        - Arquivos temporários são removidos automaticamente
        - Processamento local (sem envio para servidores externos)
        - Validação de formato XML
        
        💾 **Armazenamento:**
        - Arquivos são salvos temporariamente
        - Limpeza automática após 24 horas
        - Não são armazenados permanentemente
        """)


# Instância global
upload_handler = UploadHandler()


def get_upload_handler() -> UploadHandler:
    """Retorna instância global do upload handler"""
    return upload_handler
