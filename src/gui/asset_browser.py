import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QListWidget, QListWidgetItem, QLineEdit, QPushButton, QFileDialog,
                           QCheckBox)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ThumbnailLoaderThread(QThread):
    """텍스처 썸네일을 비동기적으로 생성하는 스레드"""
    thumbnail_ready = pyqtSignal(int, QIcon, bool)  # (인덱스, 아이콘, 성공여부)
    loading_finished = pyqtSignal(int, int)  # (성공 개수, 실패 개수)

    def __init__(self, texture_processor, texture_infos, parent=None):
        super().__init__(parent)
        self.texture_processor = texture_processor
        self.texture_infos = texture_infos
        self._is_running = True

    def run(self):
        loaded_count = 0
        failed_count = 0
        for index, texture_data in self.texture_infos:
            if not self._is_running:
                break
            try:
                # 썸네일 생성 및 이미지 변환
                thumb = self.texture_processor.create_thumbnail(texture_data)
                width, height = thumb.size
                bytes_per_line = 3 * width
                if thumb.mode == 'RGBA':
                    q_format = QImage.Format_RGBA8888
                    bytes_per_line = 4 * width
                else:
                    q_format = QImage.Format_RGB888

                q_image = QImage(thumb.tobytes(), width, height, bytes_per_line, q_format)
                pixmap = QPixmap.fromImage(q_image)
                icon = QIcon(pixmap)
                self.thumbnail_ready.emit(index, icon, True)
                loaded_count += 1
            except Exception as e:
                print(f"썸네일 생성 오류 (Texture: {texture_data.m_Name if hasattr(texture_data, 'm_Name') else 'N/A'}): {str(e)}")
                self.thumbnail_ready.emit(index, QIcon(), False)
                failed_count += 1
        
        if self._is_running:
            self.loading_finished.emit(loaded_count, failed_count)

    def stop(self):
        self._is_running = False

