"""ShapeToolbar: floating touchless shape-selector and task-selector rendered as a QPainter overlay.

Behaviour
---------
* Shape selector button (180x44 px) sits at top-right of viewport.
* Task selector button (180x44 px) sits directly below the shape selector button.
* Hovering the pointing fingertip inside a button for DWELL_OPEN_S seconds toggles its dropdown open.
* Both buttons are mutually exclusive: when one is open, the other cannot be opened.
* When shape dropdown is open, task button is temporarily disabled.
* Task button availability:
  - If 1 shape exists on screen: enabled immediately.
  - If >= 2 shapes exist on screen: enabled only when 1 shape is explicitly selected.
  - If 0 shapes exist: disabled.
* Tasks catalog:
  - Tác vụ hình học: Đo khoảng cách (Distance), Đo góc & Thông số (Angle & Metrics).
  - Khối 3D: Thiết diện cắt (Cross-section) - only enabled if target shape is 3D.
* Selecting an item in the task menu toggles that task on the target shape and immediately closes the menu.
* An object can have multiple tasks active at the same time.
* Delete-button sits at bottom-left:
  - Drag shape into trash -> delete that shape (0.8s).
  - Hover pointer on trash -> clear all shapes (0.8s).
"""

import math
from PySide6.QtCore import QRect, Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PySide6.QtWidgets import QWidget

from .theme import BACKGROUND, SURFACE, RAISED, TEXT, MUTED, ACCENT, WARNING, ERROR
from app.interaction.dwell_tracker import DwellTracker

# Shape catalog
SHAPES_2D = ("Circle", "Square", "Triangle", "Rectangle")
SHAPES_3D = ("Sphere", "Cube", "Box", "Pyramid")
ALL_SHAPES = SHAPES_2D + SHAPES_3D

# Tasks catalog
TASK_GENERAL = (
    ("distance", "📏 Đo khoảng cách"),
    ("metrics", "📐 Đo góc & Thông số"),
)
TASK_3D = (
    ("cross_section", "🔪 Thiết diện cắt"),
    ("unfold", "📦 Bung mặt phẳng"),
)

# Unicode icons for each shape
SHAPE_ICON = {
    "Circle":    "⬤",
    "Square":    "■",
    "Triangle":  "▲",
    "Rectangle": "▬",
    "Sphere":    "🌐",
    "Cube":      "⬛",
    "Box":       "📦",
    "Pyramid":   "△",
}

# Timing constants
DWELL_OPEN_S = 0.8
DWELL_SELECT_S = 0.8
DWELL_DELETE_DRAG_S = 0.8   # 0.8s to delete a shape dragged into trash
DWELL_DELETE_ALL_S = 0.8    # 0.8s when holding index finger on trash to clear all

# Layout constants
TRIGGER_W = 180         # button width (px), equal to delete button
TRIGGER_H = 44          # button height (px), equal to delete button
PANEL_W = 200           # width of dropdown menu (px)
ITEM_H = 38             # height of each item row (px)
HEADER_H = 26           # section header height (px)
PANEL_PAD = 8           # padding inside panel (px)
GROUP_SPACING = 6       # spacing between groups (px)
CAMERA_INSET_X = 24     # inset from camera frame border to keep hand + wrist within FOV
CAMERA_INSET_Y = 20     # inset from camera frame top/bottom border
MARGIN = CAMERA_INSET_Y # for backward compatibility
DELETE_H = 44           # delete button height (px)
DELETE_W = 180          # delete button width (px)
PROGRESS_H = 4          # dwell progress bar height (px)

# Colours
C_BG = QColor("#172530")
C_RAISED = QColor(RAISED)
C_TRIGGER = QColor("#1e3241")
C_ITEM_HOVER = QColor("#28525e")
C_ITEM_SELECT = QColor("#2a6070")
C_TEXT = QColor(TEXT)
C_MUTED = QColor(MUTED)
C_ACCENT = QColor(ACCENT)
C_WARNING = QColor(WARNING)
C_ERROR = QColor(ERROR)
C_DELETE_IDLE = QColor("#1e3241")
C_DELETE_SINGLE = QColor("#7a4a10")
C_DELETE_ALL = QColor("#6b1c1c")
C_DELETE_SINGLE_BORDER = QColor("#e07b3c")
C_DELETE_ALL_BORDER = QColor(ERROR)


