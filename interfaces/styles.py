"""
Estilos (QSS) compartidos para que todas las pantallas se vean uniformes.

Se definen dos temas (claro y oscuro) a partir de los mismos tokens de
color. Hay un único color de acento para botones principales, selección y
estados activos; el resto de la paleta es neutra.
"""

TEMAS = {
    "claro": {
        "fondo": "#F4F4F2",
        "superficie": "#FFFFFF",
        "superficie_alt": "#EDEDEA",
        "borde": "#DCDBD6",
        "borde_fuerte": "#C4C3BD",
        "texto": "#1D1D1F",
        "texto_sec": "#6A6A70",
        "texto_ter": "#9A9AA0",
        "acento": "#3D6B8C",
        "acento_hover": "#335B78",
        "acento_presionado": "#2A4B63",
        "acento_texto": "#FFFFFF",
        "acento_suave": "#E4ECF2",
        "exito": "#2E7450",
        "exito_suave": "#E5F1EA",
        "advertencia": "#8A5F10",
        "advertencia_suave": "#F6EEDC",
        "error": "#A93A3A",
        "error_suave": "#F6E4E4",
        "video": "#E7E7E4",
    },
    "oscuro": {
        "fondo": "#17181A",
        "superficie": "#202124",
        "superficie_alt": "#292A2E",
        "borde": "#33353A",
        "borde_fuerte": "#45474D",
        "texto": "#ECECEE",
        "texto_sec": "#A0A1A7",
        "texto_ter": "#74757B",
        "acento": "#6F9CBF",
        "acento_hover": "#82ACCC",
        "acento_presionado": "#5C88AA",
        "acento_texto": "#0F1418",
        "acento_suave": "#23303A",
        "exito": "#72BE8E",
        "exito_suave": "#1E2E25",
        "advertencia": "#D8AA55",
        "advertencia_suave": "#322A1B",
        "error": "#E08585",
        "error_suave": "#352122",
        "video": "#111214",
    },
}

_tema_actual = "claro"


def tema_actual() -> str:
    return _tema_actual


def establecer_tema(nombre: str):
    global _tema_actual
    _tema_actual = nombre if nombre in TEMAS else "claro"


def paleta(nombre: str = None) -> dict:
    return TEMAS[nombre or _tema_actual]


