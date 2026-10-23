from typing import List, Dict, Tuple, Optional
import re
from backend.models.device import ControlIdDevice


def _extract_turnstile_portal_name(area_str: str) -> Optional[str]:
    """
    Extrai o nome do portal pertencente especificamente a uma catraca iDBlock.
    Exemplo:
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE ((Entrada) ENTRADA TRANSPORTE, (Saída) EXTERNA)'
      -> 'ENTRADA TRANSPORTE'
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE ((Entrada) ENTRADA PORTÃO, (Saída) EXTERNA)'
      -> 'ENTRADA PORTÃO'
    """
    if not area_str or area_str == "N/D":
        return None

    # Catracas possuem o padrão ((Entrada) <PORTAL>, (Saída) <AREA>)
    match = re.search(r"\(\(Entrada\)\s*([^,)]+)", area_str, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_reader_portal_name(area_str: str) -> Optional[str]:
    """
    Extrai o portal para onde o leitor facial aponta.
    Exemplos:
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE (Portal)'
      -> O portal do leitor é a última área antes de '(Portal)', ou seja, 'ENTRADA TRANSPORTE'
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE (TO: ENTRADA PORTÃO)'
      -> 'ENTRADA PORTÃO'
    """
    if not area_str or area_str == "N/D":
        return None

    # Caso TO: ou Portal: explícito
    match_to = re.search(r"\((?:TO:\s*|Portal:\s*)([^)]+)\)", area_str, re.IGNORECASE)
    if match_to:
        cand = match_to.group(1).strip()
        if cand.lower() not in ("portal", "n/d", ""):
            return cand

    # Caso '..., NOME_PORTAL (Portal)'
    match_portal = re.search(r",\s*([^,()]+)\s*\(Portal\)", area_str, re.IGNORECASE)
    if match_portal:
        return match_portal.group(1).strip()

    return None


def _is_adapted_turnstile(turnstile: ControlIdDevice) -> bool:
    """
    Identifica se a catraca é adaptada via contato seco/relé.
    Catracas adaptadas possuem número de série curto (geralmente 4 caracteres, ex: K1ZN, K209, K2Z5),
    enquanto catracas nativas possuem número de série longo (13 dígitos com '/', ex: 0K5210/000015).
    """
    sn = (turnstile.serial_number or "").strip()
    clean_sn = sn.replace("/", "").replace("-", "")
    return len(clean_sn) <= 6


def clean_display_area(device: ControlIdDevice) -> str:
    """
    Retorna uma representação limpa e objetiva da área/localização do equipamento,
    removendo áreas genéricas ou não vinculadas aos portais daquele dispositivo.
    Exemplos:
      - Catraca: 'Pátio' (ou 'Pátio / Estacionamento')
      - Leitor facial: 'Pátio'
    """
    raw_info = device.raw_info or {}
    raw_areas = raw_info.get("_raw_areas") or []
    raw_portals = raw_info.get("_raw_portals") or []

    # Cria mapa de area_id -> nome da área
    area_map = {}
    for a in raw_areas:
        if isinstance(a, dict) and a.get("id") is not None and a.get("name"):
            name = str(a.get("name")).strip()
            area_map[a.get("id")] = name

    # Identifica IDs de áreas referenciadas nos portais deste dispositivo
    relevant_area_names = []
    for p in raw_portals:
        if isinstance(p, dict):
            for key in ("area_to_id", "area_from_id"):
                aid = p.get(key)
                if aid in area_map:
                    aname = area_map[aid]
                    if aname.lower() != "área padrão" and aname not in relevant_area_names:
                        relevant_area_names.append(aname)

    if relevant_area_names:
        # Se for leitor facial subordinado, prioriza a primeira área relevante (área interna de destino)
        if "face" in device.model.lower() and len(relevant_area_names) >= 1:
            return relevant_area_names[0]
        return " / ".join(relevant_area_names[:2])

    # Fallback: se não tiver raw_portals, limpa a string existente
    area_str = device.area or ""
    if area_str and area_str != "N/D":
        m_to = re.search(r"\((?:TO:\s*|Portal:\s*)([^)]+)\)", area_str, re.IGNORECASE)
        if m_to:
            cand = m_to.group(1).strip()
            if cand.lower() not in ("portal", "n/d", "área padrão", "area padrao"):
                return cand

        cleaned = re.sub(r"(?i)^área\s+padr[ãa]o\s*,\s*", "", area_str)
        cleaned = re.sub(r"\s*\(\(.*?\)\)", "", cleaned)
        cleaned = re.sub(r"\s*\(TO:.*?\)", "", cleaned)
        cleaned = re.sub(r"\s*\(Portal\)", "", cleaned)
        cleaned = cleaned.strip(" ,;")
        if cleaned:
            parts = [p.strip() for p in cleaned.split(",") if p.strip() and p.strip().lower() != "área padrão"]
            if parts:
                return parts[-1] if "face" in device.model.lower() else " / ".join(parts[:2])

    return device.area or "N/D"


def _extract_base_device_name(name: str) -> str:
    """
    Extrai o nome base do equipamento removendo sufixos comuns de direção ou portal.
    Exemplos:
      'RECEPÇÃO Entrada' -> 'RECEPÇÃO'
      'FLORESTA 2 Entrada' -> 'FLORESTA 2'
      'CATRACA 2 Entrada' -> 'CATRACA 2'
      'CATRACA TRANSPORTE Saída' -> 'CATRACA TRANSPORTE'
    """
    if not name:
        return ""
    cleaned = re.sub(r"\s+(?:Entrada|Sa[ií]da|In|Out|Portal)\b.*$", "", name, flags=re.IGNORECASE)
    return cleaned.strip()


def link_turnstiles_and_readers(devices: List[ControlIdDevice]) -> List[Tuple[ControlIdDevice, List[ControlIdDevice]]]:
    """
    Analisa a lista de equipamentos detectados e agrupa os leitores faciais
    com suas respectivas catracas iDBlock com base em portal e áreas vinculadas.

    Retorna uma lista de tuplas:
      (equipamento_pai, [filhos_leitores])
    Para equipamentos independentes (leitores de portas avulsos ou sem catraca),
    o primeiro elemento é o próprio dispositivo e a lista de filhos é vazia.
    """
    turnstiles: List[ControlIdDevice] = []
    others: List[ControlIdDevice] = []

    for dev in devices:
        # É catraca se o modelo for iDBlock/catraca OU se possuir a assinatura de catraca: ((Entrada)... (Saída)...)
        has_catra_portal_sig = bool(re.search(r"\(\(Entrada\).*?\(Saída\)", dev.area or "", re.IGNORECASE))
        is_turnstile = (
            "idblock" in dev.model.lower() or
            "catraca" in dev.model.lower() or
            has_catra_portal_sig or
            dev.role == "turnstile"
        )
        if is_turnstile:
            if dev.model == "Control iD (Genérico)":
                dev.model = "iDBlock"
            dev.role = "turnstile"
            turnstiles.append(dev)
        else:
            others.append(dev)

    # Dicionário de portal -> catraca
    turnstile_by_portal: Dict[str, ControlIdDevice] = {}
    turnstile_children: Dict[str, List[ControlIdDevice]] = {t.ip: [] for t in turnstiles}

    for t in turnstiles:
        portal = _extract_turnstile_portal_name(t.area)
        if portal:
            turnstile_by_portal[portal.upper()] = t

    linked_others: set = set()

    def can_turnstile_accept_reader(turnstile: ControlIdDevice) -> bool:
        """
        Verifica se a catraca ainda tem capacidade física de aceitar leitores:
        - Catraca Adaptada (serial curto <= 6): máximo 1 leitor (adaptada com 1 único leitor físico).
        - Catraca Nativa (serial 13 dígitos): suporta até 2 leitores (Entrada e Saída).
        """
        current_count = len(turnstile_children.get(turnstile.ip, []))
        if _is_adapted_turnstile(turnstile):
            return current_count < 1
        return current_count < 2

    # Associa leitores à respectiva catraca
    for o in others:
        o_area_upper = (o.area or "").upper()
        matched_turnstile: Optional[ControlIdDevice] = None

        # 1. Prioridade Absoluta: Vínculo por NOME DE CADASTRO DO iDSECURE
        # No iDSecure, a catraca se chama ex: 'CATRACA TRANSPORTE' e os leitores se chamam 'CATRACA TRANSPORTE Entrada' / 'CATRACA TRANSPORTE Saída'
        # Ou a catraca se chama 'FLORESTA 2' e o leitor se chama 'FLORESTA 2 Entrada'
        # Ou a catraca se chama 'RECEPÇÃO' e o leitor se chama 'RECEPÇÃO Entrada'
        o_dev_name = ""
        o_raw_devs = o.raw_info.get("_raw_devices", []) if o.raw_info else []
        for rd in o_raw_devs:
            if isinstance(rd, dict) and rd.get("ip") == o.ip:
                o_dev_name = str(rd.get("name") or "").strip()
                break

        o_base_name = _extract_base_device_name(o_dev_name)

        if o_dev_name:
            for t in turnstiles:
                if not can_turnstile_accept_reader(t):
                    continue

                t_dev_name = ""
                t_raw_devs = t.raw_info.get("_raw_devices", []) if t.raw_info else []
                for rd in t_raw_devs:
                    if isinstance(rd, dict) and rd.get("ip") == t.ip:
                        t_dev_name = str(rd.get("name") or "").strip()
                        break

                if t_dev_name and len(t_dev_name) >= 2:
                    # Comparação exata de nome base (ex: 'FLORESTA 2 Entrada' base 'FLORESTA 2' == 'FLORESTA 2')
                    if o_base_name and o_base_name.upper() == t_dev_name.upper():
                        matched_turnstile = t
                        break

                    # Ou correspondência de prefixo se o nome do leitor iniciar com o nome da catraca
                    if o_dev_name.upper().startswith(t_dev_name.upper()):
                        matched_turnstile = t
                        break

        # 2. Prioridade por IP direto cadastrado no hardware (apenas catracas nativas)
        if not matched_turnstile:
            for t in turnstiles:
                if not can_turnstile_accept_reader(t):
                    continue
                t_raw_devs = t.raw_info.get("_raw_devices", []) if t.raw_info else []
                for rd in t_raw_devs:
                    if isinstance(rd, dict) and rd.get("ip") == o.ip:
                        matched_turnstile = t
                        break
                if matched_turnstile:
                    break

        # Confere também no sentido inverso: se o leitor possui a catraca listada nos seus devices
        if not matched_turnstile:
            for rd in o_raw_devs:
                if isinstance(rd, dict):
                    rd_ip = rd.get("ip")
                    for t in turnstiles:
                        if t.ip == rd_ip and can_turnstile_accept_reader(t):
                            matched_turnstile = t
                            break
                if matched_turnstile:
                    break

        # 3. Checa pelo portal extraído do leitor facial
        if not matched_turnstile:
            r_portal = _extract_reader_portal_name(o.area)
            if r_portal and r_portal.upper() in turnstile_by_portal:
                cand_turnstile = turnstile_by_portal[r_portal.upper()]
                # Para catracas adaptadas, só aceita se o nome base bater ou se for compatível
                if can_turnstile_accept_reader(cand_turnstile):
                    if not _is_adapted_turnstile(cand_turnstile):
                        matched_turnstile = cand_turnstile
                    else:
                        # Se adaptada, confere se o portal ou nome tem relação com a catraca
                        t_raw_devs = cand_turnstile.raw_info.get("_raw_devices", []) if cand_turnstile.raw_info else []
                        t_name = ""
                        for rd in t_raw_devs:
                            if isinstance(rd, dict) and rd.get("ip") == cand_turnstile.ip:
                                t_name = str(rd.get("name") or "").strip()
                                break
                        if not t_name or (o_base_name and (o_base_name.upper() in t_name.upper() or t_name.upper() in o_base_name.upper())):
                            matched_turnstile = cand_turnstile

        # 4. Fallback de portal: APENAS para catracas nativas (13 dígitos) com capacidade livre
        # Em catracas adaptadas, NÃO faz fallback genérico de substrings em lista de áreas
        # para evitar vincular leitores de catracas desligadas a outra catraca por coincidência de texto.
        if not matched_turnstile:
            for p_name, t in turnstile_by_portal.items():
                if _is_adapted_turnstile(t) or not can_turnstile_accept_reader(t):
                    continue
                if f"({p_name})" in o_area_upper or f"TO: {p_name}" in o_area_upper or f"{p_name} (PORTAL)" in o_area_upper:
                    matched_turnstile = t
                    break

        if matched_turnstile:
            o.parent_turnstile_ip = matched_turnstile.ip
            
            # Determina papel (Entrada / Saída) com precisão:
            # 1. Prioridade máxima: sufixo/palavra final do nome do leitor (ex: 'Entrada 1 Saída' -> 'Saída', 'Entrada 1 Entrada' -> 'Entrada')
            # 2. Correspondência por regex de fronteira (\b) no nome do leitor
            # 3. Análise da área / portal configurado no leitor
            role = "reader"
            dev_tokens = re.findall(r"[A-Za-zÀ-ÿ]+", o_dev_name)
            last_token = dev_tokens[-1].upper() if dev_tokens else ""

            if last_token in ("SAIDA", "SAÍDA", "OUT", "EXIT"):
                role = "reader_exit"
            elif last_token in ("ENTRADA", "IN"):
                role = "reader_entry"
            elif re.search(r"\b(?:sa[ií]da|out|exit)\b", o_dev_name, re.IGNORECASE):
                role = "reader_exit"
            elif re.search(r"\b(?:entrada|in)\b", o_dev_name, re.IGNORECASE):
                role = "reader_entry"
            elif re.search(r"\b(?:sa[ií]da|out|exit)\b", o_area_upper, re.IGNORECASE):
                role = "reader_exit"
            elif re.search(r"\b(?:entrada|in)\b", o_area_upper, re.IGNORECASE):
                role = "reader_entry"

            o.role = role
            turnstile_children[matched_turnstile.ip].append(o)
            linked_others.add(o.ip)
        else:
            o.role = "standalone"

    # Se a catraca possuir leitores faciais acoplados/vinculados, seu modelo é "iDBlock Facial"
    # Preserva ou adiciona a especificidade de PNE se aplicável
    for t in turnstiles:
        has_face_readers = any("face" in child.model.lower() for child in turnstile_children.get(t.ip, []))
        is_pne = (
            "pne" in t.model.lower() or
            (t.serial_number or "").startswith("0K1400") or
            re.search(r"\bpne\b", t.area or "", re.IGNORECASE) or
            any(
                re.search(r"\bpne\b", str(d.get("name") or ""), re.IGNORECASE)
                for d in ((t.raw_info or {}).get("_raw_devices") or [])
                if isinstance(d, dict)
            )
        )
        if is_pne:
            t.model = "iDBlock Facial PNE" if has_face_readers else "iDBlock PNE"
        elif has_face_readers:
            t.model = "iDBlock Facial"

    # Monta a estrutura final
    result: List[Tuple[ControlIdDevice, List[ControlIdDevice]]] = []

    for t in turnstiles:
        children = turnstile_children.get(t.ip, [])
        result.append((t, children))

    for o in others:
        if o.ip not in linked_others:
            result.append((o, []))

    return result
