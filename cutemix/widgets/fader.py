"""
Custom Studio Vertical Fader Widget for CuteMix.
Features calibrated dB scale ticks, smooth mouse gestures (drag, wheel, double-click to unity),
brushed metal slider caps, and fine control modifier keys.
"""

import math
from ..qt_compat import QtCore, QtGui, QtWidgets, Signal, Qt, is_qt_available
from ..osc.cuemix_protocol import norm_to_db, db_to_norm, format_db

if is_qt_available():
    class StudioFader(QtWidgets.QWidget):
        """
        Long-throw studio vertical fader with audio-taper scale and decibel tick marks.
        """
        valueChanged = Signal(float)  # Emitted when value changes from user interaction
        sliderMoved = Signal(float)   # Emitted continuously during dragging

        # Calibrated dB ticks: (dB, label, is_major)
        DB_TICKS = [
            (6.0, "+6", False),
            (0.0, " 0", True),
            (-6.0, "-6", False),
            (-12.0, "12", False),
            (-18.0, "18", False),
            (-24.0, "24", False),
            (-36.0, "36", False),
            (-48.0, "48", False),
            (-60.0, "inf", False),
        ]

        def __init__(self, is_master: bool = False, parent=None):
            super().__init__(parent)
            self.is_master = is_master
            self._norm_value: float = 0.78  # Default to Unity (0 dB)
            self._is_dragging: bool = False
            self._drag_start_y: float = 0.0
            self._drag_start_val: float = 0.78
            self._is_muted: bool = False

            # Cap dimensions
            self.cap_height = 24
            self.cap_width = 30
            self.track_width = 6

            self.setMinimumWidth(38)
            self.setMinimumHeight(160)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setMouseTracking(True)
            self._update_tooltip()

        def value(self) -> float:
            return self._norm_value

        def db_value(self) -> float:
            return norm_to_db(self._norm_value)

        def setValue(self, val: float):
            clamped = max(0.0, min(1.0, float(val)))
            if abs(self._norm_value - clamped) > 1e-4:
                self._norm_value = clamped
                self._update_tooltip()
                self.update()
                self.valueChanged.emit(self._norm_value)

        def setValueSilent(self, val: float):
            """Updates fader position without emitting valueChanged signal."""
            clamped = max(0.0, min(1.0, float(val)))
            if abs(self._norm_value - clamped) > 1e-4:
                self._norm_value = clamped
                self._update_tooltip()
                self.update()

        def setMuted(self, muted: bool):
            if self._is_muted != muted:
                self._is_muted = muted
                self.update()

        def _update_tooltip(self):
            db = self.db_value()
            self.setToolTip(f"{format_db(db)} (Double-click for 0 dB Unity)")

        def _track_rect(self) -> QtCore.QRectF:
            h = self.height()
            w = self.width()
            top = self.cap_height / 2.0
            bottom = h - (self.cap_height / 2.0)
            track_h = max(10.0, bottom - top)
            center_x = (w - 14) / 2.0  # Leave room on the right for ticks
            return QtCore.QRectF(center_x - (self.track_width / 2.0), top, self.track_width, track_h)

        def _val_to_y(self, val: float) -> float:
            tr = self._track_rect()
            return tr.bottom() - (val * tr.height())

        def _y_to_val(self, y: float) -> float:
            tr = self._track_rect()
            if tr.height() <= 0:
                return 0.0
            return max(0.0, min(1.0, (tr.bottom() - y) / tr.height()))

        # ----------------- Mouse & Wheel Events -----------------

        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                y = event.position().y() if hasattr(event, "position") else event.y()
                cap_y = self._val_to_y(self._norm_value)

                # If click is near cap, start dragging from cap
                if abs(y - cap_y) <= self.cap_height:
                    self._is_dragging = True
                    self._drag_start_y = y
                    self._drag_start_val = self._norm_value
                else:
                    # Jump directly to clicked position
                    new_val = self._y_to_val(y)
                    self.setValue(new_val)
                    self._is_dragging = True
                    self._drag_start_y = y
                    self._drag_start_val = new_val
                event.accept()

        def mouseMoveEvent(self, event: QtGui.QMouseEvent):
            if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                y = event.position().y() if hasattr(event, "position") else event.y()
                dy = self._drag_start_y - y
                tr = self._track_rect()

                # Fine tuning if Shift or Ctrl pressed
                modifiers = event.modifiers()
                scale = 0.15 if (modifiers & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)) else 1.0

                delta_val = (dy / tr.height()) * scale
                new_val = max(0.0, min(1.0, self._drag_start_val + delta_val))
                if abs(new_val - self._norm_value) > 1e-4:
                    self._norm_value = new_val
                    self._update_tooltip()
                    self.update()
                    self.valueChanged.emit(self._norm_value)
                    self.sliderMoved.emit(self._norm_value)
                event.accept()

        def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_dragging = False
                event.accept()

        def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                # Double-click resets to Unity (0 dB = 0.78)
                self.setValue(0.78)
                event.accept()

        def wheelEvent(self, event: QtGui.QWheelEvent):
            delta = event.angleDelta().y()
            step = 0.015 if delta > 0 else -0.015
            if event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                step *= 0.2
            self.setValue(self._norm_value + step)
            event.accept()

        # ----------------- Painting -----------------

        def paintEvent(self, event: QtGui.QPaintEvent):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

            w = self.width()
            h = self.height()
            tr = self._track_rect()

            # 1. Draw dB Ticks & Labels on the right side
            painter.setFont(QtGui.QFont("Monospace", 7))
            tick_x_left = tr.right() + 4
            tick_x_right = tr.right() + 7

            for db_val, label, is_major in self.DB_TICKS:
                norm_pos = db_to_norm(db_val)
                ty = self._val_to_y(norm_pos)

                if is_major:  # 0 dB Unity line
                    painter.setPen(QtGui.QPen(QtGui.QColor("#2ec4d6"), 1.5))
                    painter.drawLine(QtCore.QPointF(tr.left() - 4, ty), QtCore.QPointF(tick_x_right + 3, ty))
                    painter.setPen(QtGui.QColor("#4fd6e6"))
                    painter.drawText(int(tick_x_right + 5), int(ty + 3), label)
                else:
                    painter.setPen(QtGui.QPen(QtGui.QColor("#454b54"), 1.0))
                    painter.drawLine(QtCore.QPointF(tick_x_left, ty), QtCore.QPointF(tick_x_right, ty))
                    painter.setPen(QtGui.QColor("#6d737d"))
                    painter.drawText(int(tick_x_right + 4), int(ty + 3), label)

            # 2. Draw Track Groove
            groove_path = QtGui.QPainterPath()
            groove_path.addRoundedRect(tr, 3, 3)

            # Inset background
            painter.fillPath(groove_path, QtGui.QColor("#0a0b0d"))
            painter.setPen(QtGui.QPen(QtGui.QColor("#1e2229"), 1.0))
            painter.drawPath(groove_path)

            # 3. Draw Center Guide Slot
            slot_x = tr.center().x()
            painter.setPen(QtGui.QPen(QtGui.QColor("#050506"), 1.5))
            painter.drawLine(QtCore.QPointF(slot_x, tr.top() + 2), QtCore.QPointF(slot_x, tr.bottom() - 2))

            # 4. Draw Fader Cap
            cap_y = self._val_to_y(self._norm_value)
            cap_rect = QtCore.QRectF(
                slot_x - (self.cap_width / 2.0),
                cap_y - (self.cap_height / 2.0),
                self.cap_width,
                self.cap_height
            )

            # Cap Shadow
            shadow_rect = cap_rect.translated(0, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 140))
            painter.drawRoundedRect(shadow_rect, 4, 4)

            # Cap Body Gradient
            grad = QtGui.QLinearGradient(cap_rect.topLeft(), cap_rect.bottomLeft())
            if self.is_master:
                # Anodized Studio Red Cap
                grad.setColorAt(0.0, QtGui.QColor("#ff6b6b"))
                grad.setColorAt(0.45, QtGui.QColor("#d42f2f"))
                grad.setColorAt(0.55, QtGui.QColor("#9c1a1a"))
                grad.setColorAt(1.0, QtGui.QColor("#d93838"))
                border_color = QtGui.QColor("#6b1414")
                notch_color = QtGui.QColor("#ffffff")
            else:
                # Brushed Studio Silver/Metal Cap
                grad.setColorAt(0.0, QtGui.QColor("#e8eff5"))
                grad.setColorAt(0.45, QtGui.QColor("#afbfc9"))
                grad.setColorAt(0.55, QtGui.QColor("#768694"))
                grad.setColorAt(1.0, QtGui.QColor("#b0c0cc"))
                border_color = QtGui.QColor("#45525e")
                notch_color = QtGui.QColor("#1b1e22")

            if self._is_muted:
                painter.setOpacity(0.55)

            painter.setBrush(grad)
            painter.setPen(QtGui.QPen(border_color, 1.0))
            painter.drawRoundedRect(cap_rect, 3, 3)

            # Grip Lines / Notch
            painter.setPen(QtGui.QPen(notch_color, 1.5))
            painter.drawLine(
                QtCore.QPointF(cap_rect.left() + 4, cap_y),
                QtCore.QPointF(cap_rect.right() - 4, cap_y)
            )

            # Upper and Lower Grip Grooves
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 50), 1.0))
            painter.drawLine(QtCore.QPointF(cap_rect.left() + 6, cap_y - 4), QtCore.QPointF(cap_rect.right() - 6, cap_y - 4))
            painter.drawLine(QtCore.QPointF(cap_rect.left() + 6, cap_y + 4), QtCore.QPointF(cap_rect.right() - 6, cap_y + 4))

            painter.setOpacity(1.0)
