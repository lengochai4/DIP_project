# Hand Landmarker model setup

The final application expects `models/hand_landmarker.task` in the repository root.
The binary is ignored by Git and must be supplied separately for offline use.

Source: Google's [Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python).
The pinned float16 version-1 asset is also referenced by the
[official sample](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/tasks/hand-landmarker.ts).

From the repository root, download only if the local model is absent:

```powershell
if (-not (Test-Path -LiteralPath models/hand_landmarker.task)) {
    Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task' -OutFile models/hand_landmarker.task
}
Get-FileHash -LiteralPath models/hand_landmarker.task -Algorithm SHA256
```

Expected SHA-256 (case-insensitive):

```text
fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

The local checked asset is 7,819,105 bytes and matches this hash. If the hash
differs, resolve the model mismatch before presenting; do not silently substitute
a different asset or change provider thresholds. No model download was needed
during final preparation.

Install the dependencies declared by `pyproject.toml`, including `demo3d`.
The verified environment uses MediaPipe 1.0.1, OpenCV contrib 4.14.0.94,
Pygame 2.6.1 and PyOpenGL 3.1.10. The project uses the MediaPipe Tasks API.
Do not install a second OpenCV distribution into the same environment.
