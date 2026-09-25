"""
Custom Studio Rotary Potentiometer (Knob) Widget for CuteMix.
Supports Pan (bipolar LED arc, center detent) and Trim/Gain (unipolar arc).
Smooth vertical dragging, fine modifiers, and double-click reset.
"""

import math
from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..osc.cuemix_protocol import norm_to_pan, format_pan, norm_to_trim, format_trim

if is_qt_available():
    class RotaryKnob(QtWidgets.QWidget):
        valueChanged = Signal(float)  # Emitted when value changed by user

        def __init__(self, mode: str = "pan", default_val: float = 0.5, parent=None):
            super().__init__(parent)
            self.mode = mode.lower()  # 'pan' or 'trim'
            self.default_val = default_val
            self._norm_value: float = default_val

            self._is_dragging: bool = False
            self._drag_start_y: float = 0.0
            self._drag_start_val: float = default_val

            self.setFixedSize(36, 46)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._update_tooltip()

        def value(self) -> float:
            return self._norm_value

        def setValue(self, val: float):
            clamped = max(0.0, min(1.0, float(val)))
            if abs(self._norm_value - clamped) > 1e-4:
                self._norm_value = clamped
                self._update_tooltip()
                self.update()
                self.valueChanged.emit(self._norm_value)

        def setValueSilent(self, val: float):
            clamped = max(0.0, min(1.0, float(val)))
            if abs(self._norm_value - clamped) > 1e-4:
                self._norm_value = clamped
                self._update_tooltip()
                self.update()

        def _update_tooltip(self):
            if self.mode == "pan":
                p = norm_to_pan(self._norm_value)
                self.setToolTip(f"Pan: {format_pan(p)} (Double-click to Center)")
            else:
                t = norm_to_trim(self._norm_value)
                self.setToolTip(f"Trim: {format_trim(t)} (Double-click to 0 dB)")

        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_dragging = True
                self._drag_start_y = event.position().y() if hasattr(event, "position") else event.y()
                self._drag_start_val = self._norm_value
                event.accept()

        def mouseMoveEvent(self, event: QtGui.QMouseEvent):
            if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                y = event.position().y() if hasattr(event, "position") else event.y()
                dy = self._drag_start_y - y
                modifiers = event.modifiers()
                scale = 0.003 if (modifiers & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)) else 0.008

                delta_val = dy * scale
                new_val = max(0.0, min(1.0, self._drag_start_val + delta_val))

                # Center detent for Pan
                if self.mode == "pan" and abs(new_val - 0.5) < 0.025:
                    new_val = 0.5

                if abs(new_val - self._norm_value) > 1e-4:
                    self._norm_value = new_val
                    self._update_tooltip()
                    self.update()
                    self.valueChanged.emit(self._norm_value)
                event.accept()

        def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_dragging = False
                event.accept()

        def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self.setValue(self.default_val)
                event.accept()

        def wheelEvent(self, event: QtGui.QWheelEvent):
            delta = event.angleDelta().y()
            step = 0.02 if delta > 0 else -0.02
            if event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                step *= 0.2
            self.setValue(self._norm_value + step)
            event.accept()

        def paintEvent(self, event: QtGui.QPaintEvent):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

            center_x = 18.0
            center_y = 17.0
            radius = 11.0

            # Sweep definition: 270 degrees total
            # Starts at 225 deg (7:30 o'clock), ends at -45 deg (4:30 o'clock)
            # In Qt degrees (1/16 of degree): 0 deg is 3 o'clock, 90 is 12 o'clock
            arc_start_deg = 225.0
            arc_total_span = -270.0

            # 1. Background Arc Track
            track_rect = QtCore.QRectF(center_x - radius - 2, center_y - radius - 2, (radius + 2) * 2, (radius + 2) * 2)
            painter.setPen(QtGui.QPen(QtGui.QColor("#22262d"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(track_rect, int(arc_start_deg * 16), int(arc_total_span * 16))

            # 2. Active LED Arc
            if self.mode == "pan":
                # Bipolar arc from 12 o'clock (90 deg in Qt)
                led_color = QtGui.QColor("#2ec4d6")
                val_diff = self._norm_value - 0.5  # -0.5 to +0.5
                start_angle = 90.0
                span_angle = -val_diff * 270.0
                painter.setPen(QtGui.QPen(led_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawArc(track_rect, int(start_angle * 16), int(span_angle * 16))

                # Center tick dot
                painter.setPen(QtGui.QPen(QtGui.QColor("#7d8591"), 1.5))
                painter.drawPoint(int(center_x), int(center_y - radius - 3))
            else:
                # Unipolar arc for Trim (from bottom-left 225 deg)
                led_color = QtGui.QColor("#f0a63a")
                span_angle = -self._norm_value * 270.0
                painter.setPen(QtGui.QPen(led_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawArc(track_rect, int(arc_start_deg * 16), int(span_angle * 16))

            # 3. Knob Body
            knob_rect = QtCore.QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            grad = QtGui.QRadialGradient(center_x - 3, center_y - 3, radius)
            grad.setColorAt(0.0, QtGui.QColor("#454b54"))
            grad.setColorAt(0.7, QtGui.QColor("#23262c"))
            grad.setColorAt(1.0, QtGui.QColor("#141619"))

            painter.setPen(QtGui.QPen(QtGui.QColor("#0d0e10"), 1.0))
            painter.setBrush(grad)
            painter.drawEllipse(knob_rect)

            # 4. Indicator Needle / Pointer
            # Angle in radians
            angle_deg = arc_start_deg + (self._norm_value * arc_total_span)
            rad = math.radians(angle_deg)
            nx = center_x + (radius - 2.5) * math.cos(rad)
            ny = center_y - (radius - 2.5) * math.sin(rad)
            cx = center_x + 3.0 * math.cos(rad)
            cy = center_y - 3.0 * math.sin(rad)

            pointer_color = QtGui.QColor("#ffffff") if self.mode == "pan" else QtGui.QColor("#ffc266")
            painter.setPen(QtGui.QPen(pointer_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(nx, ny))

            # 5. Value Text underneath
            painter.setFont(QtGui.QFont("Monospace", 7, QtGui.QFont.Weight.Bold))
            if self.mode == "pan":
                txt = format_pan(norm_to_pan(self._norm_value))
                painter.setPen(QtGui.QColor("#9ca5b0"))
            else:
                txt = format_trim(norm_to_trim(self._norm_value))
                painter.setPen(QtGui.QColor("#f0a63a"))

            painter.drawText(QtCore.QRectF(0, 32, self.width(), 13), int(Qt.AlignmentFlag.AlignCenter), txt)
