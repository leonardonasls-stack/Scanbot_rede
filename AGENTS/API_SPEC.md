# API_SPEC — Especificação Técnica de Endpoints e Protocolo Control iD

Este documento detalha o comportamento dos servidores web embarcados nos dispositivos da **Control iD** (linhas iDFace, iDClass, iDAccess, iDBox, etc.), descrevendo os endpoints de consulta pública, estruturas de payloads JSON, headers HTTP e regras de extração de metadados.

---

### 1. Visão Geral da Comunicação

- **Protocolo de Transporte:** HTTP/1.1 (Porta TCP padrão: `80` ou `443` para HTTPS).
- **Servidor Web Embarcado Típico:** `lighttpd` / FastCGI (`.fcgi`) ou microsserviço REST em C/C++ embarcado em Linux rodando no SoC do equipamento.
- **Formato de Dados:** JSON (`application/json`) e páginas HTML com metadados estruturados.
- **Modo de Acesso:** Apenas requisições de consulta **sem autenticação prévia** (read-only), evitando qualquer interferência na operação do equipamento.

---

### 2. Catálogo de Endpoints de Sondagem (Probing)

#### 2.1. Endpoint Primário: `/system_information.fcgi`
É o endpoint mais comum e abrangente na linha de controle de acesso (iDFace, iDAccess, iDBox, iDFit) e em diversos REPs.

- **Método HTTP:** `GET` (ou `POST` com body vazio)
- **Headers da Requisição:**
  ```http
  Accept: application/json
  User-Agent: ControlID-Scanner/1.0
  ```
- **Código de Status Sucesso:** `200 OK`
- **Content-Type:** `application/json` ou `text/plain`

##### Exemplo de Payload Real (iDFace / iDAccess):
```json
{
  "serial": "100200300400500",
  "device_id": "100200300400500",
  "version": "2.4.1",
  "model": "iDFace",
  "mac": "00:1A:2B:3C:4D:5E",
  "uptime": 128450
}
```

##### Exemplo de Payload Alternativo (Firmwares REP / iDClass):
```json
{
  "serial_number": "0000000012345678",
  "device_model": "iDClass",
  "firmware_version": "1.1.25",
  "hardware_version": "REV_C"
}
```

---

#### 2.2. Endpoint Secundário: `/api/system/information`
Utilizado como fallback para equipamentos com firmwares mais recentes ou arquitetura REST pura.

- **Método HTTP:** `GET`
- **Headers:** `Accept: application/json`
- **Código de Status Sucesso:** `200 OK`
- **Exemplo de Payload:**
```json
{
  "status": "success",
  "data": {
    "serialNumber": "9876543210",
    "modelName": "iDAccess Pro",
    "softwareVersion": "3.0.2"
  }
}
```

---

#### 2.3. Endpoint de Autenticação: `/login.fcgi` e `/logout.fcgi`
Para equipamentos protegidos ou firmwares que restringem o número de série apenas a sessões autenticadas:

- **Método HTTP:** `POST`
- **Headers:** `Content-Type: application/json`, `Accept: application/json`
- **Payload:**
  ```json
  {
    "login": "admin",
    "password": "admin"
  }
  ```
- **Resposta Sucesso:**
  ```json
  {
    "session": "apx7NM2CErTcvXpuvExuzaZ"
  }
  ```
- **Uso Subsequente:** Chamadas para `/system_information.fcgi?session=<SESSION>` liberam o payload com o número de série completo.
- **Encerramento:** `POST /logout.fcgi?session=<SESSION>` para liberação das conexões no hardware.

---

#### 2.4. Endpoint Terciário / Fallback de Assinatura: `/login.fcgi` (GET) ou `/`
Caso os endpoints acima retornem `401 Unauthorized` ou `404 Not Found` (devido a configurações de segurança do cliente), o scanner inspeciona os cabeçalhos e a página inicial:

- **Método HTTP:** `GET`
- **Critérios de Reconhecimento:**
  - **Título HTML (`<title>`):** Contém `Control iD` (ex.: `<title>Control iD - iDFace</title>`).
  - **Meta tags ou Rodapé:** Menção explícita ao fabricante ou ao modelo.
  - **Cabeçalho Server:** Retorno característico do firmware.

---

### 3. Regras de Normalização e Extração de Metadados

O módulo detector (`detector.py`) deve aplicar a seguinte ordem de prioridade para garantir que os dados sejam normalizados de forma consistente:

#### 3.1. Número de Série (Serial Number)
Busca nos seguintes campos da resposta JSON (em ordem de precedência):
1. `serial`
2. `serial_number`
3. `serialNumber`
4. `device_id`
5. `deviceId`
*Se nenhum campo estiver presente, mas o dispositivo foi identificado com certeza como Control iD via HTML/Header, registrar como `N/D (Bloqueado por Auth)`.*

#### 3.2. Modelo do Equipamento
1. `model`
2. `device_model`
3. `modelName`
4. Parse do `<title>` da página HTML (ex.: "Control iD - iDFace" -> extrai `"iDFace"`)
*Valor padrão caso não identificado: `"Control iD (Modelo Genérico)"`.*

#### 3.3. Versão do Firmware
1. `version`
2. `firmware_version`
3. `softwareVersion`
4. `sw_version`
*Valor padrão caso não identificado: `"N/D"`.*

#### 3.4. Endereço MAC (Camada 2 vs Payload)
- Embora alguns firmwares retornem um campo `"mac"` no JSON, **o endereço MAC retornado pela Windows API (`SendARP`) tem prioridade absoluta**.
- **Motivo Técnico:** O MAC retornado via ARP reflete com 100% de precisão a interface de rede física que está comunicando ativamente com o host na rede local, evitando problemas com interfaces virtuais ou pontes de rede internas do SoC.

---

### 4. Mapeamento de Modelos Conhecidos Control iD

| Linha | Modelos Típicos | Portas Usuais | Endpoints Suportados |
| :--- | :--- | :--- | :--- |
| **Reconhecimento Facial** | iDFace, iDFace Max, iDFace Inox | 80, 443 | `/system_information.fcgi`, `/api/system/information` |
| **Controle de Acesso Biométrico** | iDAccess, iDAccess Pro, iDAccess Nano, iDFit | 80, 443 | `/system_information.fcgi`, `/login.fcgi` |
| **Controle de Acesso / Portas** | iDBox, iDUHF | 80 | `/system_information.fcgi` |
| **Relógios de Ponto (REP)** | iDClass, PrintPoint III, iDClass 373 | 80, 8000 | `/system_information.fcgi`, `/login.fcgi` |
| **Catracas Eletrônicas** | Catraca iDBlock, Catraca Revolution | 80 | `/system_information.fcgi` |

---

### 5. Tratamento de Exceções e Respostas HTTP

| Cenário | Resposta do Host | Ação do Scanner |
| :--- | :--- | :--- |
| **Host Desligado / IP Vazio** | Timeout de Conexão (`httpx.ConnectTimeout`) | Descarte silencioso imediato (<1.5s). |
| **Porta 80 Fechada** | Conexão Recusada (`httpx.ConnectError`) | Descarte silencioso imediato. |
| **Outro Equipamento (Impressora/Roteador)** | `200 OK` com JSON/HTML de terceiros | Inspeção falha; host descartado sem erro. |
| **Control iD com Senha Restrita** | `401 Unauthorized` / `403 Forbidden` | Extrai informações da tela de login/título e salva com status de login protegido. |
| **Control iD Normal** | `200 OK` com JSON compatível | Extrai Serial, Modelo, Firmware e dispara resolução MAC via `SendARP`. |