class ShapeToolbar(QWidget):
    """Transparent overlay widget managing shape-selector and task-selector panels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(True)

        # Shape state
        self._open: bool = False
        self._trigger_must_exit: bool = False
        self._selected_shape: str | None = None
        self._hovered_item: str | None = None

        # Task state
        self._task_open: bool = False
        self._task_trigger_must_exit: bool = False
        self._hovered_task_item: str | None = None
        self._frozen_shapes: list = []
        self._selected_shape_id: str | None = None
        self._shape_select_frac: float = 0.0
        self.last_task_event: str | None = None
        self.task_dropdown_opened: bool = False
        self.task_started: bool = False

        # Delete state
        self._delete_state: str = "IDLE"   # IDLE | DRAG_DELETE | CLEAR_ALL
        self._delete_fraction: float = 0.0
        self.delete_event: str | None = None  # set to "DRAG_SINGLE" | "ALL" then cleared

        # Pointer tip
        self._tip_px: QPoint | None = None

        # Dwell trackers
        self._trigger_dwell = DwellTracker(DWELL_OPEN_S)
        self._item_dwell = DwellTracker(DWELL_SELECT_S)
        self._task_trigger_dwell = DwellTracker(DWELL_OPEN_S)
        self._task_item_dwell = DwellTracker(DWELL_SELECT_S)
        self._delete_dwell = DwellTracker(DWELL_DELETE_DRAG_S)

        # Progress fractions for visual feedback
        self._trigger_frac: float = 0.0
        self._item_frac: float = 0.0
        self._task_trigger_frac: float = 0.0
        self._task_item_frac: float = 0.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def selected_shape(self) -> str | None:
        return self._selected_shape

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def is_task_open(self) -> bool:
        return self._task_open

    @property
    def hovering_trigger(self) -> bool:
        if self._tip_px is None:
            return False
        return self._trigger_rect().contains(self._tip_px) or self._task_trigger_rect().contains(self._tip_px)

    def get_active_shape(self):
        """Active target shape for tasks:
        - Exactly 1 shape: returns that single shape.
        - >= 2 shapes: returns selected shape if chosen, else None.
        """
        if not self._frozen_shapes:
            return None
        if len(self._frozen_shapes) == 1:
            return self._frozen_shapes[0]
        if self._selected_shape_id:
            for s in self._frozen_shapes:
                if s.shape_id == self._selected_shape_id:
                    return s
        return None

    def is_task_trigger_enabled(self) -> bool:
        """Task button is disabled if shape dropdown is open, if no shapes, or if >=2 shapes unselected."""
        if self._open:
            return False
        return self.get_active_shape() is not None

    def clear_selection(self) -> None:
        self._selected_shape = None
        self._open = False
        self._task_open = False
        self._trigger_dwell.reset()
        self._item_dwell.reset()
        self._task_trigger_dwell.reset()
        self._task_item_dwell.reset()
        self._trigger_frac = 0.0
        self._item_frac = 0.0
        self._task_trigger_frac = 0.0
        self._task_item_frac = 0.0
        self._hovered_item = None
        self._hovered_task_item = None
        self.task_dropdown_opened = False
        self.task_started = False
        self.update()

    def clear_delete_event(self) -> None:
        self.delete_event = None

    def clear_task_event(self) -> None:
        self.last_task_event = None

    # ------------------------------------------------------------------
    # Main per-frame update
    # ------------------------------------------------------------------

    def update_tip(
        self,
        tip_xy,
        dt: float,
        is_dragging_shape: bool = False,
        frozen_shapes: list | None = None,
        selected_shape_id: str | None = None,
        shape_select_frac: float = 0.0,
    ) -> None:
        """Call once per frame from shell consume()."""
        if frozen_shapes is not None:
            self._frozen_shapes = frozen_shapes
        if selected_shape_id is not None or frozen_shapes is not None:
            self._selected_shape_id = selected_shape_id
        self._shape_select_frac = shape_select_frac

        tip_px = self._to_widget_px(tip_xy) if tip_xy is not None else None
        self._tip_px = tip_px

        self._update_trigger(tip_px, dt)
        if self._open:
            self._update_items(tip_px, dt)

        self._update_task_trigger(tip_px, dt)
        if self._task_open:
            self._update_task_items(tip_px, dt)

        self._update_delete(tip_px, dt, is_dragging_shape=is_dragging_shape)
        self.update()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _to_widget_px(self, norm_xy) -> QPoint | None:
        if norm_xy is None:
            return None
        pw, ph = self.width(), self.height()
        if pw <= 0 or ph <= 0:
            return None
        return QPoint(round(norm_xy[0] * pw), round(norm_xy[1] * ph))

    def _camera_rect(self) -> QRect:
        """Returns the displayed camera frame bounding box inside the viewport."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "image_rect"):
            ix, iy, iw, ih = parent.image_rect()
            if iw > 0 and ih > 0:
                return QRect(round(ix), round(iy), round(iw), round(ih))
        return QRect(0, 0, max(0, self.width()), max(0, self.height()))

    def _trigger_rect(self) -> QRect:
        """Top-right button (Shape selector), safely inside camera feed."""
        cam = self._camera_rect()
        return QRect(
            cam.x() + cam.width() - TRIGGER_W - CAMERA_INSET_X,
            cam.y() + CAMERA_INSET_Y,
            TRIGGER_W,
            TRIGGER_H,
        )

    def _task_trigger_rect(self) -> QRect:
        """Task selector button positioned directly below shape selector button."""
        cam = self._camera_rect()
        return QRect(
            cam.x() + cam.width() - TRIGGER_W - CAMERA_INSET_X,
            cam.y() + CAMERA_INSET_Y + TRIGGER_H + 8,
            TRIGGER_W,
            TRIGGER_H,
        )

    def _panel_rect(self) -> QRect:
        """Shape dropdown menu, positioned directly below both buttons."""
        cam = self._camera_rect()
        panel_h = self._panel_total_height()
        return QRect(
            cam.x() + cam.width() - PANEL_W - CAMERA_INSET_X,
            cam.y() + CAMERA_INSET_Y + TRIGGER_H + 8 + TRIGGER_H + 6,
            PANEL_W,
            panel_h,
        )

    def _panel_total_height(self) -> int:
        n = len(ALL_SHAPES)
        return PANEL_PAD * 2 + HEADER_H * 2 + ITEM_H * n + GROUP_SPACING

    def _item_rects(self) -> list[tuple[str, QRect]]:
        pr = self._panel_rect()
        rects = []
        y = pr.top() + PANEL_PAD
        for group_label, shapes in (("2D", SHAPES_2D), ("3D", SHAPES_3D)):
            y += HEADER_H
            for shape in shapes:
                rects.append((shape, QRect(pr.left() + 4, y, PANEL_W - 8, ITEM_H)))
                y += ITEM_H
            y += GROUP_SPACING
        return rects

    def _task_panel_rect(self) -> QRect:
        """Task dropdown menu, positioned directly below the task button."""
        cam = self._camera_rect()
        panel_h = self._task_panel_total_height()
        return QRect(
            cam.x() + cam.width() - PANEL_W - CAMERA_INSET_X,
            cam.y() + CAMERA_INSET_Y + TRIGGER_H + 8 + TRIGGER_H + 6,
            PANEL_W,
            panel_h,
        )

    def _task_panel_total_height(self) -> int:
        n = len(TASK_GENERAL) + len(TASK_3D)
        return PANEL_PAD * 2 + HEADER_H * 2 + ITEM_H * n + GROUP_SPACING

    def _task_item_rects(self) -> list[tuple[str, str, QRect, bool]]:
        """Returns list of (task_id, label, QRect, is_enabled)."""
        pr = self._task_panel_rect()
        rects = []
        y = pr.top() + PANEL_PAD
        active_shape = self.get_active_shape()
        is_3d = active_shape is not None and active_shape.kind in SHAPES_3D

        # General tasks
        y += HEADER_H
        for tid, label in TASK_GENERAL:
            rects.append((tid, label, QRect(pr.left() + 4, y, PANEL_W - 8, ITEM_H), True))
            y += ITEM_H
        y += GROUP_SPACING

        # Dedicated 3D section at the bottom
        y += HEADER_H
        for tid, label in TASK_3D:
            rects.append((tid, label, QRect(pr.left() + 4, y, PANEL_W - 8, ITEM_H), is_3d))
            y += ITEM_H

        return rects

    def _delete_rect(self) -> QRect:
        """Bottom-left delete button, safely inside camera feed."""
        cam = self._camera_rect()
        return QRect(
            cam.x() + CAMERA_INSET_X,
            cam.y() + cam.height() - DELETE_H - CAMERA_INSET_Y,
            DELETE_W,
            DELETE_H,
        )

    # ------------------------------------------------------------------
    # Dwell update helpers
    # ------------------------------------------------------------------

    def _update_trigger(self, tip_px, dt):
        # Do not allow opening shape menu while task menu is open
        if self._task_open:
            self._trigger_dwell.reset()
            self._trigger_frac = 0.0
            return

        inside = tip_px is not None and self._trigger_rect().contains(tip_px)
        if not inside:
            self._trigger_must_exit = False
        if self._trigger_must_exit:
            self._trigger_dwell.reset()
            self._trigger_frac = 0.0
            return

        ev = self._trigger_dwell.update("TRIGGER", dt, inside=inside)
        self._trigger_frac = self._trigger_dwell.fraction if inside else 0.0
        if ev and ev.state in ("ENTER", "HOLD"):
            self._open = not self._open
            self._trigger_dwell.reset()
            self._trigger_frac = 0.0
            self._trigger_must_exit = True
            if self._open:
                # Close task menu if opened
                self._task_open = False
                self._task_trigger_dwell.reset()
                self._task_trigger_frac = 0.0
            else:
                self._item_dwell.reset()
                self._item_frac = 0.0
                self._hovered_item = None

    def _update_items(self, tip_px, dt):
        hovered = None
        if tip_px is not None:
            for name, rect in self._item_rects():
                if rect.contains(tip_px):
                    hovered = name
                    break

        self._hovered_item = hovered
        ev_item = self._item_dwell.update(hovered, dt, inside=hovered is not None)
        self._item_frac = self._item_dwell.fraction if hovered else 0.0
        if ev_item and ev_item.state in ("ENTER", "HOLD"):
            self._selected_shape = hovered
            self._open = False
            self._item_dwell.reset()
            self._item_frac = 0.0
            self._hovered_item = None
            self._trigger_must_exit = True

    def _update_task_trigger(self, tip_px, dt):
        enabled = self.is_task_trigger_enabled()
        if not enabled:
            self._task_trigger_dwell.reset()
            self._task_trigger_frac = 0.0
            self._task_trigger_must_exit = False
            if self._task_open:
                self._task_open = False
                self._task_item_dwell.reset()
                self._task_item_frac = 0.0
                self._hovered_task_item = None
            return

        inside = tip_px is not None and self._task_trigger_rect().contains(tip_px)
        if not inside:
            self._task_trigger_must_exit = False
        if self._task_trigger_must_exit:
            self._task_trigger_dwell.reset()
            self._task_trigger_frac = 0.0
            return

        ev = self._task_trigger_dwell.update("TASK_TRIGGER", dt, inside=inside)
        self._task_trigger_frac = self._task_trigger_dwell.fraction if inside else 0.0
        if ev and ev.state in ("ENTER", "HOLD"):
            self._task_open = not self._task_open
            self._task_trigger_dwell.reset()
            self._task_trigger_frac = 0.0
            self._task_trigger_must_exit = True
            if self._task_open:
                self.task_dropdown_opened = True
            if not self._task_open:
                self._task_item_dwell.reset()
                self._task_item_frac = 0.0
                self._hovered_task_item = None

    def _update_task_items(self, tip_px, dt):
        hovered_id = None
        hovered_label = None
        if tip_px is not None:
            for tid, label, rect, enabled in self._task_item_rects():
                if enabled and rect.contains(tip_px):
                    hovered_id = tid
                    hovered_label = label
                    break

        self._hovered_task_item = hovered_id
        ev = self._task_item_dwell.update(hovered_id, dt, inside=hovered_id is not None)
        self._task_item_frac = self._task_item_dwell.fraction if hovered_id else 0.0
        if ev and ev.state in ("ENTER", "HOLD"):
            active_shape = self.get_active_shape()
            if active_shape is not None:
                if not hasattr(active_shape, "tasks"):
                    active_shape.tasks = set()
                if hovered_id in active_shape.tasks:
                    active_shape.tasks.remove(hovered_id)
                    self.last_task_event = f"Đã tắt {hovered_label} trên {active_shape.kind}."
                else:
                    active_shape.tasks.add(hovered_id)
                    self.last_task_event = f"Đã bật {hovered_label} trên {active_shape.kind}."
                    self.task_started = True

            # Auto-close task dropdown immediately on selection
            self._task_open = False
            self._task_item_dwell.reset()
            self._task_item_frac = 0.0
            self._hovered_task_item = None
            self._task_trigger_must_exit = True

    def _update_delete(self, tip_px, dt, is_dragging_shape: bool = False):
        drect = self._delete_rect()
        inside = tip_px is not None and drect.contains(tip_px)

        if not inside:
            self._delete_dwell.reset()
            if self._delete_state != "IDLE":
                self._delete_state = "IDLE"
            self._delete_fraction = 0.0
            return

        if is_dragging_shape:
            self._delete_dwell.update("DELETE_DRAG", dt, inside=True)
            elapsed = self._delete_dwell.elapsed
            self._delete_fraction = min(1.0, elapsed / DWELL_DELETE_DRAG_S)
            self._delete_state = "DRAG_DELETE"
            if elapsed >= DWELL_DELETE_DRAG_S:
                if self.delete_event != "DRAG_SINGLE":
                    self.delete_event = "DRAG_SINGLE"
                    self._delete_dwell.reset()
                    self._delete_fraction = 0.0
        else:
            self._delete_dwell.update("DELETE_ALL", dt, inside=True)
            elapsed = self._delete_dwell.elapsed
            self._delete_fraction = min(1.0, elapsed / DWELL_DELETE_ALL_S)
            self._delete_state = "CLEAR_ALL"
            if elapsed >= DWELL_DELETE_ALL_S:
                if self.delete_event != "ALL":
                    self.delete_event = "ALL"
                    self._delete_dwell.reset()
                    self._delete_fraction = 0.0

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_trigger(p)
        self._draw_task_trigger(p)
        if self._open:
            self._draw_panel(p)
        elif self._task_open:
            self._draw_task_panel(p)
        self._draw_delete_button(p)
        if self._selected_shape:
            self._draw_selected_badge(p)
        if self._tip_px is not None:
            self._draw_tip_reticle(p)
        p.end()

    def _draw_tip_reticle(self, p: QPainter):
        pos = self._tip_px
        if pos is None:
            return

        on_trigger = (not self._task_open) and self._trigger_rect().contains(pos)
        on_task_trigger = self.is_task_trigger_enabled() and self._task_trigger_rect().contains(pos)
        on_delete = self._delete_rect().contains(pos)
        on_item = False
        if self._open:
            on_item = any(r.contains(pos) for _, r in self._item_rects())
        elif self._task_open:
            on_item = any(r.contains(pos) for _, _, r, en in self._task_item_rects() if en)

        is_hovering_target = on_trigger or on_task_trigger or on_delete or on_item

        if is_hovering_target:
            ring_col = QColor(239, 202, 130, 220)  # #efca82
            fill_col = QColor(239, 202, 130, 90)
            dot_col = QColor(255, 255, 255, 255)
            radius = 12
        else:
            ring_col = QColor(0, 240, 255, 200)
            fill_col = QColor(0, 240, 255, 60)
            dot_col = QColor(255, 255, 255, 220)
            radius = 9

        p.setPen(QPen(ring_col, 2))
        p.setBrush(QBrush(fill_col))
        p.drawEllipse(pos, radius, radius)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(dot_col))
        p.drawEllipse(pos, 3, 3)

        if getattr(self, "_shape_select_frac", 0.0) > 0.001:
            # Draw circular dwell progress arc around the fingertip reticle
            p.setPen(QPen(QColor("#f59e0b"), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            r_arc = 18
            span = int(min(1.0, self._shape_select_frac) * 360 * 16)
            p.drawArc(QRect(pos.x() - r_arc, pos.y() - r_arc, r_arc * 2, r_arc * 2), 90 * 16, -span)

    def _draw_trigger(self, p: QPainter):
        rect = self._trigger_rect()
        is_hovered = self._tip_px is not None and rect.contains(self._tip_px) and not self._task_open

        if self._task_open:
            # Dimmed while task dropdown is open
            p.setBrush(QBrush(QColor("#14202a")))
            p.setPen(QPen(QColor("#1e303d"), 1.5))
            p.drawRoundedRect(rect, 8, 8)
            p.setPen(QPen(QColor("#475569")))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "📐 Chọn hình")
            return

        bg_col = QColor("#223849") if is_hovered else C_TRIGGER
        p.setBrush(QBrush(bg_col))
        border_col = C_ACCENT if (self._open or is_hovered) else C_RAISED
        pen = QPen(border_col, 2)
        p.setPen(pen)
        p.drawRoundedRect(rect, 8, 8)

        p.setPen(QPen(C_ACCENT if (self._open or is_hovered) else C_TEXT))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        label = "📐 Đóng menu  ▲" if self._open else "📐 Chọn hình  ▼"
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        if self._trigger_frac > 0.02:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(C_ACCENT))
            bar_w = round((rect.width() - 8) * self._trigger_frac)
            p.drawRect(QRect(rect.left() + 4, rect.bottom() - PROGRESS_H - 2, bar_w, PROGRESS_H))

    def _draw_task_trigger(self, p: QPainter):
        rect = self._task_trigger_rect()
        enabled = self.is_task_trigger_enabled()
        is_hovered = enabled and self._tip_px is not None and rect.contains(self._tip_px)

        if not enabled:
            p.setBrush(QBrush(QColor("#121d26")))
            p.setPen(QPen(QColor("#1a2b37"), 1.5))
            p.drawRoundedRect(rect, 8, 8)
            p.setPen(QPen(QColor("#475569")))
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            if self._open:
                txt = "Tác vụ: Đang chọn hình..."
            elif not self._frozen_shapes:
                txt = "Tác vụ: Chưa có hình"
            else:
                txt = "Tác vụ: Chạm chọn 1 hình"
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)
            return

        active_shape = self.get_active_shape()
        bg_col = QColor("#223849") if (is_hovered or self._task_open) else C_TRIGGER
        p.setBrush(QBrush(bg_col))
        border_col = C_ACCENT if (self._task_open or is_hovered) else QColor("#28525e")
        pen = QPen(border_col, 2)
        p.setPen(pen)
        p.drawRoundedRect(rect, 8, 8)

        p.setPen(QPen(C_ACCENT if (self._task_open or is_hovered) else C_TEXT))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))

        shape_name = active_shape.kind if active_shape else "Hình"
        n_tasks = len(getattr(active_shape, "tasks", set())) if active_shape else 0
        badge_str = f" ({n_tasks})" if n_tasks > 0 else ""
        if self._task_open:
            txt = f"⚡ Tác vụ ({shape_name})  ▲"
        else:
            txt = f"⚡ Tác vụ: {shape_name}{badge_str}  ▼"
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

        if self._task_trigger_frac > 0.02:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(C_ACCENT))
            bar_w = round((rect.width() - 8) * self._task_trigger_frac)
            p.drawRect(QRect(rect.left() + 4, rect.bottom() - PROGRESS_H - 2, bar_w, PROGRESS_H))

    def _draw_panel(self, p: QPainter):
        pr = self._panel_rect()
        bg = QColor(SURFACE)
        bg.setAlpha(240)
        p.setBrush(QBrush(bg))
        pen = QPen(C_ACCENT, 2)
        p.setPen(pen)
        p.drawRoundedRect(pr, 10, 10)

        item_rects = dict(self._item_rects())
        y = pr.top() + PANEL_PAD
        for group_label, shapes in (("2D", SHAPES_2D), ("3D", SHAPES_3D)):
            header_rect = QRect(pr.left() + PANEL_PAD, y, PANEL_W - PANEL_PAD * 2, HEADER_H)
            p.setPen(QPen(C_MUTED))
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.drawText(header_rect, Qt.AlignmentFlag.AlignVCenter, group_label)
            y += HEADER_H

            for shape in shapes:
                rect = item_rects[shape]
                is_hovered = shape == self._hovered_item
                if is_hovered:
                    p.setBrush(QBrush(C_ITEM_HOVER))
                    p.setPen(QPen(C_ACCENT))
                else:
                    p.setBrush(QBrush(QColor("#1e3241")))
                    p.setPen(Qt.PenStyle.NoPen)
                inner = rect.adjusted(2, 2, -2, -2)
                p.drawRoundedRect(inner, 6, 6)

                p.setPen(QPen(C_ACCENT if is_hovered else C_TEXT))
                p.setFont(QFont("Segoe UI", 13))
                icon_rect = QRect(inner.left() + 8, inner.top(), 28, inner.height())
                p.drawText(icon_rect, Qt.AlignmentFlag.AlignVCenter,
                           SHAPE_ICON.get(shape, "?"))

                p.setFont(QFont("Segoe UI", 11))
                label_rect = QRect(inner.left() + 40, inner.top(),
                                   inner.width() - 44, inner.height())
                p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, shape)

                if is_hovered and self._item_frac > 0.02:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(C_ACCENT))
                    bar_w = round((inner.width() - 8) * self._item_frac)
                    p.drawRect(QRect(inner.left() + 4,
                                     inner.bottom() - PROGRESS_H - 2,
                                     bar_w, PROGRESS_H))

                y += ITEM_H
            y += GROUP_SPACING

    def _draw_task_panel(self, p: QPainter):
        pr = self._task_panel_rect()
        bg = QColor(SURFACE)
        bg.setAlpha(240)
        p.setBrush(QBrush(bg))
        pen = QPen(C_ACCENT, 2)
        p.setPen(pen)
        p.drawRoundedRect(pr, 10, 10)

        active_shape = self.get_active_shape()
        active_tasks = getattr(active_shape, "tasks", set()) if active_shape else set()

        y = pr.top() + PANEL_PAD
        item_tuples = self._task_item_rects()
        item_dict = {tid: (label, rect, en) for tid, label, rect, en in item_tuples}

        # Group 1: TÁC VỤ HÌNH HỌC
        header_rect = QRect(pr.left() + PANEL_PAD, y, PANEL_W - PANEL_PAD * 2, HEADER_H)
        p.setPen(QPen(QColor("#72bfcc")))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(header_rect, Qt.AlignmentFlag.AlignVCenter, "TÁC VỤ HÌNH HỌC")
        y += HEADER_H

        for tid, _ in TASK_GENERAL:
            label, rect, enabled = item_dict[tid]
            is_hovered = tid == self._hovered_task_item
            is_active = tid in active_tasks
            inner = rect.adjusted(2, 2, -2, -2)

            if is_hovered:
                p.setBrush(QBrush(C_ITEM_HOVER))
                p.setPen(QPen(C_ACCENT))
            elif is_active:
                p.setBrush(QBrush(QColor("#1e3a47")))
                p.setPen(QPen(QColor("#34d399"), 1.2))
            else:
                p.setBrush(QBrush(QColor("#1e3241")))
                p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(inner, 6, 6)

            prefix = "✓ " if is_active else "○ "
            txt_col = QColor("#34d399") if is_active else (C_ACCENT if is_hovered else C_TEXT)
            p.setPen(QPen(txt_col))
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold if is_active else QFont.Weight.Normal))
            label_rect = QRect(inner.left() + 10, inner.top(), inner.width() - 14, inner.height())
            p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, f"{prefix}{label}")

            if is_hovered and self._task_item_frac > 0.02:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(C_ACCENT))
                bar_w = round((inner.width() - 8) * self._task_item_frac)
                p.drawRect(QRect(inner.left() + 4, inner.bottom() - PROGRESS_H - 2, bar_w, PROGRESS_H))

            y += ITEM_H
        y += GROUP_SPACING

        # Group 2: KHỐI 3D (CHỈ CHO 3D)
        header_rect = QRect(pr.left() + PANEL_PAD, y, PANEL_W - PANEL_PAD * 2, HEADER_H)
        p.setPen(QPen(QColor("#c084fc")))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(header_rect, Qt.AlignmentFlag.AlignVCenter, "KHỐI 3D")
        y += HEADER_H

        for tid, _ in TASK_3D:
            label, rect, enabled = item_dict[tid]
            is_hovered = enabled and (tid == self._hovered_task_item)
            is_active = tid in active_tasks
            inner = rect.adjusted(2, 2, -2, -2)

            if not enabled:
                p.setBrush(QBrush(QColor("#14202a")))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(inner, 6, 6)
                p.setPen(QPen(QColor("#475569")))
                p.setFont(QFont("Segoe UI", 9))
                label_rect = QRect(inner.left() + 10, inner.top(), inner.width() - 14, inner.height())
                p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, f"🔒 {label} [Chỉ 3D]")
            else:
                if is_hovered:
                    p.setBrush(QBrush(C_ITEM_HOVER))
                    p.setPen(QPen(C_ACCENT))
                elif is_active:
                    p.setBrush(QBrush(QColor("#1e3a47")))
                    p.setPen(QPen(QColor("#34d399"), 1.2))
                else:
                    p.setBrush(QBrush(QColor("#1e3241")))
                    p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(inner, 6, 6)

                prefix = "✓ " if is_active else "○ "
                txt_col = QColor("#34d399") if is_active else (C_ACCENT if is_hovered else C_TEXT)
                p.setPen(QPen(txt_col))
                p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold if is_active else QFont.Weight.Normal))
                label_rect = QRect(inner.left() + 10, inner.top(), inner.width() - 14, inner.height())
                p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, f"{prefix}{label}")

                if is_hovered and self._task_item_frac > 0.02:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(C_ACCENT))
                    bar_w = round((inner.width() - 8) * self._task_item_frac)
                    p.drawRect(QRect(inner.left() + 4, inner.bottom() - PROGRESS_H - 2, bar_w, PROGRESS_H))

            y += ITEM_H

    def _draw_delete_button(self, p: QPainter):
        rect = self._delete_rect()
        state = self._delete_state
        if state == "CLEAR_ALL":
            bg, border = C_DELETE_ALL, C_DELETE_ALL_BORDER
            label = "⚠ Giữ để xóa tất cả"
        elif state == "DRAG_DELETE":
            bg, border = C_DELETE_SINGLE, C_DELETE_SINGLE_BORDER
            label = "🗑 Thả để xóa hình"
        else:
            bg, border = C_DELETE_IDLE, C_RAISED
            label = "🗑 Thùng rác"

        p.setBrush(QBrush(bg))
        pen = QPen(border, 2)
        p.setPen(pen)
        p.drawRoundedRect(rect, 8, 8)

        p.setPen(QPen(C_TEXT))
        p.setFont(QFont("Segoe UI", 11))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        if self._delete_fraction > 0.02:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(border))
            bar_w = round(rect.width() * self._delete_fraction)
            p.drawRect(QRect(rect.left(), rect.bottom() - PROGRESS_H, bar_w, PROGRESS_H))

    def _draw_selected_badge(self, p: QPainter):
        rect = self._trigger_rect()
        badge_rect = QRect(rect.left() - 170, rect.top() + (rect.height() - 32) // 2, 160, 32)
        p.setBrush(QBrush(QColor("#28525e")))
        pen = QPen(C_ACCENT, 1)
        p.setPen(pen)
        p.drawRoundedRect(badge_rect, 6, 6)
        p.setPen(QPen(C_WARNING))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        icon = SHAPE_ICON.get(self._selected_shape, "")
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"{icon} {self._selected_shape}")

    def handle_mouse_press(self, pt: QPoint) -> bool:
        """Handle mouse click on toolbar buttons or dropdowns. Returns True if handled."""
        if not self.isVisible():
            return False

        # Shape selector button
        if self._trigger_rect().contains(pt):
            if not self._task_open:
                self._open = not self._open
                if self._open:
                    self._task_open = False
                self.update()
            return True

        # Task selector button
        if self._task_trigger_rect().contains(pt):
            if self.is_task_trigger_enabled():
                self._task_open = not self._task_open
                if self._task_open:
                    self.task_dropdown_opened = True
                self.update()
            return True

        # Delete button
        if self._delete_rect().contains(pt):
            self.delete_event = "ALL"
            self.update()
            return True

        # Shape panel items
        if self._open:
            for shape, r in self._item_rects():
                if r.contains(pt):
                    self._selected_shape = shape
                    self._open = False
                    self.update()
                    return True
            if self._panel_rect().contains(pt):
                return True

        # Task panel items
        if self._task_open:
            for tid, label, r, enabled in self._task_item_rects():
                if enabled and r.contains(pt):
                    active_shape = self.get_active_shape()
                    if active_shape is not None:
                        if not hasattr(active_shape, "tasks"):
                            active_shape.tasks = set()
                        if tid in active_shape.tasks:
                            active_shape.tasks.remove(tid)
                            self.last_task_event = f"Đã tắt {label} trên {active_shape.kind}."
                        else:
                            active_shape.tasks.add(tid)
                            self.last_task_event = f"Đã bật {label} trên {active_shape.kind}."
                            self.task_started = True
                    self._task_open = False
                    self.update()
                    return True
            if self._task_panel_rect().contains(pt):
                return True

        return False
