import ipaddress
import socket
from typing import Tuple, List, Optional


def get_local_ip() -> str:
    """
    Identifica o endereço IP local ativo da máquina consultando
    a tabela de rotas do sistema operacional sem tráfego externo.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não estabelece conexão real na rede, apenas resolve a rota na interface ativa
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = "127.0.0.1"
    finally:
        s.close()
    return local_ip


def get_local_network_info() -> Tuple[str, str]:
    """
    Retorna uma tupla (ip_local, subnet_cidr_24).
    Exemplo: ('192.168.0.9', '192.168.0.0/24').
    """
    ip = get_local_ip()
    if ip and ip != "127.0.0.1":
        try:
            # Assume máscara /24 padrão da rede classe C/LAN
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            return ip, str(net)
        except Exception:
            pass
    return ip, "192.168.0.0/24"


def validate_cidr(cidr_str: str) -> bool:
    """Valida se uma string é um bloco CIDR IPv4 válido."""
    if not cidr_str or not isinstance(cidr_str, str):
        return False
    try:
        ipaddress.ip_network(cidr_str.strip(), strict=False)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def get_hosts_in_cidr(cidr_str: str) -> List[str]:
    """
    Retorna a lista de endereços IP utilizáveis (hosts) de um bloco CIDR.
    Para uma rede /24, retorna os 254 IPs úteis (ex: .1 a .254).
    """
    net = ipaddress.ip_network(cidr_str.strip(), strict=False)
    # hosts() exclui o network address e o broadcast address
    return [str(ip) for ip in net.hosts()]
