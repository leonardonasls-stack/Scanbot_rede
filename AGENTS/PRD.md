# Documento de Requisitos de Produto (PRD)
## Bot de Varredura e Inventário de Equipamentos Control iD

---

### 1. Visão Geral e Objetivo
O objetivo deste projeto é desenvolver uma ferramenta automatizada (bot/scanner de rede) capaz de realizar varredura em redes locais para identificar, catalogar e extrair informações cadastrais de dispositivos da marca **Control iD** (por exemplo: iDFace, iDClass, iDAccess, iDBox, PrintPoint, etc.).

Ao final de cada execução, o bot gera um **relatório consolidado** contendo a quantidade total de equipamentos encontrados e uma listagem detalhada com **Número de Série**, **Endereço MAC** e **Endereço IP Local**.

---

### 2. Problema e Justificativa
- **Problema:** Em ambientes corporativos, industriais e comerciais, equipamentos de ponto e controle de acesso frequentemente operam sob IPs dinâmicos (DHCP) ou espalhados em sub-redes sem inventário atualizado.
- **Impacto:** O levantamento manual exige acesso físico a cada equipamento ou verificação roteador por roteador, consumindo tempo excessivo da equipe técnica.
- **Solução:** Um bot leve e rápido que faz a sondagem pela rede, identifica a assinatura dos dispositivos Control iD e consolida os dados automaticamente em poucos segundos.

---

### 3. Casos de Uso Principais
1. **Auditoria e Inventário:** Técnico de TI/Segurança executa a ferramenta para descobrir todos os dispositivos Control iD ativos na rede da empresa.
2. **Suporte e Manutenção:** Localizar rapidamente o IP e o Serial de um relógio ou catraca recém-instalado ou cujo IP foi alterado.
3. **Conferência de Quantitativo:** Relatório rápido mostrando o total de catracas, faciais e relógios de ponto em operação.

---

### 4. Escopo

#### 4.1. No Escopo (In-Scope)
- Auto-detecção de interface de rede e sub-rede local (ex: `192.168.1.0/24`) com suporte a passagem de faixas customizadas via parâmetro.
- Varredura concorrente/assíncrona de alta performance para resposta em poucos segundos.
- Mecanismo de identificação específico para dispositivos Control iD:
  - Consulta aos endpoints de API REST locais dos equipamentos (ex.: porta 80/443 e chamadas públicas de status/info do firmware).
  - Consulta à tabela ARP local do sistema operacional para resolução precisa de Endereço MAC.
- Extração de dados essenciais:
  - **Endereço IP Local**
  - **Endereço MAC**
  - **Número de Série (Serial Number)**
  - *(Desejável/Bônus)* Modelo do dispositivo e versão do firmware.
- **Formulário de Cabeçalho Manual (Uso Interno):**
  - **Cliente / Empresa**
  - **Endereço Completo:** Rua, Número e Bairro
  - **Técnico Responsável**
  - **Local do Equipamento** (ex: Recepção, Catracas Bloco A)
- **Fluxo de Confirmação e Emissão:**
  - Após a varredura e o preenchimento manual dos dados, o sistema apresenta um diálogo de confirmação com resumo dos dados e total de ativos (destacando iDFaces) antes de emitir o documento final.
- **Entrega de Documento Oficial de Uso Interno:**
  - Emissão de documento estruturado em **PDF** para controle técnico interno e inventário de ativos (sem exigência de assinatura de terceiros ou termos de recebimento).
  - Exportação auxiliar em formatos **CSV** e **JSON**.
- Tratamento robusto para dispositivos que não respondem (timeouts) ou portas filtradas.

#### 4.2. Fora de Escopo Inicial (Out-of-Scope)
- Campos de assinatura de clientes ou termos formais de recebimento por terceiros (documento focado 100% em uso técnico e controle interno da equipe).
- Alteração de parâmetros ou envio de comandos de gravação nos dispositivos (operação estritamente **read-only** / somente leitura).
- Coleta de dados biométricos ou cadastros de usuários.

---

### 5. Mecanismo Técnico de Descoberta

Os equipamentos da Control iD executam um servidor web embarcado e disponibilizam APIs HTTP locais (comuns nas linhas iDAccess, iDFace, iDClass):
1. **Varredura de Portas (TCP):** Identificação de hosts com portas HTTP ativas (tipicamente portas `80` ou `443`).
2. **Identificação por Assinatura / API:**
   - Requisição de probing para endpoints conhecidos da Control iD (ex.: `/api/system/information`, `system_information.fcgi`, cabeçalhos HTTP Server ou tela inicial).
   - O payload JSON retornado por equipamentos Control iD normalmente expõe campos como `"serial_number"`, `"model"`, `"version"`, etc.
