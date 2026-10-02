# DIP TOUCHLESS STEM V2
## Product, Interaction & Extension Specification

**Mục tiêu:** xây dựng một desktop STEM spatial-interaction application dùng webcam RGB, hỗ trợ điều khiển không chạm, nhiều STEM extension, one-hand/two-hand interaction và mô hình 3D gắn trực tiếp lên bàn tay trong camera view.

**Nguyên tắc nền:**
- G7/DIP Core và evidence giữ nguyên.
- V2 là product/interaction layer mới.
- Không scene nào đọc trực tiếp MediaPipe landmarks.
- Không gesture nào được phép sinh nhiều command cùng lúc.
- UNKNOWN, tracking loss hoặc reacquisition luôn fail-safe.
- Không coi MediaPipe z là metric depth.
- Không cố nhận biết “da hai ngón đã chạm thật”.
- Gesture phải được thiết kế theo thứ webcam quan sát ổn định.

---

# 1. KIẾN TRÚC TỔNG THỂ

```text
RGB CAMERA
    │
    ▼
────────────────────────────────
FROZEN DIP / G7 PIPELINE
────────────────────────────────
ROI
Illumination
Preprocessing
Landmark Provider
Validation
Temporal Filtering
    │
    ▼
Filtered hand observations
    │
    ├───────────────────────────────┐
    │                               │
    ▼                               ▼
Legacy Interaction            Product Hand Layer
(v1.0 fallback)               (V2)
                                    │
                                    ├─ Hand Geometry
                                    ├─ Finger States
                                    ├─ Pose Recognition
                                    ├─ Intentional Pinch
                                    ├─ Palm Frame
                                    ├─ Hand Association
                                    └─ Bimanual Geometry
                                            │
                                            ▼
                                      Intent Engine
                                            │
                                            ▼
                                      Intent Router
                                            │
                   ┌────────────────────────┼───────────────────────┐
                   ▼                        ▼                       ▼
             New Product UI          STEM Extensions          Hand Anchor
```

Hai pipeline interaction tồn tại song song:

```text
LEGACY
→ rollback / compatibility / fallback

PRODUCT
→ full-hand / two-hand / spatial interaction
```

Không tự động đổi giữa hai owner trong lúc đang thao tác.

---

# 2. PRODUCT HAND MODEL

## 2.1 One-hand

Một bàn tay có:

```text
21 landmarks
5 finger states
1 palm frame
1 pose state
1 intentional-pinch state
1 active intent owner
```

Không dùng:

```text
ring finger alone = command
pinky alone = command
middle alone = command
3 fingers = command
4 fingers = command
```

Các dạng này quá dễ nhầm và không đem lại UX tốt.

---

# 3. VOCABULARY CỬ CHỈ CHÍNH THỨC

V2 chỉ có **4 gesture nền**.

## 3.1 POINT

Hình dạng:

```text
Index extended
Middle/Ring/Pinky không extended
```

Ý nghĩa duy nhất:

```text
POINT / INSPECT
```

Dùng cho:

- con trỏ;
- hover;
- highlight;
- chọn mục tiêu trước khi thao tác;
- chỉ atom;
- chỉ điểm;
- probe vector;
- chỉ vị trí trên surface.

POINT không tự rotate model.

---

## 3.2 INTENTIONAL PINCH

Thumb + Index.

Không định nghĩa là:

```text
hai đầu ngón phải chạm da
```

Mà là:

```text
release reference
→ deliberate closing
→ entry
→ dwell
→ PINCH_ACTIVE
→ hold
→ release
→ rearm
```

Ý nghĩa duy nhất:

```text
PRIMARY ACTION / CLUTCH
```

Theo context:

```text
UI
→ click / confirm

object
→ select / grab

selected object
→ drag / manipulate

measurement
→ commit point

tool
→ confirm operation
```

Một PINCH_ACTIVE chỉ có một command owner.

---

## 3.3 OPEN PALM

