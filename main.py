import sys
import flet as ft
from frontend.app import create_app_view


async def main(page: ft.Page):
    """Ponto de entrada da aplicação desktop Flet."""
    page.title = "SCAN BOT Rede"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # Configura dimensões e comportamento da janela
    if hasattr(page, "window"):
        page.window.width = 1080
        page.window.height = 760
        page.window.min_width = 850
        page.window.min_height = 600
        try:
            res = page.window.center()
            if hasattr(res, "__await__"):
                await res
        except Exception:
            pass

    # Cria a visualização principal e anexa à página
    app_view = create_app_view(page)
    page.add(app_view)


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
