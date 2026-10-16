from typing import List, Dict, Tuple, Optional
import re
from backend.models.device import ControlIdDevice


def _extract_canonical_portal_name(area_str: str) -> Optional[str]:
    """
    Extrai o nome canônico do portal a partir da string de área/local do equipamento.
    Exemplos:
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE ((Entrada) ENTRADA TRANSPORTE, (Saída) EXTERNA)'
      -> 'ENTRADA TRANSPORTE'
      'Área Padrão, EXTERNA, ENTRADA PORTÃO, ENTRADA TRANSPORTE (Portal)'
      -> busca termos como 'ENTRADA TRANSPORTE' ou 'ENTRADA PORTÃO'
    """
    if not area_str or area_str == "N/D":
        return None

    # 1. Procura padrão explícito de portal de catraca: ((Entrada) PORTAL, (Saída) AREA)
    match_turnstile = re.search(r"\(\(Entrada\)\s*([^,)]+)", area_str, re.IGNORECASE)
    if match_turnstile:
        return match_turnstile.group(1).strip()

    # 2. Procura padrão de TO: PORTAL ou Portal: PORTAL
    match_portal = re.search(r"\((?:TO:\s*|Portal:\s*|Portal)?\s*([^,()]+)\)", area_str, re.IGNORECASE)
    if match_portal:
        cand = match_portal.group(1).strip()
        if cand.lower() not in ("portal", "n/d", ""):
            return cand

    # 3. Termos comuns de portais
    for token in area_str.split(","):
        cleaned = re.sub(r"\(.*?\)", "", token).strip()
        if any(w in cleaned.upper() for w in ("PORTÃO", "PORTAO", "TRANSPORTE", "CATRACA", "ENTRADA", "SAÍDA", "SAIDA", "RECEPCAO", "RECEPÇÃO")):
            return cleaned

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
        is_turnstile = (
            "idblock" in dev.model.lower() or
            "catraca" in dev.model.lower() or
            dev.role == "turnstile"
        )
        if is_turnstile:
            dev.role = "turnstile"
            turnstiles.append(dev)
        else:
            others.append(dev)

    # Dicionário de portal -> catraca
    turnstile_by_portal: Dict[str, ControlIdDevice] = {}
    turnstile_children: Dict[str, List[ControlIdDevice]] = {t.ip: [] for t in turnstiles}

    for t in turnstiles:
        portal = _extract_canonical_portal_name(t.area)
        if portal:
            turnstile_by_portal[portal.upper()] = t

    linked_others: set = set()

    # Associa leitores à respectiva catraca
    for o in others:
        o_area_upper = (o.area or "").upper()
        matched_turnstile: Optional[ControlIdDevice] = None

        # 1. Checa por correspondência exata do portal canônico
        o_portal = _extract_canonical_portal_name(o.area)
        if o_portal and o_portal.upper() in turnstile_by_portal:
            matched_turnstile = turnstile_by_portal[o_portal.upper()]

        # 2. Checa se o nome do portal da catraca está contido na área do leitor
        if not matched_turnstile:
            for p_name, t in turnstile_by_portal.items():
                if len(p_name) >= 4 and p_name in o_area_upper:
                    matched_turnstile = t
                    break

        if matched_turnstile:
            o.parent_turnstile_ip = matched_turnstile.ip
            if any(w in o_area_upper for w in ("ENTRADA", "IN", "ENTR")):
                o.role = "reader_entry"
            elif any(w in o_area_upper for w in ("SAIDA", "SAÍDA", "OUT", "EXIT")):
                o.role = "reader_exit"
            else:
                o.role = "reader"
            turnstile_children[matched_turnstile.ip].append(o)
            linked_others.add(o.ip)
        else:
            o.role = "standalone"

    # Monta a estrutura final
    result: List[Tuple[ControlIdDevice, List[ControlIdDevice]]] = []

    for t in turnstiles:
        children = turnstile_children.get(t.ip, [])
        result.append((t, children))

    for o in others:
        if o.ip not in linked_others:
            result.append((o, []))

    return result
