from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QWidget,
)


class ContextUsageRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = 0
        self._ring_color = QColor("#5aa9ff")  # 普通上下文颜色
        self._compacted_color = QColor("#9b59b6")  # 压缩上下文颜色（紫色）
        self._track_color = QColor(255, 255, 255, 40)
        self._normal_tokens = 0  # 普通上下文 tokens
        self._compacted_tokens = 0  # 压缩上下文 tokens
        self.setFixedSize(18, 18)
        self.setToolTip("上下文占用：0%")

    def set_usage(
        self,
        percent: int,
        used_tokens: int,
        budget_tokens: int,
        compaction: dict = None,
        normal_tokens: int = 0,
        compacted_tokens: int = 0,
    ):
        self._percent = max(0, min(100, int(percent)))
        self._normal_tokens = normal_tokens
        self._compacted_tokens = compacted_tokens
        
        if self._percent >= 90:
            self._ring_color = QColor("#ff6b6b")
        elif self._percent >= 70:
            self._ring_color = QColor("#f6c453")
        else:
            self._ring_color = QColor("#5aa9ff")

        tooltip_lines = [
            "当前上下文占用",
            f"已用: {used_tokens} tokens",
            f"预算: {budget_tokens} tokens",
            f"占比: {self._percent}%",
        ]
        
        compaction = compaction or {}
        total_tokens = normal_tokens + compacted_tokens
        if compaction.get("active"):
            # 计算压缩占比和实际消息占比
            if total_tokens > 0:
                compact_ratio = int(compacted_tokens / total_tokens * 100)
                actual_ratio = int(normal_tokens / total_tokens * 100)
                tooltip_lines.extend(
                    [
                        "",
                        f"🔵 普通上下文: {normal_tokens} tokens ({actual_ratio}%)",
                        f"🟣 压缩上下文: {compacted_tokens} tokens ({compact_ratio}%)",
                        f"压缩条数: {compaction.get('summarized_count', 0)}",
                        f"保留条数: {compaction.get('kept_count', 0)}",
                    ]
                )
            else:
                tooltip_lines.extend(
                    [
                        "",
                        f"压缩条数: {compaction.get('summarized_count', 0)}",
                        f"保留条数: {compaction.get('kept_count', 0)}",
                    ]
                )
            note = str(compaction.get("note", "") or "").strip()
            if note:
                tooltip_lines.append(note)
        elif total_tokens > 0:
            tooltip_lines.append(f"实际消息: {normal_tokens} tokens")

        self.setToolTip("\n".join(tooltip_lines))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        start_angle = 90 * 16  # 从12点钟方向开始

        # 绘制背景轨道
        track_pen = QPen(self._track_color, 2.2)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 计算分段绘制
        total_tokens = self._normal_tokens + self._compacted_tokens
        
        if total_tokens > 0 and self._compacted_tokens > 0:
            # 分段绘制：先画压缩上下文（紫色），再画普通上下文（蓝色）
            normal_ratio = self._normal_tokens / total_tokens
            compacted_ratio = self._compacted_tokens / total_tokens
            
            # 压缩上下文弧段（前半段，紫色）
            compacted_span = int(-360 * 16 * (compacted_ratio * self._percent / 100))
            compacted_pen = QPen(self._compacted_color, 2.2)
            painter.setPen(compacted_pen)
            painter.drawArc(rect, start_angle, compacted_span)
            
            # 普通上下文弧段（后半段，蓝色）
            normal_span = int(-360 * 16 * (normal_ratio * self._percent / 100))
            ring_pen = QPen(self._ring_color, 2.2)
            painter.setPen(ring_pen)
            painter.drawArc(rect, start_angle + compacted_span, normal_span)
        else:
            # 统一颜色绘制（无压缩或只有普通上下文）
            span_angle = int(-360 * 16 * (self._percent / 100.0))
            ring_pen = QPen(self._ring_color, 2.2)
            painter.setPen(ring_pen)
            painter.drawArc(rect, start_angle, span_angle)
