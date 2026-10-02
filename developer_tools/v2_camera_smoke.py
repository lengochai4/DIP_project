"""Bounded physical camera check through the V2 Start/Stop buttons; no video saved.

This confirms camera/runtime/GUI integration only, not gesture usability.
"""

import argparse
from datetime import datetime
import json
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.config import ROOT, ProductConfig, Settings
from app.ui.shell import ProductWindow


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    if args.frames < 1 or args.timeout <= 0:
        parser.error("positive frame count and timeout required")
    app = QApplication.instance() or QApplication([])
    window = ProductWindow(
        ProductConfig.load(), Settings(camera_index=args.camera), software=True
    )
    window.navigate("Analyze")
    window.show()
    samples = {}
    result = {
        "camera_index": args.camera,
        "raw_video_stored": False,
        "scope": "physical camera + V2 Start/Stop + GUI presentation only",
        "gesture_usability": "NOT VALIDATED",
        "passed": False,
    }
    started = time.monotonic()
    stopping = False
    timer = QTimer()

    def poll():
        nonlocal stopping
        frame = window.last_tracking
        if frame is not None and not stopping:
            samples[frame.frame_id] = {
                "frame_id": frame.frame_id,
                "timestamp_s": frame.timestamp_s,
                "core_status": frame.status.value,
                "product_hands": len(window.current_hands),
                "product_poses": [h.pose for h in window.current_hands],
            }
        error = window._camera_failure
        if not stopping and (
            error
            or len(samples) >= args.frames
            or time.monotonic() - started >= args.timeout
        ):
            result.update(
                run_id=window.worker.run_id,
                samples=list(samples.values()),
                passed=len(samples) >= args.frames and not error,
                error=error
                or (None if len(samples) >= args.frames else "camera check timed out"),
            )
            window.stop_button.click()
            stopping = True
        if stopping and not window.worker.isRunning():
            result["clean_shutdown"] = window.worker.isFinished()
            directory = ROOT / "runs/product-v2"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (
                "camera-smoke-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
            )
            path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False))
            print(f"Camera smoke record: {path}")
            timer.stop()
            window.close()
            app.quit()

    timer.timeout.connect(poll)
    timer.start(100)
    window.start_button.click()
    app.exec()
    return 0 if result["passed"] and result.get("clean_shutdown") else 1


if __name__ == "__main__":
    raise SystemExit(main())
