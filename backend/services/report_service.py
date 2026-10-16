import csv
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.models.device import ScanSummary

from backend.services.turnstile_linker import link_turnstiles_and_readers

# Diretório padrão para salvar os relatórios
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def get_reports_dir() -> Path:
    """Garante a existência do diretório de relatórios e o retorna."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def generate_filename(prefix: str, extension: str) -> str:
    """Gera um nome de arquivo padronizado com timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def export_to_csv(summary: ScanSummary, file_path: Optional[str] = None) -> str:
    """
    Exporta o resultado da varredura para um arquivo CSV estruturado.
    Utiliza encoding 'utf-8-sig' para compatibilidade perfeita com o Microsoft Excel.
    Preserva o agrupamento de catracas e leitores faciais vinculados.
    """
    reports_dir = get_reports_dir()
    if not file_path:
        filename = generate_filename("relatorio_scan_bot", "csv")
        target_path = reports_dir / filename
    else:
        target_path = Path(file_path)

    grouped = link_turnstiles_and_readers(summary.devices)

    with open(target_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")

        # Cabeçalho Informativo de Resumo
        writer.writerow(["# RELATORIO DE VARREDURA - SCAN BOT REDE"])
        writer.writerow(["# Data da Varredura", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
        writer.writerow(["# Rede Alvo", summary.network_target])
        writer.writerow(["# Total de IPs Varridos", summary.total_scanned])
        writer.writerow(["# Total de Dispositivos Encontrados", summary.total_found])
        writer.writerow(["# Duracao da Varredura (s)", f"{summary.duration_seconds:.2f}"])
        writer.writerow([])  # Linha em branco separadora

        # Cabeçalho da Tabela
        writer.writerow([
            "IP Local",
            "Endereco MAC",
            "Numero de Serie",
            "Modelo",
            "Funcao / Vinculo",
            "Area / Local",
            "Versao Firmware",
            "Latencia (ms)",
            "Data/Hora Descoberta"
        ])

        # Linhas de Dispositivos agrupadas hierarquicamente
        for parent, children in grouped:
            parent_role = "Catraca Principal" if "idblock" in parent.model.lower() else "Dispositivo Standalone"
            writer.writerow([
                parent.ip,
                parent.mac,
                parent.serial_number,
                parent.model,
                parent_role,
                parent.area,
                parent.firmware_version,
                f"{parent.response_time_ms:.1f}",
                parent.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ])
            for child in children:
                child_role = (
                    f"Leitor Facial (Entrada) -> Catraca {parent.ip}" if child.role == "reader_entry" else (
                        f"Leitor Facial (Saída) -> Catraca {parent.ip}" if child.role == "reader_exit" else (
                            f"Leitor Facial Vinculado -> Catraca {parent.ip}"
                        )
                    )
                )
                writer.writerow([
                    f"  ↳ {child.ip}",
                    child.mac,
                    child.serial_number,
                    child.model,
                    child_role,
                    child.area,
                    child.firmware_version,
                    f"{child.response_time_ms:.1f}",
                    child.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ])

    return str(target_path.resolve())


def export_to_json(summary: ScanSummary, file_path: Optional[str] = None) -> str:
    """
    Exporta o resultado completo em formato JSON estruturado incluindo a hierarquia de catracas.
    Retorna o caminho absoluto do arquivo gravado.
    """
    reports_dir = get_reports_dir()
    if not file_path:
        filename = generate_filename("relatorio_scan_bot", "json")
        target_path = reports_dir / filename
    else:
        target_path = Path(file_path)

    # Executa a ligação para enriquecer os atributos dos dispositivos
    link_turnstiles_and_readers(summary.devices)

    with open(target_path, mode="w", encoding="utf-8") as json_file:
        json.dump(summary.to_dict(), json_file, indent=2, ensure_ascii=False)

    return str(target_path.resolve())


def open_reports_folder() -> bool:
    """Abre o explorador de arquivos diretamente no diretório de relatórios."""
    reports_dir = str(get_reports_dir().resolve())
    try:
        if sys.platform == "win32":
            os.startfile(reports_dir)
            return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", reports_dir])
            return True
        else:
            subprocess.Popen(["xdg-open", reports_dir])
            return True
    except Exception:
        return False
