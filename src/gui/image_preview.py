import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QScrollArea, QPushButton, QGroupBox, QFrame,
                           QDialog, QDesktopWidget)
from PyQt5.QtGui import QPixmap, QImage, QColor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from utils.resource_helper import get_resource_path

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FullSizeImageDialog(QDialog):
    """원본 크기 이미지를 표시하는 대화상자"""
    
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("원본 크기 이미지")
        self.setModal(False)  # 모달리스 대화상자로 설정
        
        # 애플리케이션 아이콘 설정
        icon_path = get_resource_path("resources/icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 창 크기 설정 (화면 크기를 고려하여 조정)
        screen = QDesktopWidget().availableGeometry()
        max_width = min(pixmap.width() + 40, screen.width() * 0.9)
        max_height = min(pixmap.height() + 40, screen.height() * 0.9)
        self.resize(max_width, max_height)
        
        # 창 내부 UI 설정
        layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setPixmap(pixmap)
        image_label.setStyleSheet("background-color: #FFFFFF;")
        
        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)


class ImagePreview(QWidget):
    """선택된 텍스처의 미리보기 및 정보를 표시하는 위젯"""
    
    def __init__(self, texture_processor):
        super().__init__()
        
        self.texture_processor = texture_processor
        self.current_texture = None
        self.is_original_size = False
        self.original_pixmap = None
        self.full_size_dialog = None
        
        self.init_ui()
        
    def resizeEvent(self, event):
        """위젯 크기 변경 시 이미지 크기 재조정"""
        super().resizeEvent(event)
        
        if not self.is_original_size and self.original_pixmap is not None:
            self.display_scaled_image()
        
    def init_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 상단 타이틀과 버튼
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        title_label = QLabel("이미지 미리보기")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_layout.addWidget(title_label, 1)
        
        self.size_toggle_button = QPushButton("원본 크기로 보기")
        self.size_toggle_button.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                border-radius: 4px;
            }
        """)
        self.size_toggle_button.clicked.connect(self.toggle_size_mode)
        top_layout.addWidget(self.size_toggle_button)
        
        layout.addWidget(top_bar)
        
        # 이미지 미리보기 영역
        image_frame = QFrame()
        image_frame.setStyleSheet("""
            QFrame {
                background-color: #D4D6F0;
                border-radius: 8px;
                padding: 0px;
            }
        """)
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(2, 2, 2, 2)
        
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setMinimumHeight(300)
        self.image_scroll.setFrameShape(QFrame.NoFrame)
        self.image_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 6px;
        """)
        self.image_scroll.setWidget(self.image_label)
        
        image_layout.addWidget(self.image_scroll)
        layout.addWidget(image_frame, 1)
        
        # 텍스처 정보 영역
        info_group = QGroupBox("텍스처 정보")
        info_group.setStyleSheet("""
            QGroupBox {
                background-color: #D4D6F0;
                border-radius: 8px;
                padding: 10px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #424242;
                font-weight: bold;
            }
        """)
        
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)
        
        # 정보 레이블 공통 스타일
        label_style = "background-color: #E3E5FA; padding: 6px; border-radius: 4px;"
        
        # 텍스처 정보 레이블들
        self.name_label = QLabel("이름: -")
        self.name_label.setStyleSheet(label_style)
        info_layout.addWidget(self.name_label)
        
        self.resolution_label = QLabel("해상도: -")
        self.resolution_label.setStyleSheet(label_style)
        info_layout.addWidget(self.resolution_label)
        
        self.format_label = QLabel("포맷: -")
        self.format_label.setStyleSheet(label_style)
        info_layout.addWidget(self.format_label)
        
        self.additional_info_label = QLabel("추가 정보: -")
        self.additional_info_label.setStyleSheet(label_style)
        self.additional_info_label.setWordWrap(True)
        info_layout.addWidget(self.additional_info_label)
        
        layout.addWidget(info_group)
    
    def toggle_size_mode(self):
        """원본 크기 이미지를 별도 창에 표시"""
        if not self.current_texture or self.original_pixmap is None:
            return
        
        # 이미 열려있는 대화상자가 있으면 닫기
        if self.full_size_dialog is not None and self.full_size_dialog.isVisible():
            self.full_size_dialog.close()
            self.full_size_dialog = None
            self.size_toggle_button.setText("원본 크기로 보기")
            return
        
        # 새 대화상자 생성 및 표시
        self.full_size_dialog = FullSizeImageDialog(self.original_pixmap, self)
        self.full_size_dialog.finished.connect(self._on_dialog_closed)
        self.full_size_dialog.show()
        self.size_toggle_button.setText("미리보기로 돌아가기")
    
    def _on_dialog_closed(self):
        """대화상자가 닫힐 때 호출되는 메소드"""
        self.full_size_dialog = None
        self.size_toggle_button.setText("원본 크기로 보기")
    
    def display_scaled_image(self):
        """이미지를 스크롤 영역에 맞게 축소하여 표시"""
        if self.original_pixmap is None:
            return
            
        # 스크롤 영역 크기 기준으로 이미지 크기 조절
        viewport_width = self.image_scroll.viewport().width() - 20
        viewport_height = self.image_scroll.viewport().height() - 20
        
        scaled_pixmap = self.original_pixmap.scaled(
            viewport_width, viewport_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
        
    def set_texture(self, texture_data):
        """새 텍스처 설정 및 표시"""
        self.current_texture = texture_data
        self.is_original_size = False
        
        if texture_data:
            # 이미지 변환 및 표시
            img = self.texture_processor.get_texture_preview(texture_data)
            width, height = img.size
            
            if img.mode == 'RGBA':
                bytes_per_line = 4 * width
                q_format = QImage.Format_RGBA8888
                img_data = img.tobytes('raw', 'RGBA')
            else:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                bytes_per_line = 3 * width
                q_format = QImage.Format_RGB888
                img_data = img.tobytes('raw', 'RGB')
            
            q_image = QImage(img_data, width, height, bytes_per_line, q_format)
            self.original_pixmap = QPixmap.fromImage(q_image)
            
            self.display_scaled_image()
            self.size_toggle_button.setText("원본 크기로 보기")
            
            # 텍스처 정보 업데이트
            texture_info = self.texture_processor.get_texture_info(texture_data)
            
            self.name_label.setText(f"이름: {texture_info['name']}")
            self.resolution_label.setText(f"해상도: {texture_info['width']}x{texture_info['height']}")
            self.format_label.setText(f"포맷: {texture_info['format']}")
            
            additional_info = (
                f"밉맵 수: {texture_info['mipmap_count']}, "
                f"읽기 가능: {'예' if texture_info['is_readable'] else '아니오'}, "
                f"필터 모드: {texture_info['texture_settings']['filter_mode']}"
            )
            self.additional_info_label.setText(f"추가 정보: {additional_info}")
        else:
            # 이미지가 없을 경우 초기화
            self.image_label.clear()
            self.name_label.setText("이름: -")
            self.resolution_label.setText("해상도: -")
            self.format_label.setText("포맷: -")
            self.additional_info_label.setText("추가 정보: -")
    
    def refresh(self):
        """현재 텍스처 미리보기 새로고침"""
        if self.current_texture:
            self.set_texture(self.current_texture)
