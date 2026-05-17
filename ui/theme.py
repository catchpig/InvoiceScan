"""Unified theme & stylesheet for the Invoice Scan application."""

# ── Color tokens ──────────────────────────────────────────────────────
COLORS = {
    "primary":       "#2B5CE6",
    "primary_hover": "#1E45B8",
    "primary_light": "#E8EDFB",
    "success":       "#22C55E",
    "success_bg":    "#ECFDF5",
    "warning":       "#F59E0B",
    "warning_bg":    "#FFFBEB",
    "danger":        "#EF4444",
    "danger_bg":     "#FEF2F2",
    "info":          "#3B82F6",
    "info_bg":       "#EFF6FF",

    "bg_app":        "#F5F7FA",
    "bg_surface":    "#FFFFFF",
    "bg_hover":      "#F0F4FA",
    "bg_selected":   "#E8EDFB",

    "border":        "#E2E8F0",
    "border_focus":  "#2B5CE6",

    "text_primary":  "#1E293B",
    "text_secondary":"#64748B",
    "text_muted":    "#94A3B8",
    "text_inverse":  "#FFFFFF",

    "shadow":        "rgba(0,0,0,0.06)",
}

# ── Typography ────────────────────────────────────────────────────────
FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif'

# ── Master stylesheet ─────────────────────────────────────────────────
STYLESHEET = f"""
/* ─── Global ─── */
QMainWindow {{
    background: {COLORS['bg_app']};
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {COLORS['text_primary']};
}}

QWidget {{
    font-family: {FONT_FAMILY};
}}

/* ─── Toolbar ─── */
QToolBar {{
    background: {COLORS['bg_surface']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 6px 12px;
    spacing: 4px;
}}

QToolBar QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
    color: {COLORS['text_primary']};
}}

QToolBar QToolButton:hover {{
    background: {COLORS['bg_hover']};
    border-color: {COLORS['border']};
}}

QToolBar QToolButton:pressed {{
    background: {COLORS['primary_light']};
}}

QToolBar QToolButton[action-primary="true"] {{
    background: {COLORS['primary']};
    color: {COLORS['text_inverse']};
    border-color: {COLORS['primary']};
}}

QToolBar QToolButton[action-primary="true"]:hover {{
    background: {COLORS['primary_hover']};
    border-color: {COLORS['primary_hover']};
}}

QToolBar QToolButton[action-danger="true"] {{
    color: {COLORS['danger']};
}}

QToolBar QToolButton[action-danger="true"]:hover {{
    background: {COLORS['danger_bg']};
}}

QToolBar::separator {{
    width: 1px;
    height: 24px;
    background: {COLORS['border']};
    margin: 0 8px;
}}

/* ─── File list ─── */
QListWidget {{
    background: {COLORS['bg_surface']};
    border: none;
    border-right: 1px solid {COLORS['border']};
    outline: none;
    padding: 4px 0;
}}

QListWidget::item {{
    border-bottom: 1px solid {COLORS['border']};
    padding: 2px 0;
}}

QListWidget::item:selected {{
    background: {COLORS['bg_selected']};
}}

QListWidget::item:hover:!selected {{
    background: {COLORS['bg_hover']};
}}

/* ─── Scroll area ─── */
QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 0;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['text_muted']};
    border-radius: 4px;
    min-height: 32px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ─── Form inputs ─── */
QLineEdit {{
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['primary_light']};
}}

QLineEdit:focus {{
    border-color: {COLORS['border_focus']};
    box-shadow: 0 0 0 3px rgba(43,92,230,0.12);
}}

QLineEdit[readOnly="true"] {{
    background: {COLORS['bg_app']};
    color: {COLORS['text_secondary']};
}}

/* ─── Buttons ─── */
QPushButton {{
    background: {COLORS['primary']};
    color: {COLORS['text_inverse']};
    border: none;
    border-radius: 6px;
    padding: 9px 22px;
    font-size: 13px;
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background: {COLORS['primary_hover']};
}}

QPushButton:pressed {{
    background: {COLORS['primary']};
}}

QPushButton[btn-style="secondary"] {{
    background: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
}}

QPushButton[btn-style="secondary"]:hover {{
    background: {COLORS['bg_hover']};
    border-color: {COLORS['text_muted']};
}}

/* ─── Status bar ─── */
QStatusBar {{
    background: {COLORS['bg_surface']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_secondary']};
    font-size: 12px;
    padding: 4px 12px;
}}

QStatusBar QLabel {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}

/* ─── Splitter handle ─── */
QSplitter::handle {{
    background: {COLORS['border']};
    width: 1px;
}}

QSplitter::handle:hover {{
    background: {COLORS['primary']};
    width: 2px;
}}

/* ─── Message box ─── */
QMessageBox {{
    background: {COLORS['bg_surface']};
}}

QMessageBox QLabel {{
    font-size: 13px;
    color: {COLORS['text_primary']};
}}

QMessageBox QPushButton {{
    min-width: 72px;
}}
"""