Năm ngón mở đủ rõ.

Ý nghĩa:

```text
ANCHOR / PRESENT
```

Không phải nút click.

Dùng cho:

- đưa model lên lòng bàn tay;
- tạo hand-local workspace;
- giữ reference plane;
- release manipulation;
- presentation mode.

---

## 3.4 V-SIGN

Index + middle extended.

Ý nghĩa duy nhất:

```text
MEASURE / CREATE MODE
```

Không trực tiếp tạo geometry.

Sau khi vào mode:

```text
POINT
→ preview

PINCH
→ commit point
```

Ví dụ:

```text
point A
pinch
point B
pinch
→ distance/vector
```

---

# 4. GESTURE KHÔNG THUỘC BASELINE

## FIST

Không dùng mặc định.

Chỉ thêm sau khi physical validation đủ tốt.

Có thể dùng tương lai cho:

```text
cancel
pause
back
```

Nhưng UI luôn phải có nút Cancel/Back thật.

---

## Thumb + Middle / Thumb + Ring

Không nằm trong baseline V2.0.

Có thể nghiên cứu sau cho:

```text
secondary camera clutch
extension tool modifier
```

Chỉ thêm nếu physical validation chứng minh nhận ổn định.

---

# 5. STATE MACHINE ONE-HAND

```text
            ┌────────────┐
            │   NEUTRAL  │
            └─────┬──────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      POINT    OPEN PALM   V-SIGN
        │
        ▼
     CLOSING
        │
        ▼
   PINCH_ACTIVE
        │
        ▼
       HOLD
        │
        ▼
      RELEASE
        │
        ▼
      REARM
        │
        └────────→ POINT / NEUTRAL
```

Bất kỳ lúc nào:

```text
UNKNOWN
LOSS
RESET
TIMESTAMP GAP
REACQUISITION
```

→ command trở về neutral ngay.

Không giữ drag/scale/rotation qua tracking loss.

---

# 6. TWO-HAND MODEL

Hai tay không phải “10 nút”.

Chúng có hai vai trò:

```text
SUPPORT HAND
→ anchor / reference / workspace

DOMINANT HAND
→ point / manipulate / create
```

Cho phép người dùng đổi dominant hand trong Settings.

---

# 7. TWO-HAND GESTURES

## 7.1 HAND-ANCHORED MANIPULATION

```text
Support hand:
OPEN PALM
→ anchor object

Dominant hand:
POINT
→ inspect

Dominant PINCH
→ select / manipulate
```

Đây là interaction chính cho Hand-Anchored 3D.

---

## 7.2 TWO-HAND SCALE

Không scale chỉ vì hai tay tiến gần/ra xa.

Phải clutch rõ:

```text
Left PINCH_ACTIVE
+
Right PINCH_ACTIVE
→ BIMANUAL SCALE ACTIVE
```

Lấy khoảng cách hai palm center tại lúc bắt đầu làm reference.

```text
scale =
current palm-center distance
/
initial palm-center distance
```

Release một trong hai pinch:

```text
→ scale kết thúc
```

---

## 7.3 TWO-INDEX MEASUREMENT

```text
Index L
        ●────────────●
                 Index R
```

Hai POINT ổn định:

```text
→ preview distance/vector
```

Dwell:

```text
→ lock preview
```

PINCH dominant:

```text
→ commit measurement
```

Dùng cho:

- khoảng cách;
- vector;
- diameter;
- measurement plane;
- geometry construction.

---

## 7.4 SUPPORT PLANE

Support OPEN PALM:

```text
→ reference plane
```

Dominant POINT:

```text
→ project point lên plane
```

Dùng cho:

- Coordinate Geometry;
- Function Surface;
- Vector Field;
- shape construction.

---

# 8. INTENT CONTRACT

Scene không biết:

```text
thumb
index
finger IDs
MediaPipe
pose thresholds
```

Scene chỉ biết:

```text
IntentType
```

