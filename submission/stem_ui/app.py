"""Run with python -m submission.stem_ui.app; renderer stays on main thread."""
import argparse
import json
from pathlib import Path
import time
import yaml
from .runtime import CaptureWorker, ROOT
from .renderer import SubmissionRenderer
from .network_camera import normalize_droidcam_endpoint

def main():
    parser=argparse.ArgumentParser(description='DIP Touchless STEM — UI nộp đồ án')
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--mode',choices=('solid','tips','chemistry','physics'),default='solid')
    parser.add_argument('--smoke-frames',type=int,default=0)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    settings=yaml.safe_load(Path(__file__).with_name('settings.yaml').read_text(encoding='utf-8'))
    droidcam_prefs=ROOT/'runs/ui/droidcam.json'
    if droidcam_prefs.is_file():
        try:
            saved=json.loads(droidcam_prefs.read_text(encoding='utf-8'))
            if not isinstance(saved,dict): raise ValueError('Invalid DroidCam preferences')
            settings['droidcam_wifi_host']=str(saved.get('host',settings['droidcam_wifi_host']))
            settings['droidcam_wifi_port']=int(saved.get('port',settings['droidcam_wifi_port']))
        except (OSError,ValueError,TypeError,json.JSONDecodeError):
            pass
    renderer=SubmissionRenderer(settings); renderer.mode=args.mode
    if args.mode=='chemistry': renderer.enter_chemistry()
    elif args.mode=='physics': renderer.enter_physics()
    worker=None; active=False; error=None; webcam_index=args.camera
    current_source=('webcam',webcam_index); pending_source=None
    frame_count=0; seen=set(); max_hands=max_tips=0; start=time.monotonic()
    interaction_log=None; log_run=None; logged_frame=None
    snapshot=None; status='Camera đang tắt'
    def start_source(source=None):
        nonlocal worker,active,error,current_source
        if source is not None: current_source=source
        kind=current_source[0]
        kwargs={'camera_index':webcam_index,'replay':args.replay}
        if kind=='droidcam_wifi': kwargs['droidcam_wifi']=(current_source[1],current_source[2])
        worker=CaptureWorker(settings,**kwargs)
        worker.start(); active=True; error=None
        print('Phiên: '+worker.run_id+' • nhật ký: runs/ui/'+worker.run_id,flush=True)

    def toggle():
        nonlocal worker,active,error,pending_source
        if pending_source is not None:
            pending_source=None
            if worker: worker.stop()
            active=False
        elif active:
            active=False; worker.stop()
        elif worker is None or not worker.alive:
            start_source()

    def request_source(source):
        nonlocal pending_source,active,error,current_source
        if args.replay: return
        if active and current_source==source: return
        error=None
        if worker is not None and worker.alive:
            pending_source=source; active=False; worker.stop()
        else:
            pending_source=None; start_source(source)

    def save_droidcam(host,port):
        try:
            droidcam_prefs.parent.mkdir(parents=True,exist_ok=True)
            droidcam_prefs.write_text(json.dumps({'host':host,'port':port},ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:
            pass
    try:
        renderer.open()
        if args.replay: toggle()
        running=True
        while running:
            for action in renderer.events():
                if action=='quit':
                    running=False; pending_source=None; break
                elif action=='toggle': toggle()
                elif action=='next_camera' and not args.replay and not active and pending_source is None:
                    webcam_index=(webcam_index+1)%4; current_source=('webcam',webcam_index)
                elif action=='droidcam_connect':
                    try:
                        host,port=normalize_droidcam_endpoint(renderer.droidcam_host,renderer.droidcam_port)
                    except ValueError as exc:
                        error=str(exc)
                    else:
                        renderer.droidcam_host=host; renderer.droidcam_port=str(port); renderer.droidcam_dialog=False
                        save_droidcam(host,port); request_source(('droidcam_wifi',host,port))
                elif action=='webcam_connect':
                    renderer.droidcam_dialog=False; request_source(('webcam',webcam_index))
            if not running: break
            if worker and worker.error:
                if pending_source is None: error=worker.error
                active=False
            if pending_source is not None and (worker is None or not worker.alive):
                next_source=pending_source; pending_source=None; start_source(next_source)
            snapshot=None if pending_source is not None else (worker.latest if worker else None)
            status='Đang mở camera…' if active and snapshot is None else 'Camera đang tắt'
            if pending_source is not None:
                status='Đang chuyển nguồn camera…'
            elif active and current_source[0]=='droidcam_wifi' and snapshot is None:
                status='Đang kết nối DroidCam Wi-Fi…'
            if pending_source is None and worker and worker.alive and not active and not error:
                status='Đang dừng camera…'
            if worker and worker.finished and active:
                active=False; status='Đã kết thúc phát lại' if args.replay else 'Camera đã dừng'
            hands,tips=renderer.draw(snapshot,status,active=active,error=error,
                run_id=worker.run_id if worker else '',camera_index=webcam_index,replay=bool(args.replay),
                source_kind=current_source[0])
            if active and snapshot and (log_run!=worker.run_id or logged_frame!=snapshot.frame_id):
                if log_run!=worker.run_id:
                    if interaction_log: interaction_log.close()
                    interaction_log=(ROOT/'runs/ui'/worker.run_id/'interactions.jsonl').open('w',encoding='utf-8')
                    log_run=worker.run_id
                grip=renderer.grab
                interaction_log.write(json.dumps({'frame_id':snapshot.frame_id,'timestamp_s':snapshot.timestamp_s,
                    'held_slots':list(grip.slots),'suspended':grip.suspended,'scale_mode':grip.scale_mode,
                    'scale':grip.pose.scale,'stretch':grip.pose.stretch.tolist(),
                    'position':grip.pose.position.tolist(),'rotation':grip.pose.rotation.tolist(),
                    'mode':renderer.mode,'live_mesh_mode':getattr(renderer,'live_mesh_mode',None),
                    'draw_cpu_ms_excluding_swap_and_cap':renderer.last_draw_cpu_ms,
                    'render_msaa_samples':renderer.actual_msaa_samples,
                    'window_size':list(renderer.size),'fullscreen':renderer.fullscreen,
                    'chemistry':renderer.chemistry.scene.state() if renderer.mode=='chemistry' else None,
                    'chemistry_controls':renderer.chemistry.input.diagnostics() if renderer.mode=='chemistry' else None,
                    'physics':{'configuration':renderer.physics.model.configuration(),
                        'measurements':renderer.physics.model.metrics(),'running':renderer.physics.model.running,
                        'speed':renderer.physics.model.speed,'achieved':renderer.physics.model.achieved,
                        'prediction':renderer.physics.model.prediction,
                        'discarded_wall_s':renderer.physics.model.discarded_wall_s} if renderer.mode=='physics' else None,
                    'physics_controls':renderer.physics.input.diagnostics() if renderer.mode=='physics' else None,
                    'feedback':grip.feedback},ensure_ascii=False)+'\n')
                logged_frame=snapshot.frame_id
            max_hands=max(max_hands,hands); max_tips=max(max_tips,tips)
            if snapshot: seen.add(snapshot.frame_id)
            frame_count+=1
            if args.smoke_frames and len(seen)>=args.smoke_frames:
                running=False
            if args.smoke_frames and (error or time.monotonic()-start>60):
                raise RuntimeError(error or 'UI smoke timed out waiting for processed frames')
        if args.screenshot:
            renderer.screenshot(args.screenshot)
            renderer.draw(snapshot,status,active=active,error=error,
                run_id=worker.run_id if worker else '',camera_index=webcam_index,replay=bool(args.replay),
                source_kind=current_source[0])
    finally:
        if interaction_log: interaction_log.close()
        if worker:
            worker.stop()
            if worker.thread: worker.thread.join(timeout=5)
        renderer.close()
    if args.smoke_frames:
        result={'processed_frames_seen':len(seen),'max_hands':max_hands,'max_extended_tips':max_tips,
                'worker_stopped':not worker.alive,'error':error,'mode':args.mode,'run_id':worker.run_id}
        print(json.dumps(result,ensure_ascii=False))
        if worker.alive or error: raise RuntimeError('UI did not shut down cleanly')

if __name__=='__main__': main()
