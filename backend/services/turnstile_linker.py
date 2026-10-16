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

    # Associa leitores à respectiva catraca
    for o in others:
        o_area_upper = (o.area or "").upper()
        matched_turnstile: Optional[ControlIdDevice] = None

        # 1. Prioridade Absoluta: Vínculo por NOME DE CADASTRO DO iDSECURE
        # No iDSecure, a catraca se chama ex: 'CATRACA TRANSPORTE' e os leitores se chamam 'CATRACA TRANSPORTE Entrada' / 'CATRACA TRANSPORTE Saída'
        # Ou a catraca se chama 'ENTRADA 2' e os leitores se chamam 'ENTRADA 2 Entrada' / 'ENTRADA 2 Saída'
        # Ou a catraca se chama 'ENTRADA 1' e o leitor se chama 'ENTRADA 1 Saída'
        o_dev_name = ""
        o_raw_devs = o.raw_info.get("_raw_devices", []) if o.raw_info else []
        for rd in o_raw_devs:
            if isinstance(rd, dict) and rd.get("ip") == o.ip:
                o_dev_name = str(rd.get("name") or "").strip()
                break

        if o_dev_name:
            for t in turnstiles:
                t_dev_name = ""
                t_raw_devs = t.raw_info.get("_raw_devices", []) if t.raw_info else []
                for rd in t_raw_devs:
                    if isinstance(rd, dict) and rd.get("ip") == t.ip:
                        t_dev_name = str(rd.get("name") or "").strip()
                        break
                
                if t_dev_name and len(t_dev_name) >= 3:
                    # Ex: 'CATRACA TRANSPORTE Entrada' começa com 'CATRACA TRANSPORTE'
                    if o_dev_name.upper().startswith(t_dev_name.upper()):
                        matched_turnstile = t
                        break

        # 2. Prioridade por IP direto cadastrado no hardware
        if not matched_turnstile:
            for t in turnstiles:
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
                        if t.ip == rd_ip:
                            matched_turnstile = t
                            break
                if matched_turnstile:
                    break

        # 3. Checa pelo portal extraído do leitor facial
        if not matched_turnstile:
            r_portal = _extract_reader_portal_name(o.area)
            if r_portal and r_portal.upper() in turnstile_by_portal:
                matched_turnstile = turnstile_by_portal[r_portal.upper()]

        # 4. Se não casou via regex específico, confere se o portal da catraca é o foco do leitor
        if not matched_turnstile:
            for p_name, t in turnstile_by_portal.items():
                if f"({p_name})" in o_area_upper or f"TO: {p_name}" in o_area_upper or f"{p_name} (PORTAL)" in o_area_upper:
                    matched_turnstile = t
                    break

        if matched_turnstile:
            o.parent_turnstile_ip = matched_turnstile.ip
            # Define papel com base no nome do leitor (ex: 'Entrada' ou 'Saída') ou na área
            check_name = (o_dev_name + " " + o_area_upper).upper()
            if any(w in check_name for w in ("ENTRADA", "IN")):
                o.role = "reader_entry"
            elif any(w in check_name for w in ("SAÍDA", "SAIDA", "OUT", "EXIT")):
                o.role = "reader_exit"
            else:
                o.role = "reader"
            turnstile_children[matched_turnstile.ip].append(o)
            linked_others.add(o.ip)
        else:
            o.role = "standalone"

    # Se a catraca possuir leitores faciais acoplados/vinculados, seu modelo é "iDBlock Facial"
    for t in turnstiles:
        has_face_readers = any("face" in child.model.lower() for child in turnstile_children.get(t.ip, []))
        if has_face_readers:
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