Contract đề xuất:

```python
GestureIntent:
    type
    phase
    hand_role

    pointer_xy
    delta_xy

    scale_factor

    world_or_scene_point
    anchor_pose

    tool_id

    validity
    reason

    cycle_id
```

IntentType:

```text
POINT
SELECT
GRAB
DRAG
SCALE
ANCHOR
RELEASE

MEASURE_BEGIN
MEASURE_UPDATE
MEASURE_COMMIT

TOOL_BEGIN
TOOL_UPDATE
TOOL_COMMIT

CANCEL
```

Phase:

```text
BEGIN
UPDATE
END
CANCEL
```

Không extension nào được nhận raw landmark.

---

# 9. HAND-ANCHORED 3D

Đây là feature flagship của V2.

## 9.1 Hai Render Mode

Mọi scene hỗ trợ:

```text
WORLD_VIEW
HAND_ANCHORED
```

Không tạo bản scene riêng.

---

## 9.2 Hand anchor

Dùng palm landmarks:

```text
0  wrist
5  index MCP
9  middle MCP
13 ring MCP
17 pinky MCP
```

Palm center:

```text
mean(0, 5, 9, 13, 17)
```

Scale:

```text
palm span trong image
```

Roll:

```text
orientation của MCP5 → MCP17
```

Pitch/yaw:

có thể dùng model-relative landmark geometry để tạo **visual orientation cue**.

Không gọi đây là metric physical pose.

---

## 9.3 Visual result

Camera:

```text
┌──────────────────────────────────────┐
│                                      │
│              MOLECULE                │
│                ⚛                     │
│             ───────                  │
│               🖐                     │
│                                      │
│          OPEN PALM ANCHOR             │
│                                      │
└──────────────────────────────────────┘
```

Object:

```text
position follows palm
orientation follows palm
scale follows palm span
```

Có smoothing riêng để model không rung.

---

# 10. UI V2 — XÂY LẠI HOÀN TOÀN

Không tiếp tục layout Workspace cũ.

Frontend mới:

```text
PySide6 Desktop Application
```

Dùng:

```text
QMainWindow
QOpenGLWidget
camera/video widget
native dock/panel system
centralized theme
```

Legacy Pygame/OpenGL shell giữ như fallback/debug, không phải product UI.

---

# 11. CẤU TRÚC GIAO DIỆN MỚI

```text
┌─────────────────────────────────────────────────────────────────────┐
│ DIP TOUCHLESS STEM                                  ● TRACKING OK   │
├───────────┬───────────────────────────────────────────┬─────────────┤
│           │                                           │             │
│  EXPLORE  │                                           │ INSPECTOR   │
│           │                                           │             │
│ Coordinate│              STEM VIEW                    │ Scene       │
│ Molecule  │                                           │ Selection   │
│ Orbital   │                                           │ Tool        │
│ Vector    │                                           │ Values      │
│ Surface   │                                           │             │
│ Wave      │                                           │             │
│           │                                           │             │
├───────────┴───────────────────────────────────────────┴─────────────┤
│  POINT     PINCH: READY     LEFT: SUPPORT     RIGHT: DOMINANT       │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 12. GLOBAL NAVIGATION

Left navigation:

```text
HOME
EXPLORE
ANALYZE
EVIDENCE
CALIBRATE
SETTINGS
HELP
```

Không để mode navigation chen vào scene controls.

---

# 13. HOME

Home không mở thẳng vào technical dashboard.

Hiển thị:

```text
Continue Exploring

STEM Labs
[Coordinate]
[Molecule]
[Orbital]
[Vector]
[Surface]
[Wave]

Interaction
Hand tracking: READY
Calibration: READY

