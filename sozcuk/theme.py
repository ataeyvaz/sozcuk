"""Görsel tema: renkler, Qt stil sayfası, Windows başlık çubuğu rengi ve uygulama ikonu."""

import ctypes
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QMenu, QProxyStyle, QStyle

from . import icons

ACCENT = "#185abd"
ACCENT_DARK = "#124a9e"
TEXT = "#242424"
TEXT_MUTED = "#616161"
WINDOW = "#f3f3f3"
CANVAS = "#e9e9e9"
SURFACE = "#ffffff"
BORDER = "#e0e0e0"
HOVER = "#f0f0f0"
PRESSED = "#e0e0e0"
CHECKED = "#dde8f8"
CHECKED_HOVER = "#cfdff5"


def _asset(name, svg_text):
    folder = Path(tempfile.gettempdir()) / "sozcuk-assets"
    folder.mkdir(exist_ok=True)
    path = folder / name
    if not path.exists() or path.read_text(encoding="utf-8") != svg_text:
        path.write_text(svg_text, encoding="utf-8")
    return path.as_posix()


def stylesheet():
    chevron = _asset("chevron.svg", icons.chevron_svg(TEXT_MUTED))
    chevron_white = _asset("chevron-white.svg", icons.chevron_svg("#ffffff"))
    return f"""
QMainWindow, #central {{ background: {WINDOW}; }}
QToolTip {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 5px 8px; border-radius: 4px;
}}

/* --- başlık şeridi --- */
#header {{ background: {ACCENT}; }}
#header QLabel {{ color: #ffffff; }}
#header #docTitle {{ font-weight: 600; }}
#header #docStatus {{ color: rgba(255,255,255,0.8); }}
#header QToolButton {{
    color: #ffffff; border: none; border-radius: 4px; padding: 4px; background: transparent;
}}
#header QToolButton:hover {{ background: rgba(255,255,255,0.14); }}
#header QToolButton:pressed {{ background: rgba(255,255,255,0.24); }}
#header #fileButton {{ padding: 4px 10px; font-weight: 600; }}
#header #fileButton::menu-indicator {{ image: url({chevron_white}); width: 12px; subcontrol-position: right center; right: 4px; }}
#header #fileButton {{ padding-right: 22px; }}

/* --- menü şeridi --- */
#menuRow {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
#menuRow QToolButton {{ padding: 5px 10px; border: none; border-radius: 4px; background: transparent; }}
#menuRow QToolButton:hover {{ background: {HOVER}; }}
#menuRow QToolButton:pressed, #menuRow QToolButton[popupMode="1"]:on {{ background: {PRESSED}; }}
#menuRow QToolButton::menu-indicator {{ image: none; width: 0px; }}

/* --- komut çubuğu --- */
#commandArea {{ background: {WINDOW}; }}
#commandBar {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; }}
QToolButton {{
    border: 1px solid transparent; border-radius: 4px; padding: 3px; background: transparent;
}}
QToolButton:hover {{ background: {HOVER}; }}
QToolButton:pressed {{ background: {PRESSED}; }}
QToolButton:checked {{ background: {CHECKED}; }}
QToolButton:checked:hover {{ background: {CHECKED_HOVER}; }}
QToolButton[popupMode="1"] {{ padding-right: 14px; }}
QToolButton::menu-button {{
    border: none; border-top-right-radius: 4px; border-bottom-right-radius: 4px; width: 13px;
}}
QToolButton::menu-button:hover {{ background: {PRESSED}; }}
QToolButton::menu-arrow, QToolButton::menu-indicator {{ image: url({chevron}); width: 10px; height: 10px; }}
QToolButton::menu-indicator {{ subcontrol-position: right center; subcontrol-origin: padding; right: 1px; }}
QToolButton[popupMode="2"] {{ padding-right: 13px; }}
#moreButton {{ padding-right: 3px; }}
#moreButton::menu-indicator {{ image: none; width: 0px; }}

QComboBox {{
    background: {SURFACE}; border: 1px solid #d1d1d1; border-bottom-color: #bdbdbd;
    border-radius: 4px; padding: 2px 6px; min-height: 22px;
}}
QComboBox:hover {{ border-color: #b3b3b3; }}
QComboBox:focus, QComboBox:on {{ border-bottom: 2px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{ image: url({chevron}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER}; outline: none; padding: 4px;
    selection-background-color: {HOVER}; selection-color: {TEXT};
}}
QComboBox QLineEdit {{ border: none; background: transparent; padding: 0; }}

QMenu {{ background: {SURFACE}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 10px; border-radius: 4px; }}
QMenu::item:selected {{ background: {HOVER}; }}
QMenu::item:disabled {{ color: #a0a0a0; }}
QMenu::icon {{ padding-left: 8px; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}
QMenu::indicator {{ width: 14px; height: 14px; padding-left: 6px; }}

/* --- mesaj çubuğu --- */
#messageBar {{ background: #fff4ce; border: 1px solid #f2e3a6; border-radius: 6px; }}
#findBar {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; }}
#findBar QLineEdit {{ padding: 3px 6px; border: 1px solid #d1d1d1; border-radius: 4px; background: #ffffff; }}
#findBar QLineEdit:focus {{ border-bottom: 2px solid {ACCENT}; }}
#findBar QPushButton {{
    padding: 4px 10px; border: 1px solid {BORDER}; border-radius: 4px; background: {SURFACE};
}}
#findBar QPushButton:hover {{ background: {HOVER}; }}
#findBar #findCount {{ color: {TEXT_MUTED}; }}
#findBar #findCount[empty="true"] {{ color: #a4262c; }}
#messageBar QPushButton {{
    background: {SURFACE}; border: 1px solid #d1d1d1; border-radius: 4px; padding: 3px 12px; min-width: 0;
}}
#messageBar QPushButton:hover {{ background: {HOVER}; }}

/* kayıt sırasında mikrofon düğmesi mavi değil kırmızı tonda vurgulanır */
#micButton:checked {{ background: #fde7e9; }}
#micButton:checked:hover {{ background: #fbd5d9; }}

/* --- sayfa alanı --- */
#page {{ background: {CANVAS}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle {{ background: #c4c4c4; border-radius: 4px; min-height: 32px; min-width: 32px; }}
QScrollBar::handle:hover {{ background: #9e9e9e; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; border: none; width: 0; height: 0;
}}

/* --- durum çubuğu --- */
QStatusBar {{ background: {WINDOW}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {TEXT_MUTED}; padding: 0 10px; }}
QStatusBar QToolButton {{ color: {TEXT_MUTED}; padding: 1px; }}
QSlider::groove:horizontal {{ height: 1px; background: #8a8a8a; }}
QSlider::handle:horizontal {{
    width: 4px; height: 12px; margin: -6px 0; background: {TEXT_MUTED}; border-radius: 1px;
}}
QSlider::handle:horizontal:hover {{ background: {TEXT}; }}

QDialog, QMessageBox {{ background: {SURFACE}; }}
QPushButton {{
    background: {SURFACE}; border: 1px solid #d1d1d1; border-radius: 4px; padding: 5px 16px; min-width: 64px;
}}
QPushButton:hover {{ background: {HOVER}; }}
QPushButton:default {{ background: {ACCENT}; color: #ffffff; border-color: {ACCENT}; }}
QPushButton:default:hover {{ background: {ACCENT_DARK}; }}
"""


