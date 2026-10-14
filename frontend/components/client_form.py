from typing import Callable, Optional
import flet as ft

from backend.models.device import DocumentMetadata
from frontend.styles.theme import (
    COLOR_SURFACE,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED
)


class ClientForm(ft.Container):
    """
    Componente de formulário manual para dados de cabeçalho do documento de uso interno.
    Campos solicitados: Cliente, Endereço (Rua, Número, Bairro), Técnico Responsável e Local do Equipamento.
    """
    def __init__(self, on_generate_document: Callable[[], None]):
        self.on_generate_document = on_generate_document

        # Campos de preenchimento manual
        self.input_cliente = ft.TextField(
            label="Cliente / Empresa",
            hint_text="Ex: Condomínio Plaza Corporate",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=True
        )

        self.input_rua = ft.TextField(
            label="Rua / Logradouro",
            hint_text="Ex: Av. Paulista",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=3
        )

        self.input_numero = ft.TextField(
            label="Número",
            hint_text="Ex: 1000",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=1
        )

        self.input_bairro = ft.TextField(
            label="Bairro",
            hint_text="Ex: Bela Vista",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=2
        )

        self.input_tecnico = ft.TextField(
            label="Técnico Responsável",
            hint_text="Ex: Carlos Silva",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=1
        )

        self.input_local = ft.TextField(
            label="Local do Equipamento",
            hint_text="Ex: Recepção Central / Catracas Bloco A",
            text_size=13,
            label_style=ft.TextStyle(size=12, color=COLOR_TEXT_MUTED),
            text_style=ft.TextStyle(size=13, color=COLOR_TEXT_PRIMARY),
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=1
        )

        # Botão Principal de Ação
        self.btn_generate_doc = ft.FilledButton(
            "Gerar Documento Interno (PDF)",
            icon=ft.Icons.PICTURE_AS_PDF_ROUNDED,
            bgcolor=COLOR_SUCCESS,
            color="#FFFFFF",
            height=42,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10)
            ),
            on_click=lambda _: self.on_generate_document()
        )

        # Montagem do Layout do Card
        super().__init__(
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=COLOR_PRIMARY, size=18),
                                    ft.Text(
                                        "Cabeçalho do Documento Interno (Preenchimento Manual)",
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=COLOR_TEXT_PRIMARY
                                    ),
                                ]
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "Uso Interno • Sem assinaturas",
                                    size=11,
                                    color=COLOR_TEXT_MUTED
                                ),
                                bgcolor="#1E293B",
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                border_radius=6
                            )
                        ]
                    ),
                    # Linha 1: Cliente
                    ft.Row(
                        spacing=10,
                        controls=[self.input_cliente]
                    ),
                    # Linha 2: Endereço (Rua, Número, Bairro)
                    ft.Row(
                        spacing=10,
                        controls=[
                            self.input_rua,
                            self.input_numero,
                            self.input_bairro,
                        ]
                    ),
                    # Linha 3: Técnico e Local do Equipamento + Botão
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.input_tecnico,
                            self.input_local,
                            self.btn_generate_doc
                        ]
                    ),
                ]
            ),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=14
        )

    def get_metadata(self) -> DocumentMetadata:
        """Coleta e retorna os valores atuais preenchidos no formulário."""
        return DocumentMetadata(
            cliente=self.input_cliente.value.strip() if self.input_cliente.value else "",
            rua=self.input_rua.value.strip() if self.input_rua.value else "",
            numero=self.input_numero.value.strip() if self.input_numero.value else "",
            bairro=self.input_bairro.value.strip() if self.input_bairro.value else "",
            tecnico=self.input_tecnico.value.strip() if self.input_tecnico.value else "",
            local_equipamento=self.input_local.value.strip() if self.input_local.value else ""
        )

    def validate(self) -> tuple[bool, str]:
        """Valida se os campos obrigatórios foram preenchidos."""
        if not self.input_cliente.value or not self.input_cliente.value.strip():
            return False, "Por favor, preencha o nome do 'Cliente'."
        if not self.input_rua.value or not self.input_rua.value.strip():
            return False, "Por favor, preencha o campo 'Rua'."
        if not self.input_numero.value or not self.input_numero.value.strip():
            return False, "Por favor, preencha o campo 'Número'."
        if not self.input_bairro.value or not self.input_bairro.value.strip():
            return False, "Por favor, preencha o campo 'Bairro'."
        if not self.input_tecnico.value or not self.input_tecnico.value.strip():
            return False, "Por favor, informe o 'Técnico Responsável'."
        if not self.input_local.value or not self.input_local.value.strip():
            return False, "Por favor, informe o 'Local do Equipamento'."
        return True, ""
