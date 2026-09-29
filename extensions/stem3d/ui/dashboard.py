"""OpenCV dashboard shell for live camera and interaction status."""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np

from .layout import (
    DashboardLayout,
    Rect,
    calculate_dashboard_layout,
    fit_aspect_rect,
)
from .presentation_model import (
    ApplicationPhase,
    ApplicationState,
    PresentationState,
)
from .theme import THEME


class LiveDashboard:
    """Render immutable presentation values and a copied BGR camera frame."""

    WINDOW_NAME = "DIP Touchless STEM - Camera / Status"

    def __init__(
        self,
        *,
        reset_action: Callable[[], None] | None = None,
    ) -> None:
        self._reset_action = reset_action
        self._stop = False
        self._window_open = False
        self._last_size = (
            THEME.default_window_width,
            THEME.default_window_height,
        )

    def set_reset_action(
        self,
        reset_action: Callable[[], None],
    ) -> None:
        self._reset_action = reset_action

    def open(self) -> None:
        if self._window_open:
            return

        cv2.namedWindow(
            self.WINDOW_NAME,
            cv2.WINDOW_NORMAL,
        )
        cv2.resizeWindow(
            self.WINDOW_NAME,
            *self._last_size,
        )
        self._window_open = True

    def wait_for_start(
        self,
        state: ApplicationState,
    ) -> bool:
        """Show a start screen and wait for start or cancellation."""

        self.open()

        while not self._stop:
            width, height = self._window_size()
            layout = calculate_dashboard_layout(
                width,
                height,
            )
            canvas = np.full(
                (layout.height, layout.width, 3),
                THEME.background,
                dtype=np.uint8,
            )
            self._draw_header(
                canvas,
                layout,
                state,
                subtitle="TOUCHLESS STEM WORKSPACE",
            )
            self._draw_card(
                canvas,
                layout.vision,
                "READY TO START",
            )
            center_x = (
                layout.vision.x
                + layout.vision.width // 2
            )
            self._put_text(
                canvas,
                "Live camera and hand tracking",
                center_x,
                layout.vision.y + 150,
                scale=THEME.font_title,
                color=THEME.text_primary,
                align="center",
            )
            self._put_text(
                canvas,
                "The camera/status dashboard and 3D cube open in separate windows.",
                center_x,
                layout.vision.y + 190,
                color=THEME.text_secondary,
                align="center",
                max_width=layout.vision.width - 60,
            )
            self._put_text(
                canvas,
                "Press S, ENTER, or SPACE to begin",
                center_x,
                layout.vision.y + 250,
                scale=THEME.font_section,
                color=THEME.accent,
                align="center",
            )
            self._draw_card(
                canvas,
                layout.scene,
                "ACTIVE SCENE",
            )
            self._put_text(
                canvas,
                "COORDINATE CUBE",
                layout.scene.x + THEME.card_padding,
                layout.scene.y + 55,
                color=THEME.text_primary,
            )
            self._draw_card(
                canvas,
                layout.pipeline,
                "CONTROLS",
            )
            self._put_text(
                canvas,
                "R  Reset cube transform",
                layout.pipeline.x + THEME.card_padding,
                layout.pipeline.y + 56,
                color=THEME.text_secondary,
            )
            self._put_text(
                canvas,
                "Q / ESC  Stop application",
                layout.pipeline.x + THEME.card_padding,
                layout.pipeline.y + 82,
                color=THEME.text_secondary,
            )
            self._draw_card(
                canvas,
                layout.interaction,
                "INTERACTION",
            )
            self._put_text(
                canvas,
                "Move index fingertip to rotate",
                layout.interaction.x + THEME.card_padding,
                layout.interaction.y + 55,
                scale=THEME.font_small,
                color=THEME.text_secondary,
            )
            self._put_text(
                canvas,
                "Pinch and vary distance to scale",
                layout.interaction.x + THEME.card_padding,
                layout.interaction.y + 78,
                scale=THEME.font_small,
                color=THEME.text_secondary,
            )
            self._draw_footer(canvas, layout)
            cv2.imshow(self.WINDOW_NAME, canvas)

            key = cv2.waitKey(30) & 0xFF
            if key in {ord("s"), ord("S"), 13, 32}:
                return True
            self.handle_key(key)
            if self._window_closed():
                self._stop = True

        return False

    def consume(
        self,
        image_bgr: np.ndarray,
        presentation: PresentationState,
        application: ApplicationState,
    ) -> None:
        """Draw one runtime callback without mutating its image buffer."""

        if not self._window_open:
            self.open()
        self._window_size()
        dashboard = self.build_dashboard(
            image_bgr,
            presentation,
            application,
        )
        cv2.imshow(self.WINDOW_NAME, dashboard)
        key = cv2.waitKey(1) & 0xFF
        self.handle_key(key)
        if self._window_closed():
            self._stop = True

    def build_dashboard(
        self,
        image_bgr: np.ndarray,
        presentation: PresentationState,
        application: ApplicationState,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> np.ndarray:
        """Compose a complete dashboard at a requested responsive size."""

        if (
            image_bgr.ndim != 3
            or image_bgr.shape[2] != 3
            or image_bgr.dtype != np.uint8
        ):
            raise ValueError(
                "dashboard requires an HxWx3 uint8 BGR image"
            )
        if presentation.run_id != application.run_id:
            raise ValueError(
                "presentation and application run IDs must match"
            )

        image_height, image_width = image_bgr.shape[:2]
        requested_width = (
            self._last_size[0]
            if width is None
            else width
        )
        requested_height = (
            self._last_size[1]
            if height is None
            else height
        )
        layout = calculate_dashboard_layout(
            requested_width,
            requested_height,
        )
        canvas = np.full(
            (layout.height, layout.width, 3),
            THEME.background,
            dtype=np.uint8,
        )

        self._draw_header(canvas, layout, application)
        self._draw_camera(
            canvas,
            layout,
            image_bgr,
            presentation,
        )
        self._draw_scene(canvas, layout, application)
        self._draw_pipeline(canvas, layout, presentation)
        self._draw_interaction(canvas, layout, presentation)
        self._draw_footer(canvas, layout)

        return canvas

    def handle_key(self, key: int) -> None:
        if key in {ord("q"), ord("Q"), 27}:
            self._stop = True
        elif key in {ord("r"), ord("R")}:
            if self._reset_action is not None:
                self._reset_action()

    def stop_requested(self) -> bool:
        return self._stop

    def close(self) -> None:
        if not self._window_open:
            return
        try:
            cv2.destroyWindow(self.WINDOW_NAME)
        except cv2.error:
            pass
        self._window_open = False

    def _window_size(self) -> tuple[int, int]:
        if not self._window_open:
            return self._last_size
        try:
            _x, _y, width, height = cv2.getWindowImageRect(
                self.WINDOW_NAME
            )
        except cv2.error:
            return self._last_size
        if width > 0 and height > 0:
            self._last_size = (width, height)
        return self._last_size

    def _window_closed(self) -> bool:
        if not self._window_open:
            return False
        try:
            return (
                cv2.getWindowProperty(
                    self.WINDOW_NAME,
                    cv2.WND_PROP_VISIBLE,
                )
                < 1.0
            )
        except cv2.error:
            return True

    def _draw_header(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        application: ApplicationState,
        *,
        subtitle: str | None = None,
    ) -> None:
        rect = layout.header
        self._panel(canvas, rect, raised=True)
        title = "DIP TOUCHLESS STEM"
        self._put_text(
            canvas,
            title,
            rect.x + THEME.card_padding,
            rect.y + 25,
            scale=THEME.font_title,
            color=THEME.text_primary,
        )
        descriptor = subtitle or "LIVE INTERACTION"
        self._put_text(
            canvas,
            descriptor,
            rect.x + THEME.card_padding,
            rect.y + 45,
            scale=THEME.font_small,
            color=THEME.text_muted,
        )
        phase_color = (
            THEME.error
            if application.phase is ApplicationPhase.ERROR
            else THEME.success
            if application.phase is ApplicationPhase.RUNNING
            else THEME.accent
        )
        status_text = application.phase.value
        status_width = self._text_width(status_text, THEME.font_small)
        self._pill(
            canvas,
            Rect(
                rect.right - status_width - 38,
                rect.y + 17,
                status_width + 24,
                25,
            ),
            status_text,
            phase_color,
        )
        self._put_text(
            canvas,
            f"RUN  {application.run_id}",
            rect.right - 270,
            rect.y + 49,
            scale=THEME.font_small,
            color=THEME.text_secondary,
            max_width=250,
            align="right",
        )

    def _draw_camera(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        image_bgr: np.ndarray,
        state: PresentationState,
    ) -> None:
        self._draw_card(canvas, layout.vision, "CAMERA VIEW")
        image_h, image_w = image_bgr.shape[:2]
        target = fit_aspect_rect(
            image_w,
            image_h,
            layout.vision_image,
        )
        preview = cv2.resize(
            image_bgr.copy(),
            (target.width, target.height),
            interpolation=(
                cv2.INTER_AREA
                if target.width < image_w
                else cv2.INTER_LINEAR
            ),
        )
        x1, y1 = target.x, target.y
        x2, y2 = target.right, target.bottom
        canvas[y1:y2, x1:x2] = preview

        if state.roi is not None:
            rx, ry, rw, rh = state.roi.bounds_xywh
            sx = target.width / image_w
            sy = target.height / image_h
            p1 = (
                x1 + round(rx * sx),
                y1 + round(ry * sy),
            )
            p2 = (
                x1 + round((rx + rw) * sx) - 1,
                y1 + round((ry + rh) * sy) - 1,
            )
            cv2.rectangle(
                canvas,
                p1,
                p2,
                THEME.accent,
                2,
                cv2.LINE_AA,
            )

        pointer = state.interaction.pointer_xy
        if pointer is not None:
            px = x1 + round(pointer[0] * max(target.width - 1, 0))
            py = y1 + round(pointer[1] * max(target.height - 1, 0))
            px = max(x1, min(px, x2 - 1))
            py = max(y1, min(py, y2 - 1))
            color = (
                THEME.tracking_valid
                if state.interaction.valid
                else THEME.tracking_neutral
            )
            cv2.circle(canvas, (px, py), 8, color, 2, cv2.LINE_AA)

        cv2.rectangle(
            canvas,
            (x1, y1),
            (x2 - 1, y2 - 1),
            THEME.border,
            1,
            cv2.LINE_AA,
        )

    def _draw_scene(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        application: ApplicationState,
    ) -> None:
        self._draw_card(canvas, layout.scene, "ACTIVE SCENE")
        self._put_text(
            canvas,
            application.active_scene.upper(),
            layout.scene.x + THEME.card_padding,
            layout.scene.y + 54,
            scale=THEME.font_section,
            color=THEME.text_primary,
            max_width=layout.scene.width - 2 * THEME.card_padding,
        )
        self._put_text(
            canvas,
            "Index fingertip rotates  |  Pinch scales",
            layout.scene.x + THEME.card_padding,
            layout.scene.y + 76,
            scale=THEME.font_small,
            color=THEME.text_secondary,
            max_width=layout.scene.width - 2 * THEME.card_padding,
        )

    def _draw_pipeline(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        state: PresentationState,
    ) -> None:
        self._draw_card(canvas, layout.pipeline, "PIPELINE STATUS")
        x = layout.pipeline.x + THEME.card_padding
        y = layout.pipeline.y + THEME.card_title_height + 3
        width = layout.pipeline.width - 2 * THEME.card_padding
        roi = state.roi
        light = state.illumination
        diagnostics = state.filter

        self._status_row(
            canvas,
            x,
            y,
            width,
            "TRACKING",
            state.tracking_status,
            positive=state.tracking_status in {"VALID", "REACQUIRED"},
        )
        y += THEME.row_height
        roi_text = (
            "n/a"
            if roi is None
            else (
                f"{roi.state}  "
                f"{roi.bounds_xywh[0]},{roi.bounds_xywh[1]}  "
                f"{roi.bounds_xywh[2]}x{roi.bounds_xywh[3]}"
            )
        )
        self._value_row(canvas, x, y, width, "ROI", roi_text)
        y += THEME.row_height
        light_text = (
            "n/a"
            if light is None
            else (
                f"{light.state}  |  mean V {light.mean_v:.1f}  "
                f"|  range {light.robust_range_v:.1f}"
            )
        )
        self._value_row(canvas, x, y, width, "LIGHT", light_text)
        y += THEME.row_height
        enhancement = (
            "n/a"
            if light is None
            else "active"
            if light.enhancement_active
            else "inactive"
        )
        self._value_row(canvas, x, y, width, "CLAHE", enhancement)
        y += THEME.row_height
        filter_text = (
            f"{diagnostics.mode}  |  dt {self._fmt(diagnostics.dt_s)}  "
            f"| speed {self._fmt(diagnostics.speed)}  "
            f"| beta {self._fmt(diagnostics.beta)}  "
            f"| cutoff {self._fmt(diagnostics.cutoff_hz)} Hz"
        )
        self._value_row(canvas, x, y, width, "FILTER", filter_text)
        y += THEME.row_height
        self._value_row(
            canvas,
            x,
            y,
            width,
            "COMPUTE",
            f"{diagnostics.compute_total_ms:.2f} ms  |  frame {state.frame_id}",
        )

    def _draw_interaction(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        state: PresentationState,
    ) -> None:
        self._draw_card(canvas, layout.interaction, "INTERACTION")
        interaction = state.interaction
        x = layout.interaction.x + THEME.card_padding
        y = layout.interaction.y + THEME.card_title_height + 3
        width = layout.interaction.width - 2 * THEME.card_padding
        self._status_row(
            canvas,
            x,
            y,
            width,
            "STATE",
            "VALID" if interaction.valid else "NEUTRAL",
            positive=interaction.valid,
        )
        y += THEME.row_height
        pointer = (
            "n/a"
            if interaction.pointer_xy is None
            else (
                f"{interaction.pointer_xy[0]:.3f}, "
                f"{interaction.pointer_xy[1]:.3f}"
            )
        )
        self._value_row(canvas, x, y, width, "POINTER", pointer)
        y += THEME.row_height
        pinch = (
            "n/a"
            if interaction.pinch_active is None
            else (
                f"{'ON' if interaction.pinch_active else 'OFF'}  "
                f"| ratio {self._fmt(interaction.pinch_ratio)}"
            )
        )
        self._value_row(canvas, x, y, width, "PINCH", pinch)
        y += THEME.row_height
        rotation = (
            "n/a"
            if interaction.rotation_delta is None
            else (
                f"{interaction.rotation_delta[0]:+.3f}, "
                f"{interaction.rotation_delta[1]:+.3f}"
            )
        )
        scale = self._fmt(interaction.scale_delta)
        self._value_row(
            canvas,
            x,
            y,
            width,
            "ROT / SCALE",
            f"{rotation}  |  {scale}",
        )

    def _draw_footer(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
    ) -> None:
        rect = layout.footer
        self._panel(canvas, rect, raised=True)
        y = rect.y + 30
        self._put_text(
            canvas,
            "R  RESET CUBE",
            rect.x + THEME.card_padding,
            y,
            scale=THEME.font_small,
            color=THEME.text_secondary,
        )
        self._put_text(
            canvas,
            "Q / ESC  STOP",
            rect.x + 175,
            y,
            scale=THEME.font_small,
            color=THEME.text_secondary,
        )
        self._put_text(
            canvas,
            "3D window: ESC or close to stop",
            rect.right - THEME.card_padding,
            y,
            scale=THEME.font_small,
            color=THEME.text_muted,
            max_width=290,
            align="right",
        )

    @classmethod
    def _draw_card(
        cls,
        canvas: np.ndarray,
        rect: Rect,
        title: str,
    ) -> None:
        cls._panel(canvas, rect)
        cls._put_text(
            canvas,
            title,
            rect.x + THEME.card_padding,
            rect.y + 20,
            scale=THEME.font_small,
            color=THEME.text_muted,
        )
        cv2.line(
            canvas,
            (rect.x + THEME.card_padding, rect.y + THEME.card_title_height),
            (rect.right - THEME.card_padding, rect.y + THEME.card_title_height),
            THEME.border,
            1,
            cv2.LINE_AA,
        )

    @staticmethod
    def _panel(
        canvas: np.ndarray,
        rect: Rect,
        *,
        raised: bool = False,
    ) -> None:
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.surface_raised if raised else THEME.surface,
            thickness=-1,
        )
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.border,
            thickness=THEME.border_width,
            lineType=cv2.LINE_AA,
        )

    @classmethod
    def _value_row(
        cls,
        canvas: np.ndarray,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
    ) -> None:
        label_width = 86
        cls._put_text(
            canvas,
            label,
            x,
            y,
            scale=THEME.font_small,
            color=THEME.text_muted,
            max_width=label_width - 8,
        )
        cls._put_text(
            canvas,
            value,
            x + label_width,
            y,
            scale=THEME.font_small,
            color=THEME.text_secondary,
            max_width=width - label_width,
        )

    @classmethod
    def _status_row(
        cls,
        canvas: np.ndarray,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
        *,
        positive: bool,
    ) -> None:
        cls._put_text(
            canvas,
            label,
            x,
            y,
            scale=THEME.font_small,
            color=THEME.text_muted,
            max_width=86,
        )
        color = THEME.success if positive else THEME.warning
        cls._pill(
            canvas,
            Rect(x + 86, y - 15, min(width - 86, 105), 19),
            value,
            color,
            small=True,
        )

    @classmethod
    def _pill(
        cls,
        canvas: np.ndarray,
        rect: Rect,
        text: str,
        color: tuple[int, int, int],
        *,
        small: bool = False,
    ) -> None:
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            color,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        cls._put_text(
            canvas,
            text,
            rect.x + 7,
            rect.y + rect.height - (5 if small else 7),
            scale=THEME.font_small,
            color=THEME.background,
            max_width=rect.width - 14,
        )

    @staticmethod
    def _text_width(text: str, scale: float) -> int:
        (width, _height), _baseline = cv2.getTextSize(
            text,
            THEME.font_face,
            scale,
            THEME.font_weight,
        )
        return width

    @classmethod
    def _put_text(
        cls,
        image: np.ndarray,
        text: str,
        x: int,
        y: int,
        *,
        scale: float = THEME.font_body,
        color: tuple[int, int, int] = THEME.text_primary,
        max_width: int | None = None,
        align: str = "left",
    ) -> None:
        if max_width is not None and max_width > 0:
            while text and cls._text_width(text, scale) > max_width:
                text = text[:-2] + "…"
        text_width = cls._text_width(text, scale)
        if align == "center":
            x -= text_width // 2
        elif align == "right":
            x -= text_width
        cv2.putText(
            image,
            text,
            (x, y),
            THEME.font_face,
            scale,
            color,
            THEME.font_weight,
            cv2.LINE_AA,
        )

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.3f}"
