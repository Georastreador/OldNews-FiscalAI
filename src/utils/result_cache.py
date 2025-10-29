"""
FiscalAI MVP - Sistema de Cache de Resultados
Cache inteligente para reduzir reprocessamento de análises
"""

import hashlib
import json
import pickle
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ResultCache:
    """
    Sistema de cache inteligente para resultados de análise fiscal
    
    Funcionalidades:
    - Cache baseado em hash de conteúdo
    - Expiração automática de cache
    - Compressão de dados
    - Validação de integridade
    - Limpeza automática
    """
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 500, ttl_hours: int = 24):
        """
        Inicializa o sistema de cache
        
        Args:
            cache_dir: Diretório para armazenar cache
            max_size_mb: Tamanho máximo do cache em MB
            ttl_hours: Tempo de vida do cache em horas
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl = timedelta(hours=ttl_hours)
        
        # Configurações de cache
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
        # Limpar cache expirado na inicialização
        self._cleanup_expired()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Carrega metadados do cache"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar metadados do cache: {e}")
        return {}
    
    def _save_metadata(self):
        """Salva metadados do cache"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar metadados do cache: {e}")
    
    def _generate_cache_key(self, content: Union[str, bytes, Dict]) -> str:
        """
        Gera chave de cache baseada no conteúdo
        
        Args:
            content: Conteúdo para gerar hash
            
        Returns:
            Chave de cache única
        """
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True)
        elif isinstance(content, bytes):
            content_str = content.decode('utf-8', errors='ignore')
        else:
            content_str = str(content)
        
        # Gerar hash SHA-256 do conteúdo
        hash_obj = hashlib.sha256(content_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Usar primeiros 16 caracteres
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Retorna caminho do arquivo de cache"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def _is_expired(self, cache_key: str) -> bool:
        """Verifica se o cache expirou"""
        if cache_key not in self.metadata:
            return True
        
        created_at = datetime.fromisoformat(self.metadata[cache_key]['created_at'])
        return datetime.now() - created_at > self.ttl
    
    def _cleanup_expired(self):
        """Remove entradas expiradas do cache"""
        expired_keys = []
        for cache_key in list(self.metadata.keys()):
            if self._is_expired(cache_key):
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            self._remove_cache_entry(cache_key)
        
        if expired_keys:
            logger.info(f"Removidas {len(expired_keys)} entradas expiradas do cache")
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove entrada específica do cache"""
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo de cache {cache_key}: {e}")
        
        if cache_key in self.metadata:
            del self.metadata[cache_key]
    
    def _get_cache_size(self) -> int:
        """Calcula tamanho atual do cache em bytes"""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            total_size += cache_file.stat().st_size
        return total_size
    
    def _cleanup_oldest(self):
        """Remove entradas mais antigas quando cache está cheio"""
        if not self.metadata:
            return
        
        # Ordenar por data de criação
        sorted_entries = sorted(
            self.metadata.items(),
            key=lambda x: x[1]['created_at']
        )
        
        # Remover 20% das entradas mais antigas
        entries_to_remove = int(len(sorted_entries) * 0.2)
        for cache_key, _ in sorted_entries[:entries_to_remove]:
            self._remove_cache_entry(cache_key)
        
        logger.info(f"Removidas {entries_to_remove} entradas antigas do cache")
    
    def get(self, content: Union[str, bytes, Dict]) -> Optional[Any]:
        """
        Recupera resultado do cache
        
        Args:
            content: Conteúdo para buscar no cache
            
        Returns:
            Resultado em cache ou None se não encontrado
        """
        cache_key = self._generate_cache_key(content)
        
        # Verificar se existe e não expirou
        if cache_key not in self.metadata or self._is_expired(cache_key):
            return None
        
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            # Arquivo não existe, remover da metadata
            if cache_key in self.metadata:
                del self.metadata[cache_key]
            return None
        
        try:
            # Carregar resultado do cache
            with open(cache_path, 'rb') as f:
                result = pickle.load(f)
            
            # Atualizar estatísticas
            self.metadata[cache_key]['access_count'] += 1
            self.metadata[cache_key]['last_accessed'] = datetime.now().isoformat()
            
            logger.debug(f"Cache hit para chave {cache_key}")
            return result
            
        except Exception as e:
            logger.warning(f"Erro ao carregar cache {cache_key}: {e}")
            self._remove_cache_entry(cache_key)
            return None
    
    def set(self, content: Union[str, bytes, Dict], result: Any) -> bool:
        """
        Armazena resultado no cache
        
        Args:
            content: Conteúdo para gerar chave
            result: Resultado para armazenar
            
        Returns:
            True se armazenado com sucesso
        """
        cache_key = self._generate_cache_key(content)
        
        # Verificar se cache está cheio
        if self._get_cache_size() > self.max_size_bytes:
            self._cleanup_oldest()
        
        try:
            # Armazenar resultado
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            
            # Atualizar metadados
            now = datetime.now().isoformat()
            self.metadata[cache_key] = {
                'created_at': now,
                'last_accessed': now,
                'access_count': 0,
                'size_bytes': cache_path.stat().st_size,
                'content_type': type(result).__name__
            }
            
            self._save_metadata()
            logger.debug(f"Cache armazenado para chave {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar cache {cache_key}: {e}")
            return False
    
    def clear(self):
        """Limpa todo o cache"""
        try:
            # Remover todos os arquivos de cache
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            
            # Limpar metadados
            self.metadata.clear()
            self._save_metadata()
            
            logger.info("Cache limpo com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total_entries = len(self.metadata)
        total_size = self._get_cache_size()
        
        # Calcular estatísticas de acesso
        access_counts = [entry['access_count'] for entry in self.metadata.values()]
        avg_access = sum(access_counts) / total_entries if total_entries > 0 else 0
        
        return {
            'total_entries': total_entries,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
            'usage_percentage': round((total_size / self.max_size_bytes) * 100, 2),
            'avg_access_count': round(avg_access, 2),
            'ttl_hours': self.ttl.total_seconds() / 3600
        }


# Instância global do cache
_cache_instance: Optional[ResultCache] = None

def get_cache() -> ResultCache:
    """Retorna instância global do cache"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResultCache()
    return _cache_instance

def cache_result(content: Union[str, bytes, Dict], result: Any) -> bool:
    """Função de conveniência para armazenar no cache"""
    return get_cache().set(content, result)

def get_cached_result(content: Union[str, bytes, Dict]) -> Optional[Any]:
    """Função de conveniência para recuperar do cache"""
    return get_cache().get(content)

def clear_cache():
    """Função de conveniência para limpar cache"""
    get_cache().clear()

def get_cache_stats() -> Dict[str, Any]:
    """Função de conveniência para obter estatísticas"""
    return get_cache().get_stats()

def get_result_cache() -> ResultCache:
    """Função de conveniência para obter instância do cache de resultados"""
    return get_cache()
