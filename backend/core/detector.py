import json
import re
import time
from typing import Optional, Dict, Any, List, Union
import httpx

from backend.models.device import ControlIdDevice
from backend.core.arp_helper import get_mac_for_ip

# Endpoints conhecidos da Control iD
ENDPOINT_PRIMARY = "/system_information.fcgi"
ENDPOINT_SECONDARY = "/api/system/information"
ENDPOINT_LOGIN = "/login.fcgi"
ENDPOINT_LOGOUT = "/logout.fcgi"
ENDPOINT_CONFIG = "/get_configuration.fcgi"

# Padrões conhecidos de modelos de hardware Control iD (ordem de especificidade decrescente)
KNOWN_PATTERNS = [
    (r"\bidface\s*max\b", "iDFace Max"),
    (r"\bidface\s*pro\b", "iDFace Pro"),
    (r"\bidface\s*lite\b", "iDFace Lite"),
    (r"\bidface\b", "iDFace"),
    (r"\bidclass\s*373\b", "iDClass 373"),
    (r"\bidclass\s*bio\b", "iDClass Bio"),
    (r"\bidclass\s*prox\b", "iDClass Prox"),
    (r"\bidclass\b", "iDClass"),
    (r"\bidaccess\s*nano\b", "iDAccess Nano"),
    (r"\bidaccess\s*pro\b", "iDAccess Pro"),
    (r"\bidaccess\b", "iDAccess"),
    (r"\bidflex\b", "iDFlex"),
    (r"\bidbox\b", "iDBox"),
    (r"\bidfit\b", "iDFit"),
    (r"\bidblock\b", "iDBlock"),
    (r"\bidgate\b", "iDGate"),
    (r"\bidtouch\b", "iDTouch"),
    (r"\bidprint\b", "iDPrint"),
    (r"\bidbio\b", "iDBio"),
    (r"\bidlook\b", "iDLook"),
    (r"\bidsecure\b", "iDSecure"),
]

GENERIC_WORDS = {
    "login", "web server", "webserver", "home", "index", "painel",
    "autenticacao", "autenticação", "control id", "controlid", ""
}


def _extract_serial(data: Dict[str, Any]) -> Optional[str]:
    """Extrai número de série seguindo a ordem de prioridade da especificação."""
    for key in ("serial", "serial_number", "serialNumber", "device_id", "deviceId"):
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _extract_model(data: Dict[str, Any], html_content: Optional[Union[str, List[str]]] = None) -> str:
    """
    Extrai o modelo exato do equipamento (ex: iDFace, iDClass, iDAccess, etc.)
    inspecionando chaves do payload JSON, licença, configurações e conteúdo HTML coletado.
    """
    html_sources: List[str] = []
    if isinstance(html_content, str):
        html_sources.append(html_content)
    elif isinstance(html_content, list):
        html_sources.extend([s for s in html_content if isinstance(s, str)])

    # 1. Campos diretos no dicionário de dados (ex: 'model', 'device_model', 'product_name')
    for key in ("model", "device_model", "modelName", "product", "product_name", "device_name", "equipment_type", "equipment", "name"):
        val = data.get(key)
        if val is not None and str(val).strip():
            str_val = str(val).strip()
            # Confere se corresponde a algum padrão de modelo conhecido
            for pat, canonical in KNOWN_PATTERNS:
                if re.search(pat, str_val, re.IGNORECASE):
                    return canonical
            if str_val.lower() not in GENERIC_WORDS:
                return str_val

    # 2. Inspeciona o bloco de licença ou biometria retornado em system_information.fcgi
    license_data = data.get("license")
    if isinstance(license_data, dict):
        lic_str = json.dumps(license_data).lower()
        if any(w in lic_str for w in ("facial", "face", "faces")):
            return "iDFace"
        if any(w in lic_str for w in ("rep", "afd", "mrp")):
            return "iDClass"
        if any(w in lic_str for w in ("catraca", "turnstile")):
            return "iDBlock"

    # 3. Inspeciona todas as páginas e fragmentos HTML coletados
    for html in html_sources:
        if not html:
            continue

        # 3a. Prioridade: Título da página <title>
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE)
        if title_match:
            title_text = title_match.group(1).strip()
            for pat, canonical in KNOWN_PATTERNS:
                if re.search(pat, title_text, re.IGNORECASE):
                    return canonical

            cleaned = re.sub(r"(?i)control\s*i?d\s*[-–—:]*\s*", "", title_text).strip()
            if cleaned.lower() not in GENERIC_WORDS and len(cleaned) >= 3:
                for pat, canonical in KNOWN_PATTERNS:
                    if re.search(pat, cleaned, re.IGNORECASE):
                        return canonical
                return cleaned

        # 3b. Varredura completa do corpo do HTML (cabeçalhos, scripts, logos e tags)
        for pat, canonical in KNOWN_PATTERNS:
            if re.search(pat, html, re.IGNORECASE):
                return canonical

    # 4. Inspeciona payload JSON completo (incluindo objetos aninhados de configuração)
    if data:
        full_json_str = json.dumps(data)
        for pat, canonical in KNOWN_PATTERNS:
            if re.search(pat, full_json_str, re.IGNORECASE):
                return canonical

    return "Control iD (Genérico)"


