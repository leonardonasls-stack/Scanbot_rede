import sys
import os
import re
import socket
import struct
import subprocess
from typing import Optional


def _get_mac_windows_native(ip: str) -> Optional[str]:
    """Obtém o MAC via Windows API SendARP (iphlpapi.dll)."""
    try:
        import ctypes
        from ctypes import wintypes

        send_arp = ctypes.windll.iphlpapi.SendARP
        send_arp.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.ULONG)
        ]
        send_arp.restype = wintypes.DWORD

        # Converte IP para network byte order
        dest_ip = struct.unpack("<I", socket.inet_aton(ip))[0]
        mac_buffer = (ctypes.c_byte * 6)()
        mac_len = wintypes.ULONG(6)

        status = send_arp(dest_ip, 0, ctypes.byref(mac_buffer), ctypes.byref(mac_len))
        if status == 0 and mac_len.value == 6:
            mac_str = ":".join(f"{b & 0xFF:02X}" for b in mac_buffer)
            if mac_str != "00:00:00:00:00:00":
                return mac_str
    except Exception:
        pass
    return None


def _get_mac_arp_command(ip: str) -> Optional[str]:
    """Fallback: extrai o MAC executando o comando 'arp -a <ip>'."""
    try:
        cmd = ["arp", "-a", ip] if sys.platform == "win32" else ["arp", "-n", ip]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2).decode("latin-1", errors="ignore")
        # Procura por padrão de MAC address (ex: aa-bb-cc-dd-ee-ff ou aa:bb:cc:dd:ee:ff)
        match = re.search(r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", output)
        if match:
            mac_raw = match.group(0).upper().replace("-", ":")
            if mac_raw != "00:00:00:00:00:00":
                return mac_raw
    except Exception:
        pass
    return None


def _get_mac_linux_proc(ip: str) -> Optional[str]:
    """Fallback Linux: lê a tabela ARP em /proc/net/arp."""
    try:
        if os.path.exists("/proc/net/arp"):
            with open("/proc/net/arp", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip:
                        mac_cand = parts[3].upper()
                        if mac_cand != "00:00:00:00:00:00":
                            return mac_cand
    except Exception:
        pass
    return None


def get_mac_for_ip(ip: str) -> str:
    """
    Resolve o endereço MAC físico correspondente a um IP.
    Prioriza a chamada direta via Win32 SendARP; em seguida tenta a tabela ARP
    e retorna 'N/D' caso o host não responda à camada 2.
    """
    if not ip or ip in ("127.0.0.1", "localhost", "0.0.0.0"):
        return "N/D"

    # 1. No Windows, tenta primeiro via SendARP nativo (ultra rápido e preciso)
    if sys.platform == "win32":
        mac = _get_mac_windows_native(ip)
        if mac:
            return mac

    # 2. No Linux, tenta /proc/net/arp
    if sys.platform.startswith("linux"):
        mac = _get_mac_linux_proc(ip)
        if mac:
            return mac

    # 3. Fallback de linha de comando arp
    mac = _get_mac_arp_command(ip)
    if mac:
        return mac

    return "N/D"
