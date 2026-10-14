import flet as ft
from frontend.styles.theme import (
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_PRIMARY
)


class KPICards(ft.Container):
    """Grid horizontal de métricas em tempo real (Total Encontrados, IPs Varridos, Tempo)."""

    def __init__(self):
        # Card 1: Destaque de Equipamentos Encontrados
        self.txt_total_found = ft.Text(
            "0",
            size=30,
            weight=ft.FontWeight.BOLD,
            color=COLOR_SUCCESS
        )

        # Card 2: IPs Verificados
        self.txt_ips_scanned = ft.Text(
            "0 / 0",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT_PRIMARY
        )

        # Card 3: Tempo Decorrido
        self.txt_elapsed_time = ft.Text(
            "0.0s",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT_PRIMARY
        )

        card1 = self._build_card(
            title="EQUIPAMENTOS ENCONTRADOS",
            icon=ft.Icons.DEVICES_OTHER_ROUNDED,
            icon_color=COLOR_SUCCESS,
            value_control=self.txt_total_found,
            is_highlight=True
        )

        card2 = self._build_card(
            title="IPS VERIFICADOS",
            icon=ft.Icons.NETWORK_PING_ROUNDED,
            icon_color=COLOR_PRIMARY,
            value_control=self.txt_ips_scanned
        )

        card3 = self._build_card(
            title="TEMPO DECORRIDO",
            icon=ft.Icons.TIMER_OUTLINED,
            icon_color=COLOR_TEXT_MUTED,
            value_control=self.txt_elapsed_time
        )

        super().__init__(
            content=ft.Row(
                spacing=12,
                controls=[card1, card2, card3]
            )
        )

    def _build_card(
        self,
        title: str,
        icon: ft.Icons,
        icon_color: str,
        value_control: ft.Control,
        is_highlight: bool = False
    ) -> ft.Container:
        border_color = "#059669" if is_highlight else COLOR_BORDER
        bgcolor = "#0B2920" if is_highlight else COLOR_SURFACE

        return ft.Container(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                title,
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=COLOR_TEXT_MUTED
                            ),
                            value_control
                        ]
                    ),
                    ft.Container(
                        content=ft.Icon(icon, size=24, color=icon_color),
                        bgcolor="#121D2F",
                        padding=10,
                        border_radius=8
                    )
                ]
            ),
            bgcolor=bgcolor,
            border=ft.Border.all(1, border_color),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            expand=True
        )

    def update_metrics(
        self,
        total_found: int,
        scanned: int,
        total_hosts: int,
        elapsed_sec: float
    ):
        self.txt_total_found.value = str(total_found)
        self.txt_ips_scanned.value = f"{scanned} / {total_hosts}"
        self.txt_elapsed_time.value = f"{elapsed_sec:.1f}s"
        self.update()

    def reset(self, total_hosts: int = 0):
        self.txt_total_found.value = "0"
        self.txt_ips_scanned.value = f"0 / {total_hosts}"
        self.txt_elapsed_time.value = "0.0s"
        self.update()
