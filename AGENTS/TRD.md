# Documento de Requisitos Técnicos (TRD)
## Bot de Varredura e Inventário de Equipamentos Control iD

---

### 1. Visão Geral Técnica
O **Bot de Varredura Control iD** é uma aplicação desktop desenvolvida em Python 3.10+ com arquitetura desacoplada em duas camadas principais:
- **Backend:** Motor assíncrono de rede independente, responsável pela detecção de sub-rede, sondagem HTTP/FCGI de equipamentos Control iD, resolução nativa de endereços MAC (via Windows API) e geração de relatórios (CSV/JSON).
- **Frontend:** Interface gráfica desktop nativa construída com **Flet** (baseada na engine do Flutter), reativa e moderna, que consome o backend de forma assíncrona.

---

### 2. Arquitetura em Camadas (Frontend / Backend)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Flet Desktop)                         │
│                           (frontend/app.py)                            │
│                                                                        │
│   ┌────────────────────┐ ┌────────────────────┐ ┌──────────────────┐   │
│   │  frontend/         │ │  frontend/         │ │  frontend/       │   │
│   │  components/       │ │  components/       │ │  components/     │   │
│   │  controls.py       │ │  kpi_cards.py      │ │  device_table.py │   │
│   │  (Input IP, Botões)│ │  (Totalizadores)   │ │  (Tabela Dados)  │   │
│   └────────────────────┘ └────────────────────┘ └──────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Eventos Assíncronos & Callbacks
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Motor de Rede)                         │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  backend/core/scanner.py (Async Scanner + Semaphore Pool)      │   │
│   └───────────────────────┬────────────────┬───────────────────────┘   │
│                           │                │                           │
│                           ▼                ▼                           │
│   ┌──────────────────────────────┐  ┌──────────────────────────────┐   │
│   │  backend/core/detector.py    │  │  backend/core/arp_helper.py  │   │
│   │  (Probe HTTP Control iD)     │  │  (Windows SendARP nativo)    │   │
│   └──────────────────────────────┘  └──────────────────────────────┘   │
│                           │                        │                   │
│                           └────────────┬───────────┘                   │
│                                        ▼                               │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  backend/models/device.py (ControlIdDevice, ScanSummary)       │   │
│   └────────────────────────────────────┬───────────────────────────┘   │
│                                        ▼                               │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  backend/services/report_service.py (Exportação CSV e JSON)    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Estrutura de Diretórios Detalhada

```text
Bot Varredura - Control ID/
│
├── PRD.md                         # Requisitos de Negócio
├── TRD.md                         # Requisitos Técnicos
├── requirements.txt               # flet, httpx, etc.
├── main.py                        # Ponto de entrada que inicializa a UI Flet
│
├── backend/                       # CAMADA DE SERVIÇOS E REDE (100% isolada da UI)
│   ├── __init__.py
│   ├── core/                      # Módulos de rede e infraestrutura
│   │   ├── __init__.py
│   │   ├── scanner.py             # Orquestrador assíncrono de varredura
│   │   ├── detector.py            # Validação e coleta da API Control iD
│   │   ├── arp_helper.py          # Resolução de MAC via SendARP do Windows
│   │   └── network_utils.py       # Identificação da placa e IP local
│   ├── models/                    # Modelos de dados imutáveis
│   │   ├── __init__.py
│   │   └── device.py              # Dataclasses ControlIdDevice, ScanSummary e DocumentMetadata
│   └── services/                  # Serviços de persistência e relatórios
│       ├── __init__.py
│       ├── report_service.py      # Exportadores estruturados CSV e JSON
│       └── document_service.py    # Gerador de Documento Interno em PDF (ReportLab)
│
├── frontend/                      # CAMADA VISUAL DESKTOP (FLET)
│   ├── __init__.py
│   ├── app.py                     # Janela principal, controle de eventos e estado
│   ├── components/                # Componentes de interface modulares
│   │   ├── __init__.py
│   │   ├── header.py              # Barra de título e dados da interface local
│   │   ├── controls.py            # Campo de sub-rede e botões de varredura
│   │   ├── kpi_cards.py           # Cards de métricas (Total Encontrados, etc.)
│   │   ├── client_form.py         # Formulário manual de cabeçalho do cliente/técnico
│   │   └── device_table.py        # Tabela com exibição dos equipamentos
│   └── styles/                    # Identidade visual e temas
│       ├── __init__.py
│       └── theme.py               # Paleta de cores, tipografia e estilos
│
├── reports/                       # Diretório onde os relatórios salvos são gravados
└── tests/                         # Testes e ambiente simulado
    └── mock_control_id_server.py  # Mock de dispositivo Control iD para validação
```