3. **Resolução de MAC:**
   - Coleta via tabela ARP do Windows/Linux para correlacionar o IP com a interface de rede física.
4. **Varredura UDP Broadcast (Opcional/Complementar):**
   - Verificação de envio/escuta de pacotes de descoberta de rede utilizados pelas ferramentas proprietárias (ex.: portas UDP 5005 / 8000).

---

### 6. Requisitos do Sistema

#### 6.1. Requisitos Funcionais (RF)
- **RF01 - Definição do Alvo:** O usuário pode deixar o bot auto-detectar a sub-rede atual ou informar um range manualmente (ex.: `--network 192.168.0.0/24` ou range de IPs).
- **RF02 - Varredura Concorrente:** Executar testes simultâneos (via `asyncio` ou pool de threads) para garantir tempo total de varredura inferior a 30 segundos em sub-redes `/24`.
- **RF03 - Reconhecimento Control iD:** Discriminar se o host responde à assinatura característica de dispositivos Control iD e descartar outros dispositivos de rede (impressoras, roteadores, PCs).
- **RF04 - Extração de Metadados:** Extrair e normalizar:
  - IP
  - MAC
  - Número de Série
  - Modelo (se retornado pela API)
- **RF05 - Contabilização:** Calcular e destacar explicitamente a contagem total de equipamentos encontrados.
- **RF06 - Emissão de Relatório:**
  - Exibição de resumo visual no terminal (tabela estilizada).
  - Salvamento automático de arquivo de relatório (`relatorio_control_id_YYYYMMDD_HHMMSS.csv` e `.json`).
- **RF07 - Resiliência e Logs:** Mensagens claras caso nenhum equipamento seja encontrado ou caso ocorram erros de permissão de rede.

#### 6.2. Requisitos Não-Funcionais (RNF)
- **RNF01 - Performance:** Varredura rápida, não bloqueante, com timeout configurável por host (default: 1 a 2 segundos).
- **RNF02 - Compatibilidade:** Funcionar no ambiente Windows 10/11 (PowerShell / Prompt) e ser facilmente adaptável para Linux.
- **RNF03 - Segurança:** Não enviar pacotes maliciosos, não tentar brute-force de senhas; usar apenas requisições informativas seguras.
- **RNF04 - Empacotamento:** Possibilidade de ser compilado em executável único `.exe` (via PyInstaller) para execução em campo sem necessidade de instalar Python nas máquinas dos técnicos.

---

### 7. Tecnologias Recomendadas
- **Linguagem:** Python 3.10+
- **Comunicação Assíncrona / Rede:** `asyncio`, `aiohttp` / `httpx`
- **Manipulação de Rede e ARP:** Módulo nativo `subprocess` (comando `arp -a`) ou biblioteca `scapy` / `ipaddress`
- **Formatação de Relatório e CLI:** `rich` (tabelas e progress bar moderna no terminal)
- **Exportação:** Módulos nativos `csv` e `json`
- **Build / Distribuição:** `pyinstaller` (para gerar `bot-varredura-controlid.exe`)

---

### 8. Estrutura Proposta para o Projeto
```text
Bot Varredura - Control ID/
│
├── PRD.md                         # Requisitos de Produto
├── TRD.md                         # Requisitos Técnicos
├── requirements.txt               # Dependências Python (flet, httpx)
├── main.py                        # Ponto de entrada da aplicação
│
├── backend/                       # Camada de Rede, Descoberta e Serviços
│   ├── __init__.py
│   ├── core/                      # Scanner assíncrono, detector e resolvedor ARP
│   ├── models/                    # Modelos de dados imutáveis (Device, Summary)
│   └── services/                  # Exportação de relatórios (CSV, JSON)
│
├── frontend/                      # Camada Visual Desktop (Flet)
│   ├── __init__.py
│   ├── app.py                     # Layout principal e gerenciamento de estado
│   ├── components/                # Componentes (Header, Controls, KPIs, Table)
│   └── styles/                    # Cores e temas visuais
│
├── reports/                       # Diretório onde os relatórios salvos são gravados
└── tests/                         # Testes e ambiente simulado
    └── mock_control_id_server.py  # Mock de dispositivo Control iD para validação
```

---

### 9. Cronograma e Fases de Implementação
1. **Fase 1 (Atual):** Validação do PRD e definição de parâmetros de rede e modelos alvo.
2. **Fase 2:** Desenvolvimento do Scanner Assíncrono e resolvedor de MAC via ARP.
3. **Fase 3:** Implementação do módulo Detector com os endpoints específicos da Control iD (iDFace, iDClass, etc.).
4. **Fase 4:** Criação dos geradores de relatórios (Terminal, CSV, JSON) com contagem total.
5. **Fase 5:** Testes em rede local e geração do executável `.exe`.
