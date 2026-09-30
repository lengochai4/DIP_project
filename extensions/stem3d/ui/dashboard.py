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
    map_normalized_point_to_rect,
)
from ..evidence import (
    EvidenceBatch,
    EvidenceCatalog,
    load_evidence_catalog,
)
from .presentation_model import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    LandmarkPresentation,
    PresentationState,
)
from .spatial_panel import (
    InteractionFocus,
    PanelButton,
    SpatialPanelLayout,
    SpatialPanelViewState,
    build_spatial_panel_layout,
)
from .theme import THEME


_ANALYSIS_PIPELINE_LINES = (
    "CAMERA > ROI > HSV ILLUMINATION > ADAPTIVE PREPROCESS",
    "LANDMARKS > TEMPORAL FILTER > GESTURE > INTERACTION STATE > 3D",
)

class LiveDashboard:
    """Render immutable presentation values and a copied BGR camera frame."""

    WINDOW_NAME = "DIP Touchless STEM - Camera / Status"

    def __init__(
        self,
        *,
        reset_action: Callable[[], None] | None = None,
        evidence_catalog: EvidenceCatalog | None = None,
    ) -> None:
        self._reset_action = reset_action
        self._scene_select_action: Callable[[str], None] | None = None
        self._molecule_preset_action: Callable[[str], None] | None = None
        self._mode_action: Callable[[DashboardMode], None] | None = None
        self._control_panel_toggle_action: Callable[[], None] | None = None
        self._spatial_panel_state = SpatialPanelViewState(
            open=False,
            focus=InteractionFocus.SCENE_FOCUS,
        )
        self._control_panel_button = Rect(0, 0, 0, 0)
        self._stop = False
        self._window_open = False
        self._mode = DashboardMode.DEMO
        self._evidence_catalog = (
            load_evidence_catalog()
            if evidence_catalog is None
            else evidence_catalog
        )
        self._evidence_page_index = 0
        self._evidence_previous_button = Rect(0, 0, 0, 0)
        self._evidence_next_button = Rect(0, 0, 0, 0)
        self._last_size = (
            THEME.default_window_width,
            THEME.default_window_height,
        )

    def set_reset_action(
        self,
        reset_action: Callable[[], None],
    ) -> None:
        self._reset_action = reset_action

    def set_scene_select_action(
        self,
        action: Callable[[str], None],
    ) -> None:
        self._scene_select_action = action

    def set_molecule_preset_action(
        self,
        action: Callable[[str], None],
    ) -> None:
        self._molecule_preset_action = action

    def set_mode_action(
        self,
        action: Callable[[DashboardMode], None],
    ) -> None:
        self._mode_action = action

    def set_control_panel_toggle_action(
        self,
        action: Callable[[], None],
    ) -> None:
        self._control_panel_toggle_action = action

    def set_spatial_panel_state(
        self,
        state: SpatialPanelViewState,
    ) -> None:
        self._spatial_panel_state = state

    def set_mode_from_application(
        self,
        mode: DashboardMode,
    ) -> None:
        """Reflect a mode selected through the application controller."""

        self._set_mode_state(mode)

    def spatial_panel_layout(self) -> SpatialPanelLayout:
        width, height = self._window_size()
        return build_spatial_panel_layout(
            width,
            height,
            active_scene_id=self._spatial_panel_state.active_scene_id,
            mode=self._mode,
        )

    @property
    def mode(self) -> DashboardMode:
        return self._mode

    @property
    def evidence_page_index(self) -> int:
        return self._evidence_page_index

    @property
    def spatial_panel_state(self) -> SpatialPanelViewState:
        return self._spatial_panel_state

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
        cv2.setMouseCallback(
            self.WINDOW_NAME,
            self._on_mouse,
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
                self._mode,
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
                "COORDINATE GEOMETRY",
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
                "R  Reset active scene",
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
            self._put_text(
                canvas,
                "After start: 1/2/3 scenes  |  H water  |  C methane",
                layout.pipeline.x + THEME.card_padding,
                layout.pipeline.y + 108,
                scale=THEME.font_small,
                color=THEME.text_secondary,
                max_width=layout.pipeline.width - 2 * THEME.card_padding,
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
            self._draw_footer(
                canvas,
                layout,
                state,
                self._mode,
            )
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
        mode: DashboardMode | None = None,
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
        selected_mode = self._mode if mode is None else mode

        self._draw_header(
            canvas,
            layout,
            application,
            selected_mode,
        )
        if selected_mode is DashboardMode.EVIDENCE:
            self._draw_evidence_mode(canvas, layout)
        else:
            self._draw_camera(
                canvas,
                layout,
                image_bgr,
                presentation,
                selected_mode,
            )
            self._draw_scene(canvas, layout, application)
            if selected_mode is DashboardMode.ANALYSIS:
                self._draw_pipeline(canvas, layout, presentation)
                self._draw_interaction(canvas, layout, presentation)
            else:
                self._draw_demo_status(canvas, layout, presentation)
                self._draw_demo_interaction(canvas, layout, presentation)
        self._draw_footer(
            canvas,
            layout,
            application,
            selected_mode,
        )
        if self._spatial_panel_state.open:
            self._draw_spatial_panel(
                canvas,
                build_spatial_panel_layout(
                    layout.width,
                    layout.height,
                    active_scene_id=(
                        self._spatial_panel_state.active_scene_id
                    ),
                    mode=selected_mode,
                ),
                self._spatial_panel_state,
            )

        return canvas

    def handle_key(self, key: int) -> None:
        if key in {ord("q"), ord("Q"), 27}:
            self._stop = True
        elif key in {ord("r"), ord("R")}:
            if self._reset_action is not None:
                self._reset_action()
        elif key in {ord("a"), ord("A")}:
            self.set_mode(DashboardMode.ANALYSIS)
        elif key in {ord("d"), ord("D")}:
            self.set_mode(DashboardMode.DEMO)
        elif key in {ord("e"), ord("E")}:
            self.set_mode(DashboardMode.EVIDENCE)
        elif self._mode is DashboardMode.EVIDENCE and key == ord("["):
            self._change_evidence_page(-1)
        elif self._mode is DashboardMode.EVIDENCE and key == ord("]"):
            self._change_evidence_page(1)
        elif key in {ord("p"), ord("P")}:
            if self._control_panel_toggle_action is not None:
                self._control_panel_toggle_action()
        elif key in {ord("1"), ord("2"), ord("3")}:
            scene_id = {
                ord("1"): "coordinate-geometry",
                ord("2"): "molecule",
                ord("3"): "orbital-system",
            }[key]
            if self._scene_select_action is not None:
                self._scene_select_action(scene_id)
        elif key in {ord("h"), ord("H"), ord("c"), ord("C")}:
            preset = "H2O" if key in {ord("h"), ord("H")} else "CH4"
            if self._molecule_preset_action is not None:
                self._molecule_preset_action(preset)

    def set_mode(self, mode: DashboardMode) -> None:
        """Apply a keyboard-selected mode through the shared app callback."""

        self._set_mode_state(mode)
        if self._mode_action is not None:
            self._mode_action(mode)

    def _set_mode_state(self, mode: DashboardMode) -> None:
        if (
            mode is DashboardMode.EVIDENCE
            and self._mode is not DashboardMode.EVIDENCE
        ):
            self._evidence_page_index = 0
        self._mode = mode

    def handle_mouse_event(
        self,
        x: int,
        y: int,
        event: int,
    ) -> None:
        """Handle the visible CONTROL SPACE button in this dashboard window."""

        if event != cv2.EVENT_LBUTTONUP:
            return
        if self._mode is DashboardMode.EVIDENCE:
            if self._rect_contains(
                self._evidence_previous_button,
                x,
                y,
            ):
                self._change_evidence_page(-1)
                return
            if self._rect_contains(
                self._evidence_next_button,
                x,
                y,
            ):
                self._change_evidence_page(1)
                return
        if self._control_panel_toggle_action is None:
            return
        rect = self._control_panel_button
        if self._rect_contains(rect, x, y):
            self._control_panel_toggle_action()

    def _on_mouse(
        self,
        event: int,
        x: int,
        y: int,
        flags: int,
        parameter: object,
    ) -> None:
        del flags, parameter
        self.handle_mouse_event(x, y, event)

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

    def _change_evidence_page(self, delta: int) -> None:
        self._evidence_page_index = min(
            max(
                self._evidence_page_index + delta,
                0,
            ),
            len(self._evidence_catalog.pages) - 1,
        )

    @staticmethod
    def _rect_contains(
        rect: Rect,
        x: int,
        y: int,
    ) -> bool:
        return (
            rect.x <= x < rect.right
            and rect.y <= y < rect.bottom
        )

    def _draw_evidence_mode(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
    ) -> None:
        content = Rect(
            THEME.margin,
            layout.header.bottom + THEME.gap,
            layout.width - 2 * THEME.margin,
            layout.footer.y
            - THEME.gap
            - (layout.header.bottom + THEME.gap),
        )
        page_spec = self._evidence_catalog.pages[
            self._evidence_page_index
        ]
        self._put_text(
            canvas,
            page_spec.title,
            content.x + 4,
            content.y + 23,
            scale=THEME.font_section,
            color=THEME.text_primary,
        )
        self._put_text(
            canvas,
            page_spec.subtitle,
            content.x + 4,
            content.y + 46,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=content.width - 8,
        )
        body = Rect(
            content.x,
            content.y + 56,
            content.width,
            content.height - 56,
        )
        if page_spec.key == "OVERVIEW":
            self._draw_evidence_overview(canvas, body)
        elif page_spec.key in {"B NORMAL", "B LOW-LIGHT"}:
            self._draw_evidence_rq1(
                canvas,
                body,
                low_light=page_spec.key == "B LOW-LIGHT",
            )
        elif page_spec.key == "A1 STATIC":
            self._draw_evidence_a1(canvas, body)
        elif page_spec.key == "A2 DYNAMIC":
            self._draw_evidence_a2(canvas, body)
        else:
            self._draw_evidence_rq3(canvas, body)

    def _draw_evidence_overview(
        self,
        canvas: np.ndarray,
        body: Rect,
    ) -> None:
        content = self._evidence_catalog.content
        gap = THEME.gap
        card_width = (body.width - 2 * gap) // 3
        card_height = max(230, body.height - 124)
        cards = tuple(
            Rect(
                body.x + index * (card_width + gap),
                body.y,
                card_width,
                card_height,
            )
            for index in range(3)
        )

        self._draw_card(canvas, cards[0], "RQ1  /  EXPERIMENT B")
        text_x = cards[0].x + THEME.card_padding
        text_width = cards[0].width - 2 * THEME.card_padding
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq1_setup,
            text_x,
            cards[0].y + 55,
            text_width,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq1_result,
            text_x,
            cards[0].y + 115,
            text_width,
            color=THEME.text_secondary,
            max_lines=2,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq1_limitation,
            text_x,
            cards[0].y + 165,
            text_width,
            color=THEME.warning,
            max_lines=3,
        )

        self._draw_card(canvas, cards[1], "RQ2  /  FILTERING")
        a1 = self._evidence_catalog.batch("a1_static")
        counts = _trial_counts(a1)
        self._put_text(
            canvas,
            f"A1 static jitter: {counts}",
            cards[1].x + THEME.card_padding,
            cards[1].y + 55,
            scale=THEME.font_small,
            color=THEME.text_primary,
            max_width=cards[1].width - 2 * THEME.card_padding,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_a1_result,
            cards[1].x + THEME.card_padding,
            cards[1].y + 91,
            cards[1].width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_a1_caution,
            cards[1].x + THEME.card_padding,
            cards[1].y + 145,
            cards[1].width - 2 * THEME.card_padding,
            color=THEME.warning,
            max_lines=2,
        )
        unavailable_y = cards[1].y + 205
        self._pill(
            canvas,
            Rect(
                cards[1].x + THEME.card_padding,
                unavailable_y - 18,
                min(cards[1].width - 2 * THEME.card_padding, 185),
                25,
            ),
            content.overview_a2_status,
            THEME.error,
        )
        self._put_text(
            canvas,
            content.overview_a2_summary.format(
                reason=content.overview_a2_reason
            ),
            cards[1].x + THEME.card_padding,
            unavailable_y + 32,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=cards[1].width - 2 * THEME.card_padding,
        )

        self._draw_card(canvas, cards[2], "RQ3  /  PRACTICAL DEMO")
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq3_interaction,
            cards[2].x + THEME.card_padding,
            cards[2].y + 55,
            cards[2].width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=2,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq3_resets,
            cards[2].x + THEME.card_padding,
            cards[2].y + 98,
            cards[2].width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=2,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq3_false_positive,
            cards[2].x + THEME.card_padding,
            cards[2].y + 142,
            cards[2].width - 2 * THEME.card_padding,
            color=THEME.warning,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.overview_rq3_claim_boundary,
            cards[2].x + THEME.card_padding,
            cards[2].y + 198,
            cards[2].width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=2,
        )

        provenance = Rect(
            body.x,
            cards[0].bottom + gap,
            body.width,
            body.bottom - cards[0].bottom - gap,
        )
        self._draw_card(canvas, provenance, content.provenance_panel_title)
        self._put_text(
            canvas,
            (
                f"Release: {self._evidence_catalog.release_tag}  |  "
                f"commit {self._evidence_catalog.release_commit}"
            ),
            provenance.x + THEME.card_padding,
            provenance.y + 51,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=provenance.width - 2 * THEME.card_padding,
        )
        self._put_text(
            canvas,
            (
                f"Recorded final live demo: "
                f"{self._evidence_catalog.live_demo_run_id}  |  "
                f"{self._evidence_catalog.live_demo_frames} processed frames"
            ),
            provenance.x + THEME.card_padding,
            provenance.y + 74,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=provenance.width - 2 * THEME.card_padding,
        )
        self._put_text(
            canvas,
            (
                "Execution revision "
                f"{self._evidence_catalog.live_demo_revision}  |  "
                "the current G8 presentation session is not G7 evidence"
            ),
            provenance.x + THEME.card_padding,
            provenance.y + 97,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=provenance.width - 2 * THEME.card_padding,
        )

    def _draw_evidence_paragraph(
        self,
        canvas: np.ndarray,
        text: str,
        x: int,
        y: int,
        width: int,
        *,
        color: tuple[int, int, int],
        max_lines: int,
        scale: float = THEME.font_micro,
        line_height: int = 20,
    ) -> None:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and self._text_width(candidate, scale) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and self._text_width(f"{last}...", scale) > width:
                last = last[:-1].rstrip()
            lines[-1] = f"{last}..."
        for line_index, line in enumerate(lines):
            self._put_text(
                canvas,
                line,
                x,
                y + line_index * line_height,
                scale=scale,
                color=color,
                max_width=width,
            )

    def _draw_evidence_rq1(
        self,
        canvas: np.ndarray,
        body: Rect,
        *,
        low_light: bool,
    ) -> None:
        content = self._evidence_catalog.content
        gap = THEME.gap
        left_width = int(round((body.width - gap) * 0.64))
        plot_card = Rect(
            body.x,
            body.y,
            left_width,
            body.height,
        )
        data_card = Rect(
            plot_card.right + gap,
            body.y,
            body.width - left_width - gap,
            body.height,
        )
        batch_key = "b_lowlight" if low_light else "b_normal"
        asset_id = "b_lowlight" if low_light else "b_normal"
        light_label = "LOW-LIGHT" if low_light else "NORMAL-LIGHT"
        self._draw_card(
            canvas,
            plot_card,
            f"EXPERIMENT B  /  {light_label} VALID-HAND-OBSERVATION RATE",
        )
        self._draw_evidence_image(
            canvas,
            asset_id,
            Rect(
                plot_card.x + THEME.card_padding,
                plot_card.y + 36,
                plot_card.width - 2 * THEME.card_padding,
                plot_card.height - 50,
            ),
        )
        self._draw_card(canvas, data_card, "P0 / P1 TRIAL DATA AND LIMITATION")
        batch = self._evidence_catalog.batch(batch_key)
        outcome = (
            content.b_lowlight_result
            if low_light
            else content.b_normal_result
        )
        self._draw_evidence_paragraph(
            canvas,
            outcome,
            data_card.x + THEME.card_padding,
            data_card.y + 52,
            data_card.width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_metrics(
            canvas,
            batch,
            data_card,
            conditions=("P0", "P1"),
            start_y=data_card.y + 124,
            line_height=21,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.b_no_improvement,
            data_card.x + THEME.card_padding,
            data_card.y + 207,
            data_card.width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=2,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.b_clahe_limitation,
            data_card.x + THEME.card_padding,
            data_card.y + 260,
            data_card.width - 2 * THEME.card_padding,
            color=THEME.warning,
            max_lines=4,
        )
        self._draw_batch_provenance(
            canvas,
            batch,
            data_card,
            y=data_card.bottom - 15,
        )

    def _draw_evidence_a1(
        self,
        canvas: np.ndarray,
        body: Rect,
    ) -> None:
        content = self._evidence_catalog.content
        gap = THEME.gap
        left_width = int(round((body.width - gap) * 0.64))
        plot_card = Rect(body.x, body.y, left_width, body.height)
        data_card = Rect(
            plot_card.right + gap,
            body.y,
            body.width - left_width - gap,
            body.height,
        )
        self._draw_card(canvas, plot_card, "A1 RETAINED STATIC JITTER COMPARISON")
        self._draw_evidence_image(
            canvas,
            "a1_static_jitter",
            Rect(
                plot_card.x + THEME.card_padding,
                plot_card.y + 36,
                plot_card.width - 2 * THEME.card_padding,
                plot_card.height - 50,
            ),
        )
        self._draw_card(canvas, data_card, "A1 RETAINED TRIAL DATA")
        batch = self._evidence_catalog.batch("a1_static")
        self._put_text(
            canvas,
            f"Trials: {_trial_counts(batch)}",
            data_card.x + THEME.card_padding,
            data_card.y + 54,
            scale=THEME.font_small,
            color=THEME.text_primary,
            max_width=data_card.width - 2 * THEME.card_padding,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.a1_result,
            data_card.x + THEME.card_padding,
            data_card.y + 85,
            data_card.width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.a1_caution,
            data_card.x + THEME.card_padding,
            data_card.y + 143,
            data_card.width - 2 * THEME.card_padding,
            color=THEME.warning,
            max_lines=3,
        )
        self._draw_evidence_metrics(
            canvas,
            batch,
            data_card,
            conditions=("F0", "F1", "F2"),
            start_y=data_card.y + 218,
            line_height=21,
        )
        self._draw_batch_provenance(
            canvas,
            batch,
            data_card,
            y=data_card.bottom - 15,
        )

    def _draw_evidence_a2(
        self,
        canvas: np.ndarray,
        body: Rect,
    ) -> None:
        content = self._evidence_catalog.content
        gap = THEME.gap
        left_width = int(round((body.width - gap) * 0.64))
        plot_card = Rect(body.x, body.y, left_width, body.height)
        status_card = Rect(
            plot_card.right + gap,
            body.y,
            body.width - left_width - gap,
            body.height,
        )
        self._draw_card(canvas, plot_card, content.a2_figure_title)
        self._draw_evidence_image(
            canvas,
            "a2_unavailable",
            Rect(
                plot_card.x + THEME.card_padding,
                plot_card.y + 36,
                plot_card.width - 2 * THEME.card_padding,
                plot_card.height - 50,
            ),
        )
        self._draw_card(canvas, status_card, content.a2_primary_heading)
        self._pill(
            canvas,
            Rect(
                status_card.x + THEME.card_padding,
                status_card.y + 51,
                min(status_card.width - 2 * THEME.card_padding, 200),
                34,
            ),
            content.a2_status,
            THEME.error,
        )
        self._put_text(
            canvas,
            f"Reason: {content.a2_reason}",
            status_card.x + THEME.card_padding,
            status_card.y + 112,
            scale=THEME.font_small,
            color=THEME.warning,
            max_width=status_card.width - 2 * THEME.card_padding,
        )
        batch = self._evidence_catalog.batch("a2_dynamic")
        self._draw_evidence_paragraph(
            canvas,
            content.a2_summary,
            status_card.x + THEME.card_padding,
            status_card.y + 145,
            status_card.width - 2 * THEME.card_padding,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_metrics(
            canvas,
            batch,
            status_card,
            conditions=("F0", "F1", "F2"),
            start_y=status_card.y + 212,
            line_height=21,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.a2_zero_boundary,
            status_card.x + THEME.card_padding,
            status_card.y + 292,
            status_card.width - 2 * THEME.card_padding,
            color=THEME.warning,
            max_lines=3,
        )
        self._draw_batch_provenance(
            canvas,
            batch,
            status_card,
            y=status_card.bottom - 15,
        )

    def _draw_evidence_rq3(
        self,
        canvas: np.ndarray,
        body: Rect,
    ) -> None:
        content = self._evidence_catalog.content
        gap = THEME.gap
        left_width = int(round((body.width - gap) * 0.42))
        left = Rect(body.x, body.y, left_width, body.height)
        right = Rect(
            body.x + left_width + gap,
            body.y,
            body.width - left_width - gap,
            body.height,
        )
        self._draw_card(canvas, left, "RQ3  /  PRACTICAL TOUCHLESS INTERACTION")
        text_x = left.x + THEME.card_padding
        text_width = left.width - 2 * THEME.card_padding
        self._draw_evidence_paragraph(
            canvas,
            content.rq3_rotation,
            text_x,
            left.y + 58,
            text_width,
            color=THEME.text_secondary,
            max_lines=2,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.rq3_scaling_and_states,
            text_x,
            left.y + 108,
            text_width,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.rq3_false_positive,
            text_x,
            left.y + 174,
            text_width,
            color=THEME.warning,
            max_lines=3,
        )
        self._draw_evidence_paragraph(
            canvas,
            content.rq3_claim_boundary,
            text_x,
            left.y + 242,
            text_width,
            color=THEME.text_secondary,
            max_lines=3,
        )
        self._put_text(
            canvas,
            f"G7 demo run: {self._evidence_catalog.live_demo_run_id}",
            left.x + THEME.card_padding,
            left.bottom - 60,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=left.width - 2 * THEME.card_padding,
        )
        self._put_text(
            canvas,
            f"Execution revision: {self._evidence_catalog.live_demo_revision}",
            left.x + THEME.card_padding,
            left.bottom - 37,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=left.width - 2 * THEME.card_padding,
        )

        self._draw_card(canvas, right, content.dip_title)
        image_rect = Rect(
            right.x + THEME.card_padding,
            right.y + 36,
            right.width - 2 * THEME.card_padding,
            max(120, body.height - 113),
        )
        self._draw_evidence_image(canvas, "dip_visual", image_rect)
        policy = self._evidence_catalog.dip_policy
        policy_text = (
            "visualization policy unavailable"
            if policy is None
            else f"visualization policy={policy}"
        )
        self._put_text(
            canvas,
            (
                f"{policy_text}  |  "
                f"{content.dip_result_boundary}"
            ),
            right.x + THEME.card_padding,
            right.bottom - 25,
            scale=THEME.font_micro,
            color=THEME.warning,
            max_width=right.width - 2 * THEME.card_padding,
        )

    def _draw_evidence_image(
        self,
        canvas: np.ndarray,
        asset_id: str,
        bounds: Rect,
    ) -> bool:
        cv2.rectangle(
            canvas,
            (bounds.x, bounds.y),
            (bounds.right - 1, bounds.bottom - 1),
            THEME.preview_background,
            thickness=-1,
        )
        image = self._evidence_catalog.load_image(asset_id)
        if image is None:
            cv2.rectangle(
                canvas,
                (bounds.x, bounds.y),
                (bounds.right - 1, bounds.bottom - 1),
                THEME.border,
                thickness=1,
                lineType=cv2.LINE_AA,
            )
            self._put_text(
                canvas,
                "Evidence asset unavailable",
                bounds.x + bounds.width // 2,
                bounds.y + bounds.height // 2,
                scale=THEME.font_small,
                color=THEME.warning,
                max_width=bounds.width - 18,
                align="center",
            )
            return False
        target = fit_aspect_rect(
            image.shape[1],
            image.shape[0],
            bounds,
        )
        resized = cv2.resize(
            image,
            (target.width, target.height),
            interpolation=cv2.INTER_AREA,
        )
        canvas[
            target.y : target.bottom,
            target.x : target.right,
        ] = resized
        cv2.rectangle(
            canvas,
            (bounds.x, bounds.y),
            (bounds.right - 1, bounds.bottom - 1),
            THEME.border,
            thickness=1,
            lineType=cv2.LINE_AA,
        )
        return True

    def _draw_evidence_metrics(
        self,
        canvas: np.ndarray,
        batch: EvidenceBatch,
        rect: Rect,
        *,
        conditions: tuple[str, ...],
        start_y: int,
        line_height: int,
    ) -> None:
        if not batch.metrics_available:
            self._put_text(
                canvas,
                "Recorded metric data unavailable",
                rect.x + THEME.card_padding,
                start_y,
                scale=THEME.font_micro,
                color=THEME.warning,
                max_width=rect.width - 2 * THEME.card_padding,
            )
            return
        rows = batch.metric_rows
        if not rows:
            self._put_text(
                canvas,
                "Recorded metric data unavailable",
                rect.x + THEME.card_padding,
                start_y,
                scale=THEME.font_micro,
                color=THEME.warning,
                max_width=rect.width - 2 * THEME.card_padding,
            )
            return
        for row_index, metric_row in enumerate(rows):
            by_condition = {
                metric.condition: metric
                for metric in metric_row.metrics
            }
            values = [by_condition.get(condition) for condition in conditions]
            if any(
                metric is None or not metric.available
                for metric in values
            ):
                reasons = sorted({
                    metric.unavailable_reason
                    for metric in values
                    if metric is not None
                    and not metric.available
                    and metric.unavailable_reason is not None
                })
                reason = (
                    reasons[0]
                    if reasons
                    else "metric_unavailable"
                )
                line = f"{metric_row.trial_id}  UNAVAILABLE  {reason}"
                color = THEME.warning
            else:
                value_parts = [
                    f"{condition} {metric.value_text}"
                    for condition, metric in zip(
                        conditions,
                        values,
                        strict=True,
                    )
                    if metric is not None
                ]
                sample_counts = {
                    metric.sample_count
                    for metric in values
                    if metric is not None
                }
                sample_text = (
                    f"  (n={next(iter(sample_counts))})"
                    if len(sample_counts) == 1
                    and None not in sample_counts
                    else ""
                )
                line = (
                    f"{metric_row.trial_id}  "
                    f"{'  |  '.join(value_parts)}{sample_text}"
                )
                color = THEME.text_secondary
            self._put_text(
                canvas,
                line,
                rect.x + THEME.card_padding,
                start_y + row_index * line_height,
                scale=THEME.font_micro,
                color=color,
                max_width=rect.width - 2 * THEME.card_padding,
            )

    def _draw_batch_provenance(
        self,
        canvas: np.ndarray,
        batch: EvidenceBatch,
        rect: Rect,
        *,
        y: int,
    ) -> None:
        batch_id = batch.batch_id or "batch identity unavailable"
        self._put_text(
            canvas,
            f"BATCH {batch_id}",
            rect.x + THEME.card_padding,
            y,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=rect.width - 2 * THEME.card_padding,
        )
        if batch.analysis_revision is not None:
            self._put_text(
                canvas,
                f"ANALYSIS REVISION {batch.analysis_revision}",
                rect.x + THEME.card_padding,
                y - 17,
                scale=THEME.font_micro,
                color=THEME.text_muted,
                max_width=rect.width - 2 * THEME.card_padding,
            )

    def _draw_evidence_nav_button(
        self,
        canvas: np.ndarray,
        rect: Rect,
        label: str,
        *,
        enabled: bool,
    ) -> None:
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.surface if enabled else THEME.background,
            thickness=-1,
        )
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.accent if enabled else THEME.border,
            thickness=1,
            lineType=cv2.LINE_AA,
        )
        self._put_text(
            canvas,
            label,
            rect.x + rect.width // 2,
            rect.y + 18,
            scale=THEME.font_micro,
            color=THEME.text_secondary if enabled else THEME.text_muted,
            max_width=rect.width - 8,
            align="center",
        )

    def _draw_header(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        application: ApplicationState,
        mode: DashboardMode,
        *,
        subtitle: str | None = None,
    ) -> None:
        rect = layout.header
        self._panel(canvas, rect, raised=True)
        is_evidence = mode is DashboardMode.EVIDENCE
        title = (
            "DIP TOUCHLESS STEM"
            if not is_evidence
            else "DIP TOUCHLESS STEM  /  FROZEN G7 EVIDENCE"
        )
        self._put_text(
            canvas,
            title,
            rect.x + THEME.card_padding,
            rect.y + 25,
            scale=THEME.font_title,
            color=THEME.text_primary,
        )
        descriptor = subtitle or (
            "LIVE INTERACTION"
            if not is_evidence
            else "READ-ONLY RESULTS  |  G8 PRESENTATION SESSION IS SEPARATE"
        )
        self._put_text(
            canvas,
            descriptor,
            rect.x + THEME.card_padding,
            rect.y + 45,
            scale=THEME.font_small,
            color=THEME.text_muted,
        )
        mode_text = mode.value
        mode_width = self._text_width(
            mode_text,
            THEME.font_small,
        )
        self._pill(
            canvas,
            Rect(
                rect.right - mode_width - 62,
                rect.y + 17,
                mode_width + 48,
                25,
            ),
            mode_text,
            THEME.accent,
        )
        phase_color = (
            THEME.accent
            if is_evidence
            else THEME.error
            if application.phase is ApplicationPhase.ERROR
            else THEME.success
            if application.phase is ApplicationPhase.RUNNING
            else THEME.accent
        )
        status_text = (
            "G8 VIEWER"
            if is_evidence
            else application.phase.value
        )
        status_width = self._text_width(status_text, THEME.font_small)
        self._pill(
            canvas,
            Rect(
                rect.right - status_width - mode_width - 98,
                rect.y + 17,
                status_width + 24,
                25,
            ),
            status_text,
            phase_color,
        )
        if is_evidence:
            self._put_text(
                canvas,
                (
                    f"RELEASE {self._evidence_catalog.release_tag}"
                    f"  @  {self._evidence_catalog.release_commit[:12]}"
                ),
                rect.right - 320,
                rect.y + 49,
                scale=THEME.font_small,
                color=THEME.text_secondary,
                max_width=300,
                align="right",
            )
        else:
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
        mode: DashboardMode,
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

        if mode is DashboardMode.ANALYSIS:
            self._draw_landmarks(
                canvas,
                target,
                image_width=image_w,
                image_height=image_h,
                raw_landmarks=state.raw_landmarks,
                filtered_landmarks=state.filtered_landmarks,
            )

        pointer = state.interaction.pointer_xy
        if state.interaction.valid and pointer is not None:
            mapped_pointer = map_normalized_point_to_rect(
                pointer,
                target,
                mirror_x=False,
                mirror_y=False,
            )
            if mapped_pointer is not None:
                cv2.circle(
                    canvas,
                    mapped_pointer,
                    8,
                    THEME.tracking_valid,
                    2,
                    cv2.LINE_AA,
                )

        cv2.rectangle(
            canvas,
            (x1, y1),
            (x2 - 1, y2 - 1),
            THEME.border,
            1,
            cv2.LINE_AA,
        )
        if mode is DashboardMode.ANALYSIS:
            self._draw_landmark_legend(
                canvas,
                target,
                state,
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
        self._put_text(
            canvas,
            "1 Geometry  |  2 Molecule  |  3 Orbit  |  H/C molecule",
            layout.scene.x + THEME.card_padding,
            layout.scene.y + 98,
            scale=THEME.font_micro,
            color=THEME.text_muted,
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
        flow_width = layout.pipeline.width - 2 * THEME.card_padding
        for line_index, line in enumerate(
            _ANALYSIS_PIPELINE_LINES
        ):
            self._put_text(
                canvas,
                line,
                x,
                layout.pipeline.y
                + THEME.analysis_flow_y
                + line_index * 12,
                scale=THEME.font_micro,
                color=THEME.accent,
                max_width=flow_width,
            )
        y = layout.pipeline.y + THEME.analysis_rows_y
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
            else "not applied"
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

    def _draw_demo_status(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        state: PresentationState,
    ) -> None:
        self._draw_card(canvas, layout.pipeline, "TRACKING")
        x = layout.pipeline.x + THEME.card_padding
        y = layout.pipeline.y + THEME.card_title_height + 22
        width = layout.pipeline.width - 2 * THEME.card_padding
        self._status_row(
            canvas,
            x,
            y,
            width,
            "HAND",
            state.tracking_status,
            positive=state.tracking_status in {"VALID", "REACQUIRED"},
        )
        y += THEME.row_height + 7
        self._put_text(
            canvas,
            "Move your index fingertip to rotate the cube.",
            x,
            y,
            scale=THEME.font_body,
            color=THEME.text_secondary,
            max_width=width,
        )

    def _draw_demo_interaction(
        self,
        canvas: np.ndarray,
        layout: DashboardLayout,
        state: PresentationState,
    ) -> None:
        self._draw_card(canvas, layout.interaction, "TOUCHLESS INPUT")
        interaction = state.interaction
        x = layout.interaction.x + THEME.card_padding
        y = layout.interaction.y + THEME.card_title_height + 4
        width = layout.interaction.width - 2 * THEME.card_padding
        pinch = (
            "n/a"
            if interaction.pinch_active is None
            else "ON"
            if interaction.pinch_active
            else "OFF"
        )
        self._value_row(
            canvas,
            x,
            y,
            width,
            "INTERACTION",
            "READY" if interaction.valid else "NEUTRAL",
        )
        self._value_row(
            canvas,
            x,
            y + THEME.row_height,
            width,
            "PINCH",
            pinch,
        )
        y += THEME.line_height + 5
        self._put_text(
            canvas,
            "Pinch and vary the distance to scale it.",
            x,
            y,
            scale=THEME.font_body,
            color=THEME.text_secondary,
            max_width=width,
        )

    def _draw_landmarks(
        self,
        canvas: np.ndarray,
        target: Rect,
        *,
        image_width: int,
        image_height: int,
        raw_landmarks: tuple[LandmarkPresentation, ...],
        filtered_landmarks: tuple[LandmarkPresentation, ...],
    ) -> None:
        for landmark in raw_landmarks:
            point = _frame_point_to_preview(
                landmark,
                target,
                image_width=image_width,
                image_height=image_height,
            )
            if point is not None:
                cv2.circle(
                    canvas,
                    point,
                    4,
                    THEME.landmark_raw,
                    1,
                    cv2.LINE_AA,
                )
        for landmark in filtered_landmarks:
            point = _frame_point_to_preview(
                landmark,
                target,
                image_width=image_width,
                image_height=image_height,
            )
            if point is not None:
                cv2.circle(
                    canvas,
                    point,
                    2,
                    THEME.landmark_filtered,
                    thickness=-1,
                    lineType=cv2.LINE_AA,
                )

    def _draw_landmark_legend(
        self,
        canvas: np.ndarray,
        target: Rect,
        state: PresentationState,
    ) -> None:
        legend_height = 22
        y1 = target.bottom - legend_height
        cv2.rectangle(
            canvas,
            (target.x, y1),
            (target.right - 1, target.bottom - 1),
            THEME.preview_background,
            thickness=-1,
        )
        self._put_text(
            canvas,
            f"RAW {len(state.raw_landmarks)}",
            target.x + 18,
            target.bottom - 7,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
        )
        cv2.circle(
            canvas,
            (target.x + 10, target.bottom - 11),
            3,
            THEME.landmark_raw,
            1,
            cv2.LINE_AA,
        )
        self._put_text(
            canvas,
            f"FILTERED {len(state.filtered_landmarks)}",
            target.x + 85,
            target.bottom - 7,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
        )
        cv2.circle(
            canvas,
            (target.x + 77, target.bottom - 11),
            3,
            THEME.landmark_filtered,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        self._put_text(
            canvas,
            "POINTER",
            target.x + 205,
            target.bottom - 7,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
        )
        self._put_text(
            canvas,
            "FRAME_NORMALIZED / UNMIRRORED",
            target.right - 8,
            target.bottom - 7,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=190,
            align="right",
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
        application: ApplicationState,
        mode: DashboardMode,
    ) -> None:
        rect = layout.footer
        self._panel(canvas, rect, raised=True)
        toggle_width = 180
        toggle_height = 30
        self._control_panel_button = Rect(
            rect.right - THEME.card_padding - toggle_width,
            rect.y + 10,
            toggle_width,
            toggle_height,
        )
        self._draw_control_panel_toggle(
            canvas,
            self._control_panel_button,
        )
        y = rect.y + 18
        if mode is DashboardMode.EVIDENCE:
            self._put_text(
                canvas,
                "D DEMO  |  A ANALYSIS  |  E EVIDENCE  |  [ ] PAGE  |  R RESET  |  Q STOP  |  P PANEL",
                rect.x + THEME.card_padding,
                y,
                scale=THEME.font_small,
                color=THEME.text_secondary,
                max_width=(
                    self._control_panel_button.x
                    - rect.x
                    - 2 * THEME.card_padding
                ),
            )
            button_y = rect.y + 38
            center_x = rect.x + rect.width // 2
            self._evidence_previous_button = Rect(
                center_x - 150,
                button_y,
                105,
                27,
            )
            self._evidence_next_button = Rect(
                center_x + 45,
                button_y,
                105,
                27,
            )
            self._draw_evidence_nav_button(
                canvas,
                self._evidence_previous_button,
                "< PREVIOUS",
                enabled=self._evidence_page_index > 0,
            )
            self._draw_evidence_nav_button(
                canvas,
                self._evidence_next_button,
                "NEXT >",
                enabled=(
                    self._evidence_page_index
                    < len(self._evidence_catalog.pages) - 1
                ),
            )
            page_name = self._evidence_catalog.pages[
                self._evidence_page_index
            ].key
            self._put_text(
                canvas,
                (
                    f"{page_name}  |  PAGE "
                    f"{self._evidence_page_index + 1}/"
                    f"{len(self._evidence_catalog.pages)}"
                ),
                center_x,
                rect.bottom - 5,
                scale=THEME.font_micro,
                color=THEME.text_muted,
                align="center",
            )
            return

        self._put_text(
            canvas,
            "A ANALYSIS  |  D DEMO  |  R RESET  |  Q/ESC STOP  |  P PANEL",
            rect.x + THEME.card_padding,
            y,
            scale=THEME.font_small,
            color=THEME.text_secondary,
            max_width=(
                self._control_panel_button.x
                - rect.x
                - 2 * THEME.card_padding
            ),
        )
        if mode is DashboardMode.DEMO:
            self._put_text(
                canvas,
                "CAMERA PREVIEW  +  COORDINATE CUBE",
                rect.x + THEME.card_padding,
                rect.y + 43,
                scale=THEME.font_micro,
                color=THEME.text_muted,
            )
            self._put_text(
                canvas,
                "Press A to inspect the DIP pipeline and run identity.",
                rect.x + THEME.card_padding,
                rect.y + 64,
                scale=THEME.font_micro,
                color=THEME.text_muted,
            )
            return

        identity = application.runtime_identity
        spec = _display_value(
            None if identity is None else identity.spec_version
        )
        revision = _display_value(
            None if identity is None else identity.code_revision
        )
        schema = _display_value(
            None if identity is None else identity.log_schema_version
        )
        python = _display_value(
            None if identity is None else identity.python_version
        )
        dependencies = (
            "n/a"
            if identity is None
            else " ".join(
                f"{name}={version or 'n/a'}"
                for name, version in identity.dependency_versions
            )
        )
        self._put_text(
            canvas,
            (
                f"SPEC {spec}  |  GIT HEAD {revision}  |  SCHEMA {schema}  "
                f"|  PY {python}  |  DEPS {dependencies}"
            ),
            rect.x + THEME.card_padding,
            rect.y + 40,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=rect.width - 2 * THEME.card_padding,
        )
        config_hash = _display_value(
            None if identity is None else identity.config_sha256
        )
        model = (
            "n/a"
            if identity is None
            else (
                f"{identity.model_filename or 'n/a'} "
                f"SHA256 {_display_value(identity.model_sha256)}"
            )
        )
        provider = (
            "n/a"
            if identity is None
            else _display_value(identity.provider_name)
        )
        camera = (
            "n/a"
            if identity is None
            else (
                f"{identity.camera_backend or 'n/a'} "
                f"{identity.camera_requested or 'n/a'}"
            )
        )
        self._put_text(
            canvas,
            f"CONFIG SHA256 {config_hash}  |  PROVIDER {provider}  |  MODEL {model}  |  CAMERA {camera}",
            rect.x + THEME.card_padding,
            rect.y + 62,
            scale=THEME.font_micro,
            color=THEME.text_muted,
            max_width=(
                self._control_panel_button.x
                - rect.x
                - 2 * THEME.card_padding
            ),
        )

    def _draw_control_panel_toggle(
        self,
        canvas: np.ndarray,
        rect: Rect,
    ) -> None:
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.surface,
            thickness=-1,
        )
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            THEME.accent,
            thickness=1,
            lineType=cv2.LINE_AA,
        )
        label = (
            "CLOSE PANEL  [P]"
            if self._spatial_panel_state.open
            else "CONTROL SPACE  [P]"
        )
        self._put_text(
            canvas,
            label,
            rect.x + rect.width // 2,
            rect.y + 20,
            scale=THEME.font_small,
            color=THEME.text_primary,
            max_width=rect.width - 12,
            align="center",
        )

    def _draw_spatial_panel(
        self,
        canvas: np.ndarray,
        panel: SpatialPanelLayout,
        state: SpatialPanelViewState,
    ) -> None:
        rect = panel.viewport
        self._panel(canvas, rect, raised=True)
        self._put_text(
            canvas,
            "CONTROL SPACE",
            rect.x + THEME.card_padding,
            rect.y + 29,
            scale=THEME.font_section,
            color=THEME.text_primary,
        )
        self._put_text(
            canvas,
            "Move pointer; pinch once to select",
            rect.x + THEME.card_padding,
            rect.y + 52,
            scale=THEME.font_micro,
            color=THEME.text_secondary,
            max_width=rect.width - 2 * THEME.card_padding,
        )
        self._put_text(
            canvas,
            "SCENES",
            rect.x + THEME.card_padding,
            rect.y + 69,
            scale=THEME.font_micro,
            color=THEME.text_muted,
        )
        self._put_text(
            canvas,
            "MODE",
            rect.x + THEME.card_padding,
            rect.y + 242,
            scale=THEME.font_micro,
            color=THEME.text_muted,
        )
        for button in panel.buttons:
            self._draw_spatial_button(
                canvas,
                button,
                hovered=state.hovered_button == button.button_id,
                pressed=(
                    state.pressed_button == button.button_id
                    or state.activated_button == button.button_id
                ),
            )
        if state.cursor_xy is not None:
            cv2.circle(
                canvas,
                state.cursor_xy,
                9,
                THEME.accent,
                2,
                cv2.LINE_AA,
            )
            cv2.circle(
                canvas,
                state.cursor_xy,
                2,
                THEME.text_primary,
                -1,
                cv2.LINE_AA,
            )

    def _draw_spatial_button(
        self,
        canvas: np.ndarray,
        button: PanelButton,
        *,
        hovered: bool,
        pressed: bool,
    ) -> None:
        rect = button.rect
        fill = (
            THEME.surface
            if button.enabled
            else THEME.background
        )
        border = THEME.border
        text = (
            THEME.text_secondary
            if button.enabled
            else THEME.text_muted
        )
        if button.selected and button.enabled:
            border = THEME.success
        if hovered and button.enabled:
            fill = THEME.surface_raised
            border = THEME.accent
        if pressed and button.enabled:
            fill = THEME.accent
            border = THEME.accent
            text = THEME.background
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            fill,
            thickness=-1,
        )
        cv2.rectangle(
            canvas,
            (rect.x, rect.y),
            (rect.right - 1, rect.bottom - 1),
            border,
            thickness=2 if hovered or pressed else 1,
            lineType=cv2.LINE_AA,
        )
        self._put_text(
            canvas,
            button.label,
            rect.x + rect.width // 2,
            rect.y + rect.height // 2 + 5,
            scale=THEME.font_small,
            color=text,
            max_width=rect.width - 12,
            align="center",
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
                text = (
                    text[:-2] + "…"
                    if len(text) > 1
                    else ""
                )
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


def _frame_point_to_preview(
    landmark: LandmarkPresentation,
    target: Rect,
    *,
    image_width: int,
    image_height: int,
) -> tuple[int, int] | None:
    """Project full-frame normalized x/y into the unmirrored preview."""

    if landmark.coordinate_space != "FRAME_NORMALIZED":
        return None
    if not (
        0.0 <= landmark.x <= 1.0
        and 0.0 <= landmark.y <= 1.0
    ):
        return None
    if image_width <= 0 or image_height <= 0:
        return None
    return map_normalized_point_to_rect(
        (landmark.x, landmark.y),
        target,
        mirror_x=False,
        mirror_y=False,
    )


def _display_value(value: str | None) -> str:
    return value if value else "n/a"


def _trial_counts(batch: EvidenceBatch) -> str:
    recorded = batch.recorded_trial_count
    evaluable = batch.evaluable_trial_count
    if recorded is None or evaluable is None:
        return "recorded/evaluable counts unavailable"
    return f"{recorded} recorded / {evaluable} evaluable"
