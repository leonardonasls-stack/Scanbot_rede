from typing import List, Optional
import flet as ft

from backend.models.device import ControlIdDevice
from backend.services.turnstile_linker import link_turnstiles_and_readers
from frontend.styles.theme import (
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
    get_model_color
)


class DeviceTable(ft.Container):
    """Componente de visualização em tabela dos equipamentos detectados com suporte a hierarquia de catracas."""

    def __init__(self):
        self.devices: List[ControlIdDevice] = []

        # Tabela Flet
        self.table = ft.DataTable(
            heading_row_color="#121D2F",
            heading_row_height=42,
            data_row_min_height=46,
            data_row_max_height=52,
            divider_thickness=1,
            horizontal_margin=16,
            column_spacing=24,
            columns=[
                ft.DataColumn(ft.Text("EQUIPAMENTO / IP", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("ENDEREÇO MAC", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("NÚMERO DE SÉRIE", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("MODELO / FUNÇÃO", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("ÁREA / LOCAL", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("FIRMWARE", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
                ft.DataColumn(ft.Text("LATÊNCIA", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED)),
            ],
            rows=[]
        )

        # Placeholder de Estado Vazio
        self.empty_state_text = ft.Text(
            "Nenhuma varredura iniciada. Clique em 'Iniciar Varredura' para buscar equipamentos na rede.",
            size=13,
            color=COLOR_TEXT_MUTED,
            text_align=ft.TextAlign.CENTER
        )

        self.empty_state_container = ft.Container(
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Icon(
                        ft.Icons.SEARCH_ROUNDED,
                        size=48,
                        color="#334155"
                    ),
                    self.empty_state_text
                ]
            ),
            padding=40,
            alignment=ft.Alignment.CENTER
        )

        # Layout com rolagem vertical
        self.scroll_column = ft.Column(
            controls=[self.empty_state_container],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        )

        super().__init__(
            content=self.scroll_column,
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=0,
            expand=True
        )

    def _create_row(self, device: ControlIdDevice, is_child: bool = False, role_label: Optional[str] = None) -> ft.DataRow:
        model_color = get_model_color(device.model)

        # Badge estilizado para o Modelo
        is_turnstile = "idblock" in device.model.lower()
        badge_bg = "#F97316" if is_turnstile else model_color

        badge_controls = [
            ft.Container(
                content=ft.Text(
                    device.model,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color="#FFFFFF"
                ),
                bgcolor=badge_bg,
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                border_radius=6
            )
        ]

        if role_label:
            badge_controls.append(
                ft.Container(
                    content=ft.Text(
                        role_label,
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color="#0284C7"
                    ),
                    bgcolor="#082F49",
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4,
                    border=ft.Border.all(1, "#0369A1")
                )
            )

        model_badge = ft.Row(
            spacing=6,
            controls=badge_controls
        )

        # Célula de IP com destaque e recuo se for leitor filho de catraca
        if is_child:
            ip_content = ft.Row(
                spacing=6,
                controls=[
                    ft.Text("   ↳", size=13, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.BOLD),
                    ft.Icon(ft.Icons.FACE_ROUNDED, size=14, color="#38BDF8"),
                    ft.Text(
                        device.ip,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color="#38BDF8",
                        font_family="Consolas, monospace"
                    )
                ]
            )
            row_color = "#131E2E"
        else:
            is_turnstile = "idblock" in device.model.lower()
            icon_turnstile = ft.Icon(ft.Icons.SENSOR_DOOR_ROUNDED if not is_turnstile else ft.Icons.HLS_ROUNDED, size=16, color="#F97316" if is_turnstile else "#64748B")
            ip_content = ft.Row(
                spacing=8,
                controls=[
                    icon_turnstile,
                    ft.Text(
                        device.ip,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_TEXT_PRIMARY,
                        font_family="Consolas, monospace"
                    )
                ]
            )
            row_color = None

        # Célula de MAC
        mac_cell = ft.Text(
            device.mac,
            size=12,
            color=COLOR_TEXT_PRIMARY if device.mac != "N/D" else COLOR_TEXT_MUTED,
            font_family="Consolas, monospace"
        )

        # Célula de Serial
        serial_cell = ft.Text(
            device.serial_number,
            size=12,
            weight=ft.FontWeight.W_600,
            color="#38BDF8" if device.serial_number != "N/D" else COLOR_TEXT_MUTED,
            font_family="Consolas, monospace"
        )

        # Célula de Área / Local
        area_cell = ft.Text(
            device.area,
            size=12,
            weight=ft.FontWeight.W_500,
            color="#E2E8F0" if device.area != "N/D" else COLOR_TEXT_MUTED
        )

        # Célula de Firmware
        fw_cell = ft.Text(
            device.firmware_version,
            size=12,
            color=COLOR_TEXT_PRIMARY if device.firmware_version != "N/D" else COLOR_TEXT_MUTED
        )

        # Célula de Latência
        lat_cell = ft.Text(
            f"{device.response_time_ms:.1f} ms",
            size=12,
            color=COLOR_SUCCESS
        )

        return ft.DataRow(
            color=row_color,
            cells=[
                ft.DataCell(ip_content),
                ft.DataCell(mac_cell),
                ft.DataCell(serial_cell),
                ft.DataCell(model_badge),
                ft.DataCell(area_cell),
                ft.DataCell(fw_cell),
                ft.DataCell(lat_cell),
            ]
        )

    def add_device(self, device: ControlIdDevice):
        """Adiciona um equipamento descoberto em tempo real à lista interna e atualiza a exibição."""
        self.devices.append(device)
        self.rebuild_grouped_table()

    def rebuild_grouped_table(self):
        """Reconstrói as linhas da tabela agrupando leitores faciais sob suas catracas correspondentes."""
        self.table.rows.clear()
        grouped = link_turnstiles_and_readers(self.devices)

        for parent, children in grouped:
            # Linha da Catraca ou Dispositivo Principal
            self.table.rows.append(self._create_row(parent, is_child=False))

            # Linhas dos Leitores Vinculados
            for child in children:
                role_str = "Leitor Facial (Entrada)" if child.role == "reader_entry" else (
                    "Leitor Facial (Saída)" if child.role == "reader_exit" else "Leitor Facial Vinculado"
                )
                self.table.rows.append(self._create_row(child, is_child=True, role_label=role_str))

        if self.scroll_column.controls != [self.table]:
            self.scroll_column.controls = [self.table]

        self.update()

    def clear(self):
        """Limpa as linhas da tabela."""
        self.devices.clear()
        self.table.rows.clear()
        self.scroll_column.controls = [self.empty_state_container]
        self.update()

    def set_empty_state_text(self, message: str):
        """Atualiza a mensagem explicativa quando não há itens."""
        self.empty_state_text.value = message
        if self.scroll_column.controls != [self.empty_state_container]:
            self.scroll_column.controls = [self.empty_state_container]
        self.update()
