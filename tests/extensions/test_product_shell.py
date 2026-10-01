"""Product-shell regressions without requiring a camera or graphics context."""

from dataclasses import replace
import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from dip_touchless.core import InteractionState

from extensions.stem3d.shell_renderer import ApplicationShellRenderer, shell_pixels
from extensions.stem3d.application import RendererFailure
from extensions.stem3d.ui import (
    ApplicationPhase, ApplicationState, DashboardMode, THEME,
    build_presentation_state, InteractionFocus, SpatialPanelViewState,
    InteractionRouter,
)
from extensions.stem3d.ui.icons import ICON_NAMES, icon_mask
from extensions.stem3d.ui.layout import Rect
from extensions.stem3d.ui.shell import ProductDashboard, MODE_LABELS, build_drawer_layout
from extensions.stem3d.ui.shell_layout import calculate_shell_layout


class FakeHost:
    opened = False
    window_size = (1280, 720)

    def set_pointer_consumer(self, consumer):
        self.pointer_consumer = consumer

    def set_key_consumer(self, consumer):
        self.key_consumer = consumer

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def close_requested(self):
        return False

    def present_shell(self, *args):
        self.presented = args


@pytest.fixture
def sample():
    helpers = runpy.run_path(str(Path(__file__).with_name("test_live_demo_presentation.py")))
    packet = helpers["_packet"]()
    state = build_presentation_state(packet, helpers["_tracking_frame"](), helpers["_interaction"]())
    return packet.image, state, ApplicationState("g8-demo-test", ApplicationPhase.RUNNING)


@pytest.mark.parametrize("size", [(1024,640),(1280,720),(1440,900),(1600,900),(1920,1080)])
@pytest.mark.parametrize("mode", list(DashboardMode))
def test_shell_layout_is_bounded_and_modes_are_distinct(size, mode):
    layout = calculate_shell_layout(*size, mode)
    for rect in (layout.header,layout.sidebar,layout.content,layout.footer,layout.drawer,
                 layout.stem,layout.vision,layout.pipeline,layout.diagnostics):
        if rect is not None:
            assert rect.width > 0 and rect.height > 0
            assert 0 <= rect.x < rect.right <= layout.width
            assert 0 <= rect.y < rect.bottom <= layout.height
    if mode is DashboardMode.DEMO:
        assert .70 <= layout.stem.width/layout.content.width <= .90
        assert layout.pipeline is None
    elif mode is DashboardMode.ANALYSIS:
        assert layout.pipeline.bottom < layout.diagnostics.y
        assert layout.vision.width > THEME.shell_vision_width
    else:
        assert layout.stem is layout.vision is layout.pipeline is None


def test_workspace_is_only_a_label_for_existing_mode():
    assert MODE_LABELS[DashboardMode.DEMO] == "Workspace"
    assert [value.value for value in DashboardMode] == ["DEMO","ANALYSIS","EVIDENCE"]


def test_outline_icons_are_cached_and_immutable():
    for name in ICON_NAMES:
        mask=icon_mask(name,20)
        assert mask is icon_mask(name,20)
        assert mask.shape == (20,20) and mask.any() and not mask.flags.writeable
    with pytest.raises(ValueError,match="unknown icon"):
        icon_mask("not-an-icon",20)


def test_alpha_viewport_and_overlay_copy_preserve_input():
    image=np.full((20,30,3),(7,15,23),np.uint8)
    pixels=shell_pixels(image,Rect(5,5,15,10),(Rect(10,8,5,5),))
    assert pixels[5,5,3] == 0
    assert pixels[9,12,3] == 255
    assert pixels[0,0].tolist() == [7,15,23,255]
    assert np.array_equal(image,pixels[:,:,:3])
    pixels[0,0,0]=99
    assert image[0,0,0] == 7


@pytest.mark.parametrize("mode", list(DashboardMode))
def test_shell_renders_with_no_native_window_and_no_input_mutation(sample, mode):
    image,state,app=sample
    host=FakeHost()
    dashboard=ProductDashboard(window_host=host)
    dashboard.set_mode(mode)
    before=image.copy()
    surface=dashboard.build_surface(image,state,app)
    assert surface.canvas.shape == (720,1280,3)
    assert np.array_equal(image,before)
    assert not host.opened
    assert (surface.viewport is None) == (mode is DashboardMode.EVIDENCE)


