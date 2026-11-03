"""Read-only camera and Analyze overlay; explicit full-frame letterboxing."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget
from app.rendering.transforms import fit_rect
from app.rendering.viewport import bgr_image
from app.interaction.hand_geometry import EDGES


class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.image = self.frame = None
        self.product_landmarks = {}
        self.mirror = True
        self.analyze = False
        self.message = "Camera stopped"

    def set_packet(self, packet, frame):
        self.image = bgr_image(packet.image)
        self.frame = frame
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#101a22"))
        if self.image is None:
            p.setPen(QColor("#93a8b4"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.message)
            return
        x, y, w, h = fit_rect(
            self.width(), self.height(), self.image.width(), self.image.height()
        )
        image = self.image.mirrored(True, False) if self.mirror else self.image
        p.drawImage(QRectF(x, y, w, h), image)
        if self.analyze and self.frame is not None:
            frame = self.frame
            for landmarks, color in (
                (frame.raw_landmarks, "#dd857c"),
                (frame.filtered_landmarks, "#72bfcc"),
            ):
                points = {
                    v.index: QPointF(
                        x + (1 - v.x if self.mirror else v.x) * w, y + v.y * h
                    )
                    for v in landmarks
                }
                p.setPen(QPen(QColor(color), 2.0))
                for a, b in EDGES:
                    if a in points and b in points:
                        p.drawLine(points[a], points[b])
            for landmarks in self.product_landmarks.values():
                points = {
                    v.index: QPointF(
                        x + (1 - v.x if self.mirror else v.x) * w, y + v.y * h
                    )
                    for v in landmarks
                }
                p.setPen(QPen(QColor("#bc9bc9"), 2.0))
                for a, b in EDGES:
                    if a in points and b in points:
                        p.drawLine(points[a], points[b])
            roi = frame.roi
            if roi:
                rx = (
                    1 - (roi.x + roi.width) / image.width()
                    if self.mirror
                    else roi.x / image.width()
                )
                p.setPen(QPen(QColor("#efca82"), 2.0))
                p.drawRect(
                    QRectF(
                        x + rx * w,
                        y + roi.y / image.height() * h,
                        roi.width / image.width() * w,
                        roi.height / image.height() * h,
                    )
                )
        p.end()