_PLANTILLA = """
QWidget {{
    color: {texto};
    font-family: 'Segoe UI', 'Segoe UI Variable Text', sans-serif;
    font-size: 14px;
}}
QMainWindow, QDialog, QWidget#raiz {{
    background-color: {fondo};
}}
QScrollArea, QScrollArea > QWidget > QWidget, QStackedWidget {{
    background: transparent;
    border: none;
}}
QLabel {{ background: transparent; }}

/* ---------- Tipografía ---------- */
QLabel#titulo {{
    font-size: 24px;
    font-weight: 600;
    color: {texto};
}}
QLabel#subtitulo {{
    font-size: 14px;
    color: {texto_sec};
}}
QLabel#seccion {{
    font-size: 15px;
    font-weight: 600;
    color: {texto};
}}
QLabel#etiqueta {{
    font-size: 12px;
    font-weight: 600;
    color: {texto_sec};
    letter-spacing: 0.3px;
}}
QLabel#nota {{
    font-size: 12px;
    color: {texto_sec};
}}
QLabel#error {{
    color: {error};
    font-weight: 500;
}}
QLabel#metrica {{
    font-size: 20px;
    font-weight: 600;
    color: {texto};
}}

/* ---------- Superficies ---------- */
QFrame#tarjeta {{
    background-color: {superficie};
    border: 1px solid {borde};
    border-radius: 10px;
}}
QFrame#separador {{
    background-color: {borde};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QLabel#video {{
    background-color: {video};
    border: 1px solid {borde};
    border-radius: 10px;
    color: {texto_ter};
}}

/* ---------- Barra lateral ---------- */
QFrame#barra_lateral {{
    background-color: {superficie};
    border: none;
    border-right: 1px solid {borde};
}}
QLabel#marca {{
    font-size: 15px;
    font-weight: 700;
    color: {texto};
}}
QLabel#grupo_nav {{
    font-size: 11px;
    font-weight: 600;
    color: {texto_ter};
    padding: 14px 12px 4px 12px;
}}
QPushButton#nav {{
    background-color: transparent;
    color: {texto_sec};
    border: none;
    border-radius: 7px;
    padding: 8px 12px;
    text-align: left;
    font-weight: 500;
}}
QPushButton#nav:hover {{
    background-color: {superficie_alt};
    color: {texto};
}}
QPushButton#nav:checked {{
    background-color: {acento_suave};
    color: {acento};
}}

/* ---------- Campos ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color: {superficie};
    border: 1px solid {borde_fuerte};
    border-radius: 7px;
    padding: 7px 9px;
    color: {texto};
    selection-background-color: {acento};
    selection-color: {acento_texto};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {acento};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {superficie_alt};
    color: {texto_ter};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {superficie};
    border: 1px solid {borde};
    selection-background-color: {acento_suave};
    selection-color: {texto};
    outline: none;
}}
QCheckBox {{ spacing: 8px; background: transparent; }}

/* ---------- Botones ---------- */
QPushButton {{
    background-color: {acento};
    color: {acento_texto};
    border: 1px solid {acento};
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {acento_hover}; border-color: {acento_hover}; }}
QPushButton:pressed {{ background-color: {acento_presionado}; }}
QPushButton:disabled {{
    background-color: {superficie_alt};
    border-color: {borde};
    color: {texto_ter};
}}
QPushButton#secundario {{
    background-color: {superficie};
    border: 1px solid {borde_fuerte};
    color: {texto};
}}
QPushButton#secundario:hover {{ background-color: {superficie_alt}; }}
QPushButton#secundario:disabled {{ color: {texto_ter}; border-color: {borde}; }}
QPushButton#peligro {{
    background-color: {superficie};
    border: 1px solid {borde_fuerte};
    color: {error};
}}
QPushButton#peligro:hover {{ background-color: {error_suave}; border-color: {error}; }}
QPushButton#peligro:disabled {{ color: {texto_ter}; border-color: {borde}; }}
QPushButton#segmento {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {texto_sec};
    padding: 7px 14px;
    font-weight: 500;
}}
QPushButton#segmento:hover {{ color: {texto}; background-color: {superficie_alt}; }}
QPushButton#segmento:checked {{
    background-color: {superficie};
    border: 1px solid {borde};
    color: {texto};
}}
QFrame#barra_segmentos {{
    background-color: {superficie_alt};
    border-radius: 9px;
}}

/* ---------- Mensajes de estado ---------- */
QLabel#banner_info, QLabel#banner_exito, QLabel#banner_advertencia, QLabel#banner_error {{
    border-radius: 8px;
    padding: 10px 12px;
}}
QLabel#banner_info {{ background-color: {acento_suave}; color: {texto}; border-left: 3px solid {acento}; }}
QLabel#banner_exito {{ background-color: {exito_suave}; color: {texto}; border-left: 3px solid {exito}; }}
QLabel#banner_advertencia {{ background-color: {advertencia_suave}; color: {texto}; border-left: 3px solid {advertencia}; }}
QLabel#banner_error {{ background-color: {error_suave}; color: {texto}; border-left: 3px solid {error}; }}

QLabel#pastilla_activa {{
    background-color: {error_suave};
    color: {error};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#pastilla_neutra {{
    background-color: {superficie_alt};
    color: {texto_sec};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#pastilla_ok {{
    background-color: {exito_suave};
    color: {exito};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}

/* ---------- Progreso ---------- */
QProgressBar {{
    background-color: {superficie_alt};
    border: none;
    border-radius: 4px;
    max-height: 8px;
    min-height: 8px;
}}
QProgressBar::chunk {{ background-color: {acento}; border-radius: 4px; }}

/* ---------- Tablas ---------- */
QTableWidget {{
    background-color: {superficie};
    alternate-background-color: {superficie_alt};
    gridline-color: {borde};
    border: 1px solid {borde};
    border-radius: 8px;
    selection-background-color: {acento_suave};
    selection-color: {texto};
}}
QHeaderView::section {{
    background-color: {superficie_alt};
    color: {texto_sec};
    padding: 7px;
    border: none;
    border-bottom: 1px solid {borde};
    font-weight: 600;
}}
QTableCornerButton::section {{ background-color: {superficie_alt}; border: none; }}

/* ---------- Barras de desplazamiento ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {borde_fuerte}; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {borde_fuerte}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QToolTip {{
    background-color: {superficie};
    color: {texto};
    border: 1px solid {borde};
    padding: 4px 6px;
}}
QMessageBox QLabel {{ min-width: 280px; }}
"""


def construir_estilo(nombre: str = None) -> str:
    return _PLANTILLA.format(**paleta(nombre))


# Compatibilidad con el código existente
ESTILO_APP = construir_estilo("claro")
