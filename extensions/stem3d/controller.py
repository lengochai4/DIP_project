"""Application lifecycle and callback orchestration for the STEM demo."""

from __future__ import annotations

from dataclasses import replace

from dip_touchless.core import (
    FramePacket,
    InteractionState,
    TrackingFrame,
)

from .application import RendererFailure, Stem3DExtension
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


class DashboardFailure(RuntimeError):
    """Identify an application-dashboard presentation failure."""

    component = "dashboard"


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
        self._interaction_available = False
        self._dashboard.set_reset_action(self.reset)
        self._dashboard.set_scene_select_action(self.select_scene)
        self._dashboard.set_molecule_preset_action(
            self.select_molecule_preset
        )
        self._dashboard.set_mode_action(self.select_mode)
        self._dashboard.set_control_panel_toggle_action(
            self.toggle_control_panel
        )
        handle_key = getattr(self._dashboard, "handle_key", None)
        if callable(handle_key):
            self._extension.set_keyboard_action(
                lambda character: handle_key(ord(character))
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
        self._set_phase(
            ApplicationPhase.STARTING,
            status_message="Initializing 3D renderer",
        )
        try:
            self._extension.open()
            self._extension_open = True
        except Exception as exc:
            self.fail(exc, component="renderer")
            raise
        self._state = replace(
            self._state,
            renderer_available=True,
            status_message=(
                "Renderer ready; initializing hand model and camera"
            ),
        )
        self._publish_application_state()
        scene = self._extension.active_scene
        if scene is not None:
            self._set_active_scene(scene.title)
        self._sync_spatial_panel_state()

    def report_startup_status(self, message: str) -> None:
        """Publish a presentation-only startup step without a time estimate."""

        if self._state.phase is not ApplicationPhase.STARTING:
            return
        self._state = replace(
            self._state,
            status_message=message,
        )
        self._publish_application_state()

    def consume_interaction(
        self,
        state: InteractionState,
    ) -> None:
        if self._state.phase in {
            ApplicationPhase.STARTING,
            ApplicationPhase.RUNNING,
        }:
            if self._state.phase is ApplicationPhase.STARTING:
                self._state = replace(
                    self._state,
                    phase=ApplicationPhase.RUNNING,
                    camera_available=True,
                    provider_available=True,
                    renderer_available=True,
                )
                self._publish_application_state()
            self._interaction_available = state.interaction_valid
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
        if self._state.phase not in {
            ApplicationPhase.STARTING,
            ApplicationPhase.RUNNING,
        }:
            return
        presentation = build_presentation_state(
            packet,
            tracking_frame,
            interaction_state,
        )
        self._latest_presentation = presentation
        self._interaction_available = presentation.interaction.valid
        tracking_status = presentation.tracking_status
        self._state = replace(
            self._state,
            phase=ApplicationPhase.RUNNING,
            camera_available=True,
            provider_available=True,
            renderer_available=True,
            status_message=_tracking_status_message(
                tracking_status
            ),
        )
        self._sync_spatial_panel_state()
        try:
            self._dashboard.consume(
                packet.image,
                presentation,
                self._state,
            )
        except RendererFailure:
            # The integrated window host identifies GL failures separately
            # from dashboard pixel composition; preserve that error identity.
            raise
        except Exception as exc:
            raise DashboardFailure(
                f"Dashboard could not display the current frame: {exc}"
            ) from exc

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

    def fail(
        self,
        error: BaseException,
        *,
        component: str | None = None,
    ) -> None:
        component = component or getattr(
            error,
            "component",
            "runtime",
        )
        self._interaction_available = False
        if self._interaction_router.is_open:
            self._interaction_router.close_panel()
        updates: dict[str, object] = {
            "phase": ApplicationPhase.ERROR,
            "status_message": _failure_status_message(component),
            "failure_component": component,
            "error_message": str(error),
        }
        if component == "camera":
            updates["camera_available"] = False
        elif component == "model/provider":
            updates["provider_available"] = False
        elif component == "renderer":
            updates["renderer_available"] = False
        self._state = replace(self._state, **updates)
        self._latest_presentation = None
        self._sync_spatial_panel_state()
        self._publish_application_state()

    def wait_for_failure_dismiss(self) -> None:
        wait_for_dismiss = getattr(
            self._dashboard,
            "wait_for_failure_dismiss",
            None,
        )
        if callable(wait_for_dismiss):
            wait_for_dismiss(self._state)

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
        cleanup_error: Exception | None = None
        try:
            if self._extension_open:
                self._extension.close()
        except Exception as exc:
            cleanup_error = exc
        finally:
            self._extension_open = False

        if cleanup_error is not None and not failed:
            self.fail(
                cleanup_error,
                component=getattr(
                    cleanup_error,
                    "component",
                    "runtime",
                ),
            )
        elif cleanup_error is None and not failed:
            # Present STOPPED while the dashboard window is still open, then
            # close it. Publishing after close would reopen the window.
            self._set_phase(
                ApplicationPhase.STOPPED,
                status_message="Application stopped cleanly",
            )

        try:
            self._dashboard.close()
        except Exception as exc:
            if cleanup_error is None:
                cleanup_error = exc
                if not failed:
                    self._state = replace(
                        self._state,
                        phase=ApplicationPhase.ERROR,
                        status_message="Dashboard shutdown failed",
                        failure_component="dashboard",
                        error_message=str(exc),
                    )
        if cleanup_error is not None:
            raise cleanup_error

    def _set_phase(
        self,
        phase: ApplicationPhase,
        *,
        status_message: str | None = None,
    ) -> None:
        self._state = replace(
            self._state,
            phase=phase,
            status_message=(
                status_message
                if status_message is not None
                else self._state.status_message
            ),
        )
        self._publish_application_state()

    def _set_active_scene(self, title: str) -> None:
        self._state = replace(
            self._state,
            active_scene=title,
        )
        self._publish_application_state()

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
                interaction_available=self._interaction_available,
            )
        )

    def _publish_application_state(self) -> None:
        show_state = getattr(
            self._dashboard,
            "show_application_state",
            None,
        )
        if callable(show_state):
            try:
                show_state(self._state)
            except Exception:
                # Keep lifecycle cleanup and the original component error
                # usable even when the dashboard itself cannot render.
                pass


def _tracking_status_message(status: str) -> str:
    return {
        "VALID": "Camera and hand model ready; hand tracked",
        "NO_HAND": "Camera ready; waiting for a hand",
        "TEMPORARY_LOSS": "Tracking temporarily lost",
        "REACQUIRED": "Hand reacquired; interaction is rearming",
        "INVALID": "Hand observation is invalid",
    }.get(status, f"Tracking status: {status}")


def _failure_status_message(component: str) -> str:
    return {
        "camera": "Camera unavailable",
        "model/provider": "Hand model/provider unavailable",
        "renderer": "3D renderer unavailable",
        "dashboard": "Dashboard unavailable",
    }.get(component, "Application runtime error")