Recent Session
```

Mục tiêu:

```text
app trước
research tool sau
```

---

# 14. EXPLORE

Explore là màn hình chính.

## Layout

Left:

```text
scene library
```

Center:

```text
3D viewport
hoặc
camera + hand-anchored overlay
```

Right:

```text
scene inspector
selected object
scene-specific tools
```

Bottom:

```text
active gesture
active hand
intent
tracking state
```

Không hiển thị ROI/CLAHE/filter ở Explore.

---

# 15. VIEW MODES

Scene header có:

```text
WORLD
HAND
```

WORLD:

```text
3D viewport chuẩn
```

HAND:

```text
live camera
+
3D hand-anchored overlay
```

Chuyển mode phải neutralize command trước.

---

# 16. ANALYZE

Analyze dành cho DIP.

Layout:

```text
Live Camera
Raw landmarks
Filtered landmarks
ROI

Pipeline
Camera
→ ROI
→ Illumination
→ Preprocess
→ MediaPipe
→ Filter
→ Hand Geometry
→ Intent

Diagnostics
tracking
filter
illumination
intent
run identity
timing
```

Không trộn Evidence vào Analyze.

---

# 17. EVIDENCE

Read-only.

```text
G7 Overview
A1 Static
A2 Dynamic
B Normal
B Low-light
RQ3
Limitations
Provenance
```

Không chạy lại experiment.

Không sửa artifact frozen.

---

# 18. CALIBRATION CENTER

Đây là màn hình riêng.

Flow:

```text
1. Position Hand
2. Comfortable Release
3. Intentional Pinch
4. Point
5. Open Palm
6. Validation
```

Hiển thị:

```text
tracking quality
reference acquired
gesture detected
cycle success
```

Không hiện threshold kỹ thuật cho user bình thường.

Advanced panel có thể hiện diagnostics.

---

# 19. SETTINGS

Sections:

```text
Interaction
───────────
Dominant hand
Pointer sensitivity
Manipulation sensitivity
Recalibrate

Visual
──────
Hand skeleton
Gesture labels
Grid
Object labels

Camera
──────
Camera source
Mirror preview

Accessibility
─────────────
Mouse fallback
Keyboard shortcuts
Dwell select
Reduced motion

Developer
─────────
Diagnostics
Run identity
Legacy mode
```

Mirror chỉ là presentation transform.

Pointer mapping phải đổi nhất quán.

---

# 20. DESIGN LANGUAGE

Không gaming HUD.

Phong cách:

```text
scientific
clean
dark
professional
calm
large readable typography
single primary accent
clear warning/error states
```

Không:

```text
neon rainbow
HUD brackets khắp màn hình
text kỹ thuật nhỏ li ti
animation thừa
```

---

# 21. STEM EXTENSION PLATFORM

Scene contract:

```python
StemExtension:
    id
    title
    category

    activate()
    deactivate()
    reset()

    update(dt)
    render(context)

    on_intent(intent)

    supports_hand_anchor
    tools
```

Scene không sở hữu camera/tracking.

---

# 22. V2 CORE EXTENSIONS

## 22.1 Coordinate Lab

Features:

```text
XYZ axes
grid
points
vectors
planes
transform visualization
distance
angle
coordinate inspection
```

Hand mode:

```text
coordinate frame anchored to palm
```

Two-hand:

```text
two index → vector
support palm → plane
```

---

## 22.2 Molecular Lab

Features:

```text
H2O
CH4
additional presets

atoms
bonds
bond angles
labels
selection
```

Hand mode:

```text
molecule floating over palm
```

Dominant point:

```text
highlight atom
```

Pinch:

```text
select atom / rotate molecule
```

Measure mode:

```text
bond distance
bond angle
```

---

## 22.3 Orbital Lab

Features:

```text
central body
orbit body
orbit path
relative motion
time control
```

Hand mode:

```text
orbital system on palm
```

Tools:

```text
radius
trajectory
period visualization
```

---

# 23. V2 NEW EXTENSIONS

## 23.1 Vector Lab

```text
2-point vector
vector addition
dot product
cross product
projection
components
```

Two index fingers cực kỳ phù hợp.

---

## 23.2 Function Surface Lab

```text
z = f(x,y)

