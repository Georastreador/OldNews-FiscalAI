import pandas as pd
import re
import os

class LeitorTabelasFiscais:
    """Classe para leitura e processamento de tabelas NCM e CFOP"""
    
    def __init__(self):
        self.df_ncm = None
        self.df_cfop = None
        self.df_cfop_categorizado = None
    
    def carregar_cfop_estruturado(self, caminho):
        """
        Carrega arquivo CFOP com estrutura de categorias
        (formato específico da Receita Federal com agrupamentos)
        """
        print(f"\n{'='*70}")
        print(f"CARREGANDO TABELA CFOP ESTRUTURADA")
        print(f"Arquivo: {os.path.basename(caminho)}")
        print(f"{'='*70}")
        
        # Lê o arquivo
        with open(caminho, 'r', encoding='utf-8-sig') as f:
            linhas = f.readlines()
        
        dados = []
        categoria_atual = None
        codigo_categoria = None
        
        for linha in linhas:
            linha = linha.strip()
            
            # Ignora linhas vazias ou cabeçalhos
            if not linha or linha.startswith('Tabela') or linha.startswith('Código CFOP'):
                continue
            
            # Detecta linha de categoria (termina com "Código XX:")
            if re.search(r'Código \d{2}:', linha):
                # Extrai categoria e código
                match = re.search(r'(.+?)\s*-\s*Código (\d{2}):', linha)
                if match:
                    categoria_atual = match.group(1).strip()
                    codigo_categoria = match.group(2).strip()
                continue
            
            # Processa linhas de CFOP
            # Formato: "CÓDIGO\tDescrição"
            partes = linha.split('\t')
            if len(partes) >= 2:
                codigo = partes[0].strip()
                descricao = '\t'.join(partes[1:]).strip()
                
                # Valida se é um código CFOP válido (4 dígitos)
                if re.match(r'^\d{4}$', codigo):
                    dados.append({
                        'codigo_cfop': codigo,
                        'descricao': descricao,
                        'categoria': categoria_atual,
                        'codigo_categoria': codigo_categoria
                    })
        
        self.df_cfop = pd.DataFrame(dados)
        
        print(f"✓ Carregado com sucesso!")
        print(f"  Total de CFOPs: {len(self.df_cfop):,}")
        print(f"  Categorias encontradas: {self.df_cfop['categoria'].nunique()}")
        print(f"\nCategorias disponíveis:")
        for cat in self.df_cfop['categoria'].unique():
            cod_cat = self.df_cfop[self.df_cfop['categoria'] == cat]['codigo_categoria'].iloc[0]
            qtd = len(self.df_cfop[self.df_cfop['categoria'] == cat])
            print(f"  [{cod_cat}] {cat}: {qtd} CFOPs")
        
        return self.df_cfop
    
    def carregar_ncm(self, caminho, otimizar_memoria=True):
        """
        Carrega tabela NCM/Produtos de arquivo TXT, CSV ou XLSX
        Para arquivos grandes (>50MB), usa otimizações de memória
        """
        print(f"\n{'='*70}")
        print(f"CARREGANDO TABELA DE PRODUTOS/NCM")
        print(f"Arquivo: {os.path.basename(caminho)}")
        
        # Verifica tamanho do arquivo
        tamanho_mb = os.path.getsize(caminho) / (1024 * 1024)
        print(f"Tamanho: {tamanho_mb:.1f} MB")
        print(f"{'='*70}")
        
        if tamanho_mb > 50:
            print("⚠ Arquivo grande detectado. Usando modo otimizado...")
            otimizar_memoria = True
        
        extensao = caminho.lower().split('.')[-1]
        
        try:
            if extensao in ['xlsx', 'xls']:
                print("Lendo arquivo Excel... (pode levar alguns minutos)")
                self.df_ncm = pd.read_excel(
                    caminho, 
                    dtype=str,
                    engine='openpyxl' if extensao == 'xlsx' else 'xlrd'
                )
                
            elif extensao in ['csv', 'txt']:
                print("Detectando formato do arquivo...")
                
                # Lê primeira linha para detectar separador
                with open(caminho, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    primeira_linha = f.readline()
                
                # Detecta separador (prioriza TAB para este tipo de arquivo)
                separador = '\t'  # TAB é o padrão para este formato
                if '\t' not in primeira_linha:
                    for sep in [';', ',', '|']:
                        if sep in primeira_linha:
                            separador = sep
                            break
                
                sep_nome = 'TAB' if separador == '\t' else f"'{separador}'"
                print(f"  Separador detectado: {sep_nome}")
                print("  Carregando dados... (pode levar alguns minutos)")
                
                # Lê o arquivo com configurações otimizadas
                self.df_ncm = pd.read_csv(
                    caminho,
                    sep=separador,
                    dtype=str,
                    encoding='utf-8-sig',
                    on_bad_lines='skip',
                    engine='python'  # Melhor para arquivos grandes
                )
            
            print(f"✓ Arquivo carregado!")
            print(f"  Processando dados...")
            
            # Remove espaços em branco das colunas
            self.df_ncm.columns = self.df_ncm.columns.str.strip()
            
            # Identifica coluna de código NCM
            possiveis_nomes = ['ncm', 'codigo', 'cod', 'código', 'codigo_ncm', 'co_ncm', 'co_sh']
            col_codigo = None
            
            for nome in possiveis_nomes:
                cols_encontradas = [c for c in self.df_ncm.columns if nome == c.lower()]
                if cols_encontradas:
                    col_codigo = cols_encontradas[0]
                    break
            
            if col_codigo:
                print(f"  Coluna NCM identificada: '{col_codigo}'")
                # Padroniza NCM: remove não-numéricos e preenche com zeros
                self.df_ncm[col_codigo] = (
                    self.df_ncm[col_codigo]
                    .astype(str)
                    .str.replace(r'\D', '', regex=True)
                    .str.zfill(8)
                )
                
                # Remove registros sem NCM válido
                ncms_validos_antes = len(self.df_ncm)
                self.df_ncm = self.df_ncm[self.df_ncm[col_codigo].str.len() == 8]
                removidos = ncms_validos_antes - len(self.df_ncm)
                if removidos > 0:
                    print(f"  Removidos {removidos:,} registros com NCM inválido")
            
            # Identifica outras colunas importantes
            col_descricao = None
            for nome in ['xprod', 'descricao', 'produto', 'desc']:
                cols_encontradas = [c for c in self.df_ncm.columns if nome == c.lower()]
                if cols_encontradas:
                    col_descricao = cols_encontradas[0]
                    break
            
            print(f"\n✓ Carregado com sucesso!")
            print(f"  Total de Produtos: {len(self.df_ncm):,}")
            print(f"  NCMs únicos: {self.df_ncm[col_codigo].nunique() if col_codigo else 'N/A':,}")
            print(f"\nColunas disponíveis:")
            for i, col in enumerate(self.df_ncm.columns, 1):
                qtd_preenchidos = self.df_ncm[col].notna().sum()
                print(f"  {i}. '{col}' ({qtd_preenchidos:,} registros)")
            
            # Mostra estatísticas por categoria se existir coluna 'rotulo' ou 'Item'
            if 'rotulo' in self.df_ncm.columns:
                print(f"\nCategorias/Rótulos encontrados:")
                top_rotulos = self.df_ncm['rotulo'].value_counts().head(10)
                for rotulo, qtd in top_rotulos.items():
                    print(f"  • {rotulo}: {qtd:,} produtos")
                if len(self.df_ncm['rotulo'].value_counts()) > 10:
                    print(f"  ... e mais {len(self.df_ncm['rotulo'].value_counts()) - 10} categorias")
            
            return self.df_ncm
            
        except Exception as e:
            print(f"\n✗ Erro ao carregar arquivo: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def buscar_cfop(self, codigo):
        """Busca informações de um código CFOP"""
        if self.df_cfop is None:
            print("⚠ Tabela CFOP não foi carregada.")
            return None
        
        codigo = str(codigo).zfill(4)
        resultado = self.df_cfop[self.df_cfop['codigo_cfop'] == codigo]
        
        if len(resultado) > 0:
            return resultado.iloc[0].to_dict()
        return None
    
    def buscar_ncm(self, codigo):
        """Busca informações de um código NCM"""
        if self.df_ncm is None:
            print("⚠ Tabela de produtos/NCM não foi carregada.")
            return None
        
        # Limpa o código NCM
        codigo = str(codigo).replace('.', '').replace('-', '').replace(' ', '').zfill(8)
        
        # Encontra coluna de código NCM
        col_codigo = None
        for nome in ['ncm', 'codigo', 'cod', 'código', 'codigo_ncm', 'co_ncm', 'co_sh']:
            cols_encontradas = [c for c in self.df_ncm.columns if nome == c.lower()]
            if cols_encontradas:
                col_codigo = cols_encontradas[0]
                break
        
        if col_codigo:
            # Busca todos os produtos com esse NCM
            resultado = self.df_ncm[self.df_ncm[col_codigo] == codigo]
            
            if len(resultado) > 0:
                return resultado
            
            # Se não encontrou exato, tenta busca por prefixo (posição - 6 dígitos)
            if len(codigo) == 8:
                codigo_6 = codigo[:6]
                resultado = self.df_ncm[self.df_ncm[col_codigo].str.startswith(codigo_6)]
                if len(resultado) > 0:
                    print(f"⚠ NCM exato não encontrado. Encontrados {len(resultado)} produtos na posição {codigo_6}xx")
                    return resultado
        
        return None
    
    def buscar_produto(self, termo_busca):
        """Busca produtos por termo na descrição"""
        if self.df_ncm is None:
            print("⚠ Tabela de produtos não foi carregada.")
            return None
        
        # Identifica coluna de descrição
        col_descricao = None
        for nome in ['xprod', 'descricao', 'produto', 'desc', 'nome']:
            cols_encontradas = [c for c in self.df_ncm.columns if nome == c.lower()]
            if cols_encontradas:
                col_descricao = cols_encontradas[0]
                break
        
        if col_descricao:
            # Busca case-insensitive
            mascara = self.df_ncm[col_descricao].str.contains(
                termo_busca, 
                case=False, 
                na=False,
                regex=False
            )
            resultado = self.df_ncm[mascara]
            
            if len(resultado) > 0:
                print(f"✓ Encontrados {len(resultado)} produtos com '{termo_busca}'")
                return resultado
            else:
                print(f"✗ Nenhum produto encontrado com '{termo_busca}'")
        else:
            print("⚠ Coluna de descrição não identificada")
        
        return None
    
    def listar_produtos_por_ncm(self, codigo_ncm):
        """Lista todos os produtos de um NCM específico"""
        resultado = self.buscar_ncm(codigo_ncm)
        
        if resultado is not None and len(resultado) > 0:
            print(f"\n{'='*70}")
            print(f"PRODUTOS COM NCM {codigo_ncm}")
            print(f"{'='*70}")
            print(f"Total: {len(resultado)} produtos\n")
            
            # Identifica colunas
            col_ncm = None
            col_desc = None
            col_rotulo = None
            
            for c in resultado.columns:
                c_lower = c.lower()
                if c_lower == 'ncm' or 'ncm' in c_lower:
                    col_ncm = c
                elif c_lower in ['xprod', 'descricao', 'produto']:
                    col_desc = c
                elif c_lower == 'rotulo':
                    col_rotulo = c
            
            # Mostra os produtos
            for idx, row in resultado.head(20).iterrows():
                if col_desc:
                    print(f"• {row[col_desc]}")
                if col_rotulo:
                    print(f"  Categoria: {row[col_rotulo]}")
                if col_ncm:
                    print(f"  NCM: {row[col_ncm]}")
                print()
            
            if len(resultado) > 20:
                print(f"... e mais {len(resultado) - 20} produtos")
        
        return resultado
    
    def estatisticas_ncm(self):
        """Mostra estatísticas da tabela de produtos/NCM"""
        if self.df_ncm is None:
            print("⚠ Tabela de produtos não foi carregada.")
            return
        
        print(f"\n{'='*70}")
        print("ESTATÍSTICAS DA BASE DE PRODUTOS")
        print(f"{'='*70}")
        
        # Identifica colunas
        col_ncm = None
        col_rotulo = None
        
        for c in self.df_ncm.columns:
            c_lower = c.lower()
            if c_lower == 'ncm':
                col_ncm = c
            elif c_lower == 'rotulo':
                col_rotulo = c
        
        print(f"Total de Produtos: {len(self.df_ncm):,}")
        
        if col_ncm:
            print(f"NCMs únicos: {self.df_ncm[col_ncm].nunique():,}")
            print(f"\nTop 10 NCMs mais usados:")
            top_ncms = self.df_ncm[col_ncm].value_counts().head(10)
            for ncm, qtd in top_ncms.items():
                print(f"  {ncm}: {qtd:,} produtos")
        
        if col_rotulo:
            print(f"\nDistribuição por Categoria:")
            categorias = self.df_ncm[col_rotulo].value_counts()
            for cat, qtd in categorias.items():
                percentual = (qtd / len(self.df_ncm)) * 100
                print(f"  • {cat}: {qtd:,} produtos ({percentual:.1f}%)")
    
    def listar_cfop_por_categoria(self, codigo_categoria):
        """Lista todos os CFOPs de uma categoria específica"""
        if self.df_cfop is None:
            print("⚠ Tabela CFOP não foi carregada.")
            return None
        
        codigo_categoria = str(codigo_categoria).zfill(2)
        resultado = self.df_cfop[self.df_cfop['codigo_categoria'] == codigo_categoria]
        
        if len(resultado) > 0:
            return resultado
        return None
    
    def validar_cfop(self, codigo):
        """Valida se um CFOP existe e retorna suas informações"""
        info = self.buscar_cfop(codigo)
        
        if info:
            print(f"\n✓ CFOP {codigo} - VÁLIDO")
            print(f"  Descrição: {info['descricao']}")
            print(f"  Categoria: {info['categoria']}")
            print(f"  Código Categoria: {info['codigo_categoria']}")
            return True
        else:
            print(f"\n✗ CFOP {codigo} - NÃO ENCONTRADO")
            return False
    
    def validar_ncm(self, codigo):
        """Valida se um NCM existe e mostra produtos associados"""
        resultado = self.buscar_ncm(codigo)
        
        if resultado is not None and len(resultado) > 0:
            print(f"\n✓ NCM {codigo} - ENCONTRADO")
            print(f"  Total de produtos: {len(resultado)}")
            
            # Mostra alguns exemplos
            col_desc = None
            for c in resultado.columns:
                if c.lower() in ['xprod', 'descricao', 'produto']:
                    col_desc = c
                    break
            
            if col_desc:
                print(f"\n  Exemplos de produtos:")
                for idx, row in resultado.head(5).iterrows():
                    print(f"    • {row[col_desc]}")
            
            return True
        else:
            print(f"\n✗ NCM {codigo} - NÃO ENCONTRADO")
            return False
    
    def visualizar_amostra_cfop(self, n=10):
        """Exibe amostra da tabela CFOP"""
        if self.df_cfop is None:
            print("⚠ Tabela CFOP não foi carregada.")
            return
        
        print(f"\n{'='*70}")
        print(f"AMOSTRA DA TABELA CFOP (primeiras {n} linhas)")
        print(f"{'='*70}\n")
        
        for idx, row in self.df_cfop.head(n).iterrows():
            print(f"CFOP: {row['codigo_cfop']}")
            print(f"  Descrição: {row['descricao']}")
            print(f"  Categoria: [{row['codigo_categoria']}] {row['categoria']}")
            print()
    
    def visualizar_amostra_ncm(self, n=10):
        """Exibe amostra da tabela de produtos/NCM"""
        if self.df_ncm is None:
            print("⚠ Tabela de produtos não foi carregada.")
            return
        
        print(f"\n{'='*70}")
        print(f"AMOSTRA DA TABELA DE PRODUTOS (primeiras {n} linhas)")
        print(f"{'='*70}\n")
        
        # Identifica colunas principais
        col_ncm = None
        col_desc = None
        col_rotulo = None
        
        for c in self.df_ncm.columns:
            c_lower = c.lower()
            if c_lower == 'ncm':
                col_ncm = c
            elif c_lower in ['xprod', 'descricao', 'produto']:
                col_desc = c
            elif c_lower == 'rotulo':
                col_rotulo = c
        
        # Mostra os dados de forma organizada
        for idx, row in self.df_ncm.head(n).iterrows():
            if col_desc:
                print(f"Produto: {row[col_desc]}")
            if col_ncm:
                print(f"  NCM: {row[col_ncm]}")
            if col_rotulo:
                print(f"  Categoria: {row[col_rotulo]}")
            print()
    
    def exportar_cfop_csv(self, caminho_saida="cfop_processada.csv"):
        """Exporta tabela CFOP processada para CSV"""
        if self.df_cfop is None:
            print("⚠ Tabela CFOP não disponível para exportação.")
            return
        
        self.df_cfop.to_csv(caminho_saida, index=False, encoding='utf-8-sig', sep=';')
        print(f"\n✓ Tabela CFOP exportada para: {caminho_saida}")
    
    def exportar_ncm_csv(self, caminho_saida="ncm_processada.csv"):
        """Exporta tabela NCM processada para CSV"""
        if self.df_ncm is None:
            print("⚠ Tabela NCM não disponível para exportação.")
            return
        
        self.df_ncm.to_csv(caminho_saida, index=False, encoding='utf-8-sig', sep=';')
        print(f"\n✓ Tabela NCM exportada para: {caminho_saida}")
    
    def estatisticas_cfop(self):
        """Mostra estatísticas da tabela CFOP"""
        if self.df_cfop is None:
            print("⚠ Tabela CFOP não foi carregada.")
            return
        
        print(f"\n{'='*70}")
        print("ESTATÍSTICAS DA TABELA CFOP")
        print(f"{'='*70}")
        print(f"Total de CFOPs: {len(self.df_cfop):,}")
        print(f"Total de Categorias: {self.df_cfop['categoria'].nunique()}")
        print(f"\nDistribuição por Categoria:")
        
        for cat in sorted(self.df_cfop['categoria'].unique()):
            cod_cat = self.df_cfop[self.df_cfop['categoria'] == cat]['codigo_categoria'].iloc[0]
            qtd = len(self.df_cfop[self.df_cfop['categoria'] == cat])
            print(f"  [{cod_cat}] {cat}: {qtd} CFOPs")


# ==============================================================================
# EXEMPLO DE USO
# ==============================================================================

if __name__ == "__main__":
    # Instancia o leitor
    leitor = LeitorTabelasFiscais()
    
    # Defina os caminhos dos seus arquivos
    CAMINHO_CFOP = "cfop.txt"           # Arquivo CFOP estruturado
    CAMINHO_NCM = "produtos_ncm.txt"    # Arquivo de produtos com NCM (204MB)
    
    print("="*70)
    print("SISTEMA DE LEITURA DE TABELAS FISCAIS - NCM E CFOP")
    print("="*70)
    
    # ========== CARREGA CFOP ==========
    try:
        df_cfop = leitor.carregar_cfop_estruturado(CAMINHO_CFOP)
        leitor.visualizar_amostra_cfop(n=3)
        leitor.estatisticas_cfop()
    except FileNotFoundError:
        print("\n⚠ Arquivo CFOP não encontrado. Pulando...")
    except Exception as e:
        print(f"Erro ao carregar CFOP: {e}")
    
    # ========== CARREGA NCM/PRODUTOS ==========
    try:
        df_ncm = leitor.carregar_ncm(CAMINHO_NCM)
        leitor.visualizar_amostra_ncm(n=5)
        leitor.estatisticas_ncm()
    except FileNotFoundError:
        print("\n⚠ Arquivo de produtos/NCM não encontrado. Pulando...")
    except Exception as e:
        print(f"Erro ao carregar produtos/NCM: {e}")
    
    # ========== EXEMPLOS DE VALIDAÇÃO CFOP ==========
    print(f"\n{'='*70}")
    print("EXEMPLOS DE VALIDAÇÃO DE CFOP")
    print(f"{'='*70}")
    
    leitor.validar_cfop("1102")  # Compra para comercialização
    leitor.validar_cfop("2101")  # Compra para industrialização
    leitor.validar_cfop("5102")  # Venda de mercadoria (exemplo - pode não estar na tabela)
    
    # ========== EXEMPLOS DE BUSCA DE NCM ==========
    print(f"\n{'='*70}")
    print("EXEMPLOS DE BUSCA DE NCM E PRODUTOS")
    print(f"{'='*70}")
    
    # Valida NCMs específicos
    leitor.validar_ncm("22072020")  # Aguardente
    leitor.validar_ncm("22042911")  # Vinhos
    
    # Busca produtos por termo
    print(f"\n{'='*70}")
    print("BUSCA DE PRODUTOS POR TERMO")
    print(f"{'='*70}")
    
    resultado = leitor.buscar_produto("YPIOCA")
    if resultado is not None and len(resultado) > 0:
        print(f"\nPrimeiros 5 produtos encontrados:")
        for idx, row in resultado.head(5).iterrows():
            print(f"  • {row['XPROD']} (NCM: {row['NCM']})")
    
    # Lista todos os produtos de um NCM
    leitor.listar_produtos_por_ncm("22072020")
    
    # ========== LISTA CFOPs POR CATEGORIA ==========
    print(f"\n{'='*70}")
    print("EXEMPLO: CFOPs DE AQUISIÇÃO PARA REVENDA (Categoria 01)")
    print(f"{'='*70}")
    
    cfops_cat_01 = leitor.listar_cfop_por_categoria("01")
    if cfops_cat_01 is not None:
        print(f"\nTotal: {len(cfops_cat_01)} CFOPs\n")
        for idx, row in cfops_cat_01.head(5).iterrows():
            print(f"  {row['codigo_cfop']}: {row['descricao']}")
    
    # ========== EXPORTAÇÃO (OPCIONAL) ==========
    # Descomente as linhas abaixo para exportar as tabelas processadas
    # leitor.exportar_cfop_csv("cfop_processada.csv")
    # leitor.exportar_ncm_csv("produtos_ncm_processado.csv")
    
    print(f"\n{'='*70}")
    print("PROCESSAMENTO CONCLUÍDO!")
    print(f"{'='*70}")
