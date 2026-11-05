# DIP Touchless STEM

> **Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing and Motion Signal Filtering with a Single RGB Camera**  
> *Digital Image Processing (DIP) Graduation Capstone Project*

---

## 1. Project Overview

**DIP Touchless STEM** is an augmented reality (AR) interactive educational platform that operates using standard, low-cost monocular RGB webcams. By combining stateful Region of Interest (ROI) management, adaptive illumination analysis (CLAHE), Google MediaPipe hand landmark tracking, and 1-Euro motion signal filtering, the system provides responsive, jitter-free touchless manipulation of 3D STEM models without requiring dedicated depth sensors or wearable hardware.

### Key Highlights
- **End-to-End Image Processing Pipeline**: Stateful illumination assessment, adaptive CLAHE preprocessing, MediaPipe landmark tracking, and 1-Euro temporal filtering.
- **Markerless Touchless Interaction**: Pinch-to-grab, hover-to-dwell, and multi-finger plane/vertex geometry tracking.
- **4 Dedicated STEM Modules**:
  1. **3D Solid Shapes**: Real-time rendering, rotation, dilation, and vertex/plane construction using fingertip coordinates.
  2. **Interactive Chemistry Laboratory**: 118-element periodic table from PubChem, 72 molecular compounds, dynamic electron orbital animations, and 10 interactive chemical reaction simulations.
  3. **Gesture Tracking & Skeletons**: Live 21-landmark hand tracking with adaptive smoothing and fingertip polygon mapping.
  4. **Physics Laboratory**: 8 classical mechanics experiments with SI-unit analytical solvers (pendulum, spring-mass, projectile motion, collisions, lever equilibrium, pulley systems).

---

## 2. System Requirements

- **Operating System**: Windows 10 / Windows 11 (64-bit)
- **Python**: Python 3.11+ (64-bit)
- **Camera**: Standard built-in RGB webcam (USB) or smartphone camera via DroidCam (Wi-Fi)
- **Graphics**: OpenGL 2.1+ compatible GPU and display drivers

---

## 3. Quick Start & Execution Guide

### Option A: One-Click Launcher (Recommended for Windows)

1. **One-Time Environment Setup**:
   - Double-click **`Cai_dat_UI.bat`**  
     *(Or run in PowerShell: `python -X utf8 -m submission.setup_ui`)*  
     This automatically creates `.venv-ui`, installs all required dependencies according to `pyproject.toml`, and downloads/verifies Google MediaPipe hand tracking models with cryptographic SHA-256 validation.

2. **Launch Application**:
   - Double-click **`Chay_UI.bat`**  
     *(Or run in PowerShell: `.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app`)*

---

### Option B: Manual CLI Setup & Execution

1. **Create and Activate Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Upgrade Pip and Install Dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev,demo3d]"
   ```

3. **Launch the STEM Application**:
   ```powershell
   python -X utf8 -m submission.stem_ui.app
   ```

---

## 4. How to Use the Application

1. **Camera Connection**:
   - Click **Bật camera** (Turn on camera) to connect to the computer's webcam (Camera index 0–3).
   - Click **DroidCam** to connect to an external smartphone camera over local Wi-Fi (default port: `4747`).
2. **Main Hub Navigation**:
   - The central Home Hub features a circular wheel with 4 main sectors: **3D Solids**, **Chemistry**, **Tracking**, and **Physics**.
   - Hover over a sector and dwell or pinch to enter the corresponding laboratory.
3. **Touchless Gestures**:
   - **Pointer / Target**: Move your index finger in view of the camera to aim at buttons and objects.
   - **Pinch (Chụm ngón cái & trỏ)**: Bring thumb and index fingertips together to grab, manipulate, or rotate 3D objects, trigger sliders, and prepare chemical reactions.
   - **Dwell Selection**: Hold the pointer steady over a button for 1.0 second to automatically trigger an action without clicking.
   - **Reset View**: Press the **Đặt lại** (Reset) button to restore the camera view and objects to their initial orientation.

---

## 5. Project Structure

```text
DIP_project/
├── src/dip_touchless/          # DIP Core: Acquisition, Preprocessing, Tracking, 1-Euro Filtering
├── submission/stem_ui/        # Modern STEM UI: OpenGL Renderer, 4 Labs, Glass UI Theme
│   ├── app.py                 # Application entry point
│   ├── chemistry*.py          # 3D Molecule graphs, Periodic Table, and Reaction Simulator
│   ├── physics*.py            # Mechanics models, SI kinematic solvers, and UI widgets
│   ├── physics_labs.yaml      # Analytical parameters and formulas for 8 physics experiments
│   └── data/                  # PubChem periodic table, molecular structures, and compound templates
├── config/                    # Core pipeline and baseline configurations
├── experiments/               # Reproducible research replay scripts and comparison benchmarks
├── analysis/                  # Research telemetry and metrics aggregation
├── tests/                     # Automated unit and integration test suite (1,700+ tests)
├── models/README.md           # Hand landmark model provenance and SHA-256 verification
├── Cai_dat_UI.bat             # 1-Click automated environment setup batch script
├── Chay_UI.bat                # 1-Click application launcher batch script
└── README.md                  # Main project guide
```

---

## 6. Verification & Automated Testing

The codebase includes an exhaustive test suite covering all image processing pipelines, signal filters, physics kinematics, chemistry graphs, and touchless gesture mechanics.

To run the automated tests:
```powershell
pytest
```
*Verification status: **1,703 / 1,703 passed (100% pass rate)**.*

---

## 7. Deploy Website
url website: https://dipr-education-touchless-interaction.vercel.app/


## 8. Authors & Contributors
**Teacher**
- **Assoc.Prof.Hoang Van Dung**

**Project Group Members:**
- **Nguyễn Đăk Lộc** — Student ID: `24110107`
- **Trần Gia Kiệt** — Student ID: `24110103`
- **Lê Ngọc Hải** — Student ID: `24110089`


*Instructor & Academic Department: Faculty of Information Technology / Digital Image Processing Capstone.*
