"""One restrained palette and native widget typography."""

BACKGROUND = "#101a22"
SURFACE = "#172530"
RAISED = "#213340"
TEXT = "#e5eef1"
MUTED = "#93a8b4"
ACCENT = "#72bfcc"
WARNING = "#efca82"
ERROR = "#e69a91"
STYLE = f"""
QWidget {{ background: {BACKGROUND}; color: {TEXT}; font-family: 'Segoe UI'; font-size: 14px; }}
QMainWindow, QStackedWidget {{ background: {BACKGROUND}; }}
QLabel#Title {{ font-size: 28px; font-weight: 600; }}
QLabel#Subtitle {{ color: {MUTED}; font-size: 15px; }}
QPushButton {{ background: {RAISED}; border: 1px solid #314a59; border-radius: 6px; padding: 10px 16px; }}
QPushButton:hover {{ border-color: {ACCENT}; background: #284450; }}
QPushButton:checked {{ background: #28525e; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #657985; }}
QComboBox, QSpinBox, QDoubleSpinBox {{ background: {SURFACE}; border: 1px solid #314a59; border-radius: 4px; padding: 7px; }}
QTextBrowser, QListWidget, QGroupBox {{ background: {SURFACE}; border: 1px solid #29404e; border-radius: 6px; padding: 10px; }}
QListWidget::item {{ padding: 10px; }}
QListWidget::item:selected {{ background: #28525e; }}
QDockWidget::title {{ background: {RAISED}; padding: 12px; font-weight: 600; }}
QToolBar {{ spacing: 10px; padding: 10px; border: none; }}
QStatusBar {{ background: {SURFACE}; color: {MUTED}; }}
QScrollArea {{ border: none; }}
QCheckBox {{ padding: 6px; spacing: 10px; }}
"""
