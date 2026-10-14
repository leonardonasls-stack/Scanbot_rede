import flet as ft
from frontend.styles.theme import (
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS
)


class HeaderBar(ft.Container):
    """Componente superior da aplicação com branding SCAN BOT Rede e status da interface."""

    def __init__(self, local_ip: str, default_cidr: str = ""):
        self.local_ip = local_ip
        self.default_cidr = default_cidr

        self.txt_ip = ft.Text(
            f"IP Local: {local_ip}",
            size=12,
            weight=ft.FontWeight.W_600,
            color=COLOR_TEXT_PRIMARY
        )

        self.txt_cidr = ft.Text(
            f"({default_cidr})" if default_cidr else "(Aguardando início)",
            size=11,
            color=COLOR_TEXT_MUTED
        )

        super().__init__(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # Lado Esquerdo: Identidade do Aplicativo
                    ft.Row(
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.ROUTER_ROUNDED,
                                    size=30,
                                    color=COLOR_PRIMARY
                                ),
                                bgcolor=COLOR_SURFACE,
                                border=ft.Border.all(1, COLOR_BORDER),
                                border_radius=10,
                                padding=10
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Text(
                                                "SCAN BOT",
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                                color=COLOR_TEXT_PRIMARY
                                            ),
                                            ft.Container(
                                                content=ft.Text(
                                                    "REDE",
                                                    size=10,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=COLOR_PRIMARY
                                                ),
                                                bgcolor="#1D2A4A",
                                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                border_radius=4,
                                                border=ft.Border.all(1, COLOR_PRIMARY)
                                            )
                                        ]
                                    ),
                                    ft.Text(
                                        "Inventário e auditoria de equipamentos Control ID",
                                        size=12,
                                        color=COLOR_TEXT_MUTED
                                    )
                                ]
                            )
                        ]
                    ),

                    # Lado Direito: Chip com Interface Ativa
                    ft.Container(
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.FIBER_MANUAL_RECORD,
                                    size=12,
                                    color=COLOR_SUCCESS
                                ),
                                self.txt_ip,
                                self.txt_cidr
                            ]
                        ),
                        bgcolor=COLOR_SURFACE,
                        border=ft.Border.all(1, COLOR_BORDER),
                        border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8)
                    )
                ]
            ),
            padding=ft.Padding.symmetric(horizontal=4, vertical=6)
        )

    def update_network_info(self, local_ip: str, cidr: str):
        """Atualiza dinamicamente as informações de IP e sub-rede no cabeçalho."""
        self.txt_ip.value = f"IP Local: {local_ip}"
        self.txt_cidr.value = f"({cidr})" if cidr else "(Aguardando início)"
        self.update()


def create_header(local_ip: str, default_cidr: str = "") -> HeaderBar:
    """Função factory para instanciar o cabeçalho."""
    return HeaderBar(local_ip, default_cidr)
