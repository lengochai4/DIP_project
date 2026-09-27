# 01 — Master Project Specification

**Specification set:** Canonical v1.2  
**Project type:** Digital Image Processing final-term project + research-ready prototype  
**Platform:** Python + one RGB webcam  
**Application:** Real-time touchless interaction with rendered 3D STEM content

## 1. Project title

### Vietnamese

**Xây dựng hệ thống tương tác không chạm thời gian thực cho học tập STEM 3D sử dụng tiền xử lý ảnh thích ứng và lọc tín hiệu chuyển động từ webcam RGB**

### English

**Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing and Motion Signal Filtering with a Single RGB Camera**

## 2. Problem statement

Low-cost RGB-webcam hand interaction is affected by illumination variation, landmark jitter, temporary tracking loss, and the smoothing-versus-responsiveness trade-off. The project investigates whether a lightweight, reproducible Digital Image Processing and temporal-filtering pipeline can improve the stability and practical usability of a hand-driven rendered 3D STEM interaction without depth hardware, multi-camera reconstruction, cloud inference, or unrelated large-model components.

## 3. Primary objective

Design, implement, and experimentally evaluate a modular pipeline:

```text
RGB Webcam / Recorded Replay
        ↓
Frame + Timing Contract
        ↓
ROI Management
        ↓
Illumination Analysis
        ↓
Adaptive ROI Preprocessing
        ↓
Hand Landmark Provider
        ↓
Measurement Validation
        ↓
Raw / Canonical / Adaptive Temporal Filtering
        ↓
Gesture + Coordinate Mapping
        ↓
InteractionState
        ↓
Rendered 3D STEM Extension
```

The primary academic contribution is the **DIP + temporal signal-processing pipeline and its evaluation**. The 3D application is a demonstration/validation layer, not the research contribution itself.

## 4. Research questions

### RQ1 — Illumination preprocessing

Under the tested lighting conditions, does ROI-based adaptive illumination preprocessing improve hand-landmark detection/tracking robustness or stability compared with unprocessed input?

### RQ2 — Temporal filtering

Does the proposed bounded adaptive 1-Euro strategy reduce measured temporal jitter while preserving responsiveness compared with raw landmarks and a canonical fixed 1-Euro baseline?

### RQ3 — Practical interaction

Can the resulting processed signal support stable real-time touchless manipulation of rendered 3D STEM objects using a single RGB camera under the tested conditions?

The RQs are questions. The specifications MUST NOT encode their answers in advance.

## 5. Required course scope

The final-term baseline MUST include:

- one RGB webcam acquisition path;
- deterministic replay for fair comparison and regression testing;
- explicit frame/timestamp handling;
- ROI state management and fallback;
- HSV-based illumination assessment;
- adaptive CLAHE/bypass preprocessing;
- a MediaPipe Hand Landmarker adapter;
- project-owned landmark/data contracts;
- explicit measurement validity and optional documented measurement quality;
- raw landmark baseline;
- canonical fixed 1-Euro baseline with derivative low-pass `d_cutoff`;
- bounded adaptive 1-Euro filter;
- tracking-loss/reacquisition handling;
- gesture mapping with hysteresis where state switching occurs;
- rendered 3D STEM interaction;
- structured run logging and resolved configuration capture;
- minimal quantitative evaluation sufficient to answer RQ1 and RQ2;
- optional inferential statistics only when the team deliberately adopts them and has adequate repeated-trial evidence;
- automated tests for research-critical behavior;
- reproducible report figures/tables from recorded run artifacts.

## 6. Explicit non-goals

The course project MUST NOT expand into:

- metric 3D hand reconstruction;
- replacement of a depth camera;
- multi-camera fusion;
- multi-user tracking;
- full-body tracking;
- general object recognition;
- YOLO integration merely for additional detection;
- Transformer-based vision research;
- cloud inference or cloud backend requirements;
- a full VR/AR platform;
- a full physics engine;
- enterprise accounts/telemetry/update infrastructure;
- a broad commercial product build.

The term **3D** means interaction with a rendered 3D scene. MediaPipe/model-relative landmark `z` MUST NOT be described as measured physical camera depth.

## 7. DIP Core vs 3D Extension

The project has two architectural zones:

- **DIP Core** — the research/processing path.
- **3D Extension** — the application/demo layer.

The Core is the academic priority; the Extension demonstrates the processed signal. Exact module responsibilities, dependency direction, and public boundary contracts are owned only by `02_ARCHITECTURE_AND_CONTRACTS.md`.

## 8. Academic positioning

The project is a Digital Image Processing project because the evaluated pipeline includes:

- ROI processing;
- color-space transformation;
- illumination descriptors/statistics;
- adaptive contrast enhancement with CLAHE;
- temporal signal filtering;
- robustness/stability measurement;
- optional descriptive software-processing diagnostics;
- controlled ablation and reproducible evaluation.

MediaPipe is an external landmark provider. The report MUST NOT present MediaPipe, CLAHE, the canonical 1-Euro filter, quaternion math, or standard picking mathematics as newly invented methods.

## 9. Contribution boundary

If supported by measured evidence, the report MAY claim contributions such as:

1. a practical ROI-based adaptive illumination-preprocessing pipeline for this interaction setting;
2. a bounded adaptive 1-Euro strategy built on the canonical 1-Euro framework;
3. a reproducible comparison of stability, responsiveness, and illumination robustness;
4. a real-time 3D STEM prototype driven by the processed hand signal.

The report MUST distinguish:

```text
existing method/component
vs
project integration/adaptation
vs
measured project result
```

## 10. Required experimental evidence

The final project MUST include controlled evidence for:

- the unprocessed vs adaptive-preprocessing question in RQ1;
- raw vs canonical fixed vs proposed adaptive temporal behavior in RQ2;
- practical rendered interaction for RQ3; no FPS, latency, accuracy, or percentage-improvement threshold is required.

The exact baseline labels, minimum metrics, trial design, equations, and any optional statistical procedures are owned only by `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 11. Measurement-quality dependency

RQ2 and the course scope MUST remain implementable when no valid per-observation quality signal is available from the selected provider. The exact `MeasurementQuality` semantics are owned only by `02_ARCHITECTURE_AND_CONTRACTS.md`; algorithm behavior when quality is unavailable is owned only by `03_ALGORITHM_AND_EXPERIMENTS.md`.

## 12. Practical success interpretation

A successful final project is not defined by a preselected FPS, accuracy, or percentage improvement. Success means the system and report satisfy the final Definition of Done in `05_PROJECT_STATUS_AND_ROADMAP.md`, and conclusions are limited to what recorded experiments support.

## 13. Future research/product boundary

After course completion, the same architecture may support stronger datasets, more sessions/users, stronger calibration, alternate providers, device compatibility work, packaging, UX, accessibility, privacy/security hardening, and product validation.

Those items are FUTURE unless `05_PROJECT_STATUS_AND_ROADMAP.md` promotes them into a later phase. They are not required to answer RQ1–RQ3.