def _extract_firmware(data: Dict[str, Any]) -> str:
    """Extrai versão do firmware do equipamento."""
    for key in ("version", "firmware_version", "softwareVersion", "sw_version"):
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return "N/D"


async def login_control_id(
    client: httpx.AsyncClient,
    ip: str,
    port: int = 80,
    username: str = "admin",
    password: str = "admin",
    timeout_sec: float = 1.5
) -> Optional[str]:
    """
    Realiza autenticação no dispositivo Control iD via POST /login.fcgi
    e retorna o token de sessão criado para as requisições subsequentes.
    """
    if not username and not password:
        return None

    url = f"http://{ip}:{port}{ENDPOINT_LOGIN}"
    payload = {"login": username, "password": password}
    try:
        resp = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=timeout_sec
        )
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    session = data.get("session")
                    if session and str(session).strip():
                        return str(session).strip()
            except Exception:
                pass
    except Exception:
        pass
    return None


async def logout_control_id(
    client: httpx.AsyncClient,
    ip: str,
    port: int = 80,
    session: str = "",
    timeout_sec: float = 1.0
) -> None:
    """Encerra a sessão no equipamento para liberar conexões."""
    if not session:
        return
    url = f"http://{ip}:{port}{ENDPOINT_LOGOUT}?session={session}"
    try:
        await client.post(url, timeout=timeout_sec)
    except Exception:
        pass


