"""Tokens visuais, paleta de cores e temas para a interface Flet."""

# Paleta de Cores do Dark Mode Corporativo
COLOR_BG_DARK = "#0F172A"          # Fundo principal da aplicação (Slate 900)
COLOR_SURFACE = "#1E293B"          # Superfície de cards e painéis (Slate 800)
COLOR_SURFACE_LIGHT = "#334155"    # Destaque de containers e headers (Slate 700)
COLOR_BORDER = "#334155"           # Linhas de divisão e contornos
COLOR_PRIMARY = "#2563EB"          # Azul vibrante de ação (Blue 600)
COLOR_PRIMARY_HOVER = "#1D4ED8"    # Azul hover (Blue 700)
COLOR_SUCCESS = "#10B981"          # Verde esmeralda (Emerald 500)
COLOR_SUCCESS_BG = "#064E3B"       # Verde escuro para fundo de status
COLOR_WARNING = "#F59E0B"          # Âmbar para alertas (Amber 500)
COLOR_DANGER = "#EF4444"           # Vermelho para cancelamento/erros (Red 500)
COLOR_TEXT_PRIMARY = "#F8FAFC"     # Branco suave (Slate 50)
COLOR_TEXT_MUTED = "#94A3B8"       # Cinza médio para rótulos (Slate 400)
COLOR_ROW_ALT = "#162032"          # Linha alternada na tabela

# Dicionário de cores para badges de modelo
MODEL_COLORS = {
    "idface": "#3B82F6",    # Azul
    "idclass": "#10B981",   # Verde
    "idaccess": "#8B5CF6",  # Roxo
    "idflex": "#EC4899",    # Rosa
    "idbox": "#F59E0B",     # Âmbar
    "idfit": "#06B6D4",     # Ciano
    "idblock": "#F97316",   # Laranja
    "idgate": "#14B8A6",    # Teal
    "idtouch": "#6366F1",   # Índigo
    "idprint": "#84CC16",   # Lima
    "idbio": "#A855F7",     # Púrpura
    "idlook": "#0EA5E9",    # Azul Claro
    "default": "#64748B"    # Cinza
}


def get_model_color(model_name: str) -> str:
    """Retorna a cor associada à linha do equipamento."""
    lower_name = model_name.lower().replace(" ", "")
    for key, color in MODEL_COLORS.items():
        if key in lower_name:
            return color
    return MODEL_COLORS["default"]