class _Style(QProxyStyle):
    """Menü ikonlarını da 20 px çizer: ikonlar 20 px ızgaraya hizalı, küçültmek bulanıklaştırır."""

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_SmallIconSize and isinstance(widget, QMenu):
            return 20
        return super().pixelMetric(metric, option, widget)


def apply(app):
    app.setStyle(_Style("Fusion"))
    palette = QPalette()
    for role, color in (
        (QPalette.Window, WINDOW), (QPalette.WindowText, TEXT), (QPalette.Base, SURFACE),
        (QPalette.AlternateBase, WINDOW), (QPalette.Text, TEXT), (QPalette.Button, SURFACE),
        (QPalette.ButtonText, TEXT), (QPalette.Highlight, "#b4d3f7"), (QPalette.HighlightedText, TEXT),
        (QPalette.ToolTipBase, SURFACE), (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, "#8a8a8a"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(stylesheet())
    app.setWindowIcon(app_icon())


def app_icon():
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACCENT))
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.2, size * 0.2)
        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 1, QFont.DemiBold)
        font.setPixelSize(round(size * 0.68))
        p.setFont(font)
        p.drawText(QRectF(0, -size * 0.03, size, size), Qt.AlignCenter, "S")
        p.end()
        result.addPixmap(pix)
    return result


def color_title_bar(widget, background=ACCENT, text="#ffffff"):
    """Windows 11'de yerel başlık çubuğunu başlık şeridiyle aynı renge boyar."""
    if sys.platform != "win32":
        return

    def colorref(hex_color):
        c = QColor(hex_color)
        return c.red() | (c.green() << 8) | (c.blue() << 16)

    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        for attribute, value in ((35, colorref(background)), (36, colorref(text)), (34, colorref(background))):
            v = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(v), ctypes.sizeof(v))
    except (AttributeError, OSError):
        pass
