import os
import sys
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QListWidget, QListWidgetItem, QLineEdit, QPushButton, QFileDialog,
                           QCheckBox, QMessageBox, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import localization

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

class BundleFileSelector(QDialog):
    """번들 파일 선택 대화상자"""
    
    def __init__(self, bundle_files, parent=None):
        super().__init__(parent)
        self.bundle_files = bundle_files
        self.selected_file = None
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(localization.get_string("asset_browser.bundle_selector.title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # 안내 레이블
        info_label = QLabel(localization.get_string("asset_browser.bundle_selector.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                background-color: #E3E5FA;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                border-radius: 5px;
                padding: 8px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #B5C7E1;
            }
            QListWidget::item:hover {
                background-color: #D4D6F0;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.file_list)
        
        # 파일 정보 레이블
        self.info_label = QLabel(localization.get_string("asset_browser.bundle_selector.file_count", count=len(self.bundle_files)))
        layout.addWidget(self.info_label)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 파일 목록 채우기
        self.populate_file_list()
        
    def populate_file_list(self):
        """파일 목록 채우기"""
        for file_path in self.bundle_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # 파일 크기를 보기 좋게 변환 (KB/MB)
            if file_size < 1024 * 1024:  # 1MB 미만
                size_text = f"{file_size / 1024:.1f} KB"
            else:
                size_text = f"{file_size / (1024 * 1024):.2f} MB"
                
            # 마지막 수정 시간
            mod_time = os.path.getmtime(file_path)
            mod_time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mod_time))
            
            # 표시 텍스트 생성
            display_text = f"{file_name} ({size_text}, {mod_time_str})"
            
            file_item = QListWidgetItem(display_text)
            file_item.setData(Qt.UserRole, file_path)
            # 아이콘 추가 (번들 파일 아이콘 또는 기본 아이콘)
            icon = QIcon.fromTheme("package-x-generic")
            if not icon or icon.isNull():
                # 기본 아이콘 (테마 아이콘이 없는 경우)
                file_item.setIcon(QIcon())
            else:
                file_item.setIcon(icon)
                
            self.file_list.addItem(file_item)
            
        # 첫 번째 항목 선택
        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)
            
    def accept(self):
        """대화상자 수락 (OK 버튼)"""
        current_item = self.file_list.currentItem()
        if current_item:
            self.selected_file = current_item.data(Qt.UserRole)
            super().accept()
        else:
            QMessageBox.warning(
                self,
                localization.get_string("error.file_not_found.title"),
                localization.get_string("asset_browser.bundle_selector.no_selection"),
                QMessageBox.Ok
            )

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
        
        # 초기 UI 텍스트 업데이트
        self.update_ui_texts()
        
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
        self.title_label = QLabel(localization.get_string("asset_browser.title"))
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)
        
        # 포스트 아이템 이미지 변경 버튼 (제목 아래, 검색창 위에 배치)
        self.post_item_button = QPushButton(localization.get_string("asset_browser.post_item_button"))
        self.post_item_button.setStyleSheet("""
            QPushButton {
                background-color: #4AD075;
                color: white;
                border-radius: 5px;
                padding: 8px;
                margin-top: 5px;
                margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: #3AC065;
            }
            QPushButton:pressed {
                background-color: #2AB055;
            }
            QPushButton:disabled {
                background-color: #A0A0A0;
                color: #D0D0D0;
            }
        """)
        self.post_item_button.clicked.connect(self.load_post_item_images)
        header_layout.addWidget(self.post_item_button)
        
        # 검색 필드
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(localization.get_string("asset_browser.search_placeholder"))
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
        layout.addWidget(self.texture_list, 1) # 목록 위젯이 남은 공간을 차지하도록 설정
        
        # 정보 및 버튼 영역
        info_buttons_widget = QWidget()
        info_buttons_layout = QVBoxLayout(info_buttons_widget)
        info_buttons_layout.setContentsMargins(8, 0, 8, 8)
        info_buttons_layout.setSpacing(5)
        
        # 정보 표시 레이블
        self.info_label = QLabel(localization.get_string("asset_browser.info_label_loaded", count=0))
        self.info_label.setStyleSheet("color: #424242;")
        self.info_label.setAlignment(Qt.AlignCenter)
        info_buttons_layout.addWidget(self.info_label)
        
        # 알파값 제거 체크박스
        self.remove_alpha_checkbox = QCheckBox(localization.get_string("asset_browser.remove_alpha_checkbox"))
        self.remove_alpha_checkbox.setChecked(False)  # 기본값으로 체크 해제
        self.remove_alpha_checkbox.setToolTip(localization.get_string("asset_browser.remove_alpha_tooltip"))
        self.remove_alpha_checkbox.setStyleSheet("""
            QCheckBox {
                color: #424242;
                margin-top: 5px;
            }
        """)
        info_buttons_layout.addWidget(self.remove_alpha_checkbox)
        
        # 저장 버튼
        self.save_button = QPushButton(localization.get_string("asset_browser.save_original_button"))
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
        
        # 초기 상태 비활성화
        self.save_button.setEnabled(False)
        
    def update_ui_texts(self):
        """UI 텍스트 업데이트"""
        self.title_label.setText(localization.get_string("asset_browser.title"))
        self.search_input.setPlaceholderText(localization.get_string("asset_browser.search_placeholder"))
        # info_label은 내용이 동적으로 변하므로 filter_textures, update_texture_list 등에서 업데이트
        self.remove_alpha_checkbox.setText(localization.get_string("asset_browser.remove_alpha_checkbox"))
        self.remove_alpha_checkbox.setToolTip(localization.get_string("asset_browser.remove_alpha_tooltip"))
        self.save_button.setText(localization.get_string("asset_browser.save_original_button"))
        self.post_item_button.setText(localization.get_string("asset_browser.post_item_button"))
        
        # 현재 목록 상태에 따라 info_label 업데이트
        self.update_info_label()
        
    def update_info_label(self):
        """현재 필터링 및 로드 상태에 따라 정보 레이블 업데이트"""
        search_text = self.search_input.text().lower()
        visible_count = sum(1 for i in range(self.texture_list.count()) if not self.texture_list.item(i).isHidden())
        total_count = self.texture_list.count()
        
        if search_text:
            self.info_label.setText(localization.get_string("asset_browser.info_label_filtered", visible_count=visible_count, total_count=total_count))
        else:
            # 스레드 상태 확인 후 로딩 중/완료 메시지 표시
            if self.thumb_loader_thread and self.thumb_loader_thread.isRunning():
                self.info_label.setText(localization.get_string("asset_browser.info_label_loading"))
            else:
                # 로딩 완료 후 성공/실패 정보 표시
                failed_count = getattr(self, '_last_failed_count', 0)
                if failed_count > 0:
                    self.info_label.setText(localization.get_string("asset_browser.info_label_failed", loaded_count=total_count, failed_count=failed_count))
                else:
                    self.info_label.setText(localization.get_string("asset_browser.info_label_loaded", count=total_count))
            
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
            self.info_label.setText(localization.get_string("asset_browser.info_label_filtered", visible_count=visible_count, total_count=total_count))
        else:
            self.info_label.setText(localization.get_string("asset_browser.info_label_loaded", count=total_count))
            
    def update_texture_list(self):
        """텍스처 목록 업데이트 및 비동기 썸네일 로딩"""
        # 기존 스레드 정리
        if self.thumb_loader_thread and self.thumb_loader_thread.isRunning():
            self.thumb_loader_thread.stop()
            self.thumb_loader_thread.wait()

        # UI 초기화
        self.texture_list.clear()
        self.textures = {}
        self.info_label.setText(localization.get_string("asset_browser.info_label_loading"))
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
                item.setIcon(QIcon()) # 로딩 실패 시 빈 아이콘
                print(f"썸네일 업데이트 오류: {index}")

        # 썸네일 로딩 스레드 시작
        if textures_to_load:
            self.thumb_loader_thread = ThumbnailLoaderThread(self.texture_processor, textures_to_load, self)
            self.thumb_loader_thread.thumbnail_ready.connect(self.on_thumbnail_ready)
            self.thumb_loader_thread.loading_finished.connect(self.on_thumbnails_loaded)
            self.thumb_loader_thread.start()
        else:
            self.info_label.setText(localization.get_string("asset_browser.info_label_loaded", count=0))
            
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
            self.info_label.setText(localization.get_string("asset_browser.info_label_failed", loaded_count=loaded_count, failed_count=failed_count))
        else:
            self.info_label.setText(localization.get_string("asset_browser.info_label_loaded", count=loaded_count))
        self.thumb_loader_thread = None

    def on_texture_selected(self, item):
        """텍스처 선택 처리"""
        texture_id = item.data(Qt.UserRole)
        if texture_id in self.textures:
            obj, data = self.textures[texture_id]
            self.current_selected_texture = (obj, data)
            self.save_button.setEnabled(True)  # 텍스처 선택 시 저장 버튼 활성화
            self.texture_selected.emit(obj, data)
        else:
             self.current_selected_texture = None
             self.save_button.setEnabled(False)
    
    def save_original_texture(self):
        """선택된 원본 텍스처를 저장하는 함수"""
        if not self.current_selected_texture:
            return
        
        obj, data = self.current_selected_texture
        texture_name = getattr(data, 'm_Name', 'texture')
        
        # 파일 저장 대화상자
        file_path, _ = QFileDialog.getSaveFileName(
            self, localization.get_string("asset_browser.save_dialog.title"),
            f"{texture_name}",
            localization.get_string("asset_browser.save_dialog.filter")
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
            if alpha_removed:
                success_message = localization.get_string("asset_browser.save_success.message_alpha_removed", file_path=file_path, original_mode=original_mode)
            else:
                success_message = localization.get_string("asset_browser.save_success.message", file_path=file_path)
            
            QMessageBox.information(
                self, localization.get_string("asset_browser.save_success.title"),
                success_message
            )
        except Exception as e:
            # 오류 메시지
            QMessageBox.critical(
                self, localization.get_string("asset_browser.save_error.title"),
                localization.get_string("asset_browser.save_error.message", error=str(e))
            )

    def load_post_item_images(self):
        """포스트 아이템 이미지 파일 로드 다이얼로그"""
        # 먼저 안내 메시지 표시
        QMessageBox.information(
            self,
            localization.get_string("asset_browser.spt_folder_dialog.title"),
            localization.get_string("asset_browser.spt_folder_guide"),
            QMessageBox.Ok
        )
        
        # SPT 폴더 선택 다이얼로그
        spt_folder = QFileDialog.getExistingDirectory(
            self, localization.get_string("asset_browser.spt_folder_dialog.title"), "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not spt_folder:
            return
            
        # 본섭 타르코프 경로 확인 (main_window.py의 open_assets_file 메소드와 유사한 검증)
        be_exe_path = os.path.join(spt_folder, "EscapeFromTarkov_BE.exe")
        battle_eye_dir = os.path.join(spt_folder, "BattlEye")
        bepinex_dir = os.path.join(spt_folder, "BepInEx")
        
        # 본섭 타르코프 파일 확인
        if os.path.exists(be_exe_path) and os.path.isdir(battle_eye_dir):
            QMessageBox.critical(
                self,
                localization.get_string("live_tarkov_warning.title"),
                localization.get_string("asset_browser.spt_error.live_tarkov"),
                QMessageBox.Ok
            )
            return
            
        # SPT 폴더에 BepInEx 폴더가 없는 경우
        if not os.path.isdir(bepinex_dir):
            QMessageBox.critical(
                self,
                localization.get_string("error.file_not_found.title"),
                localization.get_string("asset_browser.spt_error.invalid_folder"),
                QMessageBox.Ok
            )
            return
            
        # 포스트 아이템 플라이어 경로
        flyers_path = os.path.join(
            spt_folder,
            "EscapeFromTarkov_Data",
            "StreamingAssets",
            "Windows",
            "assets",
            "content",
            "items",
            "barter",
            "item_barter_flyers"
        )
        
        if not os.path.exists(flyers_path):
            QMessageBox.critical(
                self,
                localization.get_string("error.file_not_found.title"),
                localization.get_string("asset_browser.spt_error.flyers_not_found", path=flyers_path),
                QMessageBox.Ok
            )
            return
            
        # 번들 파일 찾기
        bundle_files = []
        for file in os.listdir(flyers_path):
            if file.endswith(".bundle"):
                bundle_files.append(os.path.join(flyers_path, file))
                
        if not bundle_files:
            QMessageBox.critical(
                self,
                localization.get_string("error.file_not_found.title"),
                localization.get_string("asset_browser.spt_error.no_bundles"),
                QMessageBox.Ok
            )
            return
            
        # 번들 파일 선택 대화상자 표시
        dialog = BundleFileSelector(bundle_files, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_file:
            # 파일 로드를 메인 윈도우에 위임
            parent = self.window()
            if hasattr(parent, 'start_loading') and callable(parent.start_loading):
                parent.start_loading(dialog.selected_file)
            else:
                QMessageBox.critical(
                    self,
                    localization.get_string("error.file_load.title"),
                    localization.get_string("asset_browser.spt_error.load_failed"),
                    QMessageBox.Ok
                )
