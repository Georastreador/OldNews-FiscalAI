#!/usr/bin/env python3
"""
Conta o número de NFs em um arquivo XML usando o parser aprimorado do projeto.

Uso:
  python scripts/count_nfes.py /caminho/para/arquivo.xml
"""

import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/count_nfes.py /caminho/para/arquivo.xml")
        sys.exit(1)
    xml_path = Path(sys.argv[1])
    if not xml_path.exists():
        print(f"Arquivo não encontrado: {xml_path}")
        sys.exit(1)

    try:
        # Importar parser do projeto
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # OldNews-FiscalAI/
        from src.utils.enhanced_multiple_parser import parse_enhanced_multiple
        nfes, doc_type, desc = parse_enhanced_multiple(str(xml_path))
        print(f"Tipo detectado: {doc_type} - {desc}")
        print(f"Total de NFs encontradas: {len(nfes)}")
    except Exception:
        # Fallback sem dependências: contagem regex
        txt = xml_path.read_text(encoding="utf-8", errors="ignore")
        import re
        nfe = re.findall(r'<infNFe[\s\S]*?</infNFe>', txt, re.IGNORECASE)
        nfse = re.findall(r'<CompNfse[\s\S]*?</CompNfse>', txt, re.IGNORECASE)
        total = len(nfe) + len(nfse)
        if total == 0:
            total = len(re.findall(r'<NFe[\s\S]*?</NFe>', txt, re.IGNORECASE))
        print("Tipo detectado: auto (fallback)")
        print(f"Total de NFs encontradas: {total}")

if __name__ == "__main__":
    main()


