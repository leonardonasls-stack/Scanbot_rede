# SCAN BOT Rede — Scanner e Inventário de Equipamentos

Ferramenta desktop de alta performance desenvolvida em **Python** e **Flet** (Material Design 3 / Flutter Engine) para varredura sob demanda, identificação por assinatura e inventário de equipamentos de rede.

---

## 🚀 Principais Funcionalidades

- **Varredura Sob Demanda:** Nenhuma varredura é disparada automaticamente na inicialização. O usuário tem controle total para digitar a faixa de rede desejada ou clicar em "Auto-detectar" antes de iniciar.
- **Alta Performance Assíncrona:** Varre blocos `/24` (254 endereços IPv4) em menos de 20 segundos utilizando pool de 50 workers assíncronos (`httpx.AsyncClient` + `asyncio.Semaphore`).
- **Resolução Nativa de MAC via Win32:** Coleta do endereço MAC físico de camada 2 diretamente via API do Windows (`ctypes.windll.iphlpapi.SendARP`), sem dependência de privilégios de administrador.
- **Detecção Inteligente:** Sonda de endpoints embarcados com descarte silencioso de hosts irrelevantes.
- **Interface Gráfica Desktop Moderna:** Visual corporativo Dark Mode em Flet, com streaming reativo de resultados na tabela, contador de equipamentos em destaque e barra de progresso em tempo real.
- **Exportação Estruturada:** Exportação em um clique para **CSV** (otimizado com UTF-8 BOM para Excel) e **JSON**, com botão para abrir a pasta de relatórios no Windows Explorer.

---

## 📁 Estrutura do Projeto

```text
Bot Varredura - Control ID/
│
├── AGENTS/                         # Especificações completas do projeto
├── backend/                        # Camada de Serviços e Rede (Isolada da UI)
│   ├── core/
│   │   ├── scanner.py              # Orquestrador assíncrono de varredura
│   │   ├── detector.py             # Sonda e parser de equipamentos
│   │   ├── arp_helper.py           # Resolvedor de MAC via Win32 SendARP
│   │   └── network_utils.py        # Identificação de IP local e cálculo CIDR
│   ├── models/
│   │   └── device.py               # Dataclasses ControlIdDevice e ScanSummary
│   └── services/
│       └── report_service.py       # Geradores CSV/JSON e atalhos de arquivo
│
├── frontend/                       # Camada Visual Desktop (Flet)
│   ├── app.py                      # Controlador principal e eventos de interface
│   ├── components/
│   │   ├── header.py               # Topbar com branding SCAN BOT Rede
│   │   ├── controls.py             # Campo de CIDR e botões Iniciar/Cancelar
│   │   ├── kpi_cards.py            # Totalizador de equipamentos e métricas
│   │   └── device_table.py         # Tabela de dispositivos com tags de modelo
│   └── styles/
│       └── theme.py                # Tokens de design, paleta Dark Mode e cores
│
├── reports/                        # Diretório onde os relatórios gerados são gravados
├── tests/                          # Suíte de testes automatizados e Mock Server
├── main.py                         # Ponto de entrada da aplicação desktop
├── requirements.txt                # Dependências Python
├── build.ps1                       # Script de compilação PyInstaller (.exe)
└── README.md                       # Documentação do projeto
```

---

## 🛠️ Como Executar

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.

### 2. Instalação das Dependências
```powershell
pip install -r requirements.txt
```

### 3. Executando a Aplicação
```powershell
python main.py
```

### 4. Executando os Testes Automatizados
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### 5. Compilando o Executável Standalone (.exe) para Windows
Para gerar o executável standalone:
```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```
O executável será gerado em: `dist/SCAN-BOT-Rede/SCAN-BOT-Rede.exe`.