---

### 4. Especificação do Frontend (Flet)

#### 4.1. Responsabilidades do Frontend
- Interface reativa sem congelamento de tela durante o escaneamento (consumo do backend via `asyncio`).
- Atualização em tempo real da tabela de dispositivos e da barra de progresso.
- Exibição em destaque do **Total de Equipamentos Control iD Encontrados**.
- Disparo de ações de exportação (CSV/JSON) delegando a escrita ao `report_service`.

#### 4.2. Componentes Visuais
1. **`header.py`:** Identificação do aplicativo, ícone e badge com a interface ativa da máquina (ex: `192.168.1.100 / Ethernet`).
2. **`controls.py`:**
   - Campo para sub-rede (`TextField`), permitindo edição manual.
   - Botão para **Auto-detectar Rede Local**.
   - Botão **Iniciar Varredura** / **Cancelar**.
3. **`kpi_cards.py`:**
   - **Card Principal (Destaque Verde):** Quantidade total de dispositivos Control iD identificados.
   - **Card Secundário:** Quantidade de IPs já verificados no range.
   - **Card Tempo:** Duração da varredura em segundos.
4. **`device_table.py`:**
   - `DataTable` contendo as colunas: `IP Local`, `Endereço MAC`, `Número de Série`, `Modelo`, `Versão Firmware` e `Latência (ms)`.
   - Suporte a rolagem com visualização fluida.

---

### 5. Especificação do Backend

#### 5.1. `backend/core/detector.py`
Executa o probing nos endpoints conhecidos dos equipamentos Control iD:
- Endpoint 1: `/system_information.fcgi` (GET / POST)
- Endpoint 2: `/api/system/information`
- Headers / Títulos: Verificação de assinatura `Control iD`.
- Timeout configurado para 1.5s por requisição.

#### 5.2. `backend/core/arp_helper.py`
Resolução instantânea de MAC address via API do Windows:
- Chamada nativa `ctypes.windll.iphlpapi.SendARP`.
- Execução em memória sem necessidade de privilégios de administrador.
- Fallback automático para tabela ARP do sistema (`arp -a`).

#### 5.3. `backend/core/scanner.py`
- Validação e iteração sobre faixas IPv4 (biblioteca `ipaddress`).
- Controle de concorrência com `asyncio.Semaphore(50)`.
- Callback funcional `on_device_found(device)` e `on_progress(scanned, total)` para notificar o frontend em tempo real.

#### 5.4. `backend/services/report_service.py`
- Gera arquivos formatados com timestamp na pasta `reports/`:
  - `relatorio_control_id_YYYYMMDD_HHMMSS.csv`
  - `relatorio_control_id_YYYYMMDD_HHMMSS.json`

---

### 6. Parâmetros de Performance e Build

| Item | Especificação |
| :--- | :--- |
| **Linguagem** | Python 3.10+ |
| **Frontend** | Flet |
| **Cliente HTTP** | `httpx.AsyncClient` |
| **Workers Concorrentes** | 50 requisições simultâneas |
| **Tempo Estimado (/24)** | 10 a 20 segundos para 254 hosts |
| **Build Executável** | `flet pack main.py --name "Bot-Varredura-ControlID"` ou PyInstaller |
