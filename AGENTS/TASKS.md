# TASKS — Plano de Implementação Passo a Passo
## Bot de Varredura e Inventário de Equipamentos Control iD

Este documento detalha o checklist de execução para o desenvolvimento do projeto no **Antigravity IDE**. Cada tarefa possui critérios de aceite bem definidos para permitir execução incremental e testes contínuos.

---

### Fase 1: Setup do Ambiente e Estrutura Base
- [x] **1.1. Arquivo de Dependências (`requirements.txt`)**
  - **Arquivo:** `requirements.txt`
  - **Critério de Aceite:** Conter as versões mínimas testadas de `flet>=0.21.0`, `httpx>=0.27.0` e ferramentas de build (`pyinstaller`).
- [x] **1.2. Criação do Esqueleto de Pastas e Pacotes**
  - **Pastas:** `backend/core/`, `backend/models/`, `backend/services/`, `frontend/components/`, `frontend/styles/`, `reports/`, `tests/`
  - **Critério de Aceite:** Criar todos os arquivos `__init__.py` necessários para que os pacotes sejam reconhecidos.
- [x] **1.3. Arquivo de Ignorados do Git (`.gitignore`)**
  - **Arquivo:** `.gitignore`
  - **Critério de Aceite:** Ignorar diretórios virtuais (`venv/`, `.venv/`), cache (`__pycache__/`, `*.pyc`), relatórios temporários (`reports/*.csv`, `reports/*.json`) e saídas de build (`dist/`, `build/`).

---

### Fase 2: Backend — Modelos de Dados e Utilitários de Baixo Nível
- [x] **2.1. Modelos de Dados (`backend/models/device.py`)**
  - **Arquivo:** `backend/models/device.py`
  - **Critério de Aceite:**
    - Criar dataclass `ControlIdDevice` com campos: `ip` (str), `mac` (str), `serial_number` (str), `model` (str), `firmware_version` (str opcional), `response_time_ms` (float), `timestamp` (datetime).
    - Criar dataclass `ScanSummary` com campos: `network_target` (str), `total_scanned` (int), `total_found` (int), `duration_seconds` (float), `devices` (list[ControlIdDevice]).
- [x] **2.2. Resolvedor Nativo de MAC via Windows API (`backend/core/arp_helper.py`)**
  - **Arquivo:** `backend/core/arp_helper.py`
  - **Critério de Aceite:**
    - Implementar função `get_mac_for_ip(ip: str) -> str` usando `ctypes.windll.iphlpapi.SendARP`.
    - Converter o buffer binário para formato padrão legível (`AA:BB:CC:DD:EE:FF`).
    - Incluir fallback para execução em Linux (`/proc/net/arp`) ou retorno seguro `N/D` caso o IP não responda ao ARP.
- [x] **2.3. Utilitário de Identificação de Rede Local (`backend/core/network_utils.py`)**
  - **Arquivo:** `backend/core/network_utils.py`
  - **Critério de Aceite:**
    - Implementar função `get_local_network_info() -> tuple[str, str]` que identifica o IP local ativo da máquina e calcula a sub-rede padrão `/24` (ex: IP `192.168.1.45` -> Sub-rede `192.168.1.0/24`).
    - Validar sintaxe de blocos CIDR com o módulo `ipaddress`.

---

### Fase 3: Backend — Detector de Assinatura Control iD
- [x] **3.1. Módulo Detector de Equipamentos (`backend/core/detector.py`)**
  - **Arquivo:** `backend/core/detector.py`
  - **Critério de Aceite:**
    - Implementar função assíncrona `async def probe_control_id(client: httpx.AsyncClient, ip: str, port: int = 80) -> Optional[ControlIdDevice]`.
    - Timeout agressivo de conexão (1.5 segundos).
    - Consulta ao endpoint primário `/system_information.fcgi`.
    - Consulta ao endpoint secundário `/api/system/information` como fallback.
    - Parser de campos: extrair número de série (chaves `serial`, `serial_number` ou `device_id`), modelo e versão.
    - Acionar `arp_helper.get_mac_for_ip(ip)` caso o equipamento seja identificado como Control iD.
    - Retornar `None` para dispositivos de terceiros ou falhas de conexão.

---

### Fase 4: Backend — Motor de Varredura Assíncrono
- [x] **4.1. Orquestrador de Varredura (`backend/core/scanner.py`)**
  - **Arquivo:** `backend/core/scanner.py`
  - **Critério de Aceite:**
    - Criar classe `NetworkScanner` com parâmetros: `cidr: str`, `concurrency: int = 50`, `port: int = 80`.
    - Suportar callbacks funcionais:
      - `on_progress(scanned: int, total: int)` para atualização em tempo real da barra de progresso.
      - `on_device_found(device: ControlIdDevice)` para inserção imediata na tabela da interface.
    - Utilizar `asyncio.Semaphore(concurrency)` para garantir que nunca ultrapasse o limite de conexões simultâneas.
    - Suportar cancelamento gracioso (`cancel()`) que interrompe a varredura sem quebrar o loop de eventos.
    - Retornar um objeto `ScanSummary` ao final.

---

### Fase 5: Backend — Serviços de Relatório e Exportação
- [x] **5.1. Serviço de Relatórios (`backend/services/report_service.py`)**
  - **Arquivo:** `backend/services/report_service.py`
  - **Critério de Aceite:**
    - Garantir a existência do diretório `reports/`.
    - Função `export_to_csv(summary: ScanSummary, file_path: Optional[str] = None) -> str`: gerar arquivo CSV com cabeçalho contendo resumo (total de equipamentos, data/hora) e linhas detalhadas (IP, MAC, Serial, Modelo, Versão, Latência).
    - Função `export_to_json(summary: ScanSummary, file_path: Optional[str] = None) -> str`: salvar JSON estruturado completo.
    - Função `open_reports_folder()`: abrir o Windows Explorer diretamente na pasta `reports/`.

