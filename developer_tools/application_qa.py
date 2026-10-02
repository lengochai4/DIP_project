"""Deterministic synthetic UI/performance QA; never webcam or research evidence.

Run as a module from repository root. --capture-gl uses a hidden local GL
context with the actual scene renderer; model/camera inference is not executed.
"""

import argparse
import cProfile
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import pstats
import time
import cv2
import numpy as np
from dip_touchless.core import (
    ColorSpace, CoordinateSpace, FramePacket, Landmark, TrackingFrame, TrackingStatus,
    FilterDiagnostics, FilterMode, StageTimings, MeasurementQuality,
)
from extensions.stem3d.product.dashboard import ApplicationDashboard
from extensions.stem3d.product.settings import InputMode, UserSettings
from extensions.stem3d.full_hand.observe import FullHandObserver, load_observe_profile
from extensions.stem3d.full_hand.intent_session import IntentObservationSession, load_intent_profile
from extensions.stem3d.full_hand.intent_pinch_contracts import ReferenceScope
from extensions.stem3d.ui import (
    ApplicationPhase, ApplicationState, DashboardMode, build_presentation_state,
    SpatialPanelViewState, InteractionFocus,
)
from extensions.stem3d.product.interaction import neutral
from extensions.stem3d.product.simple_interaction import SimpleHandControls
from extensions.stem3d.product.settings import load_application_profile
from extensions.stem3d.scenes import build_tier1_scene_registry
from extensions.stem3d.shell_renderer import ApplicationShellRenderer

POINTS = ((.50,.80),(.40,.68),(.32,.61),(.25,.53),(.20,.48),
          (.40,.55),(.40,.42),(.40,.31),(.40,.20),(.50,.50),(.50,.35),(.50,.23),(.50,.11),
          (.60,.54),(.61,.40),(.62,.29),(.63,.19),(.68,.61),(.71,.50),(.73,.41),(.75,.33))


class HeadlessHost:
    opened = False
    window_size = (1600,900)
    def set_pointer_consumer(self, consumer): pass
    def set_key_consumer(self, consumer): pass
    def close(self): pass


def synthetic(i=0, lost=False):
    image = np.full((480,640,3), (32,30,28), np.uint8)
    cv2.putText(image, "SYNTHETIC INPUT / NO WEBCAM", (22,245), cv2.FONT_HERSHEY_SIMPLEX, .7, (180,180,180), 1, cv2.LINE_AA)
    packet = FramePacket("synthetic-v11-qa", i, i/30, image, ColorSpace.BGR, "synthetic-qa")
    landmarks = tuple(Landmark(j, .5+(x-.5)/(640/480), y, 0., CoordinateSpace.FRAME_NORMALIZED)
                      for j, (x,y) in enumerate(POINTS))
    frame = TrackingFrame(packet.run_id, i, i/30, TrackingStatus.NO_HAND if lost else TrackingStatus.VALID,
        () if lost else landmarks, () if lost else landmarks, MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW,None,None,None,None,None,None,None,False), StageTimings(0.,0.,0.,0.,0.),())
    return packet, frame