async def probe_control_id(
    client: httpx.AsyncClient,
    ip: str,
    port: int = 80,
    timeout_sec: float = 1.5,
    username: str = "admin",
    password: str = "admin"
) -> Optional[ControlIdDevice]:
    """
    Sonda um determinado IP na porta configurada verificando se responde
    às assinaturas de equipamentos Control iD. Identifica com precisão o modelo
    do hardware, número de série, firmware, latência e endereço MAC.
    """
    base_url = f"http://{ip}:{port}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "ControlID-Scanner/1.0"
    }

    start_time = time.perf_counter()
    device_data: Optional[Dict[str, Any]] = None
    is_control_id = False
    html_sources: List[str] = []
    auth_attempted = False

    # 1. Tentativa de Consulta Pública Primária: /system_information.fcgi (GET e POST)
    try:
        resp = await client.get(
            f"{base_url}{ENDPOINT_PRIMARY}",
            headers=headers,
            timeout=timeout_sec
        )
        if resp.status_code == 200:
            try:
                parsed = resp.json()
                if isinstance(parsed, dict) and any(k in parsed for k in (
                    "serial", "serial_number", "model", "device_model", "device_id", "version", "uptime", "network"
                )):
                    is_control_id = True
                    device_data = parsed
            except Exception:
                try:
                    parsed = json.loads(resp.text)
                    if isinstance(parsed, dict):
                        device_data = parsed
                        is_control_id = True
                except Exception:
                    pass
        elif resp.status_code in (401, 403):
            # Endpoint existe mas bloqueado por autenticação
            is_control_id = True
            device_data = {}
        elif resp.status_code == 405:
            # Alguns firmwares aceitam apenas POST
            resp_post = await client.post(
                f"{base_url}{ENDPOINT_PRIMARY}",
                headers=headers,
                timeout=timeout_sec
            )
            if resp_post.status_code in (200, 401, 403):
                is_control_id = True
                try:
                    device_data = resp_post.json()
                except Exception:
                    device_data = {}
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        # Descarte rápido e silencioso de hosts inalcançáveis ou portas fechadas
        return None

    # 2. Se não identificado, tenta Endpoint Secundário REST: /api/system/information
    if not is_control_id:
        try:
            resp = await client.get(
                f"{base_url}{ENDPOINT_SECONDARY}",
                headers=headers,
                timeout=timeout_sec
            )
            if resp.status_code == 200:
                try:
                    payload = resp.json()
                    if isinstance(payload, dict):
                        inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
                        if any(k in inner for k in ("serialNumber", "modelName", "softwareVersion")):
                            device_data = inner
                            is_control_id = True
                except Exception:
                    pass
            elif resp.status_code in (401, 403):
                is_control_id = True
                device_data = {}
        except Exception:
            pass

    # 3. Se não identificado, inspeciona assinatura no login ou tela inicial
    if not is_control_id:
        try:
            resp = await client.get(
                f"{base_url}{ENDPOINT_LOGIN}",
                headers=headers,
                timeout=timeout_sec
            )
            text_body = resp.text.lower()
            if "control id" in text_body or "controlid" in text_body:
                is_control_id = True
                device_data = {}
                html_sources.append(resp.text)
        except Exception:
            pass

    # 4. Se ainda não confirmado, verifica a página inicial HTTP /
    if not is_control_id:
        try:
            resp = await client.get(
                f"{base_url}/",
                headers=headers,
                timeout=timeout_sec
            )
            text_body = resp.text.lower()
            if "control id" in text_body or "controlid" in text_body or any(p in text_body for p in ("idface", "idclass", "idaccess", "idflex")):
                is_control_id = True
                device_data = {}
                html_sources.append(resp.text)
        except Exception:
            pass

    # Se após todas as tentativas não for um dispositivo Control iD reconhecido
    if not is_control_id:
        return None

    # 5. Coleta de páginas web (para extração visual/HTML do modelo)
    for path in ("/", "/login.html", "/login.fcgi"):
        try:
            r = await client.get(f"{base_url}{path}", headers=headers, timeout=timeout_sec)
            if r.status_code == 200 and r.text:
                html_sources.append(r.text)
        except Exception:
            pass

    # 6. Autenticação e extração avançada de metadados
    serial = _extract_serial(device_data) if device_data else None
    current_model = _extract_model(device_data or {}, html_sources)
    needs_auth = (not serial or serial == "N/D" or current_model == "Control iD (Genérico)")

    if needs_auth and (username or password):
        auth_attempted = True
        session = await login_control_id(
            client=client,
            ip=ip,
            port=port,
            username=username,
            password=password,
            timeout_sec=timeout_sec
        )
        if session:
            try:
                # 6a. Consulta autenticada de informações do sistema
                auth_url = f"{base_url}{ENDPOINT_PRIMARY}?session={session}"
                resp_auth = await client.post(auth_url, timeout=timeout_sec)
                if resp_auth.status_code != 200:
                    resp_auth = await client.get(auth_url, timeout=timeout_sec)

                if resp_auth.status_code == 200:
                    try:
                        auth_data = resp_auth.json()
                        if isinstance(auth_data, dict):
                            if device_data:
                                device_data.update(auth_data)
                            else:
                                device_data = auth_data
                            serial = _extract_serial(device_data)
                    except Exception:
                        pass

                # 6b. Consulta parâmetros de configuração (/get_configuration.fcgi)
                try:
                    config_url = f"{base_url}{ENDPOINT_CONFIG}?session={session}"
                    cfg_payload = {
                        "general": ["device_name", "model", "equipment_type", "product_name"],
                        "system": ["model", "name"]
                    }
                    resp_cfg = await client.post(config_url, json=cfg_payload, timeout=timeout_sec)
                    if resp_cfg.status_code == 200:
                        cfg_data = resp_cfg.json()
                        if isinstance(cfg_data, dict) and device_data is not None:
                            device_data["_config"] = cfg_data
                except Exception:
                    pass

                # 6c. Consulta página inicial autenticada (dashboard do dispositivo)
                try:
                    resp_auth_html = await client.get(f"{base_url}/?session={session}", timeout=timeout_sec)
                    if resp_auth_html.status_code == 200 and resp_auth_html.text:
                        html_sources.append(resp_auth_html.text)
                except Exception:
                    pass

            finally:
                # Libera a sessão no equipamento
                await logout_control_id(client, ip, port, session, timeout_sec=0.8)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)

    if not serial:
        if auth_attempted:
            serial = "N/D (Bloqueado por Auth - Verificar Senha)"
        else:
            serial = "N/D"

    # Extrai modelo final com todas as fontes combinadas
    model = _extract_model(device_data or {}, html_sources)
    firmware = _extract_firmware(device_data or {})

    # Resolução de MAC: Win32 SendARP tem prioridade absoluta
    mac = get_mac_for_ip(ip)
    if mac == "N/D" and device_data and "mac" in device_data:
        raw_mac = str(device_data["mac"]).strip().upper()
        if re.match(r"^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$", raw_mac):
            mac = raw_mac.replace("-", ":")

    return ControlIdDevice(
        ip=ip,
        mac=mac,
        serial_number=serial,
        model=model,
        firmware_version=firmware,
        response_time_ms=elapsed_ms
    )
