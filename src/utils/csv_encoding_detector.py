"""
OldNews FiscalAI - CSV Encoding Detector
Utilitário para detectar codificação de arquivos CSV automaticamente
"""

import chardet  # pyright: ignore[reportMissingImports]
import pandas as pd
import io
from typing import Tuple, Optional, List


class CSVEncodingDetector:
    """
    Detector automático de codificação para arquivos CSV
    """
    
    def __init__(self):
        """Inicializa o detector"""
        self.encodings_to_try = [
            'utf-8',
            'utf-8-sig',  # UTF-8 com BOM
            'latin-1',
            'cp1252',     # Windows-1252
            'iso-8859-1',
            'cp850',      # DOS
            'cp1250',     # Windows-1250 (Europa Central)
            'cp1251',     # Windows-1251 (Cyrillic)
            'iso-8859-15', # Latin-9
            'mac_roman',   # Mac Roman
            'ascii'
        ]
        
        self.separators_to_try = [',', ';', '\t', '|', ' ']
    
    def detect_encoding(self, file_bytes: bytes) -> Tuple[Optional[str], float]:
        """
        Detecta a codificação de um arquivo usando chardet
        
        Args:
            file_bytes: Bytes do arquivo
            
        Returns:
            Tuple com (codificação_detectada, confiança)
        """
        try:
            result = chardet.detect(file_bytes)
            if result and result['encoding']:
                return result['encoding'], result['confidence']
        except Exception:
            pass
        
        return None, 0.0
    
    def try_decode(self, file_bytes: bytes, encoding: str) -> Optional[str]:
        """
        Tenta decodificar o arquivo com uma codificação específica
        
        Args:
            file_bytes: Bytes do arquivo
            encoding: Codificação a tentar
            
        Returns:
            String decodificada ou None se falhar
        """
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            # Tentar com errors='replace' como fallback
            try:
                return file_bytes.decode(encoding, errors='replace')
            except (UnicodeDecodeError, UnicodeError):
                return None
    
    def find_best_encoding(self, file_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
        """
        Encontra a melhor codificação para o arquivo
        
        Args:
            file_bytes: Bytes do arquivo
            
        Returns:
            Tuple com (codificação, string_decodificada)
        """
        # Primeiro, tentar detecção automática
        detected_encoding, confidence = self.detect_encoding(file_bytes)
        
        if detected_encoding and confidence > 0.7:
            # Se a confiança for alta, tentar usar a codificação detectada
            decoded = self.try_decode(file_bytes, detected_encoding)
            if decoded:
                return detected_encoding, decoded
        
        # Se a detecção automática falhar ou tiver baixa confiança,
        # tentar as codificações conhecidas
        for encoding in self.encodings_to_try:
            decoded = self.try_decode(file_bytes, encoding)
            if decoded:
                return encoding, decoded
        
        return None, None
    
    def find_best_csv_config(self, file_bytes: bytes) -> Tuple[Optional[str], Optional[str], Optional[pd.DataFrame]]:
        """
        Encontra a melhor configuração para ler o CSV
        
        Args:
            file_bytes: Bytes do arquivo
            
        Returns:
            Tuple com (codificação, separador, dataframe)
        """
        # Encontrar melhor codificação
        encoding, decoded_content = self.find_best_encoding(file_bytes)
        
        if not encoding or not decoded_content:
            return None, None, None
        
        # Tentar diferentes separadores
        for separator in self.separators_to_try:
            try:
                df = pd.read_csv(
                    io.StringIO(decoded_content),
                    sep=separator,
                    encoding=encoding,
                    on_bad_lines='skip',
                    nrows=10  # Ler apenas as primeiras 10 linhas para teste
                )
                
                # Se tem mais de uma coluna e não está vazio, provavelmente é o separador correto
                if len(df.columns) > 1 and not df.empty:
                    return encoding, separator, df
                    
            except Exception:
                continue
        
        return None, None, None
    
    def read_csv_robust(self, file_bytes: bytes, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
        """
        Lê CSV de forma robusta, detectando automaticamente codificação e separador
        
        Args:
            file_bytes: Bytes do arquivo
            **kwargs: Argumentos adicionais para pd.read_csv
            
        Returns:
            Tuple com (dataframe, codificação_usada, separador_usado)
        """
        encoding, separator, df = self.find_best_csv_config(file_bytes)
        
        if not encoding or not separator or df is None:
            return None, None, None
        
        # Ler o arquivo completo com a configuração detectada
        try:
            decoded_content = self.try_decode(file_bytes, encoding)
            if not decoded_content:
                return None, None, None
            
            full_df = pd.read_csv(
                io.StringIO(decoded_content),
                sep=separator,
                encoding=encoding,
                on_bad_lines='skip',
                **kwargs
            )
            
            return full_df, encoding, separator
            
        except Exception:
            return None, None, None


def detect_csv_encoding(file_bytes: bytes) -> Tuple[Optional[str], Optional[str], Optional[pd.DataFrame]]:
    """
    Função utilitária para detectar codificação de CSV
    
    Args:
        file_bytes: Bytes do arquivo
        
    Returns:
        Tuple com (codificação, separador, dataframe)
    """
    detector = CSVEncodingDetector()
    return detector.find_best_csv_config(file_bytes)


def read_csv_robust(file_bytes: bytes, **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
    """
    Função utilitária para ler CSV de forma robusta
    
    Args:
        file_bytes: Bytes do arquivo
        **kwargs: Argumentos adicionais para pd.read_csv
        
    Returns:
        Tuple com (dataframe, codificação_usada, separador_usado)
    """
    detector = CSVEncodingDetector()
    return detector.read_csv_robust(file_bytes, **kwargs)
