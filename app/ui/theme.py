"""Design tokens and modern dark theme stylesheet for DIP Touchless STEM UI."""

from __future__ import annotations

# Palette colors
COLOR_BG_DARK = "#0B0F19"         # Deep Space Navy
COLOR_BG_SURFACE = "#111827"      # Dark Surface Card
COLOR_BG_CARD = "rgba(17, 24, 39, 0.85)"
COLOR_BG_ELEVATED = "#1F2937"    # Elevated Container
COLOR_BORDER = "#374151"          # Subtle border
COLOR_BORDER_LIGHT = "#4B5563"

# Accent Colors
COLOR_PRIMARY = "#06B6D4"         # Electric Cyan
COLOR_PRIMARY_HOVER = "#22D3EE"
COLOR_SECONDARY = "#8B5CF6"       # Vivid Violet / Purple
COLOR_SECONDARY_HOVER = "#A78BFA"

# Status Colors
COLOR_SUCCESS = "#10B981"         # Emerald Green (Valid Tracking)
COLOR_WARNING = "#F59E0B"         # Amber (Reacquisition / Medium light)
COLOR_DANGER = "#EF4444"          # Coral Red (No Hand / Low light)
COLOR_INFO = "#3B82F6"            # Sky Blue

# Text Colors
COLOR_TEXT_PRIMARY = "#F9FAFB"    # High contrast white
COLOR_TEXT_SECONDARY = "#9CA3AF"  # Slate gray secondary text
COLOR_TEXT_MUTED = "#6B7280"      # Dim muted text

MAIN_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

QWidget {{
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}}

QToolTip {{
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* Header Bar Styling */
#header_container {{
    background-color: {COLOR_BG_SURFACE};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 10px 20px;
}}

#project_badge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY}, stop:1 {COLOR_SECONDARY});
    color: #FFFFFF;
    font-weight: 700;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

#project_title {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}

#project_subtitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 400;
}}

/* Member Chip Card */
.member_card {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 4px 10px;
}}
.member_card:hover {{
    border: 1px solid {COLOR_PRIMARY};
    background-color: #273549;
}}
.member_name {{
    font-weight: 600;
    font-size: 12px;
    color: {COLOR_TEXT_PRIMARY};
}}
.member_role {{
    font-size: 10px;
    color: {COLOR_PRIMARY_HOVER};
}}

/* Status Badge */
#status_badge {{
    background-color: rgba(16, 185, 129, 0.15);
    border: 1px solid {COLOR_SUCCESS};
    color: {COLOR_SUCCESS};
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 11px;
}}

/* Navigation Tabs */
QTabBar::tab {{
    background-color: transparent;
    color: {COLOR_TEXT_SECONDARY};
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
    margin-right: 8px;
}}

QTabBar::tab:hover {{
    color: {COLOR_TEXT_PRIMARY};
    background-color: rgba(255, 255, 255, 0.04);
    border-radius: 6px;
}}

QTabBar::tab:selected {{
    color: {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY};
}}

/* Modern Glass Card */
QFrame.glass_card {{
    background-color: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 14px;
}}
QFrame.glass_card:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

/* Buttons */
QPushButton {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 600;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: #2d3748;
    border: 1px solid {COLOR_PRIMARY};
    color: {COLOR_PRIMARY_HOVER};
}}

QPushButton:pressed {{
    background-color: #1a202c;
}}

QPushButton.btn_primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY}, stop:1 #0891B2);
    border: none;
    color: #FFFFFF;
}}

QPushButton.btn_primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_HOVER}, stop:1 {COLOR_PRIMARY});
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {COLOR_BG_ELEVATED};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {COLOR_PRIMARY};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {COLOR_PRIMARY};
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {COLOR_PRIMARY_HOVER};
    border-color: #FFFFFF;
}}

/* ComboBox */
QComboBox {{
    background-color: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 500;
}}

QComboBox:hover {{
    border: 1px solid {COLOR_PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_BG_ELEVATED};
    selection-color: {COLOR_PRIMARY};
    border-radius: 8px;
    padding: 4px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}
"""
