"""Application composition root; frozen one-hand research runtime is untouched."""
from dataclasses import dataclass, replace
from datetime import datetime
from itertools import permutations
from pathlib import Path
import hashlib
import json
import math
import threading
import time
import subprocess

import cv2
import mediapipe as mp
import numpy as np
from dip_touchless.capture import OpenCVCameraSource, ReplayFrameSource
from dip_touchless.configuration import resolve_config
from dip_touchless.core import (CoordinateSpace, Landmark, LandmarkObservation,
    MeasurementQuality, TrackingStatus, ROI, ROIState)
from dip_touchless.preprocessing import (ROIManager, IlluminationAnalyzer,
    IlluminationDecisionStabilizer, AdaptivePreprocessor)
from dip_touchless.tracking import MeasurementValidator
from experiments.run_replay import build_landmark_filter
from dip_touchless.interaction import DeterministicGestureEngine
from .acquisition import LatestCamera
from .network_camera import DroidCamWifiSource

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class HandView:
    slot: int
    landmarks: tuple
    interaction: object
    label: str | None
    generation: int = 0
    raw_landmarks: tuple = ()

@dataclass(frozen=True)
class Snapshot:
    frame_id: int
    timestamp_s: float
    delivered_at: float
    image: np.ndarray
    hands: tuple[HandView, ...]
    illumination: object
    roi: object

def associate(previous, observations, max_distance, ambiguity_margin=0.02):
    """Nearest palm association; provider ordering never defines hand identity.

    Ambiguous/displaced pairs are neutralized rather than smoothing across hands.
    Handedness is metadata, never tracking confidence.
    """
    centers = [(np.mean([l.x for l in o.landmarks if l.index in (0,5,9,13,17)]),
                np.mean([l.y for l in o.landmarks if l.index in (0,5,9,13,17)])) for o in observations]
    best, best_cost = {}, float('inf')
    costs = []
    for slots in permutations(range(2), len(centers)):
        cost = sum(math.dist(previous[s], c) if s in previous else max_distance
                   for s,c in zip(slots,centers))
        costs.append(cost)
        if cost < best_cost:
            best_cost = cost; best = dict(zip(slots,range(len(centers))))
    resets = {s for s,i in best.items() if s not in previous or math.dist(previous[s],centers[i]) > max_distance}
    if len(previous)==2 and len(centers)==2 and len(costs)>1 and abs(costs[0]-costs[1]) < ambiguity_margin:
        resets.update(best)
    return best, resets, {s:centers[i] for s,i in best.items()}

def convert_result(result, packet):
    """Explicit provider conversion; every observation has unavailable quality."""
    out = []
    for i, points in enumerate(result.hand_landmarks[:2]):
        if len(points) != 21 or not all(math.isfinite(float(v)) for p in points for v in (p.x,p.y,p.z)):
            continue
        landmarks = tuple(Landmark(index=j,x=float(p.x),y=float(p.y),z=float(p.z),
                          coordinate_space=CoordinateSpace.FRAME_NORMALIZED) for j,p in enumerate(points))
        category = result.handedness[i][0] if i < len(result.handedness) and result.handedness[i] else None
        out.append(LandmarkObservation(frame_id=packet.frame_id,timestamp_s=packet.timestamp_s,
            status=TrackingStatus.VALID,landmarks=landmarks,
            handedness_label=category.category_name if category else None,
            handedness_score=float(category.score) if category else None,
            quality=MeasurementQuality.unavailable(),hand_bbox=None,
            provider_name='submission_mediapipe_two_hand'))
    return out

