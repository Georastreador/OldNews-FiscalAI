#!/usr/bin/env python3
"""
FiscalAI MVP - Verificação de Segurança
Script para verificar configurações de segurança da aplicação
"""

import os
import sys
from pathlib import Path
import subprocess
import json
from typing import Dict, List, Tuple

class SecurityChecker:
    """Verificador de segurança para FiscalAI MVP"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def check_production_mode(self) -> bool:
        """Verifica se modo de produção está ativo"""
        production = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
        debug = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true'
        
        if production and debug:
            self.issues.append("🚨 CRÍTICO: Debug ativo em modo de produção")
            return False
        elif production:
            self.passed.append("✅ Modo de produção ativo")
            return True
        else:
            self.warnings.append("⚠️ Modo de produção não ativo")
            return True
    
    def check_file_permissions(self) -> bool:
        """Verifica permissões de arquivos sensíveis"""
        sensitive_files = [
            'production.env',
            '.env',
            'debug_config_example.env'
        ]
        
        all_good = True
        for file_name in sensitive_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                stat = file_path.stat()
                mode = oct(stat.st_mode)[-3:]
                if mode != '600':
                    self.warnings.append(f"⚠️ Arquivo {file_name} com permissões {mode} (deveria ser 600)")
                    all_good = False
                else:
                    self.passed.append(f"✅ Permissões corretas para {file_name}")
        
        return all_good
    
    def check_temp_directory(self) -> bool:
        """Verifica configuração do diretório temporário"""
        temp_dir = Path.home() / ".fiscalai"
        if temp_dir.exists():
            stat = temp_dir.stat()
            mode = oct(stat.st_mode)[-3:]
            if mode not in ['700', '755']:
                self.warnings.append(f"⚠️ Diretório temporário com permissões {mode}")
                return False
            else:
                self.passed.append("✅ Diretório temporário com permissões adequadas")
                return True
        else:
            self.passed.append("✅ Diretório temporário não existe (será criado com permissões corretas)")
            return True
    
    def check_xml_security(self) -> bool:
        """Verifica se proteções XML estão implementadas"""
        xml_parser = self.project_root / 'src' / 'utils' / 'xml_parser.py'
        if xml_parser.exists():
            content = xml_parser.read_text()
            if 'disable_entities=True' in content:
                self.passed.append("✅ Proteção XXE implementada no parser XML")
                return True
            else:
                self.issues.append("🚨 CRÍTICO: Proteção XXE não implementada")
                return False
        return True
    
    def check_upload_security(self) -> bool:
        """Verifica segurança de uploads"""
        upload_handler = self.project_root / 'src' / 'utils' / 'upload_handler.py'
        if upload_handler.exists():
            content = upload_handler.read_text()
            if 'os.path.basename' in content and '..' in content:
                self.passed.append("✅ Proteção contra path traversal implementada")
                return True
            else:
                self.issues.append("🚨 CRÍTICO: Proteção contra path traversal não implementada")
                return False
        return True
    
    def check_debug_protection(self) -> bool:
        """Verifica proteção de debug em produção"""
        files_to_check = [
            'ui/app.py',
            'src/detectors/orquestrador_deteccao.py',
            'src/detectors/detector_ncm_incorreto.py',
            'src/detectors/detector_valor_inconsistente.py'
        ]
        
        all_good = True
        for file_path in files_to_check:
            full_path = self.project_root / file_path
            if full_path.exists():
                content = full_path.read_text()
                if 'PRODUCTION_MODE' in content and 'and not PRODUCTION_MODE' in content:
                    self.passed.append(f"✅ Proteção de debug em {file_path}")
                else:
                    self.issues.append(f"🚨 CRÍTICO: Proteção de debug não implementada em {file_path}")
                    all_good = False
        
        return all_good
    
    def check_dependencies(self) -> bool:
        """Verifica dependências de segurança"""
        requirements = self.project_root / 'requirements.txt'
        if requirements.exists():
            content = requirements.read_text()
            # Verificar se dependências conhecidas por vulnerabilidades estão presentes
            vulnerable_deps = ['xmltodict<0.13.0']  # Versões antigas podem ter vulnerabilidades
            
            for dep in vulnerable_deps:
                if dep in content:
                    self.warnings.append(f"⚠️ Dependência potencialmente vulnerável: {dep}")
                    return False
            
            self.passed.append("✅ Dependências verificadas")
            return True
        return True
    
    def run_all_checks(self) -> Dict[str, any]:
        """Executa todas as verificações de segurança"""
        print("🔒 Iniciando verificação de segurança do FiscalAI MVP...\n")
        
        checks = [
            ("Modo de Produção", self.check_production_mode),
            ("Permissões de Arquivo", self.check_file_permissions),
            ("Diretório Temporário", self.check_temp_directory),
            ("Segurança XML", self.check_xml_security),
            ("Segurança de Upload", self.check_upload_security),
            ("Proteção de Debug", self.check_debug_protection),
            ("Dependências", self.check_dependencies)
        ]
        
        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self.issues.append(f"🚨 ERRO em {check_name}: {str(e)}")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, any]:
        """Gera relatório de segurança"""
        total_checks = len(self.passed) + len(self.warnings) + len(self.issues)
        critical_issues = len([i for i in self.issues if '🚨 CRÍTICO' in i])
        
        # Calcular score de segurança
        if total_checks == 0:
            score = 0
        else:
            score = (len(self.passed) / total_checks) * 100
        
        # Determinar status
        if critical_issues > 0:
            status = "🔴 CRÍTICO"
        elif len(self.issues) > 0:
            status = "🟡 ATENÇÃO"
        elif len(self.warnings) > 0:
            status = "🟠 AVISO"
        else:
            status = "🟢 SEGURO"
        
        report = {
            'status': status,
            'score': round(score, 1),
            'total_checks': total_checks,
            'passed': len(self.passed),
            'warnings': len(self.warnings),
            'issues': len(self.issues),
            'critical_issues': critical_issues,
            'details': {
                'passed': self.passed,
                'warnings': self.warnings,
                'issues': self.issues
            }
        }
        
        return report
    
    def print_report(self, report: Dict[str, any]):
        """Imprime relatório formatado"""
        print("=" * 60)
        print("🔒 RELATÓRIO DE SEGURANÇA - FISCALAI MVP")
        print("=" * 60)
        print(f"Status: {report['status']}")
        print(f"Score de Segurança: {report['score']}/100")
        print(f"Verificações: {report['passed']} ✅ | {report['warnings']} ⚠️ | {report['issues']} 🚨")
        print()
        
        if report['details']['passed']:
            print("✅ VERIFICAÇÕES APROVADAS:")
            for item in report['details']['passed']:
                print(f"  {item}")
            print()
        
        if report['details']['warnings']:
            print("⚠️ AVISOS:")
            for item in report['details']['warnings']:
                print(f"  {item}")
            print()
        
        if report['details']['issues']:
            print("🚨 PROBLEMAS ENCONTRADOS:")
            for item in report['details']['issues']:
                print(f"  {item}")
            print()
        
        # Recomendações
        print("📋 RECOMENDAÇÕES:")
        if report['critical_issues'] > 0:
            print("  🚨 CORREÇÕES CRÍTICAS NECESSÁRIAS ANTES DA PRODUÇÃO")
        if report['warnings'] > 0:
            print("  ⚠️ Revisar avisos para melhorar segurança")
        if report['score'] < 80:
            print("  📈 Implementar melhorias de segurança adicionais")
        if report['score'] >= 90:
            print("  🎉 Excelente nível de segurança!")
        
        print()
        print("=" * 60)


def main():
    """Função principal"""
    checker = SecurityChecker()
    report = checker.run_all_checks()
    checker.print_report(report)
    
    # Exit code baseado no status
    if report['critical_issues'] > 0:
        sys.exit(1)  # Crítico
    elif report['issues'] > 0:
        sys.exit(2)  # Problemas
    else:
        sys.exit(0)  # OK


if __name__ == "__main__":
    main()
