import asyncio
import time
from typing import Optional
import flet as ft

from backend.models.device import ScanSummary, ControlIdDevice, DocumentMetadata
from backend.core.network_utils import get_local_network_info, validate_cidr
from backend.core.scanner import NetworkScanner
from backend.services.report_service import export_to_csv, export_to_json, open_reports_folder
from backend.services.document_service import generate_internal_document_pdf
from frontend.components.header import create_header
from frontend.components.controls import ControlsBar
from frontend.components.kpi_cards import KPICards
from frontend.components.device_table import DeviceTable
from frontend.components.client_form import ClientForm
from frontend.styles.theme import (
    COLOR_BG_DARK,
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_TEXT_MUTED,
    get_model_color
)


class AppState:
    """Mantém o estado central da aplicação SCAN BOT Rede."""
    def __init__(self):
        # Puxa as informações da rede local ativa na inicialização
        self.local_ip, self.default_cidr = get_local_network_info()
        self.scanner: Optional[NetworkScanner] = None
        self.latest_summary: Optional[ScanSummary] = None
        self.is_scanning: bool = False
        self.start_time: float = 0.0


def create_app_view(page: ft.Page) -> ft.Control:
    """Constrói a visualização principal e gerencia o fluxo de eventos."""
    state = AppState()

    def show_message(text: str, is_error: bool = False):
        snack = ft.SnackBar(
            content=ft.Text(text, color="#FFFFFF", size=13),
            bgcolor=COLOR_DANGER if is_error else "#065F46",
            duration=3500
        )
        snack.open = True
        page.overlay.append(snack)
        page.update()

    # 1. Header com Branding SCAN BOT Rede
    header = create_header(state.local_ip, state.default_cidr)

    # 2. Tabela de Dispositivos
    device_table = DeviceTable()

    # 3. KPI Cards
    kpi_cards = KPICards()

    # 4. Seção de Barra de Progresso e Status
    progress_bar = ft.ProgressBar(
        value=0.0,
        bgcolor=COLOR_SURFACE,
        color=COLOR_PRIMARY,
        height=6,
        border_radius=3,
        visible=False
    )

    status_text = ft.Text(
        f"Pronto. Informações da rede puxadas ({state.default_cidr}). Clique em 'Iniciar Varredura' para começar.",
        size=12,
        color=COLOR_TEXT_MUTED
    )

    progress_section = ft.Container(
        content=ft.Column(
            spacing=6,
            controls=[
                progress_bar,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        status_text,
                    ]
                )
            ]
        ),
        padding=ft.Padding.symmetric(horizontal=4)
    )

    # 5. Botões do Rodapé de Ações
    btn_export_csv = ft.OutlinedButton(
        "Exportar CSV",
        icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
        disabled=True,
        height=40
    )

    btn_export_json = ft.OutlinedButton(
        "Exportar JSON",
        icon=ft.Icons.CODE_ROUNDED,
        disabled=True,
        height=40
    )

    btn_open_folder = ft.OutlinedButton(
        "Abrir Pasta de Relatórios",
        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
        height=40
    )

    footer = ft.Container(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        btn_export_csv,
                        btn_export_json,
                        btn_open_folder,
                    ]
                ),
                ft.Text(
                    "SCAN BOT Rede v1.0 • Pronto para Auditoria",
                    size=11,
                    color=COLOR_TEXT_MUTED
                )
            ]
        ),
        padding=ft.Padding.only(top=10, bottom=4)
    )

    # 6. Assinatura do desenvolvedor
    signature = ft.Container(
        content=ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Divider(height=1, color=COLOR_BORDER),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Icon(ft.Icons.CODE_ROUNDED, size=14, color=COLOR_TEXT_MUTED),
                        ft.Text("Desenvolvido por -", size=11, color=COLOR_TEXT_MUTED),
                        ft.Text(
                            "Leonardo Nascimento",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=COLOR_PRIMARY
                        ),
                    ]
                ),
            ]
        ),
        padding=ft.Padding.only(top=4, bottom=2)
    )

    # Callbacks de Ação
    def on_pull_network():
        ip, cidr = get_local_network_info()
        state.local_ip = ip
        state.default_cidr = cidr
        controls_bar.update_pulled_network(ip, cidr)
        header.update_network_info(ip, cidr)
        status_text.value = f"Informações atualizadas: {cidr} (IP: {ip}). Clique em 'Iniciar Varredura' para começar."
        status_text.update()
        show_message(f"Informações da rede puxadas com sucesso: {cidr} (IP: {ip}).")

    async def run_scan_async():
        cidr = controls_bar.subnet_input.value.strip() if controls_bar.subnet_input.value else ""
        if not cidr:
            show_message("Por favor, informe a sub-rede ou clique em 'Puxar da Rede' antes de iniciar.", is_error=True)
            controls_bar.set_scanning_state(False)
            state.is_scanning = False
            return

        if not validate_cidr(cidr):
            show_message(f"Formato de CIDR inválido: '{cidr}'. Use o padrão ex: 192.168.0.0/24", is_error=True)
            controls_bar.set_scanning_state(False)
            state.is_scanning = False
            return

        state.is_scanning = True
        controls_bar.set_scanning_state(True)
        device_table.clear()
        device_table.set_empty_state_text("Varrendo a rede em busca de equipamentos...")
        kpi_cards.reset()

        progress_bar.value = 0.0
        progress_bar.visible = True
        progress_bar.update()

        status_text.value = f"Iniciando varredura em {cidr} com 50 workers assíncronos..."
        status_text.update()

        btn_export_csv.disabled = True
        btn_export_json.disabled = True
        btn_export_csv.update()
        btn_export_json.update()

        state.start_time = time.perf_counter()

        def on_progress(scanned: int, total: int, current_ip: str):
            elapsed = time.perf_counter() - state.start_time
            progress_bar.value = scanned / total if total > 0 else 0.0
            status_text.value = f"Verificando host: {current_ip} ({scanned} de {total} IPs)..."
            kpi_cards.update_metrics(len(device_table.devices), scanned, total, elapsed)
            progress_bar.update()
            status_text.update()

        def on_device_found(dev: ControlIdDevice):
            device_table.add_device(dev)
            elapsed = time.perf_counter() - state.start_time
            kpi_cards.txt_total_found.value = str(len(device_table.devices))
            kpi_cards.txt_total_found.update()

        auth_user = controls_bar.input_username.value.strip() if controls_bar.input_username.value else "admin"
        auth_pass = controls_bar.input_password.value.strip() if controls_bar.input_password.value else "admin"

        state.scanner = NetworkScanner(
            cidr=cidr,
            concurrency=50,
            port=80,
            timeout_sec=1.5,
            username=auth_user,
            password=auth_pass,
            on_progress=on_progress,
            on_device_found=on_device_found
        )

        try:
            summary = await state.scanner.scan()
            state.latest_summary = summary
            total_found = len(summary.devices)
            progress_bar.value = 1.0
            progress_bar.update()

            if total_found > 0:
                status_text.value = f"Varredura concluída! {total_found} equipamento(s) catalogado(s) em {summary.duration_seconds:.1f}s."
                show_message(f"Varredura concluída com sucesso! {total_found} equipamento(s) encontrado(s).")
                btn_export_csv.disabled = False
                btn_export_json.disabled = False
                btn_export_csv.update()
                btn_export_json.update()
            else:
                status_text.value = f"Varredura concluída em {summary.duration_seconds:.1f}s. Nenhum equipamento encontrado."
                device_table.set_empty_state_text(
                    "Nenhum equipamento foi encontrado nesta sub-rede.\n"
                    "Verifique se os dispositivos estão ligados e com acesso na rede."
                )
                show_message("Nenhum equipamento encontrado na sub-rede informada.")

        except Exception as ex:
            status_text.value = f"Erro durante a execução: {str(ex)}"
            show_message(f"Erro na varredura: {str(ex)}", is_error=True)

        finally:
            state.is_scanning = False
            controls_bar.set_scanning_state(False)
            status_text.update()

    def on_start_scan():
        page.run_task(run_scan_async)

    def on_cancel_scan():
        if state.scanner and state.is_scanning:
            state.scanner.cancel()
            status_text.value = "Interrompendo varredura solicitada pelo usuário..."
            status_text.update()
            show_message("Varredura cancelada pelo usuário.")

    def on_export_csv(_):
        if state.latest_summary and state.latest_summary.devices:
            path = export_to_csv(state.latest_summary)
            show_message(f"Relatório CSV gravado com sucesso em: {path}")
        else:
            show_message("Nenhum dado disponível para exportação.", is_error=True)

    def on_export_json(_):
        if state.latest_summary and state.latest_summary.devices:
            path = export_to_json(state.latest_summary)
            show_message(f"Relatório JSON gravado com sucesso em: {path}")
        else:
            show_message("Nenhum dado disponível para exportação.", is_error=True)

    def on_open_folder(_):
        opened = open_reports_folder()
        if opened:
            show_message("Pasta de relatórios aberta no Windows Explorer.")
        else:
            show_message("Não foi possível abrir a pasta de relatórios automaticamente.", is_error=True)

    # Callback para geração do documento com confirmação prévia
    def on_request_generate_document():
        valid, err_msg = client_form.validate()
        if not valid:
            show_message(err_msg, is_error=True)
            return

        if not device_table.devices:
            show_message("Nenhum equipamento foi detectado na tabela. Execute a varredura primeiro.", is_error=True)
            return

        metadata = client_form.get_metadata()
        total_devices = len(device_table.devices)
        idfaces_count = sum(1 for d in device_table.devices if "face" in d.model.lower())

        def close_dialog(_=None):
            page.pop_dialog()

        def confirm_and_generate(_=None):
            page.pop_dialog()
            try:
                summary = state.latest_summary or ScanSummary(
                    network_target=state.default_cidr,
                    total_scanned=len(device_table.devices),
                    total_found=len(device_table.devices),
                    duration_seconds=time.perf_counter() - state.start_time if state.start_time else 0.0,
                    devices=device_table.devices
                )
                pdf_path = generate_internal_document_pdf(summary, metadata)
                show_message(f"Documento Interno PDF gerado com sucesso: {pdf_path}")
                open_reports_folder()
            except Exception as ex:
                show_message(f"Erro ao gerar documento PDF: {str(ex)}", is_error=True)

        # Monta a lista detalhada de equipamentos para conferência no modal
        device_items = []
        for idx, dev in enumerate(device_table.devices, start=1):
            badge_color = get_model_color(dev.model)
            device_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(f"#{idx}", size=11, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED),
                            width=28,
                        ),
                        ft.Column([
                            ft.Row([
                                ft.Text(dev.ip, size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                ft.Container(
                                    content=ft.Text(dev.model, size=10, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                    bgcolor=badge_color,
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4,
                                ),
                            ], spacing=8),
                            ft.Row([
                                ft.Text(f"S/N: {dev.serial_number}", size=11, color=COLOR_TEXT_MUTED),
                                ft.Text(f"MAC: {dev.mac}", size=11, color=COLOR_TEXT_MUTED),
                                ft.Text(f"Latência: {dev.response_time_ms:.1f}ms", size=11, color=COLOR_TEXT_MUTED),
                            ], spacing=10),
                        ], spacing=2, expand=True),
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=COLOR_SURFACE,
                    border=ft.Border.all(1, COLOR_BORDER),
                    border_radius=6,
                    padding=ft.Padding.all(8)
                )
            )

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.VERIFIED_OUTLINED, color=COLOR_PRIMARY, size=22),
                ft.Text("Confirmar Emissão de Documento Interno", size=15, weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Verifique os dados abaixo antes de gerar o documento para uso interno:", size=12, color=COLOR_TEXT_MUTED),
                        ft.Divider(height=10, color=COLOR_BORDER),
                        ft.Text(f"• Cliente: {metadata.cliente}", size=12, weight=ft.FontWeight.W_600),
                        ft.Text(f"• Endereço: {metadata.endereco_completo}", size=12),
                        ft.Text(f"• Técnico Responsável: {metadata.tecnico}", size=12),
                        ft.Text(f"• Local dos Equipamentos: {metadata.local_equipamento}", size=12),
                        ft.Divider(height=10, color=COLOR_BORDER),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DEVICE_HUB_ROUNDED, color=COLOR_SUCCESS, size=18),
                                ft.Text(
                                    f"Total de Ativos: {total_devices} equipamento(s) ({idfaces_count} iDFace)",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_SUCCESS
                                )
                            ]),
                            bgcolor="#0F2D1F",
                            padding=8,
                            border_radius=6
                        ),
                        ft.Divider(height=10, color=COLOR_BORDER),
                        ft.Row([
                            ft.Icon(ft.Icons.LIST_ALT_ROUNDED, size=16, color=COLOR_PRIMARY),
                            ft.Text(f"Equipamentos no Documento ({total_devices}):", size=12, weight=ft.FontWeight.BOLD),
                        ], spacing=6),
                        *device_items,
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    spacing=6
                ),
                width=560,
                height=400,
            ),
            actions=[
                ft.TextButton("Voltar / Editar", on_click=close_dialog),
                ft.FilledButton(
                    "Confirmar e Gerar PDF",
                    bgcolor=COLOR_SUCCESS,
                    color="#FFFFFF",
                    on_click=confirm_and_generate
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        page.show_dialog(confirm_dialog)

    # Instancia o formulário manual de dados do cliente/cabeçalho
    client_form = ClientForm(on_generate_document=on_request_generate_document)

    btn_export_csv.on_click = on_export_csv
    btn_export_json.on_click = on_export_json
    btn_open_folder.on_click = on_open_folder

    # Instancia a barra de controles com as informações puxadas da rede e opção de escrita manual
    controls_bar = ControlsBar(
        default_cidr=state.default_cidr,
        local_ip=state.local_ip,
        on_start_scan=on_start_scan,
        on_cancel_scan=on_cancel_scan,
        on_pull_network=on_pull_network
    )

    # Layout Principal com rolagem suave
    return ft.Container(
        content=ft.Column(
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                header,
                controls_bar,
                kpi_cards,
                client_form,
                progress_section,
                device_table,
                footer,
                signature
            ]
        ),
        bgcolor=COLOR_BG_DARK,
        padding=18,
        expand=True
    )
