import asyncio
import time
from typing import Callable, Optional, List
import httpx

from backend.models.device import ControlIdDevice, ScanSummary
from backend.core.detector import probe_control_id
from backend.core.network_utils import get_hosts_in_cidr, validate_cidr


class NetworkScanner:
    """
    Orquestrador assíncrono de varredura de rede com controle
    de concorrência, suporte a credenciais de autenticação e emissão de callbacks.
    """

    def __init__(
        self,
        cidr: str,
        concurrency: int = 50,
        port: int = 80,
        timeout_sec: float = 1.5,
        username: str = "admin",
        password: str = "admin",
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_device_found: Optional[Callable[[ControlIdDevice], None]] = None,
    ):
        self.cidr = cidr.strip()
        self.concurrency = concurrency
        self.port = port
        self.timeout_sec = timeout_sec
        self.username = username
        self.password = password
        self.on_progress = on_progress
        self.on_device_found = on_device_found

        self._cancelled = False
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def cancel(self) -> None:
        """Sinaliza interrupção imediata da varredura."""
        self._cancelled = True

    async def scan(self) -> ScanSummary:
        """
        Executa a varredura completa da sub-rede especificada.
        Retorna o ScanSummary consolidado.
        """
        if not validate_cidr(self.cidr):
            raise ValueError(f"Formato de CIDR inválido: {self.cidr}")

        hosts = get_hosts_in_cidr(self.cidr)
        total_hosts = len(hosts)
        found_devices: List[ControlIdDevice] = []
        scanned_count = 0
        self._cancelled = False
        self._is_running = True

        semaphore = asyncio.Semaphore(self.concurrency)
        start_time = time.perf_counter()

        limits = httpx.Limits(
            max_connections=self.concurrency,
            max_keepalive_connections=self.concurrency
        )
        timeout = httpx.Timeout(self.timeout_sec, connect=self.timeout_sec)

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            async def scan_single_host(ip: str):
                nonlocal scanned_count
                if self._cancelled:
                    return

                async with semaphore:
                    if self._cancelled:
                        return
                    device = await probe_control_id(
                        client=client,
                        ip=ip,
                        port=self.port,
                        timeout_sec=self.timeout_sec,
                        username=self.username,
                        password=self.password
                    )

                    scanned_count += 1
                    if device:
                        found_devices.append(device)
                        if self.on_device_found:
                            try:
                                res = self.on_device_found(device)
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception:
                                pass

                    if self.on_progress:
                        try:
                            res = self.on_progress(scanned_count, total_hosts, ip)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception:
                            pass

            # Cria todas as tasks
            tasks = [asyncio.create_task(scan_single_host(ip)) for ip in hosts]

            try:
                # Executa concorrentemente respeitando o semáforo
                await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                self._is_running = False

        duration = time.perf_counter() - start_time

        return ScanSummary(
            network_target=self.cidr,
            total_scanned=scanned_count,
            total_found=len(found_devices),
            duration_seconds=duration,
            devices=found_devices
        )
