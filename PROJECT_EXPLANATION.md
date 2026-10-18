# TÀI LIỆU TOÀN DIỆN VỀ DỰ ÁN DIP TOUCHLESS STEM
## GIẢI THÍCH KIẾN TRÚC, LUỒNG HOẠT ĐỘNG VÀ CHI TIẾT TỪNG FILE MÃ NGUỒN

---

## MỤC LỤC
1. [Tổng quan dự án & Vấn đề giải quyết](#1-t%E1%BB%95ng-quan-d%E1%BB%B1-%C3%A1n--v%E1%BA%A5n-%C4%91%E1%BB%81-gi%E1%BA%A3i-quy%E1%BA%BFt)
2. [Sơ đồ kiến trúc & Luồng dữ liệu (Data Pipeline)](#2-s%C6%A1-%C4%91%E1%BB%93-ki%E1%BA%BFn-tr%C3%BAc--lu%E1%BB%93ng-d%E1%BB%AF-li%E1%BB%87u-data-pipeline)
3. [Phân tách hai phân vùng: DIP Core vs 3D Extension](#3-ph%C3%A2n-t%C3%A1ch-hai-ph%C3%A2n-v%C3%B9ng-dip-core-vs-3d-extension)
4. [Giải thích chi tiết từng thư mục, từng file mã nguồn & các hàm bên trong](#4-gi%E1%BA%A3i-th%C3%ADch-chi-ti%E1%BA%BFt-t%E1%BB%ABng-th%C6%B0-m%E1%BB%A5c-t%E1%BB%ABng-file-m%C3%A3-ngu%E1%BB%93n--c%C3%A1c-h%C3%A0m-b%C3%AAn-trong)
   - [4.1. Module `core` (`src/dip_touchless/core/`)](#41-module-core-srcdip_touchlesscore)
   - [4.2. Module `capture` (`src/dip_touchless/capture/`)](#42-module-capture-srcdip_touchlesscapture)
   - [4.3. Module `preprocessing` (`src/dip_touchless/preprocessing/`)](#43-module-preprocessing-srcdip_touchlesspreprocessing)
   - [4.4. Module `tracking` (`src/dip_touchless/tracking/`)](#44-module-tracking-srcdip_touchlesstracking)
   - [4.5. Module `filtering` (`src/dip_touchless/filtering/`)](#45-module-filtering-srcdip_touchlessfiltering)
   - [4.6. Module `interaction` (`src/dip_touchless/interaction/`)](#46-module-interaction-srcdip_touchlessinteraction)
   - [4.7. Module `runtime` (`src/dip_touchless/runtime/`)](#47-module-runtime-srcdip_touchlessruntime)
   - [4.8. Module `configuration` (`src/dip_touchless/configuration/`)](#48-module-configuration-srcdip_touchlessconfiguration)
   - [4.9. Module `telemetry` (`src/dip_touchless/telemetry/`)](#49-module-telemetry-srcdip_touchlesstelemetry)
   - [4.10. Module `stem3d` (`extensions/stem3d/`)](#410-module-stem3d-extensionsstem3d)
   - [4.11. Module `experiments` (`experiments/`)](#411-module-experiments-experiments)
   - [4.12. Module `analysis` (`analysis/`)](#412-module-analysis-analysis)
5. [Nguyên lý toán học của các thuật toán cốt lõi](#5-nguy%C3%AAn-l%C3%BD-to%C3%A1n-h%E1%BB%8Dc-c%E1%BB%A7a-c%C3%A1c-thu%E1%BA%ADt-to%C3%A1n-c%E1%BB%91t-l%C3%B5i)
   - [5.1. Đánh giá ánh sáng HSV & Hysteresis](#51-%C4%91%C3%A1nh-gi%C3%A1-%C3%A1nh-s%C3%A1ng-hsv--hysteresis)
   - [5.2. Tiền xử lý cục bộ CLAHE](#52-ti%E1%BB%81n-x%E1%BB%AD-l%C3%BD-c%E1%BB%A5c-b%E1%BB%99-clahe)
   - [5.3. Bộ lọc 1-Euro kinh điển (Canonical Fixed 1-Euro)](#53-b%E1%BB%99-l%E1%BB%8Dc-1-euro-kinh-%C4%91i%E1%BB%83n-canonical-fixed-1-euro)
   - [5.4. Bộ lọc thích ứng có chặn ngưỡng (Bounded Adaptive 1-Euro)](#54-b%E1%BB%99-l%E1%BB%8Dc-th%C3%ADch-%E1%BB%A9ng-c%C3%B3-ch%E1%BA%B7n-ng%C6%B0%E1%BB%A1ng-bounded-adaptive-1-euro)
   - [5.5. Cử chỉ Pinch & Vùng chết liên tục (Continuous Deadzone)](#55-c%E1%BB%AD-ch%E1%BB%89-pinch--v%C3%B9ng-ch%E1%BA%BFt-li%C3%AAn-t%E1%BB%A5c-continuous-deadzone)
6. [Các quy tắc khoa học bất biến](#6-c%C3%A1c-quy-t%E1%BA%AFc-khoa-h%E1%BB%8Dc-b%E1%BA%A5t-bi%E1%BA%BFn)
7. [Hướng dẫn chạy các chương trình (Demo, Replay, Tests)](#7-h%C6%B0%E1%BB%9Bng-d%E1%BA%ABn-ch%E1%BA%A1y-c%C3%A1c-ch%C6%B0%C6%A1ng-tr%C3%ACnh-demo-replay-tests)

---

## 1. Tổng quan dự án & Vấn đề giải quyết

Dự án **DIP Touchless STEM** (*Xây dựng hệ thống tương tác không chạm thời gian thực cho học tập STEM 3D sử dụng tiền xử lý ảnh thích ứng và lọc tín hiệu chuyển động từ webcam RGB*) giải quyết bài toán tương tác tự nhiên với mô hình 3D trong môi trường lớp học/thực hành STEM mà **chỉ dùng 1 webcam RGB phổ thông**.

### Thách thức chính của Webcam thông thường:
1. **Thay đổi điều kiện chiếu sáng (Illumination Variations):** Phòng học có thể bị ngược sáng, tối hoặc chói làm giảm tỉ lệ phát hiện bàn tay.
2. **Rung giật điểm mốc (Landmark Jitter):** Khi người dùng giữ yên bàn tay, các điểm mốc MediaPipe vẫn bị rung vi mô khiến vật thể 3D bị lắc.
3. **Mâu thuẫn giữa Làm mịn (Smoothing) và Độ nhạy (Responsiveness):** Nếu lọc rung quá mạnh thì khi tay di chuyển nhanh sẽ bị trễ (lag); nếu giảm lọc để nhạy thì tay dừng lại sẽ bị rung.
4. **Mất dấu tạm thời (Temporary Tracking Loss):** Khi tay bị che khuất một phần hoặc di chuyển nhanh ra ngoài biên, cần xử lý trơn tru để không làm giật vật thể 3D.

Hệ thống tập trung giải quyết toàn bộ các vấn đề trên bằng **đường ống xử lý ảnh số và xử lý tín hiệu thời gian (DIP Core)**, trong khi lớp hiển thị 3D chỉ là ứng dụng minh họa.

---

## 2. Sơ đồ kiến trúc & Luồng dữ liệu (Data Pipeline)

Hệ thống hoạt động theo đường ống xử lý một chiều, không có vòng lặp phụ thuộc ngược:

```text
[ Webcam Thực (camera.py) / Video Replay (replay.py) ]
                          │
                          ▼
                   [ FramePacket ]
                          │
                          ▼
                    [ ROIManager ] ◄── Nhận bbox từ frame trước (t - 1)
                          │            (SEARCHING / TRACKING / COASTING)
                          ▼
               [ IlluminationAnalyzer ] (Trích xuất mean, std, p10, p90 từ kênh V trong HSV)
                          │
                          ▼
             [ IlluminationDecisionStabilizer ] (Làm mịn EMA + Ngưỡng trễ Hysteresis)
                          │
                          ▼
               [ AdaptivePreprocessor ] (Áp dụng CLAHE kênh V nếu ánh sáng kém)
                          │
                          ▼
             [ MediaPipeHandLandmarkerProvider ] (Phát hiện 21 điểm mốc giải phẫu)
                          │
                          ▼
               [ MeasurementValidator ] (Thẩm định: đủ 21 mốc, giá trị finite, loại trừ rác)
                          │
                          ▼
                [ TemporalFilter ] (F0 Raw / F1 Fixed 1-Euro / F2 Adaptive 1-Euro)
                          │
                          ▼
                  [ TrackingFrame ] (Tập hợp mốc thô, mốc lọc, ROI, ánh sáng, timings)
                          │
                          ▼
                [ GestureEngine ] (Pinch Ratio, Ngưỡng trễ Hysteresis, Continuous Deadzone)
                          │
                          ▼
                [ InteractionState ] (pointer_xy, pinch_active, rotation_delta, scale_delta)
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
 [ 3D STEM Extension ]             [ FileRunLogger ]
 (Hiển thị vật thể 3D OpenGL)    (Ghi frames.csv, events.csv, metadata.json)
```

---

## 3. Phân tách hai phân vùng: DIP Core vs 3D Extension

Dự án áp dụng nguyên lý kiến trúc sạch (Clean Architecture):

| Phân vùng | Thư mục | Trách nhiệm | Nguyên tắc phụ thuộc |
| :--- | :--- | :--- | :--- |
| **DIP Core** | `src/dip_touchless/` | Trung tâm nghiên cứu học thuật: tiền xử lý ảnh, bám vết, lọc tín hiệu, tính cử chỉ, ghi log. | Hoàn toàn độc lập. **Tuyệt đối không import Pygame, OpenGL hay bất kỳ thành phần nào của thư mục `extensions/`**. |
| **3D Extension** | `extensions/stem3d/` | Lớp ứng dụng demo: nhận trạng thái cử chỉ và vẽ mô hình 3D trong cửa sổ Pygame/OpenGL. | Chỉ phụ thuộc vào các hợp đồng công khai (`InteractionState`) từ DIP Core. Không can thiệp vào logic xử lý ảnh. |

---

## 4. Giải thích chi tiết từng thư mục, từng file mã nguồn & các hàm bên trong

### 4.1. Module `core` (`src/dip_touchless/core/`)

Nơi định nghĩa ngôn ngữ chung của toàn dự án (Data Contracts, Enums, Protocols).

#### [`enums.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py)
Chứa các kiểu liệt kê chuẩn hóa:
- [`ColorSpace`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L10): Không gian màu (`BGR`, `RGB`, `HSV`, `GRAY`).
- [`TrackingStatus`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L17): Trạng thái nhận diện (`NO_HAND`: không có tay; `VALID`: phát hiện hợp lệ; `TEMPORARY_LOSS`: tạm mất dấu; `REACQUIRED`: bắt lại được dấu; `INVALID`: dữ liệu bất thường).
- [`ROIState`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L25): Trạng thái vùng quan tâm (`SEARCHING`: tìm kiếm toàn khung hình; `TRACKING`: đang bám vết bàn tay; `COASTING`: mở rộng vùng tìm kiếm tạm thời khi vừa mất dấu).
- [`IlluminationState`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L31): Trạng thái chiếu sáng (`NORMAL`, `LOW_LIGHT`, `LOW_CONTRAST`, `DIFFICULT`).
- [`FilterMode`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L38): Chế độ bộ lọc (`RAW`, `ONE_EURO_FIXED`, `ONE_EURO_ADAPTIVE`).
- [`QualitySource`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L44): Nguồn gốc thông số chất lượng (`NONE`, `PROVIDER_DOCUMENTED`, `EXPERIMENTAL_DERIVED`).
- [`CoordinateSpace`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/enums.py#L50): Không gian tọa độ (`FRAME_PIXEL`, `FRAME_NORMALIZED`, `VIEWPORT`, `NDC`, `WORLD_RENDER`, `MODEL_RELATIVE_Z`).

#### [`contracts.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py)
Chứa các lớp dữ liệu bất biến (`dataclass(frozen=True)`):
- [`FramePacket`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L25): Đóng gói khung hình gồm `run_id`, `frame_id`, `timestamp_s`, mảng ảnh `image` (numpy array) và `color_space`. Tự kiểm tra tính hợp lệ qua `__post_init__`.
- [`ROI`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L51): Vùng chữ nhật với `x, y, width, height` và `state`.
- [`IlluminationMetrics`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L66): Kết quả phân tích độ sáng gồm `mean_v`, `std_v`, `p10_v`, `p90_v`, `robust_range_v`, `state` và cờ kích hoạt CLAHE `enhancement_active`.
- [`Landmark`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L77): Một điểm mốc giải phẫu gồm `index` (0-20), tọa độ `x, y, z` và không gian tọa độ.
- [`MeasurementQuality`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L93): Thông số độ tin cậy đo đạc chuẩn hóa $[0, 1]$. Phương thức [`unavailable()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L114) dùng khi không có số liệu chất lượng thực tế.
- [`LandmarkObservation`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L125): Quan sát thô từ bộ bám vết gồm 21 mốc, nhãn tay trái/phải (`handedness_label`), điểm tự tin của bộ nhận diện tay (`handedness_score`), bounding box và tên provider.
- [`FilterDiagnostics`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L138): Chẩn đoán nội bộ của bộ lọc: bước thời gian `dt_s`, vận tốc lọc `speed`, hệ số `beta`, tần số cắt `min_cutoff_hz`, `final_cutoff_hz`, hệ số làm mịn `signal_alpha`, `derivative_alpha`, và cờ `reset_occurred`.
- [`StageTimings`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L152): Thời gian tính toán bằng mili-giây của từng giai đoạn: tiền xử lý, bám vết, lọc, tính cử chỉ và tổng thời gian tính toán.
- [`TrackingFrame`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L161): Gói dữ liệu trung tâm chứa đồng thời mốc thô (`raw_landmarks`), mốc đã lọc (`filtered_landmarks`), thông số ánh sáng, ROI, chẩn đoán bộ lọc và thời gian xử lý.
- [`InteractionState`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L177): Hợp đồng đầu ra của DIP Core gửi sang 3D Extension gồm `pointer_xy`, `pinch_ratio`, cờ `pinch_active`, góc xoay `rotation_delta` (yaw, pitch) và tỉ lệ phóng to/thu nhỏ `scale_delta`.

#### [`interfaces.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py)
Khai báo các giao diện trừu tượng (`Protocol`):
- [`FrameSource`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py#L21): Giao diện nguồn cấp frame (`open()`, `read()`, `close()`).
- [`LandmarkProvider`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py#L35): Giao diện bộ phát hiện mốc bàn tay (`process(frame)`).
- [`LandmarkFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py#L44): Giao diện bộ lọc thời gian (`update(observation)`, `reset()`).
- [`GestureEngine`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py#L57): Giao diện máy trạng thái cử chỉ (`update(frame)`, `reset()`).
- [`RunLogger`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/interfaces.py#L70): Giao diện ghi vết thực nghiệm (`start_run()`, `log_tracking_frame()`, `log_interaction_state()`, `log_event()`, `close()`).

---

### 4.2. Module `capture` (`src/dip_touchless/capture/`)

Thu nhận khung hình từ phần cứng hoặc video thu sẵn, đảm bảo tính toàn vẹn của nhãn thời gian (timestamp).

#### [`camera.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py)
Lớp [`OpenCVCameraSource`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L24):
- [`__init__(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L27): Khởi tạo tham số camera (index, width, height, fps, backend như `dshow`, `msmf`).
- [`open()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L106): Mở camera qua `cv2.VideoCapture`, thiết lập kích thước và lưu mốc thời gian ban đầu bằng đồng hồ độ chính xác cao đơn điệu (`time.perf_counter`).
- [`read()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L158): Đọc một frame BGR, kiểm tra tính hợp lệ qua [`_validate_frame()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L213), tính nhãn thời gian thực $t = \text{now} - \text{start\_time}$, bảo đảm $t$ tăng đơn điệu và đóng gói thành [`FramePacket`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L25).
- [`close()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/camera.py#L236): Giải phóng tài nguyên camera phần cứng.

#### [`replay.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/replay.py)
Lớp [`ReplayFrameSource`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/replay.py#L14):
- Dùng trong các bài thực nghiệm so sánh đối đầu (deterministic replay).
- [`open()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/replay.py#L49): Mở video và đọc thông số FPS gốc.
- [`read()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/capture/replay.py#L91): Đọc tuần tự từng frame và gán timestamp toán học:
  $$\text{timestamp\_s} = \frac{\text{frame\_id}}{\text{source\_fps}}$$
  Đảm bảo mọi cấu hình chạy lại trên cùng một video đều nhận được chuỗi thời gian hoàn toàn giống nhau 100%. Trả về `None` khi kết thúc video.

---

### 4.3. Module `preprocessing` (`src/dip_touchless/preprocessing/`)

Module xử lý ảnh số (DIP) cốt lõi: quản lý vùng bàn tay, phân tích độ sáng và tăng cường tương phản thích ứng.

#### [`roi.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/roi.py)
Lớp [`ROIManager`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/roi.py#L10):
- Quản lý máy trạng thái ROI:
  - `SEARCHING`: Khi chưa có bàn tay, ROI là toàn bộ khung hình.
  - `TRACKING`: Khi có bounding box từ frame trước, mở rộng với lề đệm `padding_ratio` (mặc định 30%) để ôm trọn vùng bàn tay.
  - `COASTING`: Khi vừa mất dấu bàn tay, mở rộng tiếp với tỉ lệ `coast_expand_ratio` và duy trì trong tối đa `coast_frames` khung hình trước khi rơi về `SEARCHING`.
- [`update(frame_width, frame_height, hand_bbox)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/roi.py#L94): Cập nhật trạng thái và trả về tọa độ ROI cho frame hiện tại.
- [`reset()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/roi.py#L88): Đưa trạng thái về lại `SEARCHING`.

#### [`illumination.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination.py)
Lớp [`IlluminationAnalyzer`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination.py#L28):
- [`measure(frame, roi)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination.py#L31): Cắt vùng ảnh ROI, chuyển từ BGR sang HSV qua `cv2.cvtColor`, tách riêng kênh $V$ (Value - độ sáng). Tính toán:
  - Giá trị trung bình độ sáng $\mu_V = \text{mean}(V)$.
  - Độ lệch chuẩn $\sigma_V = \text{std}(V)$.
  - Phân vị 10% ($P_{10}$) và phân vị 90% ($P_{90}$).
  - Dải tương phản bền vững: $\text{robust\_range\_v} = P_{90} - P_{10}$ (loại bỏ 10% điểm tối nhất và 10% điểm chói nhất).

#### [`illumination_decision.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination_decision.py)
Lớp [`IlluminationDecisionStabilizer`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination_decision.py#L13):
- Chống nhấp nháy trạng thái (state chatter):
  - Làm mịn số liệu qua EMA: $V_{\text{EMA}}(t) = \alpha \cdot V(t) + (1 - \alpha) \cdot V_{\text{EMA}}(t-1)$.
  - Phân loại trạng thái qua ngưỡng trễ (Hysteresis):
    - `LOW_LIGHT`: Kích hoạt khi $V_{\text{EMA}} < \text{enter\_v}$, chỉ tắt khi $V_{\text{EMA}} \ge \text{exit\_v}$.
    - `LOW_CONTRAST`: Kích hoạt khi $\text{Range}_{\text{EMA}} < \text{enter\_range}$, chỉ tắt khi $\text{Range}_{\text{EMA}} \ge \text{exit\_range}$.
    - `DIFFICULT`: Thỏa mãn cả 2 điều kiện trên.
    - `NORMAL`: Ánh sáng đạt yêu cầu.
- [`update(descriptors)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/illumination_decision.py#L91): Trả về [`IlluminationMetrics`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L66).

#### [`adaptive_preprocessor.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/adaptive_preprocessor.py)
Lớp [`AdaptivePreprocessor`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/adaptive_preprocessor.py#L35):
- Khởi tạo bộ cân bằng lược đồ thích ứng giới hạn tương phản CLAHE qua `cv2.createCLAHE`.
- Hỗ trợ 3 chính sách: `adaptive` (tự động bật khi không phải `NORMAL`), `always` (luôn bật), `bypass` (luôn tắt làm đối chứng).
- [`process_roi(roi_bgr, illumination)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/adaptive_preprocessor.py#L136): Chuyển ROI sang HSV, áp dụng CLAHE lên riêng kênh $V$, ghép lại kênh $H, S$ gốc và chuyển về BGR (giữ nguyên sắc độ màu da).
- [`process_frame(frame, roi, illumination)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/preprocessing/adaptive_preprocessor.py#L88): Dán đè ROI đã xử lý lên khung hình gốc, giữ nguyên kích thước toàn khung.

---

### 4.4. Module `tracking` (`src/dip_touchless/tracking/`)

Tích hợp mô hình nhận diện bàn tay và kiểm định tính hợp lệ của dữ liệu.

#### [`mediapipe_provider.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/mediapipe_provider.py)
Lớp [`MediaPipeHandLandmarkerProvider`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/mediapipe_provider.py#L29):
- Đóng gói MediaPipe Tasks Vision (`HandLandmarker`).
- [`process(frame)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/mediapipe_provider.py#L113):
  1. Chuyển BGR sang RGB liên tục trong bộ nhớ (`np.ascontiguousarray`).
  2. Đổi timestamp sang mili-giây nguyên dương tăng đơn điệu.
  3. Gọi `detect_for_video(mp_image, timestamp_ms)`.
  4. Nếu không có bàn tay: Trả về trạng thái `NO_HAND` và danh sách mốc rỗng.
  5. Nếu có bàn tay: Trích xuất 21 mốc chuẩn hóa $[0, 1]$, gán nhãn `FRAME_NORMALIZED`.
  6. Tự động tính `hand_bbox` từ tọa độ cực trị (min/max) của các điểm mốc qua [`_derive_hand_bbox()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/mediapipe_provider.py#L298).
  7. **Kỷ luật khoa học:** Tuyệt đối không lấy `handedness_score` để mạo nhận làm độ tin cậy bám vết.

#### [`validator.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/validator.py)
Lớp [`MeasurementValidator`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/validator.py#L14):
- [`validate(observation)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/tracking/validator.py#L17): Kiểm tra dữ liệu: Nếu mất dấu (`NO_HAND`, `INVALID`, `TEMPORARY_LOSS`) thì mảng mốc bắt buộc phải rỗng; nếu có dấu (`VALID`, `REACQUIRED`) thì bắt buộc phải có đủ 21 mốc với tọa độ là các số thực hữu hạn (`math.isfinite`).

---

### 4.5. Module `filtering` (`src/dip_touchless/filtering/`)

Triển khai các phương pháp xử lý tín hiệu lọc rung chuyển động: F0 (Raw), F1 (Fixed 1-Euro) và F2 (Bounded Adaptive 1-Euro).

#### [`raw.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/raw.py)
- [`RawLandmarkFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/raw.py#L14): Baseline F0, trả về nguyên vẹn các mốc thô không qua làm mịn.

#### [`low_pass.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/low_pass.py)
- [`low_pass_alpha(dt_s, cutoff_hz)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/low_pass.py#L8): Tính hệ số lọc thông thấp bậc một:
  $$\tau = \frac{1}{2\pi f_c}, \quad \alpha = \frac{1}{1 + \tau / \Delta t}$$
- [`ScalarLowPassFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/low_pass.py#L63): Bộ lọc thông thấp bậc một: $\hat{x}_t = \alpha x_t + (1 - \alpha)\hat{x}_{t-1}$. Khung hình đầu tiên nhận trực tiếp giá trị đo làm gốc ($\hat{x}_0 = x_0$).

#### [`one_euro_scalar.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/one_euro_scalar.py)
- [`ScalarOneEuroFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/one_euro_scalar.py#L27): Bộ lọc 1-Euro kinh điển (Casiez et al., 2012) cho một trục tọa độ:
  1. Tính đạo hàm vận tốc thô: $dx = (x_t - \hat{x}_{t-1}) / \Delta t$.
  2. Lọc thông thấp đạo hàm vận tốc bằng tần số cắt cố định $f_{c,d}$ (`derivative_cutoff_hz`): $\hat{dx}_t = \text{LowPass}(dx, \alpha_d)$.
  3. Tính tần số cắt thích ứng theo vận tốc: $f_c = f_{c,\min} + \beta \cdot |\hat{dx}_t|$.
  4. Lọc tín hiệu vị trí chính: $\hat{x}_t = \text{LowPass}(x_t, \alpha_s)$.
  - Khi tay đứng yên: $|\hat{dx}| \approx 0 \Rightarrow f_c \approx f_{c,\min}$ nhỏ, lọc sạch rung lắc (jitter).
  - Khi tay di chuyển nhanh: $f_c$ tăng cao, mở rộng băng thông giúp loại bỏ độ trễ (lag).

#### [`one_euro_landmarks.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/one_euro_landmarks.py)
- [`FixedOneEuroLandmarkCore`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/one_euro_landmarks.py#L61): Vector hóa bộ lọc 1-Euro cho 21 mốc. Mỗi mốc có bộ lọc $X$ và $Y$ độc lập, nhưng chia sẻ chung tần số cắt $f_c$ tính từ vận tốc 2D $\sqrt{\hat{dx}^2 + \hat{dy}^2}$. Trục $Z$ được giữ nguyên (pass-through).

#### [`fixed_one_euro.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/fixed_one_euro.py)
- [`FixedOneEuroLandmarkFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/fixed_one_euro.py#L21): Lớp bọc Baseline F1 chuẩn hóa giao diện `LandmarkFilter`.

#### [`adaptive_policy.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_policy.py)
Chứa các hàm toán học thuần túy của phương pháp F2 đề xuất:
- [`adaptive_beta(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_policy.py#L35): Tính $\beta(v)$ biến thiên theo vận tốc và chặn trong dải $[\beta_{\min}, \beta_{\max}]$.
- [`bounded_final_cutoff_hz(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_policy.py#L218): Giới hạn tần số cắt cuối cùng trong khoảng an toàn $[f_{c,\text{final},\min}, f_{c,\text{final},\max}]$ để chống bùng nổ tần số khi gặp nhiễu đột biến.

#### [`adaptive_one_euro.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_one_euro.py) & [`adaptive_one_euro_landmarks.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_one_euro_landmarks.py)
- [`AdaptiveOneEuroLandmarkFilter`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/adaptive_one_euro.py#L21): Hiện thực hóa bộ lọc F2 đề xuất (Bounded Adaptive 1-Euro Filter).

#### [`temporal_controller.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/temporal_controller.py)
- [`OneEuroTemporalController`](file:///d:/DIPR/DIP_Project/src/dip_touchless/filtering/temporal_controller.py#L62): Bộ điều khiển thời gian dùng chung cho F1 và F2. Tự động tính $\Delta t$ và kích hoạt reset khi khoảng gián đoạn thời gian vượt quá `reset_gap_s` (tránh bắn vọt mốc khi bàn tay xuất hiện trở lại).

---

### 4.6. Module `interaction` (`src/dip_touchless/interaction/`)

Chuyển đổi tín hiệu mốc bàn tay đã lọc thành các lệnh tương tác không gian 3D.

#### [`gesture_math.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py)
- [`distance_xy(a, b)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py#L11): Khoảng cách Euclid giữa 2 điểm.
- [`normalized_pinch_ratio(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py#L32): Tính tỉ lệ chụm ngón tay: khoảng cách đầu ngón cái - đầu ngón trỏ chia cho khoảng cách cổ tay - khớp gốc ngón giữa (chuẩn hóa theo kích cỡ tay người dùng).
- [`apply_deadzone(value, deadzone)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py#L78): Hàm vùng chết liên tục $D(a, z)$ triệt tiêu vi rung lắc ngón tay mà không tạo bước nhảy gián đoạn.
- [`bounded_rotation_delta(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py#L106): Tính góc xoay yaw/pitch từ độ dời ngón trỏ.
- [`bounded_scale_delta(...)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_math.py#L163): Tính biến thiên phóng to/thu nhỏ khi đang chụm ngón.

#### [`gesture_engine.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_engine.py)
Lớp [`DeterministicGestureEngine`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_engine.py#L24):
- Quản lý máy trạng thái cử chỉ tất định:
  - Theo dõi con trỏ ngón trỏ (Landmark 8).
  - Trạng thái Pinch với 2 ngưỡng trễ riêng biệt: bật chụm ngón khi `pinch_ratio <= pinch_on`, tắt chụm ngón khi `pinch_ratio >= pinch_off`.
  - [`update(frame)`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_engine.py#L202): Xuất ra [`InteractionState`](file:///d:/DIPR/DIP_Project/src/dip_touchless/core/contracts.py#L177).
  - [`reset()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/interaction/gesture_engine.py#L187): Xóa sạch trạng thái cử chỉ khi mất dấu hoặc reset bộ lọc.

---

### 4.7. Module `runtime` (`src/dip_touchless/runtime/`)

Điều phối chu trình thực thi của toàn bộ pipeline.

#### [`realtime.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/runtime/realtime.py)
- Lớp [`RealtimeRuntime`](file:///d:/DIPR/DIP_Project/src/dip_touchless/runtime/realtime.py#L33): Vòng lặp đồng bộ thời gian thực điều phối:
  Camera $\to$ ROI $\to$ Tiền xử lý $\to$ Tracking $\to$ Validator $\to$ Filter $\to$ Gesture $\to$ Logger $\to$ Callbacks.
  Cung cấp bản sao của khung hình (`packet.image.copy()`) cho giao diện hiển thị, đảm bảo thao tác vẽ trên màn hình không làm ảnh hưởng vùng đệm tính toán của DIP Core.

#### [`replay.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/runtime/replay.py)
- Lớp [`ReplayRuntime`](file:///d:/DIPR/DIP_Project/src/dip_touchless/runtime/replay.py#L32): Vòng lặp chạy lại các tệp video đã ghi hình cho các bài thực nghiệm đối chứng tất định.

---

### 4.8. Module `configuration` (`src/dip_touchless/configuration/`)

Quản lý nạp, thẩm định và đóng băng cấu hình.
- [`loader.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/configuration/loader.py): Hàm [`resolve_config()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/configuration/loader.py#L102) đọc file YAML (`config/default.yaml`), hợp nhất giá trị ghi đè, đóng băng cấu hình (immutable) và tính mã băm SHA-256.
- [`validation.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/configuration/validation.py): Hàm [`validate_config()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/configuration/validation.py#L12) xác thực kiểu dữ liệu và miền giá trị của tất cả tham số.

---

### 4.9. Module `telemetry` (`src/dip_touchless/telemetry/`)

Thu thập siêu dữ liệu môi trường và xuất bản nhật ký thực nghiệm.
- [`metadata.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/telemetry/metadata.py): Hàm [`create_run_id()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/telemetry/metadata.py#L17) tạo mã chạy duy nhất. Hàm [`build_run_metadata()`](file:///d:/DIPR/DIP_Project/src/dip_touchless/telemetry/metadata.py#L84) thu thập thông tin phần cứng, OS, Git commit hash, SHA-256 của cấu hình và mô hình.
- [`run_logger.py`](file:///d:/DIPR/DIP_Project/src/dip_touchless/telemetry/run_logger.py): Lớp [`FileRunLogger`](file:///d:/DIPR/DIP_Project/src/dip_touchless/telemetry/run_logger.py#L88) ghi nhận chi tiết mỗi lần chạy vào một thư mục riêng biệt (`frames.csv`, `landmarks.csv`, `events.csv`, `summary.json`, `checksums.sha256`).

---

### 4.10. Module `stem3d` (`extensions/stem3d/`)

Lớp ứng dụng mở rộng tiêu thụ kết quả từ DIP Core để hiển thị tương tác 3D.
- [`scene_state.py`](file:///d:/DIPR/DIP_Project/extensions/stem3d/scene_state.py): Lớp [`Stem3DSceneState`](file:///d:/DIPR/DIP_Project/extensions/stem3d/scene_state.py#L20) tích lũy góc xoay yaw/pitch và tỉ lệ scale.
- [`renderer.py`](file:///d:/DIPR/DIP_Project/extensions/stem3d/renderer.py): Lớp [`OpenGLStemRenderer`](file:///d:/DIPR/DIP_Project/extensions/stem3d/renderer.py#L11) tạo cửa sổ Pygame/OpenGL, vẽ khối lập phương STEM 3D và hệ trục tọa độ RGB.
- [`application.py`](file:///d:/DIPR/DIP_Project/extensions/stem3d/application.py): Lớp [`Stem3DExtension`](file:///d:/DIPR/DIP_Project/extensions/stem3d/application.py#L32) kết nối `Stem3DSceneState` với Renderer.
- [`demo.py`](file:///d:/DIPR/DIP_Project/extensions/stem3d/demo.py): Smoke test chạy mô hình 3D với dữ liệu chuyển động giả lập (không cần webcam).
- [`live_demo.py`](file:///d:/DIPR/DIP_Project/extensions/stem3d/live_demo.py): Điểm khởi chạy ứng dụng Live Webcam hoàn chỉnh: hiển thị đồng thời cửa sổ 3D và bảng điều khiển camera OpenCV với đầy đủ thông số tracking, ROI, độ sáng, FPS và tần số cắt.

---

### 4.11. Module `experiments` (`experiments/`)

Hạ tầng chạy thực nghiệm tự động có tính lặp lại.
- [`manifest.py`](file:///d:/DIPR/DIP_Project/experiments/manifest.py): Đọc và thẩm định tệp YAML mô tả bộ thực nghiệm (`ExperimentManifest`).
- [`record_source.py`](file:///d:/DIPR/DIP_Project/experiments/record_source.py): Ghi lại các video mẫu MJPG chuẩn thô (Raw BGR) kèm mã băm SHA-256.
- [`run_replay.py`](file:///d:/DIPR/DIP_Project/experiments/run_replay.py): Chạy một điều kiện cấu hình cụ thể (`f0`, `f1`, `f2`, `p0`, `p1`) trên video replay.
- [`run_batch.py`](file:///d:/DIPR/DIP_Project/experiments/run_batch.py): Chạy hàng loạt các cặp thực nghiệm từ manifest và tạo `batch_index.json`.

---

### 4.12. Module `analysis` (`analysis/`)

Xử lý các tệp log kết quả thực nghiệm để tính toán số liệu thống kê khoa học và sinh biểu đồ báo cáo.
- [`run_loader.py`](file:///d:/DIPR/DIP_Project/analysis/run_loader.py): Đọc và nạp các artifact từ các lần chạy vào bộ nhớ.
- [`metrics.py`](file:///d:/DIPR/DIP_Project/analysis/metrics.py): Tính toán các chỉ số khoa học:
  - [`radial_rms_jitter()`](file:///d:/DIPR/DIP_Project/analysis/metrics.py#L160): Đo độ rung tĩnh trung bình bình phương (RMS) cho thực nghiệm A1:
    $$\text{Jitter}_{\text{RMS}} = \sqrt{ \frac{1}{N} \sum_{i=1}^N \Big( (x_i - \bar{x})^2 + (y_i - \bar{y})^2 \Big) }$$
  - [`trajectory_deviation_rmse()`](file:///d:/DIPR/DIP_Project/analysis/metrics.py#L279): Đo độ lệch quỹ đạo động so với F0 cho thực nghiệm A2:
    $$\text{RMSE}_{\text{deviation}} = \sqrt{ \frac{1}{N} \sum_{i=1}^N \Big( (x_{i} - x_{i,\text{F0}})^2 + (y_{i} - y_{i,\text{F0}})^2 \Big) }$$
  - [`valid_hand_observation_rate()`](file:///d:/DIPR/DIP_Project/analysis/metrics.py#L418): Đo tỉ lệ nhận diện bàn tay hợp lệ cho thực nghiệm B (tiền xử lý ánh sáng).
- [`dip_visual.py`](file:///d:/DIPR/DIP_Project/analysis/dip_visual.py): Trích xuất ảnh và biểu đồ phân bố histogram kênh V trước/sau CLAHE.
- [`regenerate.py`](file:///d:/DIPR/DIP_Project/analysis/regenerate.py): Tự động nạp `batch_index.json`, tính toán số liệu và xuất bảng Markdown/CSV cùng đồ thị Matplotlib.

---

## 5. Nguyên lý toán học của các thuật toán cốt lõi

### 5.1. Đánh giá ánh sáng HSV & Hysteresis
1. Tính giá trị phân vị $P_{10}$ và $P_{90}$ của mảng điểm ảnh kênh $V$.
2. Khoảng tương phản bền vững: $\text{Range}_V = P_{90} - P_{10}$.
3. Khử nhiễu qua bộ lọc trung bình động hàm mũ EMA:
   $$\bar{V}_t = \alpha_{\text{EMA}} V_t + (1 - \alpha_{\text{EMA}}) \bar{V}_{t-1}$$
4. Phân loại trạng thái bằng cơ chế trễ (Dual-threshold Hysteresis) để loại bỏ hiện tượng nhấp nháy chuyển trạng thái liên tục tại vùng biên.

### 5.2. Tiền xử lý cục bộ CLAHE
- Chỉ áp dụng lên kênh $V$ của ROI, giữ nguyên kênh $H$ và $S$ để bảo tồn sắc độ màu da.
- Chia kênh $V$ thành các ô nhỏ (Tile Grid, ví dụ $8 \times 8$).
- Cân bằng lược đồ trong từng ô với giới hạn cắt ngọn (Clip Limit, ví dụ 2.0) để phân phối lại các điểm tích tụ nhằm chống khuếch đại nhiễu hạt.
- Nội suy song tuyến tính giữa các ô liền kề để loại bỏ đường biên ô.
- Ghép kênh $V$ cải thiện với kênh $H, S$ gốc và dán đè chính xác vào tọa độ ROI trên khung hình gốc.

### 5.3. Bộ lọc 1-Euro kinh điển (Canonical Fixed 1-Euro)
- Khi người dùng giữ yên tay: Vận tốc $\hat{dx} \to 0$, tần số cắt $f_c \to f_{c,\min}$ làm giảm băng thông, lọc sạch rung giật tần số cao.
- Khi người dùng di chuyển tay: Vận tốc $\hat{dx}$ lớn, $f_c$ tăng tuyến tính theo độ dốc $\beta$, mở rộng băng thông để tín hiệu bám sát tức thời tay thật, triệt tiêu cảm giác trễ.
- Đặc biệt, hệ thống lọc đạo hàm vận tốc bằng tần số cắt độc lập $f_{c,d}$ để ngăn chặn xung đột giật cục do nhiễu vận tốc gây ra.

### 5.4. Bộ lọc thích ứng có chặn ngưỡng (Bounded Adaptive 1-Euro)
- Hệ số $\beta$ được điều chỉnh động theo dải vận tốc nhưng bị chặn trong khoảng $[\beta_{\min}, \beta_{\max}]$.
- Tần số cắt cuối cùng $f_c$ được bảo vệ bằng hai ngưỡng biên cứng:
  $$f_{c,\text{final}} = \text{clip}(f_{c,\min} + \beta(v) \cdot v, f_{c,\text{final},\min}, f_{c,\text{final},\max})$$
- Đảm bảo hệ thống vừa giữ được độ mượt mà khi dừng vừa không bao giờ bị mất ổn định tín hiệu khi có chấn động vận tốc đột ngột.

### 5.5. Cử chỉ Pinch & Vùng chết liên tục (Continuous Deadzone)
- Tỉ số khoảng cách ngón tay được chuẩn hóa theo kích thước bàn tay người dùng.
- Trạng thái chụm ngón (Pinch) sử dụng 2 ngưỡng riêng biệt: chạm ngón vào (`pinch_on = 0.35`) và nhả ngón ra (`pinch_off = 0.50`), tạo ra khoảng trễ 0.15 giúp thao tác gắp/thả vật thể 3D dứt khoát.
- Vùng chết liên tục $D(a, z)$ triệt tiêu vi rung lắc ngón tay mà không tạo bước nhảy gián đoạn vận tốc khi di chuyển:
  $$D(a, z) = \begin{cases} 0 & \text{nếu } |a| \le z \\ \text{sign}(a)(|a| - z) & \text{nếu } |a| > z \end{cases}$$

---

## 6. Các quy tắc khoa học bất biến

1. **Không mạo nhận độ tin cậy:** Tuyệt đối không lấy điểm số phân loại tay trái/phải (`handedness_score`) của MediaPipe để mạo nhận làm độ tin cậy bám vết (`tracking confidence`).
2. **Minh bạch khi mất dấu:** Khi không phát hiện thấy bàn tay, trả về danh sách rỗng rõ ràng; tuyệt đối không sinh ra các điểm mốc mang tọa độ $(0, 0, 0)$ giả tạo.
3. **Bản chất của trục Z:** Tọa độ $z$ của MediaPipe là giá trị tương đối so với cổ tay theo mô hình giải phẫu của Google, **tuyệt đối không mô tả hay mạo nhận nó là khoảng cách chiều sâu vật lý (metric camera depth)** từ bàn tay đến webcam.
4. **Bảo toàn hình học detector:** Mọi bước tiền xử lý ảnh (ROI, CLAHE) đều giữ nguyên kích thước khung hình gốc truyền vào detector để không làm lệch tỉ lệ hay méo hình học phát hiện.
5. **Trung thực trong số liệu khoa học:** Mọi con số báo cáo (FPS, jitter, độ trễ) phải xuất phát từ các lần chạy ghi log thực tế được ghi nhận trong tệp run artifact, tuyệt đối không bịa đặt hay làm tròn số liệu để chứng minh thuật toán vượt trội.

---

## 7. Hướng dẫn chạy các chương trình (Demo, Replay, Tests)

### Chạy Live Demo Webcam
```powershell
python -m extensions.stem3d.live_demo
```
*(Nhấn SPACE để bắt đầu, phím `R` để reset góc xoay vật thể, phím `ESC` hoặc `Q` để kết thúc)*

### Chạy Smoke Demo giả lập 3D (không cần Webcam)
```powershell
python -m extensions.stem3d.demo
```

### Chạy toàn bộ 433 bài kiểm thử tự động
```powershell
pytest
```

### Chạy một điều kiện Replay thực nghiệm
```powershell
python -m experiments.run_replay --profile f2 --source data/recordings/sample.mp4
```

### Trích xuất ảnh minh họa xử lý ảnh số CLAHE
```powershell
python -m analysis.dip_visual --source data/recordings/sample.mp4 --frame 120
```
