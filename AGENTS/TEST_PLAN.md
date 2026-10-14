# TEST_PLAN — Plano de Testes e Homologação
## Bot de Varredura e Inventário de Equipamentos Control iD

Este documento estabelece a metodologia de testes para validar o funcionamento, a precisão e a estabilidade da aplicação em todas as camadas (backend de rede, detector, resolução ARP, persistência de relatórios e interface desktop Flet).

---

### 1. Visão Geral da Estratégia de Testes

A validação do projeto é estruturada em 4 níveis complementares:
1. **Testes Unitários:** Validação individual de funções puras (cálculo de sub-redes, parsers de JSON e formatadores de exportação).
2. **Testes de Integração com Mock Server:** Simulação local de equipamentos Control iD para desenvolvimento e testes automatizados sem necessidade de hardware físico.
3. **Testes de Performance e Carga:** Verificação do controle de concorrência (`asyncio.Semaphore`) em blocos `/24` (254 endereços).
4. **Testes de Interface (UI) e Campo:** Validação da responsividade do Flet e testes em redes reais com equipamentos físicos.

---

### 2. Especificação do Mock Server (`tests/mock_control_id_server.py`)

Para permitir o desenvolvimento e os testes a qualquer momento, será implementado um microservidor HTTP local configurável que simula diferentes perfis de equipamentos da rede:

```text
               ┌────────────────────────────────────────────────────────┐
               │         Mock Server Local (Porta 8089)                 │
               ├────────────────────────────────────────────────────────┤
               │  /system_information.fcgi?type=idface                  │
               │  └── Retorna JSON de um iDFace válido                  │
               │                                                        │
               │  /system_information.fcgi?type=idclass                 │
               │  └── Retorna JSON de um iDClass (campos alternativos)  │
               │                                                        │
               │  /system_information.fcgi?type=other_device            │
               │  └── Retorna HTML de roteador comum (não Control iD)   │
               │                                                        │
               │  /system_information.fcgi?type=slow                    │
               │  └── Simula atraso/timeout proposital (sleep 3s)       │
               │                                                        │
               │  /system_information.fcgi?type=error                   │
               │  └── Retorna HTTP 500 / 404                            │
               └────────────────────────────────────────────────────────┘
```

---

### 3. Matriz de Casos de Teste (Test Cases)

#### 3.1. Camada de Baixo Nível e Rede (Backend)

| ID | Cenário de Teste | Procedimento | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-01** | **Resolução ARP Windows (`SendARP`)** | Executar `get_mac_for_ip()` contra o IP do gateway local da máquina de teste. | Retornar o endereço MAC válido no formato `AA:BB:CC:DD:EE:FF` em menos de 10ms sem exigir admin. |
| **TC-02** | **Resolução ARP para Host Inexistente** | Executar `get_mac_for_ip()` para um IP não utilizado da sub-rede. | Retornar `"N/D"` ou `"Falha ARP"` de forma segura sem lançar exceção não tratada. |
| **TC-03** | **Detecção Automática de Sub-rede** | Chamar `get_local_network_info()`. | Identificar o IP local ativo e calcular corretamente a sub-rede no padrão CIDR (ex: `192.168.1.0/24`). |
| **TC-04** | **Validação de Sintaxe CIDR** | Informar faixas válidas (`10.0.0.0/24`) e inválidas (`999.1.1.1/99`). | Aceitar faixas válidas e levantar erro amigável para formatos inválidos. |

#### 3.2. Camada de Detecção e Probing Control iD