def stamp(canvas):
    cv2.rectangle(canvas,(16,112),(410,138),(30,30,30),-1)
    cv2.putText(canvas,"SYNTHETIC UI / NOT PHYSICAL EVIDENCE",(24,130),cv2.FONT_HERSHEY_SIMPLEX,.43,(200,200,200),1,cv2.LINE_AA)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/v11-ui-qa"))
    parser.add_argument("--capture-gl", action="store_true")
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args(argv)
    if args.iterations <= 0: parser.error("iterations must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    host = HeadlessHost()
    renderer = None
    original_mode = None
    original_flip = None
    captured = []
    if args.capture_gl:
        import pygame
        original_mode = pygame.display.set_mode
        pygame.display.set_mode = lambda size, flags=0, *a, **k: original_mode(size, flags|pygame.HIDDEN, *a, **k)
        renderer = ApplicationShellRenderer(width=1600,height=900,target_fps=60,title="Synthetic v1.1 QA")
        renderer.open()
        original_flip = pygame.display.flip
        def capture_before_swap():
            # Read the actual rendered back buffer before external desktop/driver
            # overlays hook the swap. No screenshot retouching or HUD fabrication.
            from OpenGL import GL
            GL.glReadBuffer(GL.GL_BACK)
            raw = GL.glReadPixels(0,0,1600,900,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
            captured[:] = [np.frombuffer(raw,dtype=np.uint8).reshape(900,1600,3)[::-1,:,::-1].copy()]
            original_flip()
        pygame.display.flip = capture_before_swap
        host = renderer
    dashboard = ApplicationDashboard(preferences=UserSettings(InputMode.SIMPLE,mirror=True,two_hand=True),
        preferences_path=args.output/"preferences.json", window_host=host)
    observer = FullHandObserver(load_observe_profile(Path("config/extensions/full_hand_observe.yaml")))
    intent_profile = load_intent_profile(Path("config/extensions/intent_pinch_observe.yaml"))
    session = IntentObservationSession(intent_profile, ReferenceScope("synthetic-v11-qa","synthetic-v11-qa",
        "synthetic-camera","synthetic-provider",intent_profile.sha256,"full-frame-aspect-corrected-xy","qa-0"))
    registry = build_tier1_scene_registry(initial_scale=1.,min_scale=.5,max_scale=2.)
    records = []
    timings = {}
    controls = SimpleHandControls(load_application_profile(Path("config/extensions/application.yaml"))[0])
    try:
        # The window is explicitly synthetic-confirmed, not a physical/user reference.
        for i in range(60):
            packet, frame = synthetic(i)
            observer.capture(packet)
            full = observer.consume(packet, frame, neutral(frame))
            intent = session.consume(frame, full.hand, events=("CALIBRATE_RELEASE",) if i == 0 else ())
            controls.update(frame,full,settings=dashboard.preferences)
        dashboard.full_snapshot = full
        dashboard.simple_feedback = controls.feedback
        dashboard.command_diagnostics = controls.diagnostics
        dashboard.two_hand_feedback = "Synthetic one-hand input / no pair"
        dashboard.set_intent_snapshot(intent)
        presentation = build_presentation_state(packet, frame, neutral(frame))
        application = ApplicationState(packet.run_id,ApplicationPhase.RUNNING)
        profiler = cProfile.Profile()
        profiler.enable()
        for mode in DashboardMode:
            dashboard._set_mode_state(mode)
            start = time.perf_counter()
            for _ in range(args.iterations): dashboard.build_surface(packet.image,presentation,application)
            timings[mode.value] = dict(iterations=args.iterations, total_seconds=time.perf_counter()-start)
        profiler.disable()
        report = io.StringIO()
        pstats.Stats(profiler,stream=report).sort_stats("cumulative").print_stats(25)
        (args.output/"cpu_profile.txt").write_text(report.getvalue().rstrip()+"\n",encoding="utf-8")
        cases = [("01-workspace-geometry",DashboardMode.DEMO,"coordinate-geometry",None),
                 ("02-workspace-molecule",DashboardMode.DEMO,"molecule",None),
                 ("03-workspace-orbital",DashboardMode.DEMO,"orbital-system",None),
                 ("04-analysis",DashboardMode.ANALYSIS,"coordinate-geometry",None),
                 ("05-evidence-overview",DashboardMode.EVIDENCE,"coordinate-geometry",None),
                 ("06-evidence-a1",DashboardMode.EVIDENCE,"coordinate-geometry",3),
                 ("07-settings",DashboardMode.DEMO,"coordinate-geometry","settings"),
                 ("08-help",DashboardMode.DEMO,"coordinate-geometry","help"),
                 ("09-control-space",DashboardMode.DEMO,"coordinate-geometry","panel"),
                 ("10-no-hand",DashboardMode.DEMO,"coordinate-geometry","lost")]
        for name, mode, scene_id, option in cases:
            dashboard._set_mode_state(mode)
            dashboard.settings_open = option == "settings"
            dashboard._help_open = option == "help"
            dashboard._provenance_open = False
            dashboard._evidence_page_index = option if isinstance(option,int) else 0
            dashboard._spatial_panel_state = SpatialPanelViewState(option=="panel",
                InteractionFocus.UI_FOCUS if option=="panel" else InteractionFocus.SCENE_FOCUS,
                True, active_scene_id=scene_id, mode=mode)
            state = presentation
            if option == "lost":
                p,f = synthetic(61,True)
                state = build_presentation_state(p,f,neutral(f))
                dashboard.full_snapshot = None
                dashboard.simple_feedback = None
                dashboard.set_intent_snapshot(None)
            scene = registry.activate(scene_id)
            app = replace(application,active_scene=scene.title)
            surface = dashboard.build_surface(packet.image,state,app)
            stamp(surface.canvas)
            image = surface.canvas
            if renderer is not None:
                scene.render(renderer)
                renderer.present_shell(surface.canvas,surface.viewport,surface.overlays)
                image = captured[-1]
            path = args.output/f"{name}-synthetic.png"
            if not cv2.imwrite(str(path),image): raise OSError(f"Cannot save {path}")
            records.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source="synthetic", scene_renderer="actual OpenGL" if renderer else "CPU shell; 3D viewport not rendered",
                size=[1600,900],not_research_evidence=True))
        manifest = dict(scope="local synthetic application QA, not webcam/research evidence",screenshots=records,
                        cpu_timings=timings, performance_scope="profiled CPU shell only; no camera/model/Core or FPS claim")
        (args.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(dict(output=str(args.output),screenshots=len(records),cpu_timings=timings)))
    finally:
        registry.deactivate()
        dashboard.close()
        if original_mode is not None:
            import pygame
            pygame.display.set_mode = original_mode
            if original_flip is not None:
                pygame.display.flip = original_flip


if __name__ == "__main__": main()
