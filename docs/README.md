# DIP Touchless STEM — Documentation & Specifications

This directory contains architectural and specification overviews for the DIP Touchless STEM project.

## 1. System Architecture Overview

The system operates as an end-to-end, real-time pipeline converting monocular RGB webcam frames into precise, touchless 3D STEM object interactions:

```
[ Web Camera / Video Stream ]
             │
             ▼
 [ Region of Interest (ROI) ]
             │
             ▼
[ Illumination & Adaptive CLAHE ]
             │
             ▼
[ Hand Landmark Detection (MediaPipe) ]
             │
             ▼
  [ Adaptive 1-Euro Filtering ]
             │
             ▼
[ Touchless Gesture Engine (Pinch / Dwell / Grip) ]
             │
             ▼
[ STEM Simulation & 3D OpenGL Rendering ]
```

## 2. Core Modules

- **`src/dip_touchless/core/`**: Canonical contracts, datatypes, and state definitions (`Frame`, `LandmarkSet`, `InteractionState`).
- **`src/dip_touchless/capture/`**: Video acquisition from local webcams, IP cameras (DroidCam), and recorded test replays.
- **`src/dip_touchless/preprocessing/`**: Stateful illumination assessment and adaptive histogram equalization (CLAHE) for low-light stability.
- **`src/dip_touchless/tracking/`**: MediaPipe hand landmark detection with strict validity checking and boundary protection.
- **`src/dip_touchless/filtering/`**: Low-pass and adaptive 1-Euro signal filtering to eliminate landmark jitter without introducing perceptual latency.
- **`src/dip_touchless/interaction/`**: Gesture detection (pinch, dwell, grip) mapped to 3D rotation, scaling, translation, and UI selection.
- **`submission/stem_ui/`**: Hardware-accelerated OpenGL user interface with 4 dedicated interactive domains (3D Solids, Chemistry, Gestures, and Physics).

