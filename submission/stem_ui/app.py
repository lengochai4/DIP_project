"""Run with python -m submission.stem_ui.app; renderer stays on main thread."""
import argparse
import json
from pathlib import Path
import time
import yaml
from .runtime import CaptureWorker
from .renderer import SubmissionRenderer

def main():
    parser=argparse.ArgumentParser(description='DIP Touchless STEM — UI nộp đồ án')
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--mode',choices=('solid','tips'),default='solid')
    parser.add_argument('--smoke-frames',type=int,default=0)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    settings=yaml.safe_load(Path(__file__).with_name('settings.yaml').read_text(encoding='utf-8'))
    renderer=SubmissionRenderer(settings); renderer.mode=args.mode
    worker=None; active=False; error=None; camera_index=args.camera
    frame_count=0; seen=set(); max_hands=max_tips=0; start=time.monotonic()
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
