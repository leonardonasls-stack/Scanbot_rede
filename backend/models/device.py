from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class ControlIdDevice:
    """Representa um dispositivo Control iD descoberto na rede."""
    ip: str
    mac: str = "N/D"
    serial_number: str = "N/D"
    model: str = "Control iD (Genérico)"
    firmware_version: str = "N/D"
    area: str = "N/D"
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância para dicionário serializável."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ScanSummary:
    """Consolida as métricas e resultados de uma rodada de varredura."""
    network_target: str
    total_scanned: int = 0
    total_found: int = 0
    duration_seconds: float = 0.0
    devices: List[ControlIdDevice] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converte o sumário para dicionário serializável em JSON."""
        return {
            "network_target": self.network_target,
            "total_scanned": self.total_scanned,
            "total_found": self.total_found,
            "duration_seconds": round(self.duration_seconds, 2),
            "devices": [d.to_dict() for d in self.devices]
        }


@dataclass
class DocumentMetadata:
    """Metadados preenchidos manualmente pelo técnico para uso interno."""
    cliente: str = ""
    rua: str = ""
    numero: str = ""
    bairro: str = ""
    tecnico: str = ""
    local_equipamento: str = ""
    data_emissao: datetime = field(default_factory=datetime.now)

    @property
    def endereco_completo(self) -> str:
        partes = []
        if self.rua:
            partes.append(self.rua)
        if self.numero:
            partes.append(f"nº {self.numero}")
        if self.bairro:
            partes.append(f"Bairro {self.bairro}")
        return ", ".join(partes) if partes else "Não informado"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cliente": self.cliente,
            "rua": self.rua,
            "numero": self.numero,
            "bairro": self.bairro,
            "endereco_completo": self.endereco_completo,
            "tecnico": self.tecnico,
            "local_equipamento": self.local_equipamento,
            "data_emissao": self.data_emissao.strftime("%d/%m/%Y %H:%M:%S")
        }