class CaptureWorker:
    def __init__(self, settings, *, camera_index=0, droidcam_wifi=None, replay=None):
        self.settings = settings
        self.camera_index = camera_index
        self.droidcam_wifi = droidcam_wifi
        self.replay = replay
        self.stop_event = threading.Event()
        self.thread = None
        self.latest = None
        self.error = None
        self.finished = False
        self.camera_pump = None
        self.run_id = 'ui-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')

    @property
    def alive(self):
        return (self.thread is not None and self.thread.is_alive()) or (self.camera_pump is not None and self.camera_pump.alive)

    def start(self):
        if self.thread is not None:
            raise RuntimeError('worker already started')
        self.thread = threading.Thread(target=self._run, name=self.run_id, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        source = landmarker = log = None
        folder = ROOT / 'runs/ui' / self.run_id
        try:
            model = ROOT / 'models/hand_landmarker.task'
            if not model.is_file():
                raise FileNotFoundError('Thiếu models/hand_landmarker.task. Xem models/README.md.')
            cfg = resolve_config(ROOT / 'config/default.yaml',
                profile_path=ROOT / 'config/experiments/f2.yaml',
                overrides={'filter':self.settings['filter_overrides'],
                    'runtime':{'mode':'replay' if self.replay else 'realtime','replay_source':str(self.replay) if self.replay else None},
                    'experiment':{'condition':'UI_INTERACTION'}}).to_dict()
            filters = [build_landmark_filter(cfg) for _ in range(2)]
            gestures = [DeterministicGestureEngine(**cfg['gesture']) for _ in range(2)]
            manager = ROIManager(**cfg['roi'])
            analyzer = IlluminationAnalyzer()
            decision = IlluminationDecisionStabilizer(**cfg['illumination'])
            preprocessor = AdaptivePreprocessor(**{**cfg['clahe'], 'tile_grid_size':tuple(cfg['clahe']['tile_grid_size'])})
            options = mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=self.settings['max_hands'],
                min_hand_detection_confidence=cfg['tracking']['min_hand_detection_confidence'],
                min_hand_presence_confidence=cfg['tracking']['min_hand_presence_confidence'],
                min_tracking_confidence=cfg['tracking']['min_tracking_confidence'])
            landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
            if self.replay:
                source = ReplayFrameSource(self.replay, run_id=self.run_id)
                source.open()
            else:
                def camera_factory():
                    if self.droidcam_wifi is not None:
                        host,port=self.droidcam_wifi
                        return DroidCamWifiSource(run_id=self.run_id,host=host,port=port,
                            open_timeout_ms=self.settings['droidcam_open_timeout_ms'],
                            read_timeout_ms=self.settings['droidcam_read_timeout_ms'])
                    # Backend fallback stays inside the sole camera owner thread.
                    class Camera:
                        inner = None
                        def open(camera):
                            for backend in ('default','dshow'):
                                camera.inner = OpenCVCameraSource(run_id=self.run_id,camera_index=self.camera_index,
                                    width=cfg['camera']['width'],height=cfg['camera']['height'],
                                    requested_fps=cfg['camera']['requested_fps'],backend=backend)
                                try:
                                    camera.inner.open(); return
                                except RuntimeError:
                                    camera.inner.close()
                            raise RuntimeError('Không mở được camera. Đóng ứng dụng đang dùng camera, kiểm tra quyền Camera của Windows hoặc chọn camera khác.')
                        def read(camera): return camera.inner.read()
                        def close(camera):
                            if camera.inner: camera.inner.close()
                    return Camera()
                source = LatestCamera(camera_factory,self.stop_event,self.settings['camera_shutdown_timeout_s'])
                self.camera_pump = source
                source.open()
            folder.mkdir(parents=True,exist_ok=True)
            try:
                revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=False).stdout.strip() or None
                dirty=bool(subprocess.run(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,capture_output=True,text=True,check=False).stdout.strip())
            except OSError:
                revision=None
                dirty=None
            (folder/'metadata.json').write_text(json.dumps({'kind':'submission_presentation_only',
                'presentation_schema':'10',
                'chemistry_grab_motion':'observed_contact_baseline_response_handle_aim',
                'chemistry_viewport':'center_crop_cover',
                'chemistry_quick_select':'relative_index_push_shared_dwell_latch',
                'discrete_gesture_basis':'validated_raw_landmarks',
                'fingertip_geometry':'observed_vertices_only',
                'chemistry_data_sha256':hashlib.sha256((Path(__file__).with_name('data')/'pubchem-periodic-table.json').read_bytes()).hexdigest(),
                'acquisition_policy':'ordered_replay' if self.replay else 'latest_camera_single_slot',
                'run_id':self.run_id,'core_config':cfg,'ui_settings':self.settings,'camera_index':self.camera_index,
                'live_source':'droidcam_wifi' if self.droidcam_wifi is not None else ('replay' if self.replay else 'webcam'),
                'code_revision':revision,
                'code_working_tree_dirty':dirty,
                'source':str(self.replay) if self.replay else ('droidcam_wifi' if self.droidcam_wifi is not None else 'camera'),
                'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
                'research_compatible':False,'raw_video_saved':False},ensure_ascii=False,indent=2),encoding='utf-8')
            log = (folder/'frames.jsonl').open('w',encoding='utf-8')
            previous = {}; last_seen = {}; generations = [0,0]
            bbox = None; validator = MeasurementValidator(); last_ms = -1; skipped_timestamp_packets=0
            # Public TrackingFrame is used only at the composition root for
            # canonical gesture mapping, never leaked into renderer internals.
            from dip_touchless.core import TrackingFrame, StageTimings
            while not self.stop_event.is_set():
                packet = source.read()
                if packet is None:
                    break
                timestamp_ms = round(packet.timestamp_s*1000)
                if timestamp_ms <= last_ms:
                    if self.replay:
                        raise RuntimeError('Dấu thời gian camera không tăng sau chuyển đổi mili giây.')
                    # A network burst may deliver multiple live frames in one
                    # millisecond. Skip duplicates without inventing timestamps
                    # or advancing Core state on an unprocessed observation.
                    skipped_timestamp_packets+=1
                    continue
                last_ms = timestamp_ms
                compute_start=time.perf_counter()
                h,w = packet.image.shape[:2]
                roi = manager.update(frame_width=w,frame_height=h,hand_bbox=bbox)
                illumination = decision.update(analyzer.measure(packet,roi))
                processed = preprocessor.process_frame(packet,roi,illumination)
                preprocess_end=time.perf_counter()
                rgb = np.ascontiguousarray(cv2.cvtColor(processed.frame.image,cv2.COLOR_BGR2RGB))
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb),timestamp_ms)
                observations = [validator.validate(o) for o in convert_result(result,packet)]
                observations = [o for o in observations if o.status is TrackingStatus.VALID]
                tracking_end=time.perf_counter()
                previous={s:c for s,c in previous.items() if packet.timestamp_s-last_seen[s] <= self.settings['association_retention_s']}
                assignments, resets, centers = associate(previous,observations,self.settings['association_max_distance'],self.settings['association_ambiguity_margin'])
                hands = []
                for s in range(2):
                    if s not in assignments:
                        missing=LandmarkObservation(packet.frame_id,packet.timestamp_s,TrackingStatus.NO_HAND,(),None,None,
                            MeasurementQuality.unavailable(),None,'submission_mediapipe_two_hand')
                        filters[s].update(missing)
                        gestures[s].reset()
                        continue
                    if s in resets:
                        generations[s]+=1
                        filters[s].reset(); gestures[s].reset()
                    observation = observations[assignments[s]]
                    filter_start=time.perf_counter()
                    filtered, diagnostics = filters[s].update(observation)
                    filter_end=time.perf_counter()
                    preprocess_ms=(preprocess_end-compute_start)*1000
                    tracking_ms=(tracking_end-preprocess_end)*1000
                    filtering_ms=(filter_end-filter_start)*1000
                    frame = TrackingFrame(run_id=packet.run_id,frame_id=packet.frame_id,timestamp_s=packet.timestamp_s,
                        status=observation.status,raw_landmarks=observation.landmarks,filtered_landmarks=filtered,
                        quality=observation.quality,roi=roi,illumination=processed.illumination,
                        filter_diagnostics=diagnostics,
                        timings=StageTimings(preprocess_ms,tracking_ms,filtering_ms,0,
                                            preprocess_ms+tracking_ms+filtering_ms),events=diagnostics.events)
                    interaction = gestures[s].update(frame)
                    hands.append(HandView(s,filtered,interaction,observation.handedness_label,generations[s],observation.landmarks))
                previous.update(centers)
                for s in centers: last_seen[s]=packet.timestamp_s
                if observations:
                    # Union of previous hands is presentation-only ROI selection.
                    all_points = [l for o in observations for l in o.landmarks]
                    left=max(0,min(w-1,math.floor(min(l.x for l in all_points)*w)))
                    top=max(0,min(h-1,math.floor(min(l.y for l in all_points)*h)))
                    right=max(left+1,min(w,math.ceil(max(l.x for l in all_points)*w)))
                    bottom=max(top+1,min(h,math.ceil(max(l.y for l in all_points)*h)))
                    bbox=ROI(left,top,right-left,bottom-top,ROIState.TRACKING)
                else:
                    bbox=None
                image = packet.image.copy(); image.setflags(write=False)
                self.latest = Snapshot(packet.frame_id,packet.timestamp_s,time.monotonic(),image,tuple(hands),processed.illumination,roi)
                from .manipulation import pinch_ratio
                log.write(json.dumps({'frame_id':packet.frame_id,'timestamp_s':packet.timestamp_s,
                    'hands':len(hands),'illumination':processed.illumination.state.value,
                    'clahe_active':processed.illumination.enhancement_active,'neutral_slots':sorted(resets),
                    'hand_states':[{'slot':hand.slot,'generation':hand.generation,
                        'ui_pinch_ratio':pinch_ratio(hand,w/h),'canonical_pinch_active':hand.interaction.pinch_active,
                        'canonical_interaction_valid':hand.interaction.interaction_valid} for hand in hands],
                    'camera_packets_dropped':source.dropped if not self.replay else 0,
                    'camera_queue_wait_ms':source.last_wait_ms if not self.replay else None,
                    'live_timestamp_packets_skipped':skipped_timestamp_packets,
                    'compute_ms':(time.perf_counter()-compute_start)*1000})+'\n')
                if self.replay:
                    self.stop_event.wait(1/30)
        except Exception as exc:
            self.error = str(exc)
        finally:
            # Each resource is attempted even when another close fails.
            for resource in (source,landmarker,log):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception as exc:
                        self.error = self.error or str(exc)
            self.finished = True