presets:
plane
paraboloid
saddle
wave surface
Gaussian
```

Features:

```text
probe point
gradient direction
contours
cross-section
```

Hand mode:

```text
surface nằm trên palm plane
```

---

## 23.3 Wave & Signal Lab

Rất hợp môn DIP.

```text
sine
square
standing wave
sampling
frequency
amplitude
phase
filter response
```

Interaction:

```text
POINT
→ inspect sample

PINCH
→ move sample/probe

two index
→ interval
```

---

## 23.4 Vector Field Lab

```text
2D/3D arrows
field magnitude
streamline
probe
```

Examples:

```text
radial
rotational
electric
magnetic
fluid-like
```

Support palm:

```text
sampling plane
```

---

## 23.5 Optics Lab

```text
light ray
reflection
refraction
lens
mirror
```

POINT:

```text
move source
```

PINCH:

```text
place optical element
```

Two index:

```text
define ray / axis
```

---

## 23.6 Crystal Lattice Lab

```text
unit cell
atoms
lattice repetition
planes
```

Hand anchor rất phù hợp để “cầm” crystal.

---

# 24. FINGERTIP CONSTRUCTION TOOL

Không dùng gesture phức tạp.

Flow:

```text
MEASURE/CREATE mode
        ↓
POINT preview
        ↓
PINCH commit point
        ↓
POINT next
        ↓
PINCH commit
```

Từ đó dựng:

```text
2 points
→ line
→ vector
→ diameter

3 points
→ triangle
→ angle
→ plane

4 points
→ rectangle
→ quadrilateral

N points
→ polygon
```

Không cần “4 ngón tạo hình vuông” để baseline hoạt động.

Snap là tool hỗ trợ sau commit.

---

# 25. INTERACTION OWNERSHIP

Mỗi frame chỉ có:

```text
ONE INTENT OWNER
```

Priority:

```text
SYSTEM MODAL
    >
CALIBRATION
    >
UI
    >
TOOL
    >
SCENE
```

Nếu UI đang giữ pinch:

```text
scene receives neutral
```

Nếu scene đang drag:

```text
UI hover vẫn hiển thị
nhưng click disabled
```

---

# 26. SAFETY RULES

Bắt buộc:

```text
UNKNOWN
→ no command

tracking lost
→ cancel active intent

reacquisition
→ neutral
→ release required

run restart
→ reset all product state

scene switch
→ cancel interaction

render mode switch
→ cancel interaction

calibration/profile switch
→ cancel + rearm
```

Không có stale action.

---

# 27. VISUAL FEEDBACK

Camera overlay:

```text
hand skeleton
pointer
palm anchor
gesture state
```

Màu/state:

```text
READY
ARMING
ACTIVE
UNKNOWN
LOST
```

Không hiển thị “confidence %” giả.

---

# 28. FALLBACK

Mọi chức năng quan trọng có:

```text
mouse
keyboard
screen button
```

Gesture không phải con đường duy nhất để sử dụng application.

Legacy interaction:

```text
Settings
→ Interaction Engine
→ Legacy v1.0
```

---

# 29. PRODUCT RUNTIME STRUCTURE

Đề xuất package mới:

```text
app/
├── main.py
├── runtime/
│   ├── application_runtime.py
│   ├── hand_runtime.py
│   ├── intent_runtime.py
│   └── lifecycle.py
│
├── interaction/
│   ├── contracts.py
│   ├── hand_geometry.py
│   ├── pose.py
│   ├── intentional_pinch.py
│   ├── bimanual.py
│   └── router.py
│
├── ui/
│   ├── shell.py
│   ├── theme.py
│   ├── navigation.py
│   ├── explore.py
│   ├── analyze.py
│   ├── evidence.py
│   ├── calibration.py
│   ├── settings.py
│   └── components/
│
├── rendering/
│   ├── viewport.py
│   ├── camera_overlay.py
│   ├── hand_anchor.py
│   └── transforms.py
│
└── extensions/
    ├── registry.py
    ├── coordinate/
    ├── molecule/
    ├── orbital/
    ├── vector/
    ├── surface/
    ├── wave/
    ├── vector_field/
    └── optics/
