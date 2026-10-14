"""Run with python -m submission.stem_ui.app; renderer stays on main thread."""
import argparse
import json
from pathlib import Path
import time
import yaml
from .runtime import CaptureWorker, ROOT
from .renderer import SubmissionRenderer

def main():
    parser=argparse.ArgumentParser(description='DIP Touchless STEM — UI nộp đồ án')
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--mode',choices=('solid','tips','chemistry'),default='solid')
    parser.add_argument('--smoke-frames',type=int,default=0)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    settings=yaml.safe_load(Path(__file__).with_name('settings.yaml').read_text(encoding='utf-8'))
    renderer=SubmissionRenderer(settings); renderer.mode=args.mode
    if args.mode=='chemistry': renderer.enter_chemistry()
    worker=None; active=False; error=None; camera_index=args.camera
    frame_count=0; seen=set(); max_hands=max_tips=0; start=time.monotonic()
    interaction_log=None; log_run=None; logged_frame=None
    def toggle():
        nonlocal worker,active,error
        if active:
            active=False; worker.stop()
        elif worker is None or not worker.alive:
            worker=CaptureWorker(settings,camera_index=camera_index,replay=args.replay)
            worker.start(); active=True; error=None
            print('Phiên: '+worker.run_id+' • nhật ký: runs/ui/'+worker.run_id,flush=True)
    try:
        renderer.open()
        if args.replay: toggle()
        running=True
        while running:
            for action in renderer.events():
                if action=='quit': running=False
                elif action=='toggle': toggle()
                elif action=='next_camera' and not active:
                    camera_index=(camera_index+1)%4
            if worker and worker.error:
                error=worker.error; active=False
            snapshot=worker.latest if worker else None
            status='Đang mở camera…' if active and snapshot is None else 'Camera đang tắt'
            if worker and worker.alive and not active and not error:
                status='Đang dừng camera…'
            if worker and worker.finished and active:
                active=False; status='Đã kết thúc phát lại' if args.replay else 'Camera đã dừng'
            hands,tips=renderer.draw(snapshot,status,active=active,error=error,
                run_id=worker.run_id if worker else '',camera_index=camera_index,replay=bool(args.replay))
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
                    'chemistry':renderer.chemistry.scene.state() if renderer.mode=='chemistry' else None,
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
                run_id=worker.run_id if worker else '',camera_index=camera_index,replay=bool(args.replay))
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