class AssetBrowser(QWidget):
    """에셋 파일 내 텍스처 목록을 표시하고 탐색하는 위젯"""
    
    texture_selected = pyqtSignal(object, object)
    
    def __init__(self, assets_manager, texture_processor):
        super().__init__()
        
        self.assets_manager = assets_manager
        self.texture_processor = texture_processor
        
        self.textures = {}
        self.filtered_textures = []
        self.thumb_loader_thread = None
        self.current_selected_texture = None
        
        self.init_ui()
        
    def init_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 헤더 영역 (제목 + 검색)
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 8, 8, 0)
        header_layout.setSpacing(5)
        
        # 제목
        title_label = QLabel("에셋 브라우저")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        
        # 검색 필드
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("텍스처 검색...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border-radius: 5px;
                padding: 6px;
                background-color: #D4D6F0;
            }
        """)
        self.search_input.textChanged.connect(self.filter_textures)
        header_layout.addWidget(self.search_input)
        
        layout.addWidget(header_widget)
        
        # 텍스처 목록
        self.texture_list = QListWidget()
        self.texture_list.setIconSize(QSize(48, 48))
        self.texture_list.setSpacing(2)
        self.texture_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #E3E5FA;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                border-radius: 5px;
                padding: 5px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #B5C7E1;
            }
            QListWidget::item:hover {
                background-color: #D4D6F0;
            }
        """)
        self.texture_list.itemClicked.connect(self.on_texture_selected)
        layout.addWidget(self.texture_list)
        
        # 정보 및 버튼 영역
        info_buttons_widget = QWidget()
        info_buttons_layout = QVBoxLayout(info_buttons_widget)
        info_buttons_layout.setContentsMargins(8, 0, 8, 8)
        info_buttons_layout.setSpacing(5)
        
        # 정보 표시 레이블
        self.info_label = QLabel("로드된 텍스처: 0개")
        self.info_label.setStyleSheet("color: #424242;")
        self.info_label.setAlignment(Qt.AlignCenter)
        info_buttons_layout.addWidget(self.info_label)
        
        # 알파값 제거 체크박스
        self.remove_alpha_checkbox = QCheckBox("PNG 저장 시 투명도(알파값) 제거하기")
        self.remove_alpha_checkbox.setChecked(False)  # 기본값으로 비활성화
        self.remove_alpha_checkbox.setToolTip("PNG 파일 저장 시 투명도를 제거하고 불투명한 이미지로 저장합니다.\n이미지 편집 프로그램에서 더 보기 쉽게 작업할 수 있습니다.\n그러나 이 이미지로 수정 후 다시 적용하려고 할 때\n원본 이미지 투명도 패턴으로 교체하는 것을 추천합니다.")
        self.remove_alpha_checkbox.setStyleSheet("""
            QCheckBox {
                color: #424242;
                margin-top: 5px;
            }
        """)
        info_buttons_layout.addWidget(self.remove_alpha_checkbox)
        
        # 저장 버튼
        self.save_button = QPushButton("원본 텍스처 저장")
        self.save_button.setEnabled(False)  # 초기에는 비활성화
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4A6DD0;
                color: white;
                border-radius: 5px;
                padding: 8px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #3A5DC0;
            }
            QPushButton:pressed {
                background-color: #2A4DB0;
            }
            QPushButton:disabled {
                background-color: #A0A0A0;
                color: #D0D0D0;
            }
        """)
        self.save_button.clicked.connect(self.save_original_texture)
        info_buttons_layout.addWidget(self.save_button)
        
        layout.addWidget(info_buttons_widget)
        
    def filter_textures(self, search_text):
        """검색어에 따라 텍스처 목록 필터링"""
        # 항목 필터링
        for i in range(self.texture_list.count()):
            item = self.texture_list.item(i)
            
            if not search_text:
                item.setHidden(False)
                continue
                
            text = item.text().lower()
            item.setHidden(search_text.lower() not in text)
        
        # 표시 상태 업데이트
        visible_count = sum(1 for i in range(self.texture_list.count()) if not self.texture_list.item(i).isHidden())
        total_count = self.texture_list.count()
        
        if search_text:
            self.info_label.setText(f"검색 결과: {visible_count}/{total_count}개")
        else:
            self.info_label.setText(f"로드된 텍스처: {total_count}개")
            
    def update_texture_list(self):
        """텍스처 목록 업데이트 및 비동기 썸네일 로딩"""
        # 기존 스레드 정리
        if self.thumb_loader_thread and self.thumb_loader_thread.isRunning():
            self.thumb_loader_thread.stop()
            self.thumb_loader_thread.wait()

        # UI 초기화
        self.texture_list.clear()
        self.textures = {}
        self.info_label.setText("텍스처 목록 로딩 중...")
        self.search_input.clear()

        # 텍스처 메타데이터 가져오기
        texture_metadata_list = self.assets_manager.get_texture_list()
        
        # 목록에 항목 추가 및 로딩 준비
        textures_to_load = []
        for index, texture_info in enumerate(texture_metadata_list):
            item = QListWidgetItem()
            item.setText(f"{texture_info['name']} ({texture_info['width']}x{texture_info['height']})")
            item.setData(Qt.UserRole, texture_info['id'])
            
            # 아이템 설정
            item.setSizeHint(QSize(200, 60))
            self.texture_list.addItem(item)
            
            # 텍스처 데이터 가져오기
            result = self.assets_manager.get_texture_by_id(texture_info['id'])
            if result:
                obj, data = result
                self.textures[texture_info['id']] = (obj, data)
                textures_to_load.append((index, data))
            else:
                item.setText(f"{texture_info['name']} ({texture_info['width']}x{texture_info['height']}) - 로드 실패")

        # 썸네일 로딩 스레드 시작
        if textures_to_load:
            self.thumb_loader_thread = ThumbnailLoaderThread(self.texture_processor, textures_to_load, self)
            self.thumb_loader_thread.thumbnail_ready.connect(self.on_thumbnail_ready)
            self.thumb_loader_thread.loading_finished.connect(self.on_thumbnails_loaded)
            self.thumb_loader_thread.start()
        else:
            self.info_label.setText("로드된 텍스처: 0개")
            
    def on_thumbnail_ready(self, index, icon, success):
        """썸네일 준비 완료 시 처리"""
        item = self.texture_list.item(index)
        if item:
            item.setIcon(icon)
            texture_id = item.data(Qt.UserRole)
            if texture_id in self.textures:
                obj, data = self.textures[texture_id]
                if success:
                    item.setText(f"{data.m_Name} ({data.m_Width}x{data.m_Height})")

    def on_thumbnails_loaded(self, loaded_count, failed_count):
        """모든 썸네일 로딩 완료 시 처리"""
        if failed_count > 0:
            self.info_label.setText(f"로드된 텍스처: {loaded_count}개 (썸네일 로드 실패: {failed_count}개)")
        else:
            self.info_label.setText(f"로드된 텍스처: {loaded_count}개")
        self.thumb_loader_thread = None

    def on_texture_selected(self, item):
        """텍스처 선택 처리"""
        texture_id = item.data(Qt.UserRole)
        if texture_id in self.textures:
            obj, data = self.textures[texture_id]
            self.current_selected_texture = (obj, data)
            self.save_button.setEnabled(True)  # 텍스처 선택 시 저장 버튼 활성화
            self.texture_selected.emit(obj, data)
    
    def save_original_texture(self):
        """선택된 원본 텍스처를 저장하는 함수"""
        if not self.current_selected_texture:
            return
        
        obj, data = self.current_selected_texture
        texture_name = getattr(data, 'm_Name', 'texture')
        
        # 파일 저장 대화상자
        file_path, _ = QFileDialog.getSaveFileName(
            self, "원본 텍스처 저장",
            f"{texture_name}",
            "PNG 이미지 (*.png);;TGA 이미지 (*.tga);;모든 파일 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 이미지 가져오기
            img = self.texture_processor.get_texture_preview(data)
            original_mode = img.mode
            
            # 파일 확장자에 따라 저장 포맷 결정
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()
            
            # 로그 및 메시지용 변수
            alpha_removed = False
            
            # PNG 저장 시 알파값 제거 옵션 적용
            if file_extension == '.png' or not file_extension:
                # 확장자가 없으면 .png 추가
                if not file_extension:
                    file_path += '.png'
                
                # 알파값 제거 옵션이 체크되어 있고 이미지에 알파 채널이 있는 경우
                if self.remove_alpha_checkbox.isChecked() and img.mode == 'RGBA':
                    # RGB 모드로 변환하여 알파값 제거
                    img = img.convert('RGB')
                    alpha_removed = True
                    print(f"이미지 모드 변환: {original_mode} -> RGB (알파값 제거)")
                
                img.save(file_path)
            elif file_extension == '.tga':
                # TGA 파일로 저장 (알파값 유지)
                img.save(file_path, format='TGA')
                print(f"이미지 저장: {file_path} (TGA 포맷, 알파채널 유지)")
            else:
                # 기타 확장자는 그대로 저장
                img.save(file_path)
                print(f"이미지 저장: {file_path} (원본 포맷 유지)")
            
            # 성공 메시지
            from PyQt5.QtWidgets import QMessageBox
            success_message = f"텍스처가 성공적으로 저장되었습니다:\n{file_path}"
            
            # 알파값 제거 정보 추가
            if alpha_removed:
                success_message += f"\n\n원본 이미지 형식: {original_mode}\n투명도(알파값)가 제거되었습니다."
            
            QMessageBox.information(
                self, "저장 성공",
                success_message
            )
        except Exception as e:
            # 오류 메시지
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "저장 오류",
                f"텍스처 저장 중 오류가 발생했습니다:\n{str(e)}"
            )