```

Existing frozen/research code không bị chuyển vào đây.

---

# 30. IMPLEMENTATION ORDER

## P0 — Freeze

```text
tag v1.0 preserved
G7 preserved
new V2 branch
```

## P1 — New Product Shell

```text
PySide6 shell
navigation
theme
3D viewport
camera surface
lifecycle
```

Không gesture mới.

---

## P2 — One-Hand Intent

```text
POINT
intentional PINCH
OPEN PALM
V-SIGN
Intent Router
```

Legacy fallback giữ nguyên.

---

## P3 — Calibration

```text
release reference
pinch calibration
dominant hand
sensitivity
rearm
```

---

## P4 — Extension Migration

```text
Coordinate
Molecule
Orbital
```

migrate sang new Scene Extension API.

---

## P5 — Hand-Anchored Render Mode

```text
palm anchor
camera overlay
orientation smoothing
shared scene transform
```

Bắt đầu bằng Molecule.

Sau đó Coordinate và Orbital.

---

## P6 — Two-Hand Runtime

```text
2 hands
hand association
dominant/support roles
two-index measure
bimanual scale
```

---

## P7 — New STEM Extensions

```text
Vector
Function Surface
Wave/Signal
Vector Field
Optics
```

---

## P8 — Product Hardening

```text
error states
settings
accessibility
performance
resource cleanup
restart
```

---

## P9 — Validation

Engineering acceptance:

```text
intentional action success
>= 90%

release/rearm
>= 95%

false activation
<= 0.1 / valid-tracking minute

stuck actions
= 0

UNKNOWN safety violation
= 0

loss/reacquisition violation
= 0
```

Không gọi đây là research result.

---

# 31. DEFINITION OF DONE V2

V2 chỉ COMPLETE khi:

```text
[ ] New UI shell hoàn toàn thay UI cũ

[ ] Explore / Analyze / Evidence /
    Calibration / Settings / Help

[ ] POINT usable

[ ] Intentional PINCH usable

[ ] OPEN PALM anchor usable

[ ] V-SIGN measure mode usable

[ ] UNKNOWN/loss safe

[ ] legacy fallback còn chạy

[ ] Coordinate migrated

[ ] Molecule migrated

[ ] Orbital migrated

[ ] Hand-Anchored Molecule chạy thật

[ ] Hand-Anchored Coordinate chạy thật

[ ] Hand-Anchored Orbital chạy thật

[ ] two-hand provider hoạt động

[ ] two-index measurement hoạt động

[ ] bimanual scale hoạt động

[ ] Vector Lab

[ ] Function Surface

[ ] Wave/Signal

[ ] full regression pass

[ ] physical usability gate pass

[ ] clean shutdown/restart

[ ] packaging/docs/release complete
```

---

# 32. PRODUCT IDENTITY

Tên sản phẩm:

**DIP Touchless STEM**

Mô tả:

> A touchless spatial STEM visualization application driven by a reusable Digital Image Processing hand-interaction pipeline.

Không gọi:

```text
AR platform
commercially validated system
production-ready gesture engine
```

nếu chưa có bằng chứng tương ứng.

---

# 33. NGUYÊN TẮC CUỐI

Application phải có ba tầng độc lập:

```text
SEE
→ camera / DIP / tracking

INTERACT
→ point / pinch / hand anchor / two-hand

LEARN
→ STEM scenes / tools / measurements
```

Người học không cần biết MediaPipe.

Scene developer không cần biết gesture classifier.

Gesture layer không cần biết Molecule hay Orbital.

Core G7 không cần biết UI mới tồn tại.

Đó là kiến trúc cuối cần hướng tới.