# -*- coding: utf-8 -*-
"""浮窗基类 - 统一位置、动画、透明度处理"""
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtWidgets import QWidget


class FloatingWidgetBase(QWidget):
    """浮窗基类：统一位置、动画、透明度处理"""
    
    # 信号
    visibilityChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 1.0
        self._setup_base()
        
    def _setup_base(self):
        """基础设置"""
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setVisible(False)
        
    def set_opacity(self, opacity: float):
        """设置透明度"""
        self._opacity = max(0.0, min(1.0, opacity))
        self.setWindowOpacity(self._opacity)
        
    def get_opacity(self) -> float:
        """获取透明度"""
        return self._opacity
        
    def position_at_top_right(self, reference_widget: QWidget, offset_x: int = 0, offset_y: int = 0):
        """定位到参考控件的右上角"""
        if reference_widget is None:
            return
        ref_pos = reference_widget.mapToGlobal(reference_widget.rect().topRight())
        self.move(ref_pos.x() + offset_x, ref_pos.y() + offset_y)
        
    def position_at_bottom_right(self, reference_widget: QWidget, offset_x: int = 0, offset_y: int = 0):
        """定位到参考控件的右下角"""
        if reference_widget is None:
            return
        ref_pos = reference_widget.mapToGlobal(reference_widget.rect().bottomRight())
        self.move(ref_pos.x() + offset_x, ref_pos.y() + offset_y)
        
    def position_center(self, reference_widget: QWidget):
        """居中于参考控件"""
        if reference_widget is None:
            return
        ref_rect = reference_widget.rect()
        self.move(
            reference_widget.mapToGlobal(ref_rect.center()) - self.rect().center()
        )
        
    def show_with_animation(self, duration_ms: int = 200):
        """带动画显示"""
        self.show()
        self._fade_in(duration_ms)
        self.visibilityChanged.emit(True)
        
    def hide_with_animation(self, duration_ms: int = 200):
        """带动画隐藏"""
        self._fade_out(duration_ms)
        self.visibilityChanged.emit(False)
        
    def _fade_in(self, duration_ms: int = 200):
        """淡入动画"""
        anim = QPropertyAnimation(self, b"windowOpacity".encode(), self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0)
        anim.setEndValue(self._opacity)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._fade_anim = anim
        
    def _fade_out(self, duration_ms: int = 200):
        """淡出动画"""
        anim = QPropertyAnimation(self, b"windowOpacity".encode(), self)
        anim.setDuration(duration_ms)
        anim.setStartValue(self._opacity)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.finished.connect(self.hide)
        anim.start()
        self._fade_anim = anim
        
    def toggle(self):
        """切换显示/隐藏"""
        if self.isVisible():
            self.hide_with_animation()
        else:
            self.show_with_animation()
            
    def is_visible(self) -> bool:
        """检查是否可见"""
        return super().isVisible()
        
    # 确保兼容 Qt 的 property
    def getWindowOpacity(self):
        return self._opacity
        
    def setWindowOpacity(self, opacity):
        self._opacity = opacity
        super().setWindowOpacity(opacity)