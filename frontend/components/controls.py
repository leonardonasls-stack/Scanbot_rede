from typing import Callable, Optional
import flet as ft

from frontend.styles.theme import (
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_DANGER,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS
)


class ControlsBar(ft.Container):
    """
    Barra de controles com suporte a extração automática das informações da rede,
    campos de autenticação de usuário e senha (padrão admin/admin para extração do serial)
    e alternador explícito para permitir escrita/edição manual de blocos CIDR.
    """

    def __init__(
        self,
        default_cidr: str = "",
        local_ip: str = "",
        on_start_scan: Callable[[], None] = None,
        on_cancel_scan: Callable[[], None] = None,
        on_pull_network: Callable[[], None] = None
    ):
        self.on_start_scan_cb = on_start_scan
        self.on_cancel_scan_cb = on_cancel_scan
        self.on_pull_network_cb = on_pull_network
        self.is_scanning = False
        self.local_ip = local_ip
        self.auto_detected_cidr = default_cidr

        # Campo de entrada de rede (inicia com as informações puxadas da rede)
        self.subnet_input = ft.TextField(
            value=default_cidr,
            label="Faixa de Rede / CIDR",
            hint_text="Ex: 192.168.0.0/24 ou 10.0.0.0/24",
            prefix_icon=ft.Icons.ROUTER_ROUNDED,
            text_size=14,
            read_only=True,  # Por padrão travado no modo puxado da rede
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            expand=True
        )

        # Campo de Usuário para autenticação Control iD
        self.input_username = ft.TextField(
            value="admin",
            label="Usuário (Auth)",
            hint_text="admin",
            width=135,
            text_size=13,
            prefix_icon=ft.Icons.PERSON_OUTLINED,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8)
        )

        # Campo de Senha para autenticação Control iD
        self.input_password = ft.TextField(
            value="admin",
            label="Senha (Auth)",
            hint_text="admin",
            password=True,
            can_reveal_password=True,
            width=145,
            text_size=13,
            prefix_icon=ft.Icons.LOCK_OUTLINED,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8)
        )

        # Botão para puxar/atualizar as informações da rede local
        self.btn_pull_network = ft.OutlinedButton(
            "Puxar da Rede",
            icon=ft.Icons.AUTORENEW_ROUNDED,
            height=46,
            tooltip="Re-detectar a interface de rede ativa e recalcular a sub-rede",
            on_click=self._handle_pull_network_click
        )

        # Botão principal de início/cancelamento da varredura
        self.btn_scan = ft.FilledButton(
            "Iniciar Varredura",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            bgcolor=COLOR_PRIMARY,
            height=46,
            on_click=self._handle_scan_click
        )

        # Alternador (Switch) para permitir edição/digitação manual
        self.switch_allow_write = ft.Switch(
            label="Permitir escrever manualmente",
            value=False,
            active_color=COLOR_PRIMARY,
            on_change=self._handle_toggle_write_mode
        )

        # Tag/Badge indicando o modo corrente (AUTO ou MANUAL)
        self.mode_badge_text = ft.Text(
            "AUTO",
            size=10,
            weight=ft.FontWeight.BOLD,
            color="#38BDF8"
        )
        self.mode_badge = ft.Container(
            content=self.mode_badge_text,
            bgcolor="#0C2A4D",
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            border_radius=4,
            border=ft.Border.all(1, "#1E40AF")
        )

        # Legenda explicativa inferior
        self.helper_label = ft.Text(
            f"Informações puxadas automaticamente da rede ativa (IP: {local_ip}) • Auth: admin/admin" if local_ip else "Informações da rede carregadas.",
            size=11,
            color=COLOR_TEXT_MUTED
        )

        # Estrutura visual em duas linhas organizadas
        super().__init__(
            content=ft.Column(
                spacing=10,
                controls=[
                    # Linha 1: Input de Rede + Usuário + Senha + Botão Puxar + Botão Iniciar
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.subnet_input,
                            self.input_username,
                            self.input_password,
                            self.btn_pull_network,
                            self.btn_scan
                        ]
                    ),
                    # Linha 2: Opção "Permitir escrever manualmente" + Status/Helper
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    self.switch_allow_write,
                                    self.helper_label
                                ]
                            ),
                            self.mode_badge
                        ]
                    )
                ]
            ),
            bgcolor=COLOR_SURFACE,
            padding=14,
            border_radius=10,
            border=ft.Border.all(1, COLOR_BORDER)
        )

    def _handle_toggle_write_mode(self, e):
        """Alterna entre modo somente leitura (informações puxadas) e modo de escrita manual."""
        is_manual = self.switch_allow_write.value
        self.subnet_input.read_only = not is_manual

        if is_manual:
            self.mode_badge_text.value = "MANUAL"
            self.mode_badge_text.color = "#FBBF24"
            self.mode_badge.bgcolor = "#3D2C04"
            self.mode_badge.border = ft.Border.all(1, "#B45309")
            self.helper_label.value = "Modo manual ativado: você pode digitar ou alterar a faixa livremente (ex: 10.0.0.0/24)."
        else:
            self.mode_badge_text.value = "AUTO"
            self.mode_badge_text.color = "#38BDF8"
            self.mode_badge.bgcolor = "#0C2A4D"
            self.mode_badge.border = ft.Border.all(1, "#1E40AF")
            if self.auto_detected_cidr:
                self.subnet_input.value = self.auto_detected_cidr
            self.helper_label.value = f"Informações restauradas da rede ativa (IP: {self.local_ip}) • Auth: admin/admin."

        self.update()

    def _handle_pull_network_click(self, _):
        if self.on_pull_network_cb:
            self.on_pull_network_cb()

    def _handle_scan_click(self, _):
        if not self.is_scanning:
            if self.on_start_scan_cb:
                self.on_start_scan_cb()
        else:
            if self.on_cancel_scan_cb:
                self.on_cancel_scan_cb()

    def update_pulled_network(self, ip: str, cidr: str):
        """Atualiza os dados puxados da rede e reflete no input e labels."""
        self.local_ip = ip
        self.auto_detected_cidr = cidr
        self.subnet_input.value = cidr
        if not self.switch_allow_write.value:
            self.helper_label.value = f"Informações puxadas automaticamente da rede ativa (IP: {ip}) • Auth: admin/admin."
        self.update()

    def set_scanning_state(self, scanning: bool):
        """Atualiza a aparência dos controles entre 'Executando' e 'Pronto'."""
        self.is_scanning = scanning
        self.subnet_input.disabled = scanning
        self.input_username.disabled = scanning
        self.input_password.disabled = scanning
        self.btn_pull_network.disabled = scanning
        self.switch_allow_write.disabled = scanning

        if scanning:
            self.btn_scan.content = "Cancelar"
            self.btn_scan.icon = ft.Icons.STOP_ROUNDED
            self.btn_scan.bgcolor = COLOR_DANGER
        else:
            self.btn_scan.content = "Iniciar Varredura"
            self.btn_scan.icon = ft.Icons.PLAY_ARROW_ROUNDED
            self.btn_scan.bgcolor = COLOR_PRIMARY

        self.update()