def test_help_is_modal_and_evidence_tabs_are_clickable(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard.build_surface(*sample)
    rect=dashboard._targets["page:4"]
    dashboard.handle_pointer(rect.x+5,rect.y+5,True)
    assert dashboard.evidence_page_index == 4
    dashboard.handle_key(ord("?"))
    surface=dashboard.build_surface(*sample)
    assert tuple(dashboard._targets) == ("help","details")
    assert len(surface.overlays) == 1
    dashboard.handle_key(ord("?"))
    dashboard.build_surface(*sample)
    assert "page:4" in dashboard._targets


def test_drawer_disabled_actions_and_geometry():
    panel=build_drawer_layout(1024,640,interaction_available=False)
    assert panel.viewport.width == THEME.shell_drawer_width
    for button in panel.buttons:
        assert not button.enabled
        assert panel.hit_test((button.rect.x+2,button.rect.y+2)) is None
        assert button.rect.bottom <= panel.viewport.bottom


def test_shutdown_does_not_reopen_context_or_leave_targets(sample):
    host=FakeHost()
    dashboard=ProductDashboard(window_host=host)
    dashboard.open()
    dashboard.consume(*sample)
    assert len(host.presented) == 3
    dashboard.close()
    assert not host.opened and not dashboard._targets
    assert dashboard.show_application_state(ApplicationState("g8",ApplicationPhase.STOPPED)) is False


@pytest.mark.parametrize("phase", list(ApplicationPhase))
def test_lifecycle_screens_gate_processing_actions(phase):
    dashboard=ProductDashboard(window_host=FakeHost())
    app=ApplicationState("g8",phase,failure_component="camera",error_message="raw traceback secret")
    screen=dashboard.build_application_state_screen(app,width=1024,height=640)
    assert screen.shape == (640,1024,3)
    if phase is not ApplicationPhase.RUNNING:
        assert "reset" not in dashboard._targets
        assert not any(key.startswith("scene:") for key in dashboard._targets)
    assert ("start" in dashboard._targets) == (phase is ApplicationPhase.READY)


def test_provenance_preserves_recorded_metrics_and_is_modal(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard._evidence_page_index=3
    dashboard._provenance_open=True
    observed=[]
    original=dashboard._text
    def capture(canvas,text,*args,**kwargs):
        observed.append(text)
        return original(canvas,text,*args,**kwargs)
    dashboard._text=capture
    dashboard.build_surface(*sample)
    assert tuple(dashboard._targets) == ("provenance",)
    assert any("Release revision: f454c6b" in text for text in observed)
    assert any(text.startswith("Batch:") for text in observed)
    assert any("F0:" in text and "n=" in text for text in observed)


def test_missing_asset_is_resource_error_not_a2_result(sample, monkeypatch):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard._evidence_page_index=4
    observed=[]
    original=dashboard._paragraph
    def capture(canvas,text,*args,**kwargs):
        observed.append(text)
        return original(canvas,text,*args,**kwargs)
    dashboard._paragraph=capture
    monkeypatch.setattr(type(dashboard._evidence_catalog),"load_image",lambda self,key:None)
    dashboard.build_surface(*sample)
    assert any("missing or unsupported" in text for text in observed)
    assert any("No numeric outcome" in text for text in observed)


def test_drawer_cannot_click_through_to_evidence_tabs(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard.set_spatial_panel_state(SpatialPanelViewState(
        open=True,focus=InteractionFocus.UI_FOCUS,interaction_available=False))
    dashboard.build_surface(*sample)
    assert "provenance" not in dashboard._targets
    assert "close" not in dashboard._targets


def test_scaled_evidence_is_reused_and_does_not_mutate_sources(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard._evidence_page_index=3
    dashboard.build_surface(*sample)
    cached=dict(dashboard._scaled_evidence)
    assert cached
    dashboard.build_surface(*sample)
    assert all(dashboard._scaled_evidence[key] is value for key,value in cached.items())
    assert all(not value.flags.writeable for value in cached.values())


def test_render_failure_is_identified_and_context_released(sample):
    host=FakeHost()
    dashboard=ProductDashboard(window_host=host)
    dashboard.open()
    def fail(*args):
        raise RuntimeError("GL context lost")
    host.present_shell=fail
    with pytest.raises(RendererFailure,match="Application renderer failed"):
        dashboard.consume(*sample)
    assert not host.opened and dashboard._fallback


def test_help_closes_touchless_drawer_focus_before_display(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    calls=[]
    dashboard.set_control_panel_toggle_action(lambda:calls.append("close"))
    dashboard.set_spatial_panel_state(SpatialPanelViewState(
        open=True,focus=InteractionFocus.UI_FOCUS,interaction_available=True))
    dashboard.handle_key(ord("?"))
    assert calls == ["close"] and dashboard._help_open


def test_keyboard_start_and_exit_share_the_window_event_seam():
    host=FakeHost()
    dashboard=ProductDashboard(window_host=host)
    dashboard.build_application_state_screen(ApplicationState("g8",ApplicationPhase.READY))
    host.key_consumer("\r")
    assert dashboard._start_requested
    host.key_consumer("q")
    assert dashboard.stop_requested()


def test_all_pipeline_stage_labels_fit_the_minimum_size(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.ANALYSIS)
    labels=[]
    original=dashboard._text
    stages={"Camera","ROI","Illumination","CLAHE","Landmark Tracking",
            "Temporal Filter","Gesture","InteractionState"}
    def capture(canvas,text,*args,**kwargs):
        if text in stages:
            labels.append(text)
            assert dashboard._text_width(text,kwargs["scale"]) <= kwargs["width"]
        return original(canvas,text,*args,**kwargs)
    dashboard._text=capture
    dashboard.build_surface(*sample,width=1024,height=640)
    assert set(labels) == stages


def test_session_identity_is_secondary_and_modal(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard._help_open=True
    dashboard.build_surface(*sample)
    rect=dashboard._targets["details"]
    dashboard.handle_pointer(rect.x+5,rect.y+5,True)
    dashboard.build_surface(*sample)
    assert dashboard._provenance_open and not dashboard._help_open
    assert tuple(dashboard._targets) == ("provenance",)


def test_sdl_resize_and_pointer_use_explicit_canvas_coordinates():
    renderer=ApplicationShellRenderer(width=1280,height=720,target_fps=30)
    renderer._opened=True
    renderer._canvas_size=(1024,640)
    events=[SimpleNamespace(type=3),SimpleNamespace(type=5,pos=(320,180))]
    renderer._pygame=SimpleNamespace(
        QUIT=1,VIDEORESIZE=2,WINDOWSIZECHANGED=3,WINDOWRESIZED=4,
        MOUSEMOTION=5,MOUSEBUTTONUP=6,KEYDOWN=7,
        event=SimpleNamespace(get=lambda:events),
        display=SimpleNamespace(get_window_size=lambda:(640,360)))
    observed=[]
    renderer.set_pointer_consumer(lambda x,y,clicked:observed.append((x,y,clicked)))
    assert renderer.close_requested() is False
    assert renderer.window_size == (640,360)
    assert observed == [(512,320,False)]


def test_theme_contains_the_complete_shell_token_groups():
    for name in ("surface_elevated","surface_overlay","divider","accent_hover",
                 "accent_selected","disabled","control_hover","control_pressed",
                 "spacing_xs","spacing_sm","spacing_md","spacing_lg","spacing_xl",
                 "radius_sm","radius_md","radius_lg","font_heading","font_caption",
                 "icon_sm","icon_md","icon_lg"):
        assert getattr(THEME,name) is not None


def test_new_drawer_preserves_rising_edge_rearm_and_scene_focus_rules():
    panel=build_drawer_layout(1024,640,interaction_available=True)
    button=panel.buttons[1]
    pointer=((button.rect.x+button.rect.width//2-panel.viewport.x)/(panel.viewport.width-1),
             (button.rect.y+button.rect.height//2-panel.viewport.y)/(panel.viewport.height-1))
    state=InteractionState(run_id="g8-synthetic",frame_id=1,timestamp_s=.1,
        interaction_valid=True,pointer_xy=pointer,pinch_ratio=.2,pinch_active=True,
        rotation_delta=(.1,.1),scale_delta=.1)
    router=InteractionRouter()
    router.open_panel()
    assert router.route(state,panel).action is None
    released=replace(state,pinch_active=False)
    assert not router.route(released,panel).forward_to_scene
    assert router.route(state,panel).action == "scene:molecule"
    assert router.route(state,panel).action is None
    invalid=replace(state,interaction_valid=False,pointer_xy=None)
    assert not router.route(invalid,panel).forward_to_scene
    assert router.route(state,panel).action is None
    router.route(released,panel)
    assert router.route(state,panel).action == "scene:molecule"
    router.close_panel()
    assert not router.route(state,None).forward_to_scene
    assert not router.route(released,None).forward_to_scene
    assert router.route(state,None).forward_to_scene


@pytest.mark.parametrize("size",[(1280,720),(1440,900),(1600,900),(1920,1080)])
def test_final_workspace_priority_and_drawer_nonoverlap(size):
    layout=calculate_shell_layout(*size)
    assert .70 <= layout.stem.width/layout.content.width <= .80
    assert layout.sidebar.height == THEME.shell_scene_bar_height
    assert layout.vision.height <= THEME.shell_vision_max_height
    panel=build_drawer_layout(*size)
    for i,button in enumerate(panel.buttons):
        assert panel.viewport.x <= button.rect.x < button.rect.right <= panel.viewport.right
        assert panel.viewport.y <= button.rect.y < button.rect.bottom <= panel.viewport.bottom
        for other in panel.buttons[i+1:]:
            assert (button.rect.right <= other.rect.x or other.rect.right <= button.rect.x
                    or button.rect.bottom <= other.rect.y or other.rect.bottom <= button.rect.y)


def test_workspace_hides_engineering_and_analysis_exposes_actual_outputs(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    texts=[]
    original=dashboard._text
    def capture(canvas,text,*args,**kwargs):
        texts.append(text)
        return original(canvas,text,*args,**kwargs)
    dashboard._text=capture
    dashboard.build_surface(*sample)
    assert not any(text.startswith(('Run ','Core compute','Filter dt','Pinch ratio','Rotation ')) for text in texts)
    texts.clear()
    dashboard.set_mode(DashboardMode.ANALYSIS)
    dashboard.build_surface(*sample)
    assert 'Rotation +0.010, -0.020 rad' in texts
    assert 'Scale delta 0.030' in texts
    assert 'Core compute 3.300 ms' in texts
    assert 'Run g8-demo-test' in texts
    assert 'Frame normalized / unmirrored' in texts


def test_evidence_navigation_follows_visible_sections_and_hides_scene_navigation(sample):
    dashboard=ProductDashboard(window_host=FakeHost())
    dashboard.set_mode(DashboardMode.EVIDENCE)
    dashboard.build_surface(*sample)
    assert not any(key.startswith('scene:') for key in dashboard._targets)
    for index in (3,4,1,2,5):
        dashboard.handle_key(ord(']'))
        assert dashboard.evidence_page_index == index
    dashboard.handle_key(ord(']'))
    assert dashboard.evidence_page_index == 5
    for index in (2,1,4,3,0):
        dashboard.handle_key(ord('['))
        assert dashboard.evidence_page_index == index


@pytest.mark.parametrize('component', ['camera','model/provider','renderer','logging','scene','runtime'])
def test_error_guidance_remains_user_facing(component):
    dashboard=ProductDashboard(window_host=FakeHost())
    texts=[]
    original=dashboard._paragraph
    def capture(canvas,text,*args,**kwargs):
        texts.append(text)
        return original(canvas,text,*args,**kwargs)
    dashboard._paragraph=capture
    app=ApplicationState('qa',ApplicationPhase.ERROR,failure_component=component,
        error_message='Traceback: internal provider detail')
    dashboard.build_application_state_screen(app)
    assert any('restart' in text.lower() or 'check' in text.lower() for text in texts)
    assert not any('Traceback' in text for text in texts)


def test_camera_framing_is_presentation_only():
    from extensions.stem3d.scenes import build_tier1_scene_registry
    renderer=ApplicationShellRenderer(width=1280,height=720,target_fps=30)
    registry=build_tier1_scene_registry(initial_scale=1.,min_scale=.5,max_scale=2.)
    for scene in registry.scenes:
        registry.activate(scene.id)
        before=scene.transform
        frame=scene.frame
        angles=renderer._scene_view_angles(frame)
        if scene.id in {'coordinate-geometry','orbital-system'}:
            assert angles == (THEME.scene_view_pitch_deg,THEME.scene_view_yaw_deg)
        else:
            assert angles == (0.,0.)
        assert scene.transform == before == frame.transform


def test_roi_overlay_is_analysis_only_and_source_is_read_only(sample):
    image,state,app=sample
    image.setflags(write=False)
    dashboard=ProductDashboard(window_host=FakeHost())
    for mode,expected in ((DashboardMode.DEMO,False),(DashboardMode.ANALYSIS,True)):
        dashboard.set_mode(mode)
        surface=dashboard.build_surface(image,state,app)
        rect=surface.layout.vision
        preview=surface.canvas[rect.y+44:rect.bottom-70,rect.x+12:rect.right-12]
        assert bool(np.any(np.all(preview==THEME.accent,axis=2))) is expected
    assert image.flags.writeable is False
