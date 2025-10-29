# 🚀 OldNews FiscalAI
## Sistema Inteligente de Análise Fiscal

---

## 📋 VISÃO GERAL DO PROJETO

O **OldNews FiscalAI** representa uma solução inovadora e abrangente para análise fiscal automatizada, desenvolvida especificamente para enfrentar os desafios crescentes de detecção de fraudes em documentos fiscais eletrônicos brasileiros. O sistema utiliza tecnologias de ponta em inteligência artificial, combinando arquitetura multi-agente com CrewAI, processamento de linguagem natural e técnicas avançadas de análise de dados para identificar padrões suspeitos em Notas Fiscais Eletrônicas (NF-e), Notas Fiscais de Serviços Eletrônicas (NFS-e) e documentos fiscais em formato CSV.

A arquitetura do sistema foi projetada com base em princípios de engenharia de software modernos, empregando programação orientada a objetos, padrões de design robustos e uma estrutura modular que permite escalabilidade e manutenibilidade. O OldNews FiscalAI não apenas automatiza processos de auditoria fiscal que tradicionalmente exigiam horas de trabalho manual, mas também oferece insights profundos através de análise inteligente de padrões, classificação automatizada de códigos NCM (Nomenclatura Comum do Mercosul), e detecção de anomalias que podem indicar tentativas de fraude fiscal.

O sistema foi desenvolvido para ser acessível tanto a profissionais de contabilidade e auditoria quanto a empresas que necessitam realizar análises fiscais internas, oferecendo uma interface web intuitiva que elimina a necessidade de conhecimento técnico profundo em programação ou análise de dados. Com suporte para processamento em lote de múltiplas notas fiscais simultaneamente, o sistema pode analisar centenas de documentos em minutos, proporcionando relatórios detalhados e acionáveis que facilitam a tomada de decisões estratégicas.

---

## ✨ FUNCIONALIDADES PRINCIPAIS

### 🔍 Análise Inteligente de Documentos Fiscais
O sistema possui capacidade avançada de processamento e análise de documentos fiscais em múltiplos formatos (XML, CSV, NFS-e), utilizando algoritmos de parsing inteligente que extraem informações estruturadas mesmo de documentos com estruturas variadas ou ligeiramente inconsistentes. A análise inclui validação de conformidade com schemas XML oficiais, detecção de erros estruturais e identificação de campos obrigatórios ausentes ou inválidos.

### 🤖 Sistema Multi-Agente com CrewAI
A arquitetura multi-agente implementada através do framework CrewAI permite que cinco agentes especializados trabalhem em conjunto de forma coordenada:

- **Agente 1 - Extrator de Dados**: Responsável pela extração precisa de informações de documentos fiscais, identificando e estruturando dados como valores, datas, emitentes, destinatários e itens de nota fiscal.
- **Agente 2 - Classificador NCM**: Utiliza inteligência artificial para classificar produtos e serviços corretamente segundo a Nomenclatura Comum do Mercosul, validando classificações existentes e sugerindo correções quando necessário.
- **Agente 3 - Validador Fiscal**: Realiza validações cruzadas de informações fiscais, verificando consistência de cálculos, validação de CFOP (Código Fiscal de Operações e Prestações) e conformidade com legislação vigente.
- **Agente 4 - Orquestrador**: Coordena o fluxo de trabalho entre os agentes, garantindo que todas as análises sejam executadas na ordem correta e que os resultados sejam consolidados adequadamente.
- **Agente 5 - Interface Conversacional**: Oferece um assistente inteligente que permite aos usuários fazer perguntas em linguagem natural sobre os documentos analisados, proporcionando insights de forma interativa e acessível.

### 📊 Dashboard Interativo com Streamlit
A interface web desenvolvida com Streamlit oferece uma experiência de usuário moderna e intuitiva, apresentando visualizações gráficas de análise de risco, métricas de desempenho e resultados detalhados de detecção de fraudes. O dashboard permite navegação fluida entre diferentes seções, visualização de dados em tempo real e exportação de relatórios em formato texto para análise posterior.

### 💬 Chat com Inteligência Artificial V2
A versão mais recente do sistema de chat oferece acesso direto aos dados dos arquivos carregados, permitindo que usuários façam perguntas específicas sobre quantidade de notas fiscais analisadas, valores totais, fraudes detectadas e detalhes de itens suspeitos. O sistema compreende contexto e fornece respostas precisas baseadas exclusivamente nos dados reais processados, com capacidade de exportar conversas para análise posterior.

### 📄 Processamento Multi-formato
O sistema suporta análise de documentos fiscais em múltiplos formatos, incluindo XML (padrão nacional para NF-e e NFS-e), CSV (para análises em lote de dados estruturados) e processamento de múltiplas notas fiscais dentro de um único arquivo XML. A detecção automática de encoding garante que arquivos com diferentes codificações de caracteres sejam processados corretamente.

