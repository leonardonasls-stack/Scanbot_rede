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
ENDPOINT_LOAD_OBJECTS = "/load_objects.fcgi"
ENDPOINT_CATRA_INFO = "/get_catra_info.fcgi"

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

    candidate_model: Optional[str] = None

    # 1. Campos diretos no dicionário de dados (ex: 'model', 'device_model', 'product_name')
    for key in ("model", "device_model", "modelName", "product", "product_name", "device_name", "equipment_type", "equipment", "name"):
        val = data.get(key)
        if val is not None and str(val).strip():
            str_val = str(val).strip()
            # Confere se corresponde a algum padrão de modelo conhecido
            for pat, canonical in KNOWN_PATTERNS:
                if re.search(pat, str_val, re.IGNORECASE):
                    candidate_model = canonical
                    break
            if candidate_model:
                break
            if str_val.lower() not in GENERIC_WORDS:
                candidate_model = str_val
                break

    # 2. Inspeciona o bloco de licença ou biometria retornado em system_information.fcgi
    if not candidate_model:
        license_data = data.get("license")
        if isinstance(license_data, dict):
            lic_str = json.dumps(license_data).lower()
            if any(w in lic_str for w in ("facial", "face", "faces")):
                candidate_model = "iDFace"
            elif any(w in lic_str for w in ("rep", "afd", "mrp")):
                candidate_model = "iDClass"
            elif any(w in lic_str for w in ("catraca", "turnstile")):
                candidate_model = "iDBlock"

    # 3. Inspeciona todas as páginas e fragmentos HTML coletados
    if not candidate_model:
        for html in html_sources:
            if not html:
                continue

            # 3a. Prioridade: Título da página <title>
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE)
            if title_match:
                title_text = title_match.group(1).strip()
                for pat, canonical in KNOWN_PATTERNS:
                    if re.search(pat, title_text, re.IGNORECASE):
                        candidate_model = canonical
                        break
                if candidate_model:
                    break

                cleaned = re.sub(r"(?i)control\s*i?d\s*[-–—:]*\s*", "", title_text).strip()
                if cleaned.lower() not in GENERIC_WORDS and len(cleaned) >= 3:
                    for pat, canonical in KNOWN_PATTERNS:
                        if re.search(pat, cleaned, re.IGNORECASE):
                            candidate_model = canonical
                            break
                    if candidate_model:
                        break
                    candidate_model = cleaned
                    break

            # 3b. Varredura completa do corpo do HTML (cabeçalhos, scripts, logos e tags)
            for pat, canonical in KNOWN_PATTERNS:
                if re.search(pat, html, re.IGNORECASE):
                    candidate_model = canonical
                    break
            if candidate_model:
                break

    # 4. Inspeciona payload JSON completo (incluindo objetos aninhados de configuração)
    if not candidate_model and data:
        full_json_str = json.dumps(data)
        for pat, canonical in KNOWN_PATTERNS:
            if re.search(pat, full_json_str, re.IGNORECASE):
                candidate_model = canonical
                break

    if not candidate_model:
        candidate_model = "Control iD (Genérico)"

    # 5. Refinamento de Catraca Facial (iDBlock Facial):
    # Se o modelo base for da família iDFace ou Control iD genérico, mas houver indícios de catraca
    # (parâmetros de giro 'catra', 'turnstile', 'get_catra_info' ou portas/portais de catraca)
    is_face = "idface" in candidate_model.lower() or "facial" in candidate_model.lower()
    has_catra_evidence = False

    if data:
        if data.get("_is_catra") is True:
            has_catra_evidence = True
        else:
            cfg = data.get("_config")
            if isinstance(cfg, dict):
                catra_cfg = cfg.get("catra")
                if isinstance(catra_cfg, dict) and any(catra_cfg.get(k) is not None for k in ("gateway", "anti_passback", "daily_reset")):
                    has_catra_evidence = True
            
            # Checa se nas configurações ou no nome do dispositivo há menção explícita de catraca/idblock
            dev_name = str(data.get("device_name") or data.get("name") or "")
            if any(w in dev_name.lower() for w in ("catraca", "turnstile", "idblock")):
                has_catra_evidence = True

    if has_catra_evidence:
        if is_face:
            if "max" in candidate_model.lower():
                return "iDFace Max (iDBlock Facial)"
            elif "pro" in candidate_model.lower():
                return "iDFace Pro (iDBlock Facial)"
            return "iDFace (iDBlock Facial)"
        elif candidate_model == "Control iD (Genérico)":
            candidate_model = "iDBlock"

    # 6. Refinamento de iDBlock PNE:
    # Identifica catracas PNE por prefixo do número de série (ex: 0K1400) ou indícios de PNE no nome/configurações
    if "idblock" in candidate_model.lower():
        is_pne = False
        sn = str(data.get("serial") or data.get("serial_number") or data.get("serialNumber") or "")
        if sn.startswith("0K1400"):
            is_pne = True
        else:
            dev_name = str(data.get("device_name") or data.get("name") or "")
            if re.search(r"\bpne\b", dev_name, re.IGNORECASE):
                is_pne = True
            else:
                raw_devs = data.get("_raw_devices")
                if isinstance(raw_devs, list):
                    for d in raw_devs:
                        if isinstance(d, dict) and re.search(r"\bpne\b", str(d.get("name") or ""), re.IGNORECASE):
                            is_pne = True
                            break
                if not is_pne:
                    raw_ports = data.get("_raw_portals")
                    if isinstance(raw_ports, list):
                        for p in raw_ports:
                            if isinstance(p, dict) and re.search(r"\bpne\b", str(p.get("name") or ""), re.IGNORECASE):
                                is_pne = True
                                break

        if is_pne:
            return "iDBlock PNE"

    return candidate_model