---

### Fase 6: Ambiente de Testes e Simulação
- [x] **6.1. Servidor Mock Control iD (`tests/mock_control_id_server.py`)**
  - **Arquivo:** `tests/mock_control_id_server.py`
  - **Critério de Aceite:**
    - Criar um microservidor HTTP local (usando `http.server` ou `aiohttp`) rodando em porta local (ex.: 8089).
    - Responder aos endpoints `/system_information.fcgi` simulando um **iDFace** com serial fictício e versão de firmware.
    - Permitir testar todo o fluxo do bot sem necessidade de hardware físico no momento da programação.

---

### Fase 7: Frontend — Estilos e Componentes Flet
- [x] **7.1. Paleta de Cores e Temas (`frontend/styles/theme.py`)**
  - **Arquivo:** `frontend/styles/theme.py`
  - **Critério de Aceite:** Definir cores modernas (modo escuro por padrão, destaque verde para equipamentos encontrados, azuis corporativos e tipografia legível).
- [x] **7.2. Componente de Cabeçalho (`frontend/components/header.py`)**
  - **Arquivo:** `frontend/components/header.py`
  - **Critério de Aceite:** Renderizar ícone da aplicação, título ("Scanner de Rede Control iD") e chip informativo exibindo o IP local da máquina e interface detectada.
- [x] **7.3. Componente de Controles (`frontend/components/controls.py`)**
  - **Arquivo:** `frontend/components/controls.py`
  - **Critério de Aceite:**
    - Campo de texto `subnet_input` com máscara/validador de formato CIDR.
    - Botão "Auto-detectar Rede".
    - Botão "Iniciar Varredura" (que alterna para "Cancelar" durante a execução).
- [x] **7.4. Componente de Cards de Métricas (`frontend/components/kpi_cards.py`)**
  - **Arquivo:** `frontend/components/kpi_cards.py`
  - **Critério de Aceite:**
    - Card com destaque: **Total de Equipamentos Encontrados** (contador com fonte grande).
    - Card com IPs verificados / Total do range.
    - Card com Tempo de execução decorrido.
- [x] **7.5. Componente de Tabela de Dispositivos (`frontend/components/device_table.py`)**
  - **Arquivo:** `frontend/components/device_table.py`
  - **Critério de Aceite:**
    - Renderizar `DataTable` do Flet com colunas: IP, MAC, Número de Série, Modelo, Firmware, Latência.
    - Permitir rolagem vertical suave para suportar listas grandes.
    - Exibir estado vazio amigável ("Nenhum dispositivo encontrado ainda").

---

### Fase 8: Frontend — Integração e Ponto de Entrada
- [x] **8.1. Controlador da Aplicação (`frontend/app.py`)**
  - **Arquivo:** `frontend/app.py`
  - **Critério de Aceite:**
    - Orquestrar o estado da UI: vinculação dos botões com o `NetworkScanner`.
    - Atualizar a barra de progresso em tempo real através do callback `on_progress`.
    - Inserir novas linhas na tabela via callback `on_device_found`.
    - Tratar botões de "Exportar CSV" e "Exportar JSON" exibindo notificações toast/SnackBar de confirmação.
- [x] **8.2. Entrypoint da Aplicação (`main.py`)**
  - **Arquivo:** `main.py`
  - **Critério de Aceite:**
    - Chamar `flet.run(main)` / `flet.app(target=main)` com título de janela, dimensões padrão (1080x760) e redimensionamento habilitado.

---

### Fase 9: Testes Finais, Documentação e Empacotamento
- [x] **9.1. Validação do Fluxo Completo**
  - **Critério de Aceite:** Executar a aplicação contra o mock server e contra a rede local, confirmando preenchimento da tabela, cálculo do totalizador e geração de CSV/JSON na pasta `reports/`.
- [x] **9.2. Script de Build do Executável (`build.ps1` ou comando PyInstaller)**
  - **Critério de Aceite:** Gerar executável único standalone `.exe` funcional sem necessidade de Python instalado na máquina de destino.

---

### Fase 10: Formulário de Cabeçalho Manual e Emissão de Documento Interno (PDF)
- [x] **10.1. Modelo de Metadados (`backend/models/device.py`)**
  - **Arquivo:** `backend/models/device.py`
  - **Critério de Aceite:** Implementar dataclass `DocumentMetadata` com campos manuais: Cliente, Rua, Número, Bairro, Técnico Responsável e Local do Equipamento.
- [x] **10.2. Serviço de Emissão de Documento PDF (`backend/services/document_service.py`)**
  - **Arquivo:** `backend/services/document_service.py`
  - **Critério de Aceite:** Utilizar `reportlab` para construir documento formal de uso interno (sem assinaturas de clientes), contendo cabeçalho estruturado, caixas de resumo com contagem de iDFaces/REPs e tabela completa de equipamentos.
- [x] **10.3. Componente de Formulário Desktop (`frontend/components/client_form.py`)**
  - **Arquivo:** `frontend/components/client_form.py`
  - **Critério de Aceite:** Formulário com campos de preenchimento manual (Cliente, Rua, Número, Bairro, Técnico, Local) e validação de preenchimento obrigatório.
- [x] **10.4. Modal de Confirmação Pré-Emissão e Integração (`frontend/app.py`)**
  - **Arquivo:** `frontend/app.py`
  - **Critério de Aceite:** Exibir `AlertDialog` de confirmação contendo os dados digitados e a contagem total de equipamentos encontrados antes de disparar a geração do PDF.

