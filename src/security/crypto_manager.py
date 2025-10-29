"""
FiscalAI MVP - Gerenciador de Criptografia
Sistema de criptografia com chaves rotativas e gerenciamento seguro
"""

import os
import base64
import hashlib
import hmac
import secrets
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class EncryptionKey:
    """Chave de criptografia"""
    key_id: str
    key_type: str  # 'symmetric', 'asymmetric', 'hmac'
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    usage_count: int = 0

@dataclass
class EncryptionResult:
    """Resultado da criptografia"""
    encrypted_data: bytes
    key_id: str
    algorithm: str
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None

class CryptoManager:
    """
    Gerenciador de criptografia com chaves rotativas
    
    Funcionalidades:
    - Geração e rotação de chaves
    - Criptografia simétrica e assimétrica
    - Assinatura digital
    - Gerenciamento seguro de chaves
    - Backup criptografado
    """
    
    def __init__(self, keys_dir: str = "security/keys"):
        """
        Inicializa o gerenciador de criptografia
        
        Args:
            keys_dir: Diretório para armazenar chaves
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Chaves ativas
        self.active_keys: Dict[str, EncryptionKey] = {}
        self.key_rotation_interval = timedelta(days=30)  # Rotacionar a cada 30 dias
        self.max_key_usage = 10000  # Máximo de usos por chave
        
        # Configurações de criptografia
        self.symmetric_algorithm = "AES-256-GCM"
        self.asymmetric_key_size = 2048
        self.hmac_algorithm = "SHA-256"
        
        # Thread de rotação de chaves
        self.rotation_thread = threading.Thread(target=self._rotate_keys_periodically, daemon=True)
        self.rotation_thread.start()
        
        # Carregar chaves existentes
        self._load_existing_keys()
        
        # Gerar chaves iniciais se necessário
        if not self.active_keys:
            self._generate_initial_keys()
    
    def _load_existing_keys(self):
        """Carrega chaves existentes do disco"""
        for key_file in self.keys_dir.glob("*.key"):
            try:
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                
                # Decriptografar chave
                decrypted_data = self._decrypt_key_file(key_data)
                key_info = json.loads(decrypted_data.decode('utf-8'))
                
                # Criar objeto de chave
                key = EncryptionKey(
                    key_id=key_info['key_id'],
                    key_type=key_info['key_type'],
                    key_data=base64.b64decode(key_info['key_data']),
                    created_at=datetime.fromisoformat(key_info['created_at']),
                    expires_at=datetime.fromisoformat(key_info['expires_at']) if key_info['expires_at'] else None,
                    is_active=key_info['is_active'],
                    usage_count=key_info.get('usage_count', 0)
                )
                
                self.active_keys[key.key_id] = key
                
            except Exception as e:
                logger.error(f"Erro ao carregar chave {key_file}: {e}")
    
    def _generate_initial_keys(self):
        """Gera chaves iniciais"""
        # Chave simétrica principal
        self._generate_symmetric_key("main_symmetric")
        
        # Chave assimétrica principal
        self._generate_asymmetric_key("main_asymmetric")
        
        # Chave HMAC
        self._generate_hmac_key("main_hmac")
        
        logger.info("Chaves iniciais geradas")
    
    def _generate_symmetric_key(self, key_id: str) -> str:
        """Gera chave simétrica"""
        key_data = Fernet.generate_key()
        
        key = EncryptionKey(
            key_id=key_id,
            key_type="symmetric",
            key_data=key_data,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.key_rotation_interval,
            is_active=True
        )
        
        self.active_keys[key_id] = key
        self._save_key(key)
        
        logger.info(f"Chave simétrica gerada: {key_id}")
        return key_id
    
    def _generate_asymmetric_key(self, key_id: str) -> str:
        """Gera par de chaves assimétricas"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.asymmetric_key_size
        )
        
        public_key = private_key.public_key()
        
        # Serializar chaves
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Armazenar chave privada
        private_key_obj = EncryptionKey(
            key_id=f"{key_id}_private",
            key_type="asymmetric_private",
            key_data=private_pem,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.key_rotation_interval,
            is_active=True
        )
        
        # Armazenar chave pública
        public_key_obj = EncryptionKey(
            key_id=f"{key_id}_public",
            key_type="asymmetric_public",
            key_data=public_pem,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.key_rotation_interval,
            is_active=True
        )
        
        self.active_keys[f"{key_id}_private"] = private_key_obj
        self.active_keys[f"{key_id}_public"] = public_key_obj
        
        self._save_key(private_key_obj)
        self._save_key(public_key_obj)
        
        logger.info(f"Chaves assimétricas geradas: {key_id}")
        return key_id
    
    def _generate_hmac_key(self, key_id: str) -> str:
        """Gera chave HMAC"""
        key_data = secrets.token_bytes(32)  # 256 bits
        
        key = EncryptionKey(
            key_id=key_id,
            key_type="hmac",
            key_data=key_data,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.key_rotation_interval,
            is_active=True
        )
        
        self.active_keys[key_id] = key
        self._save_key(key)
        
        logger.info(f"Chave HMAC gerada: {key_id}")
        return key_id
    
    def encrypt_symmetric(self, data: bytes, key_id: Optional[str] = None) -> EncryptionResult:
        """
        Criptografa dados com chave simétrica
        
        Args:
            data: Dados a serem criptografados
            key_id: ID da chave (usa chave ativa se não especificado)
            
        Returns:
            Resultado da criptografia
        """
        if key_id is None:
            key_id = self._get_active_symmetric_key()
        
        if key_id not in self.active_keys:
            raise ValueError(f"Chave {key_id} não encontrada")
        
        key = self.active_keys[key_id]
        if key.key_type != "symmetric":
            raise ValueError(f"Chave {key_id} não é simétrica")
        
        # Usar Fernet para criptografia simétrica
        fernet = Fernet(key.key_data)
        encrypted_data = fernet.encrypt(data)
        
        # Atualizar contador de uso
        key.usage_count += 1
        
        return EncryptionResult(
            encrypted_data=encrypted_data,
            key_id=key_id,
            algorithm=self.symmetric_algorithm
        )
    
    def decrypt_symmetric(self, encrypted_data: bytes, key_id: str) -> bytes:
        """
        Descriptografa dados com chave simétrica
        
        Args:
            encrypted_data: Dados criptografados
            key_id: ID da chave
            
        Returns:
            Dados descriptografados
        """
        if key_id not in self.active_keys:
            raise ValueError(f"Chave {key_id} não encontrada")
        
        key = self.active_keys[key_id]
        if key.key_type != "symmetric":
            raise ValueError(f"Chave {key_id} não é simétrica")
        
        # Usar Fernet para descriptografia simétrica
        fernet = Fernet(key.key_data)
        return fernet.decrypt(encrypted_data)
    
    def encrypt_asymmetric(self, data: bytes, public_key_id: str) -> EncryptionResult:
        """
        Criptografa dados com chave pública
        
        Args:
            data: Dados a serem criptografados
            public_key_id: ID da chave pública
            
        Returns:
            Resultado da criptografia
        """
        if public_key_id not in self.active_keys:
            raise ValueError(f"Chave pública {public_key_id} não encontrada")
        
        key = self.active_keys[public_key_id]
        if key.key_type != "asymmetric_public":
            raise ValueError(f"Chave {public_key_id} não é pública")
        
        # Carregar chave pública
        public_key = serialization.load_pem_public_key(key.key_data)
        
        # Criptografar dados
        encrypted_data = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptionResult(
            encrypted_data=encrypted_data,
            key_id=public_key_id,
            algorithm="RSA-OAEP"
        )
    
    def decrypt_asymmetric(self, encrypted_data: bytes, private_key_id: str) -> bytes:
        """
        Descriptografa dados com chave privada
        
        Args:
            encrypted_data: Dados criptografados
            private_key_id: ID da chave privada
            
        Returns:
            Dados descriptografados
        """
        if private_key_id not in self.active_keys:
            raise ValueError(f"Chave privada {private_key_id} não encontrada")
        
        key = self.active_keys[private_key_id]
        if key.key_type != "asymmetric_private":
            raise ValueError(f"Chave {private_key_id} não é privada")
        
        # Carregar chave privada
        private_key = serialization.load_pem_private_key(
            key.key_data,
            password=None
        )
        
        # Descriptografar dados
        decrypted_data = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted_data
    
    def sign_data(self, data: bytes, private_key_id: str) -> bytes:
        """
        Assina dados com chave privada
        
        Args:
            data: Dados a serem assinados
            private_key_id: ID da chave privada
            
        Returns:
            Assinatura digital
        """
        if private_key_id not in self.active_keys:
            raise ValueError(f"Chave privada {private_key_id} não encontrada")
        
        key = self.active_keys[private_key_id]
        if key.key_type != "asymmetric_private":
            raise ValueError(f"Chave {private_key_id} não é privada")
        
        # Carregar chave privada
        private_key = serialization.load_pem_private_key(
            key.key_data,
            password=None
        )
        
        # Assinar dados
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature
    
    def verify_signature(self, data: bytes, signature: bytes, public_key_id: str) -> bool:
        """
        Verifica assinatura digital
        
        Args:
            data: Dados originais
            signature: Assinatura a ser verificada
            public_key_id: ID da chave pública
            
        Returns:
            True se assinatura for válida
        """
        if public_key_id not in self.active_keys:
            raise ValueError(f"Chave pública {public_key_id} não encontrada")
        
        key = self.active_keys[public_key_id]
        if key.key_type != "asymmetric_public":
            raise ValueError(f"Chave {public_key_id} não é pública")
        
        try:
            # Carregar chave pública
            public_key = serialization.load_pem_public_key(key.key_data)
            
            # Verificar assinatura
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception:
            return False
    
    def generate_hmac(self, data: bytes, key_id: Optional[str] = None) -> bytes:
        """
        Gera HMAC para dados
        
        Args:
            data: Dados para HMAC
            key_id: ID da chave (usa chave ativa se não especificado)
            
        Returns:
            HMAC dos dados
        """
        if key_id is None:
            key_id = self._get_active_hmac_key()
        
        if key_id not in self.active_keys:
            raise ValueError(f"Chave {key_id} não encontrada")
        
        key = self.active_keys[key_id]
        if key.key_type != "hmac":
            raise ValueError(f"Chave {key_id} não é HMAC")
        
        # Gerar HMAC
        hmac_obj = hmac.new(key.key_data, data, hashlib.sha256)
        return hmac_obj.digest()
    
    def verify_hmac(self, data: bytes, hmac_value: bytes, key_id: str) -> bool:
        """
        Verifica HMAC
        
        Args:
            data: Dados originais
            hmac_value: HMAC a ser verificado
            key_id: ID da chave
            
        Returns:
            True se HMAC for válido
        """
        expected_hmac = self.generate_hmac(data, key_id)
        return hmac.compare_digest(expected_hmac, hmac_value)
    
    def _get_active_symmetric_key(self) -> str:
        """Obtém chave simétrica ativa"""
        for key_id, key in self.active_keys.items():
            if key.key_type == "symmetric" and key.is_active:
                return key_id
        
        # Gerar nova chave se não houver ativa
        return self._generate_symmetric_key("symmetric_" + str(int(time.time())))
    
    def _get_active_hmac_key(self) -> str:
        """Obtém chave HMAC ativa"""
        for key_id, key in self.active_keys.items():
            if key.key_type == "hmac" and key.is_active:
                return key_id
        
        # Gerar nova chave se não houver ativa
        return self._generate_hmac_key("hmac_" + str(int(time.time())))
    
    def _rotate_keys_periodically(self):
        """Rotaciona chaves periodicamente"""
        while True:
            try:
                now = datetime.now()
                
                # Verificar chaves que precisam ser rotacionadas
                for key_id, key in list(self.active_keys.items()):
                    if key.expires_at and now > key.expires_at:
                        self._rotate_key(key_id)
                    elif key.usage_count > self.max_key_usage:
                        self._rotate_key(key_id)
                
                time.sleep(3600)  # Verificar a cada hora
                
            except Exception as e:
                logger.error(f"Erro na rotação de chaves: {e}")
                time.sleep(3600)
    
    def _rotate_key(self, key_id: str):
        """Rotaciona uma chave específica"""
        if key_id not in self.active_keys:
            return
        
        old_key = self.active_keys[key_id]
        
        # Gerar nova chave baseada no tipo
        if old_key.key_type == "symmetric":
            new_key_id = self._generate_symmetric_key(f"symmetric_{int(time.time())}")
        elif old_key.key_type == "asymmetric_private":
            base_id = key_id.replace("_private", "")
            new_key_id = self._generate_asymmetric_key(f"asymmetric_{int(time.time())}")
        elif old_key.key_type == "hmac":
            new_key_id = self._generate_hmac_key(f"hmac_{int(time.time())}")
        else:
            return
        
        # Desativar chave antiga
        old_key.is_active = False
        self._save_key(old_key)
        
        logger.info(f"Chave rotacionada: {key_id} -> {new_key_id}")
    
    def _save_key(self, key: EncryptionKey):
        """Salva chave no disco"""
        key_info = {
            "key_id": key.key_id,
            "key_type": key.key_type,
            "key_data": base64.b64encode(key.key_data).decode('utf-8'),
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "is_active": key.is_active,
            "usage_count": key.usage_count
        }
        
        # Criptografar arquivo de chave
        encrypted_data = self._encrypt_key_file(json.dumps(key_info).encode('utf-8'))
        
        key_file = self.keys_dir / f"{key.key_id}.key"
        with open(key_file, 'wb') as f:
            f.write(encrypted_data)
    
    def _encrypt_key_file(self, data: bytes) -> bytes:
        """Criptografa arquivo de chave"""
        # Usar chave mestre para criptografar arquivos de chave
        master_key = self._get_master_key()
        fernet = Fernet(master_key)
        return fernet.encrypt(data)
    
    def _decrypt_key_file(self, encrypted_data: bytes) -> bytes:
        """Descriptografa arquivo de chave"""
        master_key = self._get_master_key()
        fernet = Fernet(master_key)
        return fernet.decrypt(encrypted_data)
    
    def _get_master_key(self) -> bytes:
        """Obtém chave mestre para criptografar arquivos de chave"""
        master_key_file = self.keys_dir / "master.key"
        
        if master_key_file.exists():
            with open(master_key_file, 'rb') as f:
                return f.read()
        else:
            # Gerar nova chave mestre
            master_key = Fernet.generate_key()
            with open(master_key_file, 'wb') as f:
                f.write(master_key)
            return master_key
    
    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de uma chave"""
        if key_id not in self.active_keys:
            return None
        
        key = self.active_keys[key_id]
        return {
            "key_id": key.key_id,
            "key_type": key.key_type,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "is_active": key.is_active,
            "usage_count": key.usage_count
        }
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """Lista todas as chaves"""
        return [self.get_key_info(key_id) for key_id in self.active_keys.keys()]
    
    def export_keys(self, file_path: str, password: str):
        """Exporta chaves para arquivo criptografado"""
        keys_data = {
            "exported_at": datetime.now().isoformat(),
            "keys": [
                {
                    "key_id": key.key_id,
                    "key_type": key.key_type,
                    "key_data": base64.b64encode(key.key_data).decode('utf-8'),
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "is_active": key.is_active,
                    "usage_count": key.usage_count
                }
                for key in self.active_keys.values()
            ]
        }
        
        # Criptografar com senha
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        
        encrypted_data = fernet.encrypt(json.dumps(keys_data).encode('utf-8'))
        
        with open(file_path, 'wb') as f:
            f.write(salt + encrypted_data)
        
        logger.info(f"Chaves exportadas para {file_path}")


# Instância global do gerenciador de criptografia
_crypto_manager_instance: Optional[CryptoManager] = None

def get_crypto_manager() -> CryptoManager:
    """Retorna instância global do gerenciador"""
    global _crypto_manager_instance
    if _crypto_manager_instance is None:
        _crypto_manager_instance = CryptoManager()
    return _crypto_manager_instance

def encrypt_data(data: bytes, key_type: str = "symmetric") -> EncryptionResult:
    """Função de conveniência para criptografar dados"""
    crypto_manager = get_crypto_manager()
    
    if key_type == "symmetric":
        return crypto_manager.encrypt_symmetric(data)
    elif key_type == "asymmetric":
        public_key_id = crypto_manager._get_active_symmetric_key().replace("symmetric", "asymmetric") + "_public"
        return crypto_manager.encrypt_asymmetric(data, public_key_id)
    else:
        raise ValueError(f"Tipo de chave não suportado: {key_type}")

def decrypt_data(encrypted_data: bytes, key_id: str) -> bytes:
    """Função de conveniência para descriptografar dados"""
    return get_crypto_manager().decrypt_symmetric(encrypted_data, key_id)
