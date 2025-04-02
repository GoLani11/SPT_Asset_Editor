import os
import sys
import json
import time
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QFileDialog, QMessageBox,
                             QAction, QVBoxLayout, QWidget, QSplitter, QProgressDialog,
                             QHBoxLayout, QToolBar, QActionGroup, QMenu)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.asset_browser import AssetBrowser
from gui.image_preview import ImagePreview
from gui.image_editor import ImageEditor
from core.assets_manager import AssetsManager
from core.texture_processor import TextureProcessor
from core.backup_manager import BackupManager
from utils.resource_helper import get_resource_path
from utils.localization import get_string as _
from utils import localization

try:
    from _version import __version__, __author__, __copyright__, __app_name__, __description__
except ImportError:
    # 빌드 전에 _version.py가 존재하지 않을 경우 기본값 설정
    __version__ = "개발 버전"
    __author__ = "Golani11"
    __copyright__ = "© 2025 Golani11. All rights reserved."
    __app_name__ = "SPT Asset Editor"
    __description__ = "SPT 타르코프 게임의 에셋 파일에서 Texture2D 이미지를 추출, 미리보기, 수정 및 복원하는 도구"

# 에셋 파일 비동기 로딩을 위한 작업 스레드
class AssetLoaderThread(QThread):
    load_finished = pyqtSignal(bool, str)  # 로딩 완료 시그널 (성공 여부, 파일 경로)
    load_progress = pyqtSignal(int, int)   # 진행 상태 시그널 (현재 값, 최대 값)

    def __init__(self, assets_manager, file_path):
        super().__init__()
        self.assets_manager = assets_manager
        self.file_path = file_path

    def run(self):
        # 파일 로딩 실행 및 결과 전송
        success = self.assets_manager.load_file(self.file_path)
        self.load_finished.emit(success, self.file_path)


class MainWindow(QMainWindow):
    """타르코프 에셋 에디터의 메인 윈도우 클래스"""
    
    language_changed = pyqtSignal() # 언어 변경 시그널
    
    def __init__(self):
        super().__init__()
        
        # 핵심 객체 초기화
        self.assets_manager = AssetsManager()
        self.texture_processor = TextureProcessor()
        self.backup_manager = BackupManager()
        
        # 백업 디렉토리 초기화 제거 (저장 시마다 새로 설정하도록 함)
        # self.backup_manager.ensure_backup_directory()
        
        self.init_ui() # UI 요소 생성 먼저
        
        self.current_file_path = None
        self.load_thread = None
        self.progress_dialog = None
        self.texture_modified_since_load = False
        
        # 언어 변경 시 UI 업데이트 연결
        self.language_changed.connect(self.update_ui_texts)
        # 초기 UI 텍스트 설정
        self.update_ui_texts()
        
    def init_ui(self):
        """UI 초기화"""
        # 윈도우 기본 설정
        self.setWindowTitle(_("main_window.title"))
        self.setGeometry(100, 100, 1280, 800)
        
        # 애플리케이션 아이콘 설정
        icon_path = get_resource_path("resources/icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 중앙 위젯 및 메인 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 메인 스플리터 (좌측 사이드바와 우측 콘텐츠 영역)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(1)
        
        # 좌측 사이드바 (에셋 브라우저)
        self.sidebar_panel = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_panel)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        self.asset_browser = AssetBrowser(self.assets_manager, self.texture_processor)
        sidebar_layout.addWidget(self.asset_browser)
        
        # 우측 콘텐츠 패널 (미리보기 + 에디터)
        self.content_panel = QWidget()
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 미리보기와 에디터 수직 분할
        self.content_splitter = QSplitter(Qt.Vertical)
        
        self.image_preview = ImagePreview(self.texture_processor)
        self.content_splitter.addWidget(self.image_preview)
        
        self.image_editor = ImageEditor(self.texture_processor, self.backup_manager)
        self.image_editor.texture_replaced.connect(self.on_texture_replaced)
        self.content_splitter.addWidget(self.image_editor)
        
        # 스플리터 비율 설정
        self.content_splitter.setSizes([350, 450])
        content_layout.addWidget(self.content_splitter)
        
        # 패널 추가 및 비율 설정
        self.main_splitter.addWidget(self.sidebar_panel)
        self.main_splitter.addWidget(self.content_panel)
        self.main_splitter.setSizes([300, 980])
        
        main_layout.addWidget(self.main_splitter)
        
        # 시그널 연결 및 UI 요소 설정
        self.asset_browser.texture_selected.connect(self.on_texture_selected)
        self.setup_menu()
        self.statusBar().showMessage(_("main_window.status_ready"))
        
    def setup_menu(self):
        """메뉴바 구성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        self.file_menu = menubar.addMenu(_("menu.file"))
        
        # 열기
        self.open_action = QAction(QIcon.fromTheme("document-open"), _("menu.file.open"), self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_assets_file)
        self.file_menu.addAction(self.open_action)
        
        self.file_menu.addSeparator()
        
        # 저장 관련 액션
        self.save_action = QAction(QIcon.fromTheme("document-save"), _("menu.file.save"), self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_current_file)
        self.file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), _("menu.file.save_as"), self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_file_as)
        self.file_menu.addAction(self.save_as_action)
        
        self.file_menu.addSeparator()
        
        # 종료
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), _("menu.file.exit"), self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        # 설정 메뉴
        self.settings_menu = menubar.addMenu(_("menu.settings"))
        
        # 백업 설정
        self.set_backup_dir_action = QAction(_("menu.settings.set_backup_dir"), self)
        self.set_backup_dir_action.triggered.connect(self.select_backup_directory)
        self.settings_menu.addAction(self.set_backup_dir_action)
        
        # 언어 변경 메뉴 - 메인 메뉴바에 직접 추가
        self.language_menu = menubar.addMenu(_("menu.settings.language"))
        
        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.setExclusive(True)
        
        # 사용 가능한 언어 액션 추가
        for lang_code in localization.SUPPORTED_LANGUAGES:
            # 초기 텍스트는 언어 코드로 설정
            action = QAction(lang_code.upper(), self, checkable=True) # 예: KO, EN
            action.setData(lang_code)
            action.setChecked(localization.get_current_language() == lang_code)
            action.triggered.connect(self.change_language)
            self.language_menu.addAction(action)
            self.lang_action_group.addAction(action)
            
        # 도구 메뉴
        self.tools_menu = menubar.addMenu(_("menu.tools"))
        
        self.asset_info_action = QAction(_("menu.tools.asset_info"), self)
        self.asset_info_action.triggered.connect(self.show_asset_structure_info)
        self.tools_menu.addAction(self.asset_info_action)
        
        self.cleanup_temp_action = QAction(_("menu.tools.cleanup_temp"), self)
        self.cleanup_temp_action.triggered.connect(self.cleanup_temp_files)
        self.tools_menu.addAction(self.cleanup_temp_action)
        
        # 도움말 메뉴
        self.help_menu = menubar.addMenu(_("menu.help"))
        
        self.about_action = QAction(_("menu.help.about"), self)
        self.about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(self.about_action)
        
    def change_language(self):
        """언어 변경 액션 처리"""
        action = self.sender()
        if action:
            new_lang_code = action.data()
            if new_lang_code != localization.get_current_language():
                localization.set_language(new_lang_code)
                self.language_changed.emit() # 시그널 발생
                
                # 사용자에게 재시작 안내 (필요에 따라)
                QMessageBox.information(
                    self, 
                    _("main_window.language_changed_title"), 
                    _("main_window.language_changed_message")
                )

    def update_ui_texts(self):
        """UI의 모든 텍스트를 현재 언어로 업데이트"""
        self.setWindowTitle(_("main_window.title"))
        self.statusBar().showMessage(_("main_window.status_ready"))

        # 메뉴 업데이트
        self.file_menu.setTitle(_("menu.file"))
        self.open_action.setText(_("menu.file.open"))
        self.save_action.setText(_("menu.file.save"))
        self.save_as_action.setText(_("menu.file.save_as"))
        self.exit_action.setText(_("menu.file.exit"))
        self.settings_menu.setTitle(_("menu.settings"))
        self.set_backup_dir_action.setText(_("menu.settings.set_backup_dir"))
        self.language_menu.setTitle(_("menu.settings.language"))
        self.tools_menu.setTitle(_("menu.tools"))
        self.asset_info_action.setText(_("menu.tools.asset_info"))
        self.cleanup_temp_action.setText(_("menu.tools.cleanup_temp"))
        self.help_menu.setTitle(_("menu.help"))
        self.about_action.setText(_("menu.help.about"))
        
        # 언어 메뉴 액션 텍스트 업데이트 (번역된 이름 사용)
        for action in self.lang_action_group.actions():
            lang_code = action.data()
            # lang_code ('ko', 'en')를 실제 번역 키 ('korean', 'english')로 매핑
            lang_name_map = {"ko": "korean", "en": "english"}
            translation_key = f"menu.settings.language.{lang_name_map.get(lang_code, lang_code)}"
            action.setText(_(translation_key))
            action.setChecked(localization.get_current_language() == lang_code)

        # 하위 위젯 업데이트 (시그널 또는 직접 호출)
        self.asset_browser.update_ui_texts() # 하위 위젯 업데이트 메서드 호출
        self.image_preview.update_ui_texts()
        self.image_editor.update_ui_texts()

        # 기타 UI 요소 업데이트 (필요시 추가)

    def select_backup_directory(self):
        """백업 디렉토리 선택 대화상자"""
        directory = QFileDialog.getExistingDirectory(
            self, _("dialog.backup_path_select.title"), self.backup_manager.get_backup_directory(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            success = self.backup_manager.set_backup_directory(directory)
            
            if success:
                QMessageBox.information(
                    self, _("main_window.backup_folder_set_success_title"), 
                    _("main_window.backup_folder_set_success_message", directory=directory) + 
                    "\n\n" + _("main_window.backup_folder_set_info")
                )
            else:
                QMessageBox.critical(
                    self, _("error.backup_dir_set.title"), 
                    _("error.backup_dir_set.message", directory=directory)
                )
    
    def open_assets_file(self):
        """에셋 파일 열기 및 비동기 로딩 시작"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, localization.get_string("menu.file.open"), "", localization.get_string("main_window.open_file_filter")
        )
        
        if file_path:
            # 본섭 타르코프 경로 확인
            if "EscapeFromTarkov_Data" in file_path:
                data_dir = file_path.split("EscapeFromTarkov_Data")[0] + "EscapeFromTarkov_Data"
                parent_dir = os.path.dirname(data_dir)
                
                # 본섭 타르코프 파일 확인
                be_exe_path = os.path.join(parent_dir, "EscapeFromTarkov_BE.exe")
                battle_eye_dir = os.path.join(parent_dir, "BattlEye")
                
                if os.path.exists(be_exe_path) and os.path.isdir(battle_eye_dir):
                    QMessageBox.critical(
                        self,
                        localization.get_string("live_tarkov_warning.title"),
                        localization.get_string("live_tarkov_warning.message"),
                        QMessageBox.Ok
                    )
                    return
            
            # 파일 로딩 시작
            self.start_loading(file_path)
    
    def start_loading(self, file_path):
        """비동기 파일 로딩 시작"""
        if self.load_thread and self.load_thread.isRunning():
            QMessageBox.warning(self, localization.get_string("warning.loading_in_progress.title"), localization.get_string("warning.loading_in_progress.message"))
            return

        self.statusBar().showMessage(localization.get_string("main_window.status_loading_start", file_path=file_path))
        
        # 진행률 대화상자 설정
        self.progress_dialog = QProgressDialog(localization.get_string("dialog.loading.message"), localization.get_string("general.cancel"), 0, 0, self)
        self.progress_dialog.setWindowTitle(localization.get_string("dialog.loading.title"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.cancel_loading)
        self.progress_dialog.show()

        # 로딩 스레드 시작
        self.load_thread = AssetLoaderThread(self.assets_manager, file_path)
        self.load_thread.load_finished.connect(self.on_load_finished)
        self.load_thread.start()
    
    def cancel_loading(self):
        """로딩 작업 취소"""
        if self.load_thread and self.load_thread.isRunning():
            print("로딩 취소 요청됨...")
            self.load_thread.quit()
            self.load_thread.wait(1000)
            if self.load_thread.isRunning():
                print("경고: 스레드를 정상적으로 종료하지 못했습니다.")

        self.statusBar().showMessage(localization.get_string("main_window.status_loading_cancelled"))
        if self.progress_dialog:
            self.progress_dialog.close()

    def on_load_finished(self, success, file_path):
        """파일 로딩 완료 처리"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        if success:
            self.current_file_path = file_path

            # 창 제목 업데이트
            file_type = self.assets_manager.file_type.capitalize() if self.assets_manager.file_type else "Unknown"
            self.setWindowTitle(f"{localization.get_string('main_window.title')} - {os.path.basename(file_path)} ({file_type})")

            # .assets 파일의 경우 .resS 파일 확인
            if self.assets_manager.file_type == 'assets':
                self._check_resS_files(file_path)

            # 에셋 브라우저 업데이트
            try:
                self.asset_browser.update_texture_list()

                # 누락된 텍스처 처리
                if hasattr(self.assets_manager, 'missing_texture_ids') and self.assets_manager.missing_texture_ids:
                    count = len(self.assets_manager.missing_texture_ids)
                    reason_key = "warning.texture_load.reason_assets" if self.assets_manager.file_type == 'assets' else "warning.texture_load.reason_bundle"
                    reason = localization.get_string(reason_key)
                    msg = localization.get_string("warning.texture_load.message", count=count, reason=reason)
                    QMessageBox.warning(self, localization.get_string("warning.texture_load.title"), msg)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    localization.get_string("error.texture_list_load.title"),
                    localization.get_string("error.texture_list_load.message", error=str(e))
                )

            # UI 상태 초기화
            self.image_editor.set_texture(None, None)
            self.image_preview.set_texture(None)
            self.image_editor.restore_button.setEnabled(False)
            self.texture_modified_since_load = False

            # 상태 메시지 업데이트
            file_ext = os.path.splitext(file_path)[1].lower()
            file_type_str = "Bundle" if file_ext == ".bundle" else "Assets"
            self.statusBar().showMessage(localization.get_string("main_window.status_loading_complete", file_type=file_type_str, file_path=file_path))
        else:
            QMessageBox.critical(self, localization.get_string("error.file_load.title"), localization.get_string("error.file_load.message", file_path=file_path))
            self.statusBar().showMessage(localization.get_string("main_window.status_loading_failed", file_path=file_path))
            self.texture_modified_since_load = False
        
        self.load_thread = None
    
    def _check_resS_files(self, file_path):
        """에셋 파일과 관련된 .resS 파일 존재 여부 확인"""
        file_dir = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        filename_noext = os.path.splitext(filename)[0]
        
        # 가능한 .resS 파일 패턴
        res_patterns = [
            f"{filename}.resS",
            f"{filename_noext}.resS",
            f"sharedassets{filename_noext}.resS"
        ]
        
        # Unity 패턴 추가
        for i in range(10):
            res_patterns.append(f"sharedassets{i}.assets.resS")
        
        # 파일 존재 확인
        found_res_files = []
        for pattern in res_patterns:
            res_path = os.path.join(file_dir, pattern)
            if os.path.exists(res_path):
                found_res_files.append(pattern)
        
        # 파일이 없으면 경고 표시
        if not found_res_files:
            QMessageBox.warning(
                self, 
                localization.get_string("warning.resS_missing.title"), 
                localization.get_string("warning.resS_missing.message")
            )
    
    def save_current_file(self):
        """현재 로드된 파일 저장"""
        if not self.current_file_path:
            QMessageBox.warning(self, localization.get_string("warning.no_file_to_backup.title"), localization.get_string("warning.no_file_to_backup.message"))
            return
        
        # 백업 여부 플래그
        backup_requested = False
        temp_backup_dir = None
        
        # 저장 전 백업 안내
        reply = QMessageBox.question(
            self, 
            localization.get_string("dialog.backup_before_save.title"),
            localization.get_string("dialog.backup_before_save.message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            backup_requested = True
            # 파일명과 관련된 기본 백업 폴더명 생성
            file_name = os.path.basename(self.current_file_path)
            file_base, file_ext = os.path.splitext(file_name)
            suggested_backup_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "backups",
                f"{file_base}_backups"
            )
            
            # 백업 경로 선택 대화상자 표시
            QMessageBox.information(
                self,
                localization.get_string("dialog.backup_path_set.title"),
                localization.get_string("dialog.backup_path_set.message"),
                QMessageBox.Ok
            )
            
            backup_dir = QFileDialog.getExistingDirectory(
                self, localization.get_string("dialog.backup_path_select.title"), suggested_backup_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            # 사용자가 백업 폴더 선택을 취소한 경우
            if not backup_dir:
                backup_requested = False
                # 수정: reply 변수 재사용 대신 새로운 변수 사용
                cancel_reply = QMessageBox.warning(
                    self, 
                    localization.get_string("dialog.backup_cancelled.title"),
                    localization.get_string("dialog.backup_cancelled.message"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if cancel_reply == QMessageBox.No:
                    self.statusBar().showMessage(localization.get_string("main_window.status_save_cancelled"))
                    return
            else:
                # 선택한 백업 경로 설정
                if not self.backup_manager.set_backup_directory(backup_dir):
                    QMessageBox.critical(
                        self,
                        localization.get_string("error.backup_folder_invalid.title"),
                        localization.get_string("error.backup_folder_invalid.message", backup_dir=backup_dir),
                        QMessageBox.Ok
                    )
                    self.statusBar().showMessage(localization.get_string("main_window.status_backup_failed"))
                    return
                
                # 백업 생성
                backup_result = self.backup_manager.create_backup(self.current_file_path)
                if not backup_result:
                    error_msg = localization.get_string("error.backup_creation.message", filename=os.path.basename(self.current_file_path))
                    # 수정: reply 변수 재사용 대신 새로운 변수 사용
                    continue_reply = QMessageBox.critical(
                        self,
                        localization.get_string("error.backup_creation.title"),
                        localization.get_string("dialog.backup_failed_continue.message", error_msg=error_msg),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if continue_reply == QMessageBox.No:
                        self.statusBar().showMessage(localization.get_string("main_window.status_backup_failed"))
                        return
                    backup_requested = False

        # 파일 저장 로직
        save_successful = False
        saved_to_path = None
        
        # 임시 디렉토리 생성 (백업 원하지 않을 경우)
        if not backup_requested:
            # 임시 백업 디렉토리 생성
            temp_backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_backup")
            os.makedirs(temp_backup_dir, exist_ok=True)
            self.backup_manager.set_backup_directory(temp_backup_dir)
            print(f"임시 백업 디렉토리 생성: {temp_backup_dir}")
        
        # 백업 폴더에 임시 저장 후 원본 위치로 복사
        if self.backup_manager.ensure_backup_directory():
            file_basename = os.path.basename(self.current_file_path)
            temp_file_name = f"temp_{file_basename}"
            temp_path = os.path.join(self.backup_manager.get_backup_directory(), temp_file_name)
            
            if self.assets_manager.save_file(temp_path):
                try:
                    # 임시 파일에서 원본 위치로 복사
                    with open(temp_path, 'rb') as src_file, open(self.current_file_path, 'wb') as dst_file:
                        chunk_size = 1024 * 1024  # 1MB 청크
                        while True:
                            chunk = src_file.read(chunk_size)
                            if not chunk:
                                break
                            dst_file.write(chunk)
                    
                    # 임시 파일 삭제
                    try:
                        os.remove(temp_path)
                        print(f"임시 파일 삭제: {temp_path}")
                    except Exception as e:
                        print(f"임시 파일 삭제 오류: {str(e)} - {temp_path}")
                    
                    save_successful = True
                    saved_to_path = self.current_file_path
                    
                    # 성공 메시지 생성
                    if self.assets_manager.file_type == 'assets':
                        # 임시 .resS 파일 정리
                        deleted_files = self.backup_manager.cleanup_temp_resource_files()
                        
                        message = localization.get_string("main_window.save_success_assets_message")
                        
                        if deleted_files > 0:
                            message += localization.get_string("main_window.save_success_assets_cleaned_message", count=deleted_files)
                    else:
                        message = localization.get_string("main_window.save_success_bundle_message", type=self.assets_manager.file_type)
                    
                    QMessageBox.information(self, localization.get_string("asset_browser.save_success.title"), message)
                except Exception as e:
                    QMessageBox.critical(
                        self, 
                        localization.get_string("error.copy_file.title"), 
                        localization.get_string("error.copy_file.message", error=str(e), temp_path=temp_path)
                    )
            else:
                QMessageBox.critical(self, localization.get_string("error.save_temp_file.title"), localization.get_string("error.save_temp_file.message"))
        else:
            # 백업 폴더 없이 직접 저장 (이 경우는 거의 발생하지 않음, 임시 폴더가 생성되므로)
            if self.assets_manager.save_file():
                save_successful = True
                saved_to_path = self.current_file_path
            else:
                 QMessageBox.critical(self, localization.get_string("error.save_file.title"), localization.get_string("error.save_file.message"))
        
        # 저장 성공 후 처리
        if save_successful and saved_to_path:
            self.statusBar().showMessage(localization.get_string("main_window.status_saving_complete", file_path=saved_to_path))
            if self.texture_modified_since_load:
                self.image_editor.restore_button.setEnabled(True)
            self.texture_modified_since_load = False
            
            # 백업을 원하지 않았던 경우 임시 디렉토리 삭제
            if not backup_requested and temp_backup_dir and os.path.exists(temp_backup_dir):
                try:
                    # 디렉토리 내 모든 파일 삭제
                    for filename in os.listdir(temp_backup_dir):
                        file_path_to_delete = os.path.join(temp_backup_dir, filename)
                        try:
                            if os.path.isfile(file_path_to_delete):
                                os.remove(file_path_to_delete)
                        except Exception as e:
                            print(f"임시 파일 삭제 오류: {str(e)} - {file_path_to_delete}")
                    
                    # 디렉토리 삭제
                    os.rmdir(temp_backup_dir)
                    print(f"임시 백업 디렉토리 삭제 완료: {temp_backup_dir}")
                    
                    # 백업 디렉토리 초기화
                    self.backup_manager.backup_dir = None
                except Exception as e:
                    print(f"임시 백업 디렉토리 삭제 오류: {str(e)} - {temp_backup_dir}")
                    # 오류가 나도 백업 디렉토리는 초기화
                    self.backup_manager.backup_dir = None
    
    def save_file_as(self):
        """다른 이름으로 파일 저장"""
        # 초기 저장 경로 설정
        initial_dir = ""
        if self.current_file_path:
            initial_dir = os.path.dirname(self.current_file_path)
        
        # 파일 유형에 따른 필터 설정
        file_filter = localization.get_string("main_window.save_as_filter_all")
        if self.assets_manager.file_type == 'assets':
            file_filter = localization.get_string("main_window.save_as_filter_assets")
        elif self.assets_manager.file_type == 'bundle':
            file_filter = localization.get_string("main_window.save_as_filter_bundle")
        else:
            file_filter = localization.get_string("main_window.save_as_filter_unity")
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, localization.get_string("menu.file.save_as"), initial_dir, file_filter
        )
        
        if file_path:
            # 백업 여부 플래그
            backup_requested = False
            temp_backup_dir = None
            
            # 저장 전 백업 안내
            reply = QMessageBox.question(
                self, 
                localization.get_string("dialog.backup_before_save.title"),
                localization.get_string("dialog.backup_before_save.message"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                backup_requested = True
                # 파일명과 관련된 기본 백업 폴더명 생성
                file_name = os.path.basename(self.current_file_path or file_path)
                file_base, file_ext = os.path.splitext(file_name)
                suggested_backup_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    "backups",
                    f"{file_base}_backups"
                )
                
                # 백업 경로 선택 대화상자 표시
                QMessageBox.information(
                    self,
                    localization.get_string("dialog.backup_path_set.title"),
                    localization.get_string("dialog.backup_path_set.message"),
                    QMessageBox.Ok
                )
                
                backup_dir = QFileDialog.getExistingDirectory(
                    self, localization.get_string("dialog.backup_path_select.title"), suggested_backup_dir,
                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
                )
                
                # 사용자가 백업 폴더 선택을 취소한 경우
                if not backup_dir:
                    backup_requested = False
                    # 백업 없이 계속 진행할지 확인
                    choice = QMessageBox.warning(
                        self, 
                        localization.get_string("dialog.backup_cancelled.title"),
                        localization.get_string("dialog.backup_cancelled.message"),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if choice == QMessageBox.No:
                        self.statusBar().showMessage(localization.get_string("main_window.status_save_cancelled"))
                        return
                else:
                    # 선택한 백업 경로 설정
                    if not self.backup_manager.set_backup_directory(backup_dir):
                        QMessageBox.critical(
                            self,
                            localization.get_string("error.backup_folder_invalid.title"),
                            localization.get_string("error.backup_folder_invalid.message", backup_dir=backup_dir),
                            QMessageBox.Ok
                        )
                        self.statusBar().showMessage(localization.get_string("main_window.status_backup_failed"))
                        return
                    
                    # 현재 파일이 있는 경우에만 백업 생성
                    if self.current_file_path:
                        backup_result = self.backup_manager.create_backup(self.current_file_path)
                        if not backup_result:
                            error_msg = localization.get_string("error.backup_creation.message", filename=os.path.basename(self.current_file_path))
                            choice = QMessageBox.critical(
                                self,
                                localization.get_string("error.backup_creation.title"),
                                localization.get_string("dialog.backup_failed_continue.message", error_msg=error_msg),
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No
                            )
                            if choice == QMessageBox.No:
                                self.statusBar().showMessage(localization.get_string("main_window.status_backup_failed"))
                                return
                            backup_requested = False
            
            # 임시 디렉토리 생성 (백업 원하지 않을 경우)
            if not backup_requested:
                # 임시 백업 디렉토리 생성
                temp_backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp_backup")
                os.makedirs(temp_backup_dir, exist_ok=True)
                self.backup_manager.set_backup_directory(temp_backup_dir)
                print(f"임시 백업 디렉토리 생성: {temp_backup_dir}")
            
            # 백업에서 복원 여부 확인
            latest_backup = None
            if self.current_file_path:
                latest_backup = self.backup_manager.get_latest_backup(self.current_file_path)
                
            if latest_backup:
                reply = QMessageBox.question(
                    self,
                    localization.get_string("dialog.restore_from_backup.title"),
                    localization.get_string("dialog.restore_from_backup.message", backup_name=os.path.basename(latest_backup)),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                # 백업에서 복원
                if reply == QMessageBox.Yes:
                    self.statusBar().showMessage(localization.get_string("main_window.status_restore_backup_start", backup_path=latest_backup))
                    if not self.assets_manager.load_file(latest_backup):
                        QMessageBox.critical(self, localization.get_string("error.backup_file_load.title"), localization.get_string("error.backup_file_load.message", backup_path=latest_backup))
                        return
            
            # .assets 파일 저장 시 .resS 파일 복사 옵션
            dst_dir = os.path.dirname(file_path)
            src_dir = ""
            if self.current_file_path:
                src_dir = os.path.dirname(self.current_file_path)
            
            should_copy_ress = False
            if self.assets_manager.file_type == 'assets' and src_dir and src_dir != dst_dir:
                # 수정: QMessageBox.question의 버튼 텍스트도 번역
                copy_button = localization.get_string("general.copy")
                dont_copy_button = localization.get_string("general.dont_copy")
                reply = QMessageBox.question(
                    self,
                    localization.get_string("dialog.ress_copy.title"),
                    localization.get_string("dialog.ress_copy.message"),
                    copy_button + "|" + dont_copy_button,
                    copy_button
                )
                
                # 버튼 텍스트 기반으로 결과 확인
                should_copy_ress = (reply == 0)
                
            # 파일 저장
            save_successful = self.assets_manager.save_file(file_path, copy_resource_files=should_copy_ress)
            
            if save_successful:
                self.current_file_path = file_path
                
                # 창 제목 업데이트
                file_type = self.assets_manager.file_type.capitalize() if self.assets_manager.file_type else "Unknown"
                self.setWindowTitle(f"{localization.get_string('main_window.title')} - {os.path.basename(file_path)} ({file_type})")
                
                # 저장 완료 메시지
                if self.assets_manager.file_type == 'assets':
                    if should_copy_ress:
                        message = localization.get_string("main_window.save_as_success_assets_copied_message")
                    else:
                        message = localization.get_string("main_window.save_as_success_assets_not_copied_message")
                else:
                    message = localization.get_string("main_window.save_as_success_bundle_message")
                
                QMessageBox.information(self, localization.get_string("asset_browser.save_success.title"), message)
                
                # UI 업데이트
                self.asset_browser.update_texture_list()
                self.statusBar().showMessage(localization.get_string("main_window.status_saving_complete", file_path=file_path))
                
                if self.texture_modified_since_load:
                    self.image_editor.restore_button.setEnabled(True)
                self.texture_modified_since_load = False
                
                # 백업을 원하지 않았던 경우 임시 디렉토리 삭제
                if not backup_requested and temp_backup_dir and os.path.exists(temp_backup_dir):
                    try:
                        # 디렉토리 내 모든 파일 삭제
                        for filename in os.listdir(temp_backup_dir):
                            file_path_to_delete = os.path.join(temp_backup_dir, filename)
                            try:
                                if os.path.isfile(file_path_to_delete):
                                    os.remove(file_path_to_delete)
                            except Exception as e:
                                print(f"임시 파일 삭제 오류: {str(e)} - {file_path_to_delete}")
                        
                        # 디렉토리 삭제
                        os.rmdir(temp_backup_dir)
                        print(f"임시 백업 디렉토리 삭제 완료: {temp_backup_dir}")
                        
                        # 백업 디렉토리 초기화
                        self.backup_manager.backup_dir = None
                    except Exception as e:
                        print(f"임시 백업 디렉토리 삭제 오류: {str(e)} - {temp_backup_dir}")
                        # 오류가 나도 백업 디렉토리는 초기화
                        self.backup_manager.backup_dir = None
            else:
                QMessageBox.critical(self, localization.get_string("error.save_file.title"), localization.get_string("error.save_file.message", file_path=file_path))
    
    def create_backup(self):
        """현재 파일의 백업 생성"""
        if not self.current_file_path:
            QMessageBox.warning(self, localization.get_string("warning.no_file_to_backup.title"), localization.get_string("warning.no_file_to_backup.message"))
            return
        
        backup_path = self.backup_manager.create_backup(self.current_file_path)
        if backup_path:
            QMessageBox.information(self, localization.get_string("image_editor.restore_success.title"), localization.get_string("main_window.create_backup_success", path=backup_path))
        else:
            QMessageBox.critical(self, localization.get_string("error.backup_creation.failed.title"), localization.get_string("error.backup_creation_failed.message"))
    
    def on_texture_selected(self, texture_obj, texture_data):
        """텍스처 선택 시 처리"""
        self.image_preview.set_texture(texture_data)
        self.image_editor.set_texture(texture_obj, texture_data)
    
    def on_texture_replaced(self):
        """텍스처 교체 시 처리"""
        self.image_preview.refresh()
        
        # 수정 상태 표시 (번역 적용)
        title = self.windowTitle()
        if not title.endswith(" *"):
             self.setWindowTitle(title + " *")
        
        self.texture_modified_since_load = True
        self.image_editor.restore_button.setEnabled(False)
    
    def show_about(self):
        """프로그램 정보 표시"""
        try:
            icon_path = get_resource_path("resources/icon.ico")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                about_box = QMessageBox(self)
                about_box.setIconPixmap(icon.pixmap(64, 64))  # 아이콘 크기 설정
                about_box.setWindowTitle(localization.get_string("dialog.about.title"))
                about_box.setTextFormat(Qt.RichText)
                about_box.setText(
                    localization.get_string("dialog.about.text", 
                      app_name=__app_name__, version=__version__, 
                      description=__description__, author=__author__, copyright=__copyright__)
                )
                about_box.exec_()
            else:
                # 아이콘이 없을 경우 기본 메시지 박스 사용
                QMessageBox.about(
                    self,
                    localization.get_string("dialog.about.default.title"),
                    localization.get_string("dialog.about.default.text")
                )
        except Exception as e:
            # 오류 발생 시 기본 정보 표시
            QMessageBox.about(
                self,
                localization.get_string("dialog.about.default.title"),
                localization.get_string("dialog.about.default.text")
            )
    
    def show_asset_structure_info(self):
        """Unity 에셋 구조 정보 표시"""
        QMessageBox.information(
            self,
            localization.get_string("dialog.asset_info.title"),
            localization.get_string("dialog.asset_info.text")
        )
    
    def cleanup_temp_files(self):
        """백업 폴더의 임시 리소스 파일 정리"""
        if not self.backup_manager.ensure_backup_directory():
            QMessageBox.warning(
                self, localization.get_string("warning.backup_dir_invalid.title"), 
                localization.get_string("warning.backup_dir_invalid.message")
            )
            return
            
        reply = QMessageBox.question(
            self,
            localization.get_string("dialog.cleanup_temp.title"),
            localization.get_string("dialog.cleanup_temp.confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = self.backup_manager.cleanup_temp_resource_files()
            
            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    localization.get_string("dialog.cleanup_temp.title"),
                    localization.get_string("dialog.cleanup_temp.success", count=deleted_count)
                )
            else:
                QMessageBox.information(
                    self,
                    localization.get_string("dialog.cleanup_temp.title"),
                    localization.get_string("dialog.cleanup_temp.no_files")
                )
    
    def closeEvent(self, event):
        """윈도우 닫기 이벤트 처리"""
        event.accept()
