# Model nhận tay

Bản nộp dùng MediaPipe Hand Landmarker float16, phiên bản model 1.

- Tài liệu chính thức: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- File: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
- Lưu tại `models/hand_landmarker.task`.
- SHA-256: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.

Chạy `Cai_dat_UI.bat` hoặc `py -3.12 -X utf8 -m submission.setup_ui` từ gốc repo
để tải và kiểm tra tự động. Binary không đưa vào Git. Sau lần cài đầu có thể
chạy bằng webcam offline; DroidCam cần mạng nội bộ. Không đổi model hoặc ngưỡng
nghiên cứu để tái hiện các kết quả đã chốt.

Nếu tải thủ công, dùng `Get-FileHash models/hand_landmarker.task -Algorithm SHA256`
và đối chiếu giá trị trên. Bộ cài không ghi đè model có hash khác.
