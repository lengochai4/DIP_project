"""Application lifecycle and callback orchestration for the STEM demo."""

from __future__ import annotations

from dip_touchless.core import (
    FramePacket,
    InteractionState,
    TrackingFrame,
)

from .application import Stem3DExtension
from .ui.dashboard import LiveDashboard
from .ui.presentation_model import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    PresentationState,
    RuntimeIdentityPresentation,
    build_presentation_state,
)
from .ui.spatial_panel import (
    InteractionRouter,
)


class Stem3DApplicationController:
    """Coordinate app lifecycle and route public runtime callback values."""

    def __init__(
        self,
        *,
        run_id: str,
        extension: Stem3DExtension,
        dashboard: LiveDashboard,
        runtime_identity: RuntimeIdentityPresentation | None = None,
    ) -> None:
        self._extension = extension
        self._dashboard = dashboard
        self._state = ApplicationState(
            run_id=run_id,
            phase=ApplicationPhase.READY,
            runtime_identity=runtime_identity,
        )
        self._extension_open = False
        self._closed = False
        self._latest_presentation: PresentationState | None = None
        self._interaction_router = InteractionRouter()
        self._dashboard.set_reset_action(self.reset)
        self._dashboard.set_scene_select_action(self.select_scene)
        self._dashboard.set_molecule_preset_action(
            self.select_molecule_preset
        )
        self._dashboard.set_mode_action(self.select_mode)
        self._dashboard.set_control_panel_toggle_action(
            self.toggle_control_panel
        )
        self._sync_spatial_panel_state()

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def latest_presentation(self) -> PresentationState | None:
        return self._latest_presentation

    def wait_for_start(self) -> bool:
        if self._closed:
            return False
        started = self._dashboard.wait_for_start(self._state)
        if not started:
            self._set_phase(ApplicationPhase.STOPPING)
        return started

    def start(self) -> None:
        if self._closed:
            raise RuntimeError("application has already closed")
        if self._state.phase is not ApplicationPhase.READY:
            raise RuntimeError(
                f"application cannot start from {self._state.phase.value}"
            )
        self._set_phase(ApplicationPhase.STARTING)
        try:
            self._extension.open()
            self._extension_open = True
        except Exception as exc:
            self.fail(exc)
            raise
        scene = self._extension.active_scene
        if scene is not None:
            self._set_active_scene(scene.title)
        self._set_phase(ApplicationPhase.RUNNING)
        self._sync_spatial_panel_state()

    def consume_interaction(
        self,
        state: InteractionState,
    ) -> None:
        if self._state.phase is ApplicationPhase.RUNNING:
            panel_layout = (
                self._dashboard.spatial_panel_layout()
                if self._interaction_router.is_open
                else None
            )
            route = self._interaction_router.route(
                state,
                panel_layout,
            )
            if route.action is not None:
                self._dispatch_panel_action(route.action)
            if route.forward_to_scene:
                self._extension.consume(state)
            self._sync_spatial_panel_state()

    def consume_presentation(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ) -> None:
        if self._state.phase is not ApplicationPhase.RUNNING:
            return
        presentation = build_presentation_state(
            packet,
            tracking_frame,
            interaction_state,
        )
        self._latest_presentation = presentation
        self._state = ApplicationState(
            run_id=self._state.run_id,
            phase=self._state.phase,
            active_scene=self._state.active_scene,
            camera_available=True,
            error_message=self._state.error_message,
            runtime_identity=self._state.runtime_identity,
        )
        self._dashboard.consume(
            packet.image,
            presentation,
            self._state,
        )

    def reset(self) -> None:
        if self._state.phase is ApplicationPhase.RUNNING:
            self._extension.reset()
            scene = self._extension.active_scene
            if scene is not None:
                self._set_active_scene(scene.title)
            if self._interaction_router.is_open:
                self._interaction_router.reset_after_action()
                self._sync_spatial_panel_state()

    def select_scene(self, scene_id: str) -> None:
        if self._state.phase is not ApplicationPhase.RUNNING:
            return
        scene = self._extension.activate_scene(scene_id)
        self._set_active_scene(scene.title)
        if self._interaction_router.is_open:
            self._interaction_router.reset_after_action()
            self._sync_spatial_panel_state()

    def select_mode(
        self,
        mode: DashboardMode,
    ) -> None:
        if self._state.phase is not ApplicationPhase.RUNNING:
            return
        self._dashboard.set_mode_from_application(mode)
        if self._interaction_router.is_open:
            self._interaction_router.reset_after_action()
        self._sync_spatial_panel_state()

    def toggle_control_panel(self) -> None:
        if self._state.phase is not ApplicationPhase.RUNNING:
            return
        self._interaction_router.toggle()
        self._sync_spatial_panel_state()

    def select_molecule_preset(self, preset_key: str) -> None:
        if self._state.phase is not ApplicationPhase.RUNNING:
            return
        scene = self._extension.active_scene
        select_preset = getattr(scene, "select_preset", None)
        if not callable(select_preset):
            return
        select_preset(preset_key)
        scene = self._extension.refresh_active_scene()
        self._set_active_scene(scene.title)
        if self._interaction_router.is_open:
            self._interaction_router.reset_after_action()
            self._sync_spatial_panel_state()

    def stop_requested(self) -> bool:
        if self._dashboard.stop_requested():
            if self._state.phase not in {
                ApplicationPhase.ERROR,
                ApplicationPhase.STOPPED,
            }:
                self._set_phase(ApplicationPhase.STOPPING)
            return True
        if self._extension_open and self._extension.close_requested():
            if self._state.phase not in {
                ApplicationPhase.ERROR,
                ApplicationPhase.STOPPED,
            }:
                self._set_phase(ApplicationPhase.STOPPING)
            return True
        return False

    def fail(self, error: BaseException) -> None:
        self._state = ApplicationState(
            run_id=self._state.run_id,
            phase=ApplicationPhase.ERROR,
            active_scene=self._state.active_scene,
            camera_available=self._state.camera_available,
            error_message=str(error),
            runtime_identity=self._state.runtime_identity,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._interaction_router.is_open:
            self._interaction_router.close_panel()
            self._sync_spatial_panel_state()
        failed = self._state.phase is ApplicationPhase.ERROR
        if not failed:
            self._set_phase(ApplicationPhase.STOPPING)
        try:
            self._dashboard.close()
        finally:
            try:
                if self._extension_open:
                    self._extension.close()
            finally:
                if not failed:
                    self._set_phase(ApplicationPhase.STOPPED)

    def _set_phase(self, phase: ApplicationPhase) -> None:
        self._state = ApplicationState(
            run_id=self._state.run_id,
            phase=phase,
            active_scene=self._state.active_scene,
            camera_available=self._state.camera_available,
            error_message=self._state.error_message,
            runtime_identity=self._state.runtime_identity,
        )

    def _set_active_scene(self, title: str) -> None:
        self._state = ApplicationState(
            run_id=self._state.run_id,
            phase=self._state.phase,
            active_scene=title,
            camera_available=self._state.camera_available,
            error_message=self._state.error_message,
            runtime_identity=self._state.runtime_identity,
        )

    def _dispatch_panel_action(
        self,
        action: str,
    ) -> None:
        if action.startswith("scene:"):
            self.select_scene(action.removeprefix("scene:"))
        elif action.startswith("mode:"):
            self.select_mode(
                DashboardMode(action.removeprefix("mode:"))
            )
        elif action == "reset":
            self.reset()
        elif action == "close":
            self._interaction_router.close_panel()
            self._sync_spatial_panel_state()
        else:
            raise ValueError(f"unknown spatial-panel action: {action}")

        if self._interaction_router.is_open and action != "close":
            self._interaction_router.reset_after_action()
            self._sync_spatial_panel_state()

    def _sync_spatial_panel_state(self) -> None:
        scene_id = self._extension.active_scene_id
        self._dashboard.set_spatial_panel_state(
            self._interaction_router.view_state(
                active_scene_id=scene_id,
                mode=self._dashboard.mode,
            )
        )