def _extract_firmware(data: Dict[str, Any]) -> str:
    """Extrai versão do firmware do equipamento."""
    for key in ("version", "firmware_version", "softwareVersion", "sw_version"):
        val = data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return "N/D"


def _extract_area_info(device_data: Dict[str, Any]) -> str:
    """
    Extrai a área e/ou localização configurada para o equipamento.
    Prioriza objetos de áreas/portais retornados pelo load_objects.fcgi
    e faz fallback para configurações de device_name/location.
    """
    if not device_data:
        return "N/D"

    # 1. Se capturou dados estruturados de áreas e portais via load_objects
    area_names = device_data.get("_area_names", [])
    portal_names = device_data.get("_portal_names", [])

    if area_names and portal_names:
        return f"{', '.join(area_names)} ({', '.join(portal_names)})"
    elif area_names:
        return ", ".join(area_names)
    elif portal_names:
        return f"Portal: {', '.join(portal_names)}"

    # 2. Busca em device_name das configurações gerais (_config)
    cfg = device_data.get("_config", {})
    if isinstance(cfg, dict):
        gen = cfg.get("general", {})
        if isinstance(gen, dict):
            dev_name = gen.get("device_name")
            if dev_name and str(dev_name).strip() and str(dev_name).lower() not in GENERIC_WORDS:
                return str(dev_name).strip()

        sys_cfg = cfg.get("system", {})
        if isinstance(sys_cfg, dict):
            dev_name = sys_cfg.get("name")
            if dev_name and str(dev_name).strip() and str(dev_name).lower() not in GENERIC_WORDS:
                return str(dev_name).strip()

    # 3. Busca campos diretos de localização ou nome no payload
    for key in ("area", "area_name", "location", "device_name", "portal_name"):
        val = device_data.get(key)
        if val is not None and str(val).strip() and str(val).lower() not in GENERIC_WORDS:
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
    has_credentials = bool(username or password)

    if has_credentials:
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
                        "system": ["model", "name"],
                        "catra": ["gateway", "anti_passback", "daily_reset"]
                    }
                    resp_cfg = await client.post(config_url, json=cfg_payload, timeout=timeout_sec)
                    if resp_cfg.status_code == 200:
                        cfg_data = resp_cfg.json()
                        if isinstance(cfg_data, dict) and device_data is not None:
                            device_data["_config"] = cfg_data
                            # Se o bloco catra retornou parâmetros válidos
                            catra_block = cfg_data.get("catra")
                            if isinstance(catra_block, dict) and any(catra_block.get(k) is not None for k in ("gateway", "anti_passback", "daily_reset")):
                                device_data["_is_catra"] = True
                except Exception:
                    pass

                # 6c. Consulta objetos de Áreas e Portais vinculados via /load_objects.fcgi
                try:
                    load_url = f"{base_url}{ENDPOINT_LOAD_OBJECTS}?session={session}"
                    
                    # Carrega as áreas cadastradas
                    resp_areas = await client.post(load_url, json={"object": "areas"}, timeout=timeout_sec)
                    if resp_areas.status_code == 200:
                        areas_json = resp_areas.json()
                        if isinstance(areas_json, dict) and "areas" in areas_json:
                            area_list = areas_json.get("areas", [])
                            names = [a.get("name") for a in area_list if isinstance(a, dict) and a.get("name")]
                            if names and device_data is not None:
                                device_data["_area_names"] = names
                                device_data["_raw_areas"] = area_list

                    # Carrega os portais vinculados com detalhes
                    resp_portals = await client.post(load_url, json={"object": "portals"}, timeout=timeout_sec)
                    if resp_portals.status_code == 200:
                        portals_json = resp_portals.json()
                        if isinstance(portals_json, dict) and "portals" in portals_json:
                            portal_list = portals_json.get("portals", [])
                            p_names = [p.get("name") for p in portal_list if isinstance(p, dict) and p.get("name")]
                            if p_names and device_data is not None:
                                device_data["_portal_names"] = p_names
                                device_data["_raw_portals"] = portal_list

                    # Carrega os dispositivos/terminais associados (devices)
                    try:
                        resp_devices = await client.post(load_url, json={"object": "devices"}, timeout=timeout_sec)
                        if resp_devices.status_code == 200:
                            devs_json = resp_devices.json()
                            if isinstance(devs_json, dict) and "devices" in devs_json and device_data is not None:
                                device_data["_raw_devices"] = devs_json.get("devices", [])
                    except Exception:
                        pass
                except Exception:
                    pass

                # 6d. Verificação de endpoint específico de catraca (/get_catra_info.fcgi)
                try:
                    catra_url = f"{base_url}{ENDPOINT_CATRA_INFO}?session={session}"
                    resp_catra = await client.get(catra_url, timeout=timeout_sec)
                    if resp_catra.status_code == 200:
                        catra_info = resp_catra.json()
                        if isinstance(catra_info, dict) and any(k in catra_info for k in ("total_turns", "entrance_turns", "exit_turns", "left_turns", "right_turns")):
                            if device_data is not None:
                                device_data["_is_catra"] = True
                except Exception:
                    pass

                # 6e. Consulta página inicial autenticada (dashboard do dispositivo)
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
    area = _extract_area_info(device_data or {})

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
        area=area,
        response_time_ms=elapsed_ms,
        raw_info=device_data or {}
    )