| ID | Cenário de Teste | Procedimento | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-05** | **Identificação iDFace Padrão** | Executar probe contra o mock do iDFace. | Extrair corretamente Serial, Modelo `"iDFace"` e Versão. Identificar como Control iD. |
| **TC-06** | **Identificação iDClass (Chaves Alternativas)** | Executar probe contra endpoint com campos `serial_number` e `device_model`. | Normalizar os dados corretamente para o modelo imutável `ControlIdDevice`. |
| **TC-07** | **Descarte de Dispositivo de Terceiros** | Executar probe contra servidor Apache/Nginx ou roteador da rede. | Retornar `None` e descartar o host silenciosamente sem falsos positivos. |
| **TC-08** | **Host com Timeout / Desligado** | Executar probe contra IP inexistente na rede. | Concluir tentativa em até 1.5s (respeitando o timeout) e descartar. |

#### 3.3. Camada de Varredura e Concorrência

| ID | Cenário de Teste | Procedimento | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-09** | **Varredura Completa de Sub-rede `/24`** | Executar varredura em bloco de 254 endereços com 50 workers assíncronos. | Concluir varredura completa entre 10 e 25 segundos. |
| **TC-10** | **Cancelamento Gracioso** | Disparar varredura e solicitar cancelamento aos 5 segundos de execução. | Interromper todas as tarefas pendentes imediatamente sem travar o loop do `asyncio`. |
| **TC-11** | **Consolidação de Métricas** | Finalizar varredura com equipamentos detectados. | O `ScanSummary` deve conter contagem exata de equipamentos encontrados, total de IPs varridos e tempo total decorrido. |

#### 3.4. Camada de Interface Gráfica (Frontend Flet)

| ID | Cenário de Teste | Procedimento | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-12** | **Não Congelamento da Interface** | Iniciar varredura longa e tentar interagir com a janela (arrastar, redimensionar, clicar). | A interface permanece fluida a 60 FPS, sem exibir mensagem "Não Respondendo". |
| **TC-13** | **Atualização Reativa da Tabela** | Durante a varredura, o scanner encontra um dispositivo. | O novo dispositivo aparece imediatamente como uma nova linha na tabela sem precisar esperar o fim da varredura. |
| **TC-14** | **Barra de Progresso em Tempo Real** | Acompanhar a execução de 0% a 100%. | A `ProgressBar` se movimenta continuamente de forma proporcional aos IPs escaneados. |
| **TC-15** | **Atualização do Card KPI Totalizador** | Cada equipamento encontrado deve incrementar o contador. | O card "Total de Equipamentos Encontrados" exibe o número exato com destaque visual. |

#### 3.5. Camada de Exportação de Relatórios

| ID | Cenário de Teste | Procedimento | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-16** | **Exportação para CSV** | Clicar em "Exportar CSV" ao término da varredura. | Cria arquivo `reports/relatorio_control_id_YYYYMMDD_HHMMSS.csv` com cabeçalho de resumo e linhas de dados legíveis no Excel. |
| **TC-17** | **Exportação para JSON** | Clicar em "Exportar JSON". | Cria arquivo `reports/relatorio_control_id_YYYYMMDD_HHMMSS.json` válido com estrutura completa para integrações. |
| **TC-18** | **Abrir Pasta de Relatórios** | Clicar em "Abrir Pasta". | Abre o Windows Explorer diretamente na pasta `reports/`. |

---

### 4. Critérios de Homologação e Aceite Final

A versão será considerada **aprovada para produção** quando atender cumulativamente aos seguintes critérios:
- [ ] **100% de precisão na detecção:** Nenhum falso positivo gerado para outros equipamentos da rede corporativa.
- [ ] **Performance validada:** Varredura de sub-rede padrão `/24` (254 hosts) concluída em menos de 25 segundos.
- [ ] **Resolução de MAC funcional:** 100% dos equipamentos da mesma sub-rede devem ter seu MAC físico resolvido via ARP.
- [ ] **Estabilidade da UI:** Zero travamentos na interface Flet durante início, execução, cancelamento e exportação.
- [ ] **Execução sem privilégios:** Aplicação roda com sucesso sob usuário comum do Windows (não-administrador).
- [ ] **Build Standalone (.exe):** Executável único gerado e testado em máquina Windows limpa (sem Python instalado).
