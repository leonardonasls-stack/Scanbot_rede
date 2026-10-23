# SCAN BOT Rede — Scanner e Inventário de Equipamentos Control iD

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flet](https://img.shields.io/badge/UI-Flet%20(Flutter)-02569B?logo=flutter&logoColor=white)
![Platform](https://img.shields.io/badge/Plataforma-Windows-0078D6?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

Ferramenta desktop desenvolvida em **Python** e **Flet** (Material Design 3 / Flutter Engine) para **varredura sob demanda**, **identificação por assinatura** e **inventário técnico** de equipamentos **Control iD** (iDFace, iDClass, iDAccess, iDFlex, iDBlock, entre outros) em redes locais.

---

## 🚀 Principais Funcionalidades

### 🔎 Varredura de Rede
- **Sob demanda:** nenhuma varredura é disparada na inicialização; o usuário decide quando iniciar e pode cancelar a qualquer momento.
- **Detecção automática da rede:** o IP local e a sub-rede (CIDR) são puxados automaticamente da interface ativa (botão **Puxar da Rede**).
- **Modo AUTO / MANUAL:** chave *"Permitir escrever manualmente"* libera a edição livre da faixa (ex.: `10.0.0.0/24`).
- **Alta performance assíncrona:** pool de **50 workers** (`httpx.AsyncClient` + `asyncio.Semaphore`), varrendo um bloco `/24` (254 hosts) em menos de 20 segundos.

### 🧠 Identificação Inteligente e Topologia de Hardware
- **Sondagem em cascata** dos endpoints embarcados:
  1. `/system_information.fcgi` (GET/POST)
  2. `/api/system/information`
  3. `/login.fcgi` e página inicial `/` (assinatura HTML)
- **Autenticação automática** (`/login.fcgi` → sessão → `/logout.fcgi`) quando o serial ou modelo estão protegidos. Credenciais configuráveis na interface (padrão `admin` / `admin`).
- **Reconhecimento avançado de modelos:**
  - Leitores faciais: iDFace, iDFace Pro, iDFace Max.
  - Catracas: **iDBlock**, **iDBlock Facial** e modelo específico **iDBlock PNE** (identificado por serial `0K1400` ou nomenclatura de dispositivo).
  - Demais linhas: iDClass, iDAccess, iDFlex, iDBox, iDFit, iDGate, iDTouch, iDPrint, iDBio, iDLook, iDSecure.
- **Topologia e Hierarquia de Catracas (`turnstile_linker`):**
  - Associa automaticamente leitores faciais escravos à sua catraca mestre por cruzamento de portais e nomes de cadastro no iDSecure.
  - **Identificação precisa de Direção:** detecta e rotula individualmente quem é **Entrada** e quem é **Saída** com base na palavra final do dispositivo e nos fluxos de transição (`area_to_id`).
- **Filtragem Inteligente de Áreas:**
  - Descarta automaticamente tabelas globais e áreas genéricas órfãs (como `"Área Padrão"`), exibindo com precisão a localização física real do dispositivo na empresa.
- **Coleta de metadados:** IP, MAC, número de série, modelo, firmware e latência.
- **Resolução nativa de MAC via Win32** (`iphlpapi.SendARP` via `ctypes`), sem exigir privilégios de administrador.
- **Descarte silencioso** de hosts inalcançáveis ou que não sejam Control iD.

### 🖥️ Interface Desktop
- Visual corporativo **Dark Mode** em Flet.
- Agrupamento visual de catracas e leitores com recuo hierárquico (`↳`).
- Badges modernos e diretos: **`[Entrada]`** (verde esmeralda) e **`[Saída]`** (âmbar).
- Cards de KPI (total de equipamentos e métricas) e barra de progresso em tempo real.

### 📄 Relatórios e Documentos
- **CSV** (separador `;`, UTF-8 BOM — abre direto no Excel) com cabeçalho de resumo e detalhamento dos vínculos.
- **JSON** estruturado com o resumo completo e metadados brutos de diagnóstico (`devices` e `portals`).
- **Documento Técnico em PDF** (ReportLab) com:
  - Cabeçalho personalizado: Cliente, Endereço, Bairro, Técnico Responsável e Local.
  - Indicadores KPI por categoria.
  - Tabela técnica com numeração hierárquica (`1`, `1.1`, `1.2`), IPs sem quebra de linha, badges de direção e áreas limpas.
  - Assinatura digital Authenticode com certificado LLSystem.
- Atalho para **abrir a pasta de relatórios** no Windows Explorer.

---

## 📁 Estrutura do Projeto

```text
Bot Varredura - Control ID/
│
├── AGENTS/                         # Especificações do projeto (PRD, TRD, API, Frontend, Testes, Tarefas)
├── backend/                        # Camada de Serviços e Rede (isolada da UI)
│   ├── core/
│   │   ├── scanner.py              # Orquestrador assíncrono de varredura (NetworkScanner)
│   │   ├── detector.py             # Sonda, autenticação e parser de equipamentos Control iD
│   │   ├── arp_helper.py           # Resolvedor de MAC via Win32 SendARP
│   │   └── network_utils.py        # Identificação de IP local e cálculo/validação de CIDR
│   ├── models/
│   │   └── device.py               # Dataclasses ControlIdDevice, ScanSummary e DocumentMetadata
│   └── services/
│       ├── report_service.py       # Exportação CSV/JSON e atalho para pasta de relatórios
│       ├── document_service.py     # Geração do Documento Interno em PDF (ReportLab)
│       └── turnstile_linker.py     # Agrupamento hierárquico de catracas e leitores subordinados
│
├── frontend/                       # Camada Visual Desktop (Flet)
│   ├── app.py                      # Controlador principal e eventos da interface
│   ├── components/
│   │   ├── header.py               # Topbar com branding SCAN BOT Rede
│   │   ├── controls.py             # CIDR (AUTO/MANUAL), credenciais e botões Iniciar/Cancelar
│   │   ├── kpi_cards.py            # Totalizador de equipamentos e métricas
│   │   ├── device_table.py         # Tabela de dispositivos com tags de modelo
│   │   └── client_form.py          # Formulário de cabeçalho do Documento Interno (PDF)
│   └── styles/
│       └── theme.py                # Tokens de design, paleta Dark Mode e cores
│
├── reports/                        # Saída dos relatórios gerados (CSV, JSON, PDF)
├── tests/                          # Testes automatizados e servidor mock Control iD
│   ├── mock_control_id_server.py   # Servidor HTTP que simula um equipamento Control iD
│   ├── test_backend.py             # Modelos, utilitários de rede e relatórios
│   ├── test_scanner.py             # Detector e orquestrador de varredura
│   ├── test_document.py            # Geração do PDF interno
│   └── test_e2e.py                 # Fluxo ponta a ponta contra o servidor mock
├── main.py                         # Ponto de entrada da aplicação desktop
├── requirements.txt                # Dependências Python
├── build.ps1                       # Script de compilação PyInstaller (.exe)
└── README.md                       # Documentação do projeto
```

---

## 🛠️ Como Executar

### 1. Pré-requisitos
- **Windows 10/11** (a resolução de MAC usa a API Win32).
- **Python 3.10** ou superior.

### 2. Clonar o repositório
```powershell
git clone https://github.com/leonardonasls-stack/Scanbot_rede.git
cd Scanbot_rede
```

### 3. (Opcional) Criar um ambiente virtual
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Instalar as dependências
```powershell
pip install -r requirements.txt
```

| Pacote        | Uso                                         |
|---------------|---------------------------------------------|
| `flet`        | Interface gráfica desktop                   |
| `httpx`       | Cliente HTTP assíncrono para a varredura    |
| `reportlab`   | Geração do Documento Interno em PDF         |
| `pyinstaller` | Compilação do executável standalone (.exe)  |

### 5. Executar a aplicação
```powershell
python main.py
```

---

## 📋 Fluxo de Uso

1. Abra o aplicativo — a rede ativa é detectada e o CIDR é preenchido automaticamente.
2. (Opcional) Ative **"Permitir escrever manualmente"** para digitar outra faixa.
3. Confira as credenciais de autenticação dos equipamentos (padrão `admin` / `admin`).
4. Clique em **Iniciar Varredura** e acompanhe os resultados em tempo real.
5. Exporte em **CSV** ou **JSON**, ou preencha o cabeçalho e clique em **Gerar Documento Interno (PDF)**.
6. Os arquivos são salvos em `reports/` com timestamp no nome.

---

## 🧪 Testes Automatizados

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Os testes de integração e E2E sobem automaticamente um **servidor mock Control iD** local (`127.0.0.1:8089`), dispensando hardware real.

---

## 📦 Compilando o Executável (.exe)

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

O script executa três etapas:
1. Instala/verifica as dependências.
2. Roda a suíte de testes.
3. Gera o executável único com PyInstaller (`--onefile --windowed`).

Saída: `dist/SCAN-BOT-Rede.exe`

---

## ⚠️ Observações

- A varredura deve ser realizada **apenas em redes onde você tem autorização**.
- O PDF gerado é destinado a **uso interno** (inventário técnico, conferência e manutenção de ativos).
- Equipamentos com senha diferente da informada aparecerão com serial `N/D (Bloqueado por Auth - Verificar Senha)`.
