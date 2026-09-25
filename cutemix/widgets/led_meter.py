"""
Segmented LED Ladder Meter Widget with Peak-Hold and Latching Clip Lamp.
Inspired by hardware LED ladders on MOTU interfaces and analog mixing desks.
Click to reset latching clip indicator. Supports Mono or Stereo modes.
"""

from ..qt_compat import QtCore, QtGui, QtWidgets, Qt, is_qt_available

if is_qt_available():
    class LedLadderMeter(QtWidgets.QWidget):
        """
        Segmented LED bar meter with peak-hold and latching clip lamp.
        """
        ZONES = [
            (0.00, 0.70, QtGui.QColor("#2ec468")),  # Green (-inf to -12 dB)
            (0.70, 0.90, QtGui.QColor("#f0a63a")),  # Amber (-12 to -2 dB)
            (0.90, 1.00, QtGui.QColor("#e24b4b")),  # Red (-2 to 0 dB)
        ]
        PEAK_DECAY = 0.35  # Fraction per second
        CLIP_THRESHOLD = 0.98

        def __init__(self, is_stereo: bool = False, parent=None):
            super().__init__(parent)
            self.is_stereo = is_stereo

            # Mono / Left levels
            self.level_l: float = 0.0
            self.peak_l: float = 0.0
            self.clip_l: bool = False

            # Right levels (for stereo mode)
            self.level_r: float = 0.0
            self.peak_r: float = 0.0
            self.clip_r: bool = False

            self.clip_lamp_height = 8

            width = 18 if is_stereo else 10
            self.setMinimumWidth(width)
            self.setMaximumWidth(width + 4)
            self.setMinimumHeight(140)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
            self.setToolTip("Click to reset clip lamp")

        def setLevel(self, val: float):
            """Sets mono level (0.0 .. 1.0)."""
            v = max(0.0, min(1.0, float(val)))
            self.level_l = v
            if v > self.peak_l:
                self.peak_l = v
            if v >= self.CLIP_THRESHOLD:
                self.clip_l = True
            self.update()

        def setStereoLevels(self, left: float, right: float):
            """Sets stereo levels (0.0 .. 1.0)."""
            vl = max(0.0, min(1.0, float(left)))
            vr = max(0.0, min(1.0, float(right)))

            self.level_l = vl
            if vl > self.peak_l:
                self.peak_l = vl
            if vl >= self.CLIP_THRESHOLD:
                self.clip_l = True

            self.level_r = vr
            if vr > self.peak_r:
                self.peak_r = vr
            if vr >= self.CLIP_THRESHOLD:
                self.clip_r = True

            self.update()

        def decay(self, dt: float):
            """Decays peak-hold indicators."""
            changed = False
            if self.peak_l > 0.0:
                self.peak_l = max(self.level_l, self.peak_l - self.PEAK_DECAY * dt)
                changed = True
            if self.is_stereo and self.peak_r > 0.0:
                self.peak_r = max(self.level_r, self.peak_r - self.PEAK_DECAY * dt)
                changed = True
            if changed:
                self.update()

        def clearClip(self):
            self.clip_l = False
            self.clip_r = False
            self.update()

        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self.clearClip()
                event.accept()

        def paintEvent(self, event: QtGui.QPaintEvent):
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)

            w = self.width()
            h = self.height()

            # Background housing
            painter.fillRect(0, 0, w, h, QtGui.QColor("#08090b"))

            if self.is_stereo:
                bar_w = (w - 3) / 2.0
                self._draw_single_meter(painter, 0, bar_w, h, self.level_l, self.peak_l, self.clip_l)
                self._draw_single_meter(painter, bar_w + 2, bar_w, h, self.level_r, self.peak_r, self.clip_r)
            else:
                self._draw_single_meter(painter, 0, w, h, self.level_l, self.peak_l, self.clip_l)

        def _draw_single_meter(self, painter: QtGui.QPainter, x: float, w: float, h: float, level: float, peak: float, clip: bool):
            lamp_h = self.clip_lamp_height
            bar_y = lamp_h + 2
            bar_h = h - bar_y - 1

            # 1. Clip Lamp at top
            clip_color = QtGui.QColor("#ff3333") if clip else QtGui.QColor("#241414")
            painter.fillRect(QtCore.QRectF(x, 0, w, lamp_h), clip_color)

            # 2. Ladder Bar Segments
            # Draw segment by segment from bottom up
            segment_h = 3.0
            gap = 1.0
            step = segment_h + gap
            num_segments = int(bar_h / step)

            for i in range(num_segments):
                # Fraction from 0.0 (bottom) to 1.0 (top)
                frac = (i + 1) / float(num_segments)
                seg_y = (bar_y + bar_h) - ((i + 1) * step)

                # Determine zone color
                seg_color = QtGui.QColor("#2ec468")
                for z_min, z_max, color in self.ZONES:
                    if frac >= z_min:
                        seg_color = color

                # Is this segment lit by signal level?
                if frac <= level:
                    painter.fillRect(QtCore.QRectF(x + 1, seg_y, w - 2, segment_h), seg_color)
                else:
                    # Dim unlit LED
                    dim_color = QtGui.QColor(seg_color.red() // 6, seg_color.green() // 6, seg_color.blue() // 6)
                    painter.fillRect(QtCore.QRectF(x + 1, seg_y, w - 2, segment_h), dim_color)

            # 3. Peak-Hold Indicator
            if peak > 0.02:
                peak_y = (bar_y + bar_h) - (peak * bar_h)
                painter.fillRect(QtCore.QRectF(x + 1, peak_y - 1, w - 2, 2), QtGui.QColor("#ffffff"))