### 🚨 Detecção Avançada de Fraudes
Implementa sete tipos distintos de detectores de fraude fiscal:

- **Subfaturamento**: Identifica valores de produtos ou serviços significativamente abaixo do mercado, comparando com bases de dados históricas e referências de preço.
- **NCM Incorreto**: Detecta classificações fiscais inadequadas que podem indicar tentativas de redução indevida de impostos ou importações fraudulentas.
- **Triangulação**: Identifica operações suspeitas envolvendo múltiplas empresas que podem indicar esquemas de evasão fiscal ou contrabando.
- **Fracionamento**: Detecta divisões artificiais de operações que podem ser utilizadas para evitar limites fiscais ou regulatórios.
- **Fornecedor de Risco**: Analisa histórico de fornecedores e identifica aqueles com padrões suspeitos ou histórico de irregularidades fiscais.
- **Anomalia Temporal**: Identifica padrões temporais incomuns que podem indicar operações fraudulentas, como transações em horários atípicos ou sequências suspeitas de operações.
- **Valor Inconsistente**: Detecta inconsistências em cálculos fiscais, somas de valores, impostos calculados incorretamente ou disparidades entre valores declarados e calculados.

### 🔒 Validação XML Schema
Implementa validação rigorosa contra schemas XML oficiais da Receita Federal do Brasil, garantindo que documentos estejam em conformidade com especificações técnicas antes da análise. O sistema também oferece validação básica de estrutura quando schemas completos não estão disponíveis, permitindo análise mesmo em cenários com conectividade limitada.

### ⚡ Sistema de Cache Inteligente
O sistema implementa cache persistente de resultados de análise, reduzindo significativamente o tempo de processamento quando documentos são reanalisados. O cache é gerenciado de forma inteligente, invalidando automaticamente quando necessário e oferecendo economia de até 70% no tempo de reprocessamento.

### 🛡️ Segurança Avançada
Implementa múltiplas camadas de segurança incluindo headers de segurança HTTP (CORS, CSP), rate limiting para proteção contra ataques de negação de serviço, sanitização de dados de entrada para prevenir ataques de injeção, auditoria completa de operações sensíveis e criptografia de dados sensíveis com chaves rotativas.

---

## 📝 RESUMO DA APLICAÇÃO

O **OldNews FiscalAI** representa uma evolução significativa na forma como organizações lidam com análise fiscal e detecção de fraudes. Desenvolvido como uma solução completa e integrada, o sistema combina o poder da inteligência artificial com uma interface intuitiva, tornando análises fiscais complexas acessíveis a profissionais de diversos níveis técnicos.

A aplicação diferencia-se por sua capacidade de processar grandes volumes de documentos fiscais de forma automatizada, fornecendo análises detalhadas que anteriormente exigiam equipes especializadas e horas de trabalho manual. Através de sua arquitetura multi-agente, o sistema não apenas automatiza processos, mas também oferece insights profundos através de análise inteligente de padrões, identificando nuances que podem escapar a análises manuais tradicionais.

A interface web desenvolvida com Streamlit oferece uma experiência de usuário excepcional, permitindo que usuários visualizem resultados de análise de forma clara e intuitiva, naveguem entre diferentes seções com facilidade e exportem relatórios detalhados para análise posterior. O sistema de chat inteligente V2 adiciona uma camada adicional de interatividade, permitindo que usuários façam perguntas específicas e recebam respostas precisas baseadas nos dados reais processados.

A capacidade de processar múltiplos formatos de documentos fiscais, incluindo XML padrão nacional e CSV para análises em lote, torna o sistema extremamente versátil e aplicável a diferentes contextos organizacionais. A detecção de sete tipos distintos de fraudes fiscais, combinada com validação rigorosa contra schemas oficiais e múltiplas camadas de segurança, garante que o sistema seja não apenas eficiente, mas também confiável e seguro para uso em ambientes corporativos.

O sistema de cache inteligente e otimizações de performance garantem que o sistema possa processar grandes volumes de dados de forma eficiente, enquanto a arquitetura modular permite fácil manutenção e extensão futura. O OldNews FiscalAI não é apenas uma ferramenta de análise fiscal, mas uma plataforma completa que pode transformar a forma como organizações gerenciam conformidade fiscal e detectam fraudes.

Em resumo, o OldNews FiscalAI representa uma solução tecnológica avançada que democratiza o acesso a análises fiscais de alta qualidade, oferecendo às organizações capacidade de identificar fraudes, garantir conformidade fiscal e tomar decisões informadas baseadas em dados precisos e análises inteligentes. A combinação de tecnologia de ponta, interface intuitiva e funcionalidades abrangentes posiciona o sistema como uma ferramenta essencial para qualquer organização que necessite realizar análises fiscais eficientes e precisas.

---

**Desenvolvido com tecnologia de ponta para análise fiscal inteligente**

*Sistema em constante evolução com melhorias contínuas baseadas em feedback de usuários e avanços em inteligência artificial.*

