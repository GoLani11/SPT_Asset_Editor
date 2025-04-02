import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QScrollArea, QPushButton, QGroupBox, QFrame,
                           QDialog, QDesktopWidget)
from PyQt5.QtGui import QPixmap, QImage, QColor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from utils.resource_helper import get_resource_path
from utils.localization import get_string as _

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FullSizeImageDialog(QDialog):
    """원본 크기 이미지를 표시하는 대화상자"""
    
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("image_preview.full_size_dialog.title"))
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
        self.close_button = QPushButton(_("image_preview.full_size_dialog.close_button"))
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

    def update_ui_texts(self):
        """UI 텍스트 업데이트"""
        self.setWindowTitle(_("image_preview.full_size_dialog.title"))
        self.close_button.setText(_("image_preview.full_size_dialog.close_button"))


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
        
        self.title_label = QLabel(_("image_preview.title"))
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_layout.addWidget(self.title_label, 1)
        
        self.size_toggle_button = QPushButton(_("image_preview.button.show_original"))
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
        self.info_group = QGroupBox(_("image_preview.info_group_title"))
        self.info_group.setStyleSheet("""
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
        
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setSpacing(8)
        
        # 정보 레이블 공통 스타일
        label_style = "background-color: #E3E5FA; padding: 6px; border-radius: 4px;"
        
        # 텍스처 정보 레이블들
        self.name_label = QLabel(_("image_preview.info.name_default"))
        self.name_label.setStyleSheet(label_style)
        info_layout.addWidget(self.name_label)
        
        self.resolution_label = QLabel(_("image_preview.info.resolution_default"))
        self.resolution_label.setStyleSheet(label_style)
        info_layout.addWidget(self.resolution_label)
        
        self.format_label = QLabel(_("image_preview.info.format_default"))
        self.format_label.setStyleSheet(label_style)
        info_layout.addWidget(self.format_label)
        
        self.additional_info_label = QLabel(_("image_preview.info.additional_default"))
        self.additional_info_label.setStyleSheet(label_style)
        self.additional_info_label.setWordWrap(True)
        info_layout.addWidget(self.additional_info_label)
        
        layout.addWidget(self.info_group)
    
    def toggle_size_mode(self):
        """원본 크기 이미지를 별도 창에 표시"""
        if not self.current_texture or self.original_pixmap is None:
            return
        
        # 이미 열려있는 대화상자가 있으면 닫기
        if self.full_size_dialog is not None and self.full_size_dialog.isVisible():
            self.full_size_dialog.close()
            self.full_size_dialog = None
            self.size_toggle_button.setText(_("image_preview.button.show_original"))
            return
        
        # 새 대화상자 생성 및 표시
        self.full_size_dialog = FullSizeImageDialog(self.original_pixmap, self)
        self.full_size_dialog.finished.connect(self._on_dialog_closed)
        self.full_size_dialog.show()
        self.size_toggle_button.setText(_("image_preview.button.show_scaled"))
    
    def _on_dialog_closed(self):
        """대화상자가 닫힐 때 호출되는 메소드"""
        self.full_size_dialog = None
        self.size_toggle_button.setText(_("image_preview.button.show_original"))
    
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
        """표시할 텍스처 설정"""
        self.current_texture = texture_data
        self.original_pixmap = None # 새 텍스처 로드 시 초기화
        self.is_original_size = False # 스케일 모드로 초기화
        
        if self.full_size_dialog:
            self.full_size_dialog.close()

        if texture_data is None:
            self.image_label.clear()
            self.image_label.setText(_("image_preview.no_preview_label"))
            self.name_label.setText(_("image_preview.info.name_default"))
            self.resolution_label.setText(_("image_preview.info.resolution_default"))
            self.format_label.setText(_("image_preview.info.format_default"))
            self.additional_info_label.setText(_("image_preview.info.additional_default"))
            self.size_toggle_button.setEnabled(False)
            self.size_toggle_button.setText(_("image_preview.button.show_original"))
            return
            
        # UI 활성화
        self.size_toggle_button.setEnabled(True)
        self.size_toggle_button.setText(_("image_preview.button.show_original"))

        # 텍스처 정보 업데이트
        self.name_label.setText(_("image_preview.info.name", name=getattr(texture_data, 'm_Name', 'N/A')))
        width = getattr(texture_data, 'm_Width', '?')
        height = getattr(texture_data, 'm_Height', '?')
        self.resolution_label.setText(_("image_preview.info.resolution", res=f"{width}x{height}"))
        self.format_label.setText(_("image_preview.info.format", format=str(getattr(texture_data, 'm_TextureFormat', 'Unknown'))))
        
        # 추가 정보 구성
        additional_info_parts = []
        if hasattr(texture_data, 'm_MipCount') and texture_data.m_MipCount > 1:
            additional_info_parts.append(_("image_preview.info.mipmaps", count=texture_data.m_MipCount))
        if hasattr(texture_data, 'm_IsReadable') and texture_data.m_IsReadable:
            additional_info_parts.append(_("image_preview.info.readable"))
        if hasattr(texture_data, 'm_LightmapFormat') and texture_data.m_LightmapFormat != 0:
            additional_info_parts.append(_("image_preview.info.lightmap"))
            
        additional_info_str = ", ".join(additional_info_parts)
        if not additional_info_str:
            additional_info_str = "-"
        self.additional_info_label.setText(_("image_preview.info.additional", info=additional_info_str))

        # 이미지 로드 및 표시
        try:
            # TextureProcessor를 사용하여 이미지 데이터 가져오기
            img = self.texture_processor.get_texture_preview(texture_data)
            if img is None:
                raise ValueError(_("image_preview.error.load_failed"))
            
            self.original_pixmap = self._convert_pil_to_pixmap(img)
            self.display_scaled_image() # 스케일 모드로 표시

        except Exception as e:
            print(f"{_('image_preview.error.load_error')}: {str(e)}")
            self.image_label.setText(_("image_preview.error.load_failed"))
            self.original_pixmap = None
            self.size_toggle_button.setEnabled(False)
            self.size_toggle_button.setText(_("image_preview.button.show_original"))
            
    def _convert_pil_to_pixmap(self, img):
        """PIL 이미지를 QPixmap으로 변환"""
        if img.mode == "RGBA":
            qim = QImage(img.tobytes("raw", "RGBA"), img.width, img.height, QImage.Format_RGBA8888)
        elif img.mode == "RGB":
            qim = QImage(img.tobytes("raw", "RGB"), img.width, img.height, QImage.Format_RGB888)
        else:
            # 다른 모드 처리 (예: 그레이스케일)
            qim = QImage(img.tobytes(), img.width, img.height, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qim)

    def refresh(self):
        """현재 텍스처를 다시 로드하여 미리보기 업데이트"""
        self.set_texture(self.current_texture)

    def update_ui_texts(self):
        """UI 텍스트 업데이트"""
        self.title_label.setText(_("image_preview.title"))
        self.info_group.setTitle(_("image_preview.info_group_title"))

        # 텍스트 정보 업데이트 (현재 상태에 따라)
        if self.current_texture:
            # 이미지가 로드된 상태의 텍스트 업데이트
            self.size_toggle_button.setText(
                _("image_preview.button.show_scaled") if self.full_size_dialog and self.full_size_dialog.isVisible() 
                else _("image_preview.button.show_original")
            )
            # 이름, 해상도 등은 set_texture에서 이미 _()를 사용하므로 여기서는 다시 설정 불필요
        else:
            # 이미지가 없는 상태의 텍스트 업데이트
            self.image_label.setText(_("image_preview.no_preview_label"))
            self.name_label.setText(_("image_preview.info.name_default"))
            self.resolution_label.setText(_("image_preview.info.resolution_default"))
            self.format_label.setText(_("image_preview.info.format_default"))
            self.additional_info_label.setText(_("image_preview.info.additional_default"))
            self.size_toggle_button.setText(_("image_preview.button.show_original"))
            self.size_toggle_button.setEnabled(False)

        # 원본 크기 대화상자가 열려있으면 텍스트 업데이트
        if self.full_size_dialog:
            self.full_size_dialog.update_ui_texts()