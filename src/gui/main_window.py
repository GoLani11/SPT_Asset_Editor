import os
import sys
import json
import time
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QFileDialog, QMessageBox,
                             QAction, QVBoxLayout, QWidget, QSplitter, QProgressDialog,
                             QHBoxLayout, QToolBar)
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
    
    def __init__(self):
        super().__init__()
        
        # 핵심 객체 초기화
        self.assets_manager = AssetsManager()
        self.texture_processor = TextureProcessor()
        self.backup_manager = BackupManager()
        
        self.backup_manager.ensure_backup_directory()
        self.init_ui()
        
        self.current_file_path = None
        self.load_thread = None
        self.progress_dialog = None
        self.texture_modified_since_load = False
        
    def init_ui(self):
        """UI 초기화"""
        # 윈도우 기본 설정
        self.setWindowTitle("타르코프 에셋 에디터")
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
        self.statusBar().showMessage("준비")
        
    def setup_menu(self):
        """메뉴바 구성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        # 열기
        self.open_action = QAction(QIcon.fromTheme("document-open"), "열기", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_assets_file)
        file_menu.addAction(self.open_action)
        
        file_menu.addSeparator()
        
        # 저장 관련 액션
        self.save_action = QAction(QIcon.fromTheme("document-save"), "저장", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_current_file)
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "다른 이름으로 저장", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()
        
        # 설정 메뉴
        settings_menu = menubar.addMenu("설정")
        
        # 백업 설정
        set_backup_dir_action = QAction("백업 폴더 설정", self)
        set_backup_dir_action.triggered.connect(self.select_backup_directory)
        settings_menu.addAction(set_backup_dir_action)
        
        file_menu.addSeparator()
        
        # 종료
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "종료", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu("도구")
        
        asset_info_action = QAction("에셋 구조 정보", self)
        asset_info_action.triggered.connect(self.show_asset_structure_info)
        tools_menu.addAction(asset_info_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def select_backup_directory(self):
        """백업 디렉토리 선택 대화상자"""
        directory = QFileDialog.getExistingDirectory(
            self, "백업 폴더 선택", self.backup_manager.get_backup_directory(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            success = self.backup_manager.set_backup_directory(directory)
            
            if success:
                QMessageBox.information(
                    self, "백업 폴더 설정", 
                    f"백업 폴더가 성공적으로 설정되었습니다:\n{directory}\n\n"
                    f"앞으로 모든 백업 파일은 이 폴더에 저장됩니다."
                )
            else:
                QMessageBox.critical(
                    self, "오류", 
                    f"백업 폴더를 설정할 수 없습니다:\n{directory}\n\n"
                    f"폴더가 존재하는지, 쓰기 권한이 있는지 확인하세요."
                )
    
    def open_assets_file(self):
        """에셋 파일 열기 및 비동기 로딩 시작"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "에셋 파일 열기", "", "Unity 에셋 파일 (*.assets *.bundle);;Assets 파일 (*.assets);;Bundle 파일 (*.bundle);;모든 파일 (*.*)"
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
                        "위험: 본섭 타르코프 에셋 파일 수정 시도",
                        "주의! 당신은 본섭 타르코프의 에셋 파일을 수정하려고 합니다!\n\n"
                        "이는 게임 클라이언트를 손상시킬 수 있으며 BattlEye 안티치트에 의해\n"
                        "탐지되어 계정이 차단될 수 있습니다.\n\n"
                        "본섭 타르코프 에셋 파일 수정은 권장하지 않습니다.\n"
                        "만약 다른 방법으로 수정을 진행할 경우\n"
                        "발생할 수 있는 문제에 대해 책임지지 않습니다.",
                        QMessageBox.Ok
                    )
                    return
            
            # 백업 경로 설정 (항상 선택하도록 함)
            # 파일명과 관련된 기본 백업 폴더명 생성
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            suggested_backup_dir = os.path.join(
                self.backup_manager.get_backup_directory(),
                f"{file_base}_backups"
            )
            
            # 백업 경로 선택 대화상자 표시
            QMessageBox.information(
                self,
                "백업 경로 설정",
                "이 에셋 파일의 백업을 저장할 폴더를 선택해주세요.\n"
                "백업은 필수이며, 지정된 폴더에 타임스탬프가 포함된 백업 파일이 생성됩니다.",
                QMessageBox.Ok
            )
            
            backup_dir = QFileDialog.getExistingDirectory(
                self, "백업 폴더 선택", suggested_backup_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            # 사용자가 백업 폴더 선택을 취소한 경우
            if not backup_dir:
                self.statusBar().showMessage("파일 로딩 취소됨 - 백업 폴더가 선택되지 않았습니다.")
                return
            
            # 선택한 백업 경로 설정
            if not self.backup_manager.set_backup_directory(backup_dir):
                QMessageBox.critical(
                    self,
                    "백업 폴더 오류",
                    f"선택한 백업 폴더를 사용할 수 없습니다: {backup_dir}\n"
                    "폴더가 존재하는지, 쓰기 권한이 있는지 확인하세요.",
                    QMessageBox.Ok
                )
                return
            
            # 자동 백업 수행
            print(f"[DEBUG] 자동 백업 호출 시작: {file_path}")
            backup_result = self.backup_manager.create_automatic_backup(file_path)
            if backup_result:
                print(f"[DEBUG] 자동 백업 생성 성공: {backup_result}")
                # 성공 메시지 표시
                QMessageBox.information(
                    self,
                    "백업 완료",
                    f"자동 백업이 성공적으로 생성되었습니다:\n{backup_result}",
                    QMessageBox.Ok
                )
            else:
                error_msg = f"에셋 파일 '{file_name}'의 백업을 생성하지 못했습니다."
                print(f"[DEBUG] 자동 백업 생성 실패: {error_msg}")
                if QMessageBox.critical(
                    self,
                    "백업 실패",
                    f"{error_msg}\n파일 로드를 계속하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                ) == QMessageBox.No:
                    self.statusBar().showMessage("파일 로딩 취소됨 - 백업 실패")
                    return
                
            # 파일 로딩 시작
            self.start_loading(file_path)
    
    def start_loading(self, file_path):
        """비동기 파일 로딩 시작"""
        if self.load_thread and self.load_thread.isRunning():
            QMessageBox.warning(self, "로딩 중", "이미 다른 파일을 로딩 중입니다.")
            return

        self.statusBar().showMessage(f"파일 로딩 시작: {file_path}...")
        
        # 진행률 대화상자 설정
        self.progress_dialog = QProgressDialog("파일을 로딩 중입니다...", "취소", 0, 0, self)
        self.progress_dialog.setWindowTitle("로딩 중")
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

        self.statusBar().showMessage("파일 로드 취소됨")
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
            self.setWindowTitle(f"타르코프 에셋 에디터 - {os.path.basename(file_path)} ({file_type})")

            # .assets 파일의 경우 .resS 파일 확인
            if self.assets_manager.file_type == 'assets':
                self._check_resS_files(file_path)

            # 에셋 브라우저 업데이트
            try:
                self.asset_browser.update_texture_list()

                # 누락된 텍스처 처리
                if hasattr(self.assets_manager, 'missing_texture_ids') and self.assets_manager.missing_texture_ids:
                    msg = f"일부 텍스처({len(self.assets_manager.missing_texture_ids)}개)를 로드할 수 없습니다.\\n\\n"

                    if self.assets_manager.file_type == 'assets':
                        msg += "이 문제는 관련된 .resS 파일이 없거나, 텍스처 데이터가 손상되었을 때 발생합니다.\\n"
                    elif self.assets_manager.file_type == 'bundle':
                        msg += "이 문제는 번들 파일의 텍스처 데이터가 손상되었거나 접근할 수 없을 때 발생합니다.\\n"

                    msg += "텍스처 편집이 제한될 수 있습니다."

                    QMessageBox.warning(self, "텍스처 로드 경고", msg)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "텍스처 로드 오류",
                    f"텍스처 목록을 로드하는 중 오류가 발생했습니다:\\n{str(e)}\\n\\n"
                    f"일부 기능이 제한될 수 있습니다."
                )

            # UI 상태 초기화
            self.image_editor.set_texture(None, None)
            self.image_preview.set_texture(None)
            self.image_editor.restore_button.setEnabled(False)
            self.texture_modified_since_load = False

            # 상태 메시지 업데이트
            file_ext = os.path.splitext(file_path)[1].lower()
            file_type_str = "Bundle" if file_ext == ".bundle" else "Assets"
            self.statusBar().showMessage(f"{file_type_str} 파일 로드 완료: {file_path}")
        else:
            QMessageBox.critical(self, "오류", f"파일을 로드할 수 없습니다: {file_path}")
            self.statusBar().showMessage(f"파일 로드 실패: {file_path}")
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
                "리소스 파일 누락 경고", 
                "관련된 .resS 파일을 찾을 수 없습니다.\n\n"
                "이로 인해 일부 텍스처가 올바르게 로드되지 않을 수 있으며,\n"
                "텍스처가 저장된 후에도 변경사항이 게임에 적용되지 않을 수 있습니다.\n\n"
                "에셋 파일이 있는 폴더에 관련 .resS 파일(예: sharedassets*.assets.resS)이 "
                "함께 있는지 확인하세요."
            )
    
    def save_current_file(self):
        """현재 로드된 파일 저장"""
        if not self.current_file_path:
            QMessageBox.warning(self, "경고", "저장할 파일이 로드되지 않았습니다.")
            return

        # 백업 생성
        file_name = os.path.basename(self.current_file_path)
        file_base, file_ext = os.path.splitext(file_name)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_backup_name = f"{file_base}_save_{timestamp}{file_ext}"

        # 이미 설정된 백업 디렉토리 사용
        backup_dir_path = self.backup_manager.get_backup_directory()
        if not backup_dir_path:
            QMessageBox.critical(
                self,
                "백업 폴더 오류",
                "백업 폴더가 설정되지 않았습니다. 파일을 다시 열어 백업 폴더를 설정해주세요.",
                QMessageBox.Ok
            )
            self.statusBar().showMessage("백업 폴더가 설정되지 않아 저장 작업을 중단합니다.")
            return

        # 백업 파일 경로 설정 및 백업 생성
        backup_path = os.path.join(backup_dir_path, default_backup_name)
        created_backup_path = self.backup_manager.create_backup(self.current_file_path, backup_path=backup_path)

        if not created_backup_path:
            QMessageBox.critical(self, "백업 실패", f"필수 백업 파일을 생성할 수 없습니다: {backup_path}\n저장 작업을 중단합니다.")
            self.statusBar().showMessage("백업 실패로 저장 작업 중단됨")
            return

        # 파일 저장 로직
        save_successful = False
        saved_to_path = None
        
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
                        
                        message = (
                            f"파일이 성공적으로 저장되었습니다.\n\n"
                            f"변경된 .assets 파일이 원본 위치에 적용되었습니다.\n"
                            f"기존 .resS 파일을 유지하여 텍스처 변경사항이 게임에 올바르게 적용됩니다."
                        )
                        
                        if deleted_files > 0:
                            message += f"\n\n임시 생성된 .resS 파일 {deleted_files}개가 백업 폴더에서 삭제되었습니다."
                    else:
                        message = (
                            f"파일이 성공적으로 저장되었습니다.\n\n"
                            f"변경된 {self.assets_manager.file_type} 파일이 원본 위치에 적용되었습니다."
                        )
                    
                    QMessageBox.information(self, "저장 완료", message)
                except Exception as e:
                    QMessageBox.critical(
                        self, 
                        "오류", 
                        f"파일 복사 중 오류가 발생했습니다: {str(e)}\n\n"
                        f"백업 폴더에 저장된 임시 파일: {temp_path}"
                    )
            else:
                QMessageBox.critical(self, "오류", "임시 파일을 저장할 수 없습니다.")
        else:
            # 백업 폴더 없이 직접 저장
            if self.assets_manager.save_file():
                save_successful = True
                saved_to_path = self.current_file_path
            else:
                 QMessageBox.critical(self, "오류", "파일을 저장할 수 없습니다.")
        
        # 저장 성공 후 처리
        if save_successful and saved_to_path:
            self.statusBar().showMessage(f"파일 저장 완료: {saved_to_path}")
            if self.texture_modified_since_load:
                self.image_editor.restore_button.setEnabled(True)
            self.texture_modified_since_load = False
    
    def save_file_as(self):
        """다른 이름으로 파일 저장"""
        # 초기 저장 경로 설정
        initial_dir = ""
        if self.current_file_path:
            initial_dir = os.path.dirname(self.current_file_path)
        
        # 파일 유형에 따른 필터 설정
        file_filter = "모든 파일 (*.*)"
        if self.assets_manager.file_type == 'assets':
            file_filter = "Unity Assets 파일 (*.assets);;모든 파일 (*.*)"
        elif self.assets_manager.file_type == 'bundle':
            file_filter = "Unity Bundle 파일 (*.bundle);;모든 파일 (*.*)"
        else:
            file_filter = "Unity 파일 (*.assets *.bundle);;Unity Assets 파일 (*.assets);;Unity Bundle 파일 (*.bundle);;모든 파일 (*.*)"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "다른 이름으로 저장", initial_dir, file_filter
        )
        
        if file_path:
            # 백업 디렉토리 확인
            self.backup_manager.ensure_backup_directory()
            
            # 백업에서 복원 여부 확인
            latest_backup = None
            if self.current_file_path:
                latest_backup = self.backup_manager.get_latest_backup(self.current_file_path)
                
            if latest_backup:
                reply = QMessageBox.question(
                    self,
                    "백업에서 복원",
                    f"최신 백업({os.path.basename(latest_backup)})에서 복원한 후 저장하시겠습니까?\n\n"
                    f"'예'를 선택하면 백업 파일에서 복원한 후 저장합니다.\n"
                    f"'아니오'를 선택하면 현재 수정 중인 파일을 그대로 저장합니다.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                # 백업에서 복원
                if reply == QMessageBox.Yes:
                    self.statusBar().showMessage(f"백업에서 복원 중: {latest_backup}")
                    if not self.assets_manager.load_file(latest_backup):
                        QMessageBox.critical(self, "오류", f"백업 파일을 로드할 수 없습니다: {latest_backup}")
                        return
            
            # .assets 파일 저장 시 .resS 파일 복사 옵션
            dst_dir = os.path.dirname(file_path)
            src_dir = ""
            if self.current_file_path:
                src_dir = os.path.dirname(self.current_file_path)
            
            should_copy_ress = False
            if self.assets_manager.file_type == 'assets' and src_dir and src_dir != dst_dir:
                reply = QMessageBox.question(
                    self,
                    ".resS 파일 복사 여부",
                    "다른 폴더에 저장합니다. .resS 파일 처리 방식을 선택하세요:\n\n"
                    "• '복사하기'를 선택하면 원본 폴더의 .resS 파일이 새 위치로 복사됩니다.\n"
                    "• '복사하지 않음'을 선택하면 .assets 파일만 저장되고 .resS 파일은 복사되지 않습니다.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                should_copy_ress = (reply == QMessageBox.StandardButton.Yes)
            
            # 파일 저장
            save_successful = self.assets_manager.save_file(file_path, copy_resource_files=should_copy_ress)
            
            if save_successful:
                self.current_file_path = file_path
                
                # 창 제목 업데이트
                file_type = self.assets_manager.file_type.capitalize() if self.assets_manager.file_type else "Unknown"
                self.setWindowTitle(f"타르코프 에셋 에디터 - {os.path.basename(file_path)} ({file_type})")
                
                # 저장 완료 메시지
                if self.assets_manager.file_type == 'assets':
                    if should_copy_ress:
                        message = (
                            f"파일이 성공적으로 저장되었습니다.\n\n"
                            f"관련된 .resS 파일이 발견되면 함께 복사되었습니다.\n"
                            f"이렇게 하면 텍스처 변경사항이 게임에 올바르게 적용됩니다."
                        )
                    else:
                        message = (
                            f"파일이 성공적으로 저장되었습니다.\n\n"
                            f".assets 파일만 저장되었습니다.\n"
                            f"텍스처 변경사항이 게임에 올바르게 적용되려면 관련 .resS 파일도 필요합니다."
                        )
                else:
                    message = f"파일이 성공적으로 저장되었습니다."
                
                QMessageBox.information(self, "저장 완료", message)
                
                # UI 업데이트
                self.asset_browser.update_texture_list()
                self.statusBar().showMessage(f"파일 저장 완료: {file_path}")
                
                if self.texture_modified_since_load:
                    self.image_editor.restore_button.setEnabled(True)
                self.texture_modified_since_load = False
            else:
                QMessageBox.critical(self, "오류", f"파일을 저장할 수 없습니다: {file_path}")
    
    def create_backup(self):
        """현재 파일의 백업 생성"""
        if not self.current_file_path:
            QMessageBox.warning(self, "경고", "백업할 파일이 로드되지 않았습니다.")
            return
        
        backup_path = self.backup_manager.create_backup(self.current_file_path)
        if backup_path:
            QMessageBox.information(self, "백업 완료", f"백업 파일이 생성되었습니다:\n{backup_path}")
        else:
            QMessageBox.critical(self, "오류", "백업을 생성할 수 없습니다.")
    
    def on_texture_selected(self, texture_obj, texture_data):
        """텍스처 선택 시 처리"""
        self.image_preview.set_texture(texture_data)
        self.image_editor.set_texture(texture_obj, texture_data)
    
    def on_texture_replaced(self):
        """텍스처 교체 시 처리"""
        self.image_preview.refresh()
        
        # 수정 상태 표시
        if not self.windowTitle().endswith(" *"):
             self.setWindowTitle(self.windowTitle() + " *")
        
        self.texture_modified_since_load = True
        self.image_editor.restore_button.setEnabled(False)
    
    def show_about(self):
        """프로그램 정보 표시"""
        QMessageBox.about(
            self,
            "타르코프 에셋 에디터 정보",
            "타르코프 에셋 에디터 v1.0\n\n"
            "SPT 타르코프 게임의 .assets 파일에서 Texture2D 이미지를 추출, 미리보기, 수정 및 복원할 수 있는 도구입니다.\n\n"
            "© 2025 Golani11"
        )
    
    def show_asset_structure_info(self):
        """Unity 에셋 구조 정보 표시"""
        QMessageBox.information(
            self,
            "Unity 에셋 구조 정보",
            "<h3>Unity 에셋 파일 구조 안내</h3>"
            "<p>Unity 게임의 에셋은 다음과 같은 파일들로 구성됩니다:</p>"
            "<ul>"
            "<li><b>.assets 파일</b>: 에셋 메타데이터와 작은 리소스를 저장합니다.</li>"
            "<li><b>.resS 파일</b>: 큰 리소스 데이터(주로 텍스처, 오디오 등)를 저장합니다.</li>"
            "<li><b>.bundle 파일</b>: 여러 에셋을 하나로 묶은 번들 파일로, 게임에 바로 로드될 수 있습니다.</li>"
            "</ul>"
            "<p>텍스처 이미지를 수정할 때 다음 사항에 주의하세요:</p>"
            "<ul>"
            "<li>텍스처의 실제 이미지 데이터는 보통 .resS 파일에 저장됩니다.</li>"
            "<li>텍스처 수정이 게임에 올바르게 적용되려면 .assets 파일과 관련된 .resS 파일이 모두 필요합니다.</li>"
            "<li>항상 원본 .assets 파일이 있는 폴더에 관련 .resS 파일이 있는지 확인하세요.</li>"
            "<li>에셋 편집기는 파일 저장 시 자동으로 관련 .resS 파일을 찾아 함께 복사합니다.</li>"
            "<li>번들 파일(.bundle)은 필요한 모든 자원을 포함하고 있어 별도의 .resS 파일이 필요하지 않습니다.</li>"
            "</ul>"
            "<p>텍스처 로드 오류가 발생하면 관련 .resS 파일이 없거나 손상되었을 가능성이 높습니다.</p>"
        )
    
    def cleanup_temp_files(self):
        """백업 폴더의 임시 리소스 파일 정리"""
        if not self.backup_manager.ensure_backup_directory():
            QMessageBox.warning(
                self, "경고", 
                "백업 폴더가 존재하지 않거나 접근할 수 없습니다."
            )
            return
            
        reply = QMessageBox.question(
            self,
            "임시 파일 정리",
            "백업 폴더에서 임시 리소스 파일(.resS)들을 정리하시겠습니까?\n\n"
            "이 작업은 백업 폴더에 있는 모든 임시 리소스 파일을 삭제합니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = self.backup_manager.cleanup_temp_resource_files()
            
            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "정리 완료",
                    f"총 {deleted_count}개의 임시 리소스 파일이 삭제되었습니다."
                )
            else:
                QMessageBox.information(
                    self,
                    "정리 완료",
                    "삭제할 임시 리소스 파일이 없습니다."
                )
    
    def closeEvent(self, event):
        """윈도우 닫기 이벤트 처리"""
        event.accept()

    def toggle_auto_backup(self, checked):
        """자동 백업 설정 토글 - 더 이상 사용되지 않음"""
        # 강제 백업이 적용되었으므로 이 함수는 더 이상 사용되지 않음
        self.statusBar().showMessage("백업은 항상 자동으로 수행됩니다", 3000)
    
    def save_auto_backup_preference(self, preference):
        """자동 백업 설정 저장 - 항상 True로 설정"""
        # 백업이 필수이므로 항상 True로 설정
        try:
            settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "settings")
            os.makedirs(settings_dir, exist_ok=True)
            
            settings_file = os.path.join(settings_dir, "backup_preferences.json")
            
            # 기존 설정 로드 또는 새로 생성
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            # 항상 True로 설정
            settings['auto_backup'] = True
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
                
            return True
        except Exception as e:
            print(f"자동 백업 설정 저장 오류: {str(e)}")
            return False

    def get_auto_backup_preference(self):
        """자동 백업 설정 로드 - 항상 True 반환"""
        # 백업이 필수이므로 항상 True 반환
        return True
