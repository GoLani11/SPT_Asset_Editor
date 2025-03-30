import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QGroupBox, QProgressBar
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PIL import Image
from PyQt5.QtWidgets import QApplication

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_resizer import ImageResizer


class ImageEditor(QWidget):
    """
    이미지 교체 및 리사이징 인터페이스를 제공하는 위젯
    """
    
    # 텍스처 교체 시그널
    texture_replaced = pyqtSignal()
    
    def __init__(self, texture_processor, backup_manager):
        super().__init__()
        
        self.texture_processor = texture_processor
        self.backup_manager = backup_manager
        self.image_resizer = ImageResizer(texture_processor)
        
        self.current_texture_obj = None
        self.current_texture_data = None
        self.original_texture_image = None  # 원본 텍스처 이미지 데이터 저장
        self.new_image_path = None
        self.resized_image_path = None
        
        # 이미지 캐싱 관련 속성 추가
        self.image_cache = {}
        self.resize_cache = {}
        self.max_cache_size = 10
        
        # UI 초기화
        self.init_ui()
        
        # 임시 파일 정리
        self._clean_temp_files()
        
    def init_ui(self):
        """
        UI 컴포넌트 초기화
        """
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        
        # 제목 레이블
        title_label = QLabel("이미지 교체 및 리사이징")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 이미지 교체 그룹
        replace_group = QGroupBox("커스텀 이미지 선택")
        replace_layout = QVBoxLayout(replace_group)
        
        # 이미지 선택 버튼 및 경로 표시
        select_layout = QHBoxLayout()
        
        self.select_button = QPushButton("이미지 선택...")
        self.select_button.clicked.connect(self.select_image)
        select_layout.addWidget(self.select_button)
        
        self.path_label = QLabel("선택된 이미지: 없음")
        select_layout.addWidget(self.path_label, 1)
        
        replace_layout.addLayout(select_layout)
        
        # 선택된 이미지 미리보기
        preview_layout = QHBoxLayout()
        
        # 원본 이미지 미리보기
        original_layout = QVBoxLayout()
        original_layout.addWidget(QLabel("원본 이미지:"))
        self.original_image_label = QLabel()
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setStyleSheet("background-color: #f0f0f0;")
        self.original_image_label.setMinimumHeight(150)
        self.original_image_label.setMaximumHeight(200)
        original_layout.addWidget(self.original_image_label)
        preview_layout.addLayout(original_layout)
        
        # 새 이미지 미리보기
        new_layout = QVBoxLayout()
        new_layout.addWidget(QLabel("새 이미지:"))
        self.new_image_label = QLabel()
        self.new_image_label.setAlignment(Qt.AlignCenter)
        self.new_image_label.setStyleSheet("background-color: #f0f0f0;")
        self.new_image_label.setMinimumHeight(150)
        self.new_image_label.setMaximumHeight(200)
        new_layout.addWidget(self.new_image_label)
        preview_layout.addLayout(new_layout)
        
        replace_layout.addLayout(preview_layout)
        
        # 리사이징 정보
        self.resize_info_label = QLabel("원본 해상도에 맞게 자동으로 리사이징됩니다.")
        replace_layout.addWidget(self.resize_info_label)
        
        # 리사이징 진행 상태
        self.resize_progress = QProgressBar()
        self.resize_progress.setVisible(False)
        replace_layout.addWidget(self.resize_progress)
        
        layout.addWidget(replace_group)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 교체 버튼
        self.replace_button = QPushButton("이미지 교체")
        self.replace_button.clicked.connect(self.replace_image)
        self.replace_button.setEnabled(False)
        button_layout.addWidget(self.replace_button)
        
        # 원본 복원 버튼
        self.restore_button = QPushButton("원본 복원")
        self.restore_button.clicked.connect(self.restore_original)
        self.restore_button.setEnabled(False)
        button_layout.addWidget(self.restore_button)
        
        layout.addLayout(button_layout)
        
    def set_texture(self, texture_obj, texture_data):
        """
        현재 텍스처 설정
        
        Args:
            texture_obj: 텍스처 객체
            texture_data: 텍스처 데이터 객체
        """
        self.current_texture_obj = texture_obj
        self.current_texture_data = texture_data
        
        # 원본 텍스처 이미지 저장 (복원을 위해)
        if texture_data:
            try:
                # TextureProcessor를 사용하여 이미지 데이터 가져오기
                img = self.texture_processor.get_texture_preview(texture_data)
                if img:
                    self.original_texture_image = img.copy()
                else:
                    self.original_texture_image = None
                    print("텍스처 이미지를 가져올 수 없습니다.")
            except Exception as e:
                self.original_texture_image = None
                print(f"원본 텍스처 이미지 복사 오류: {str(e)}")
        else:
            self.original_texture_image = None
        
        # 새 이미지 초기화
        self.new_image_path = None
        self.resized_image_path = None
        self.path_label.setText("선택된 이미지: 없음")
        self.new_image_label.clear()
        
        # 원본 이미지 표시
        if texture_data:
            img = self.texture_processor.get_texture_preview(texture_data)
            
            # 이미지 모드에 따라 적절한 QImage 포맷 사용
            width, height = img.size
            
            if img.mode == 'RGBA':
                # RGBA 모드일 경우 알파 채널 포함하여 변환
                bytes_per_line = 4 * width
                q_format = QImage.Format_RGBA8888
                img_data = img.tobytes('raw', 'RGBA')
            else:
                # RGB 모드일 경우
                bytes_per_line = 3 * width
                q_format = QImage.Format_RGB888
                img_data = img.tobytes('raw', 'RGB')
            
            q_image = QImage(img_data, width, height, bytes_per_line, q_format)
            pixmap = QPixmap.fromImage(q_image)
            
            # 원본 비율 유지하면서 적절한 크기로 스케일링
            scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.original_image_label.setPixmap(scaled_pixmap)
        else:
            self.original_image_label.clear()
        
        # 버튼 상태 업데이트
        self.replace_button.setEnabled(False)
        self.restore_button.setEnabled(False)  # 처음에는 복원 버튼 비활성화
        
        # 리사이징 정보 업데이트
        if texture_data:
            self.resize_info_label.setText(
                f"원본 해상도: {texture_data.m_Width}x{texture_data.m_Height} - 자동으로 리사이징됩니다."
            )
        else:
            self.resize_info_label.setText("원본 해상도에 맞게 자동으로 리사이징됩니다.")
    
    def select_image(self):
        """
        이미지 파일 선택 대화상자 표시
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "", "이미지 파일 (*.png *.jpg *.jpeg *.bmp *.tga);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                # PIL로 이미지 로드 (알파 채널도 올바르게 처리하기 위함)
                img = Image.open(file_path)
                
                # 이미지 모드에 따라 적절한 QImage 포맷 사용
                width, height = img.size
                
                if img.mode == 'RGBA':
                    # RGBA 모드일 경우 알파 채널 포함하여 변환
                    bytes_per_line = 4 * width
                    q_format = QImage.Format_RGBA8888
                    img_data = img.tobytes('raw', 'RGBA')
                else:
                    # RGB 모드로 변환
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    bytes_per_line = 3 * width
                    q_format = QImage.Format_RGB888
                    img_data = img.tobytes('raw', 'RGB')
                
                # QImage 및 QPixmap 생성
                q_image = QImage(img_data, width, height, bytes_per_line, q_format)
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.new_image_label.setPixmap(scaled_pixmap)
                
                # 경로 저장 및 표시
                self.new_image_path = file_path
                self.path_label.setText(f"선택된 이미지: {os.path.basename(file_path)}")
                
                # 교체 버튼 활성화
                self.replace_button.setEnabled(True)
                
                # 리사이징 정보 업데이트
                if self.current_texture_data:
                    # 이미지 해상도 비교
                    match, source_dims = self.image_resizer.compare_dimensions(
                        file_path, self.current_texture_data.m_Width, self.current_texture_data.m_Height
                    )
                    
                    if match:
                        self.resize_info_label.setText(
                            f"이미지 해상도가 일치합니다: {source_dims[0]}x{source_dims[1]}"
                        )
                        self.resized_image_path = None
                    else:
                        self.resize_info_label.setText(
                            f"원본 해상도: {self.current_texture_data.m_Width}x{self.current_texture_data.m_Height}, "
                            f"선택된 이미지: {source_dims[0]}x{source_dims[1]} - 자동으로 리사이징됩니다."
                        )
                        
                        # 이미지 리사이징
                        self.resize_progress.setVisible(True)
                        self.resize_progress.setValue(0)
                        
                        # 리사이징 수행
                        self.resize_progress.setValue(50)
                        self.resized_image_path = self.image_resizer.resize_image(
                            file_path, self.current_texture_data.m_Width, self.current_texture_data.m_Height
                        )
                        self.resize_progress.setValue(100)
                        
                        if self.resized_image_path:
                            self.resize_info_label.setText(
                                f"리사이징 완료: {source_dims[0]}x{source_dims[1]} -> "
                                f"{self.current_texture_data.m_Width}x{self.current_texture_data.m_Height}"
                            )
                        else:
                            self.resize_info_label.setText("리사이징 실패! 이미지를 교체할 수 없습니다.")
                            self.replace_button.setEnabled(False)
                        
                        # 잠시 후 진행 상태 바 숨기기
                        QTimer.singleShot(2000, lambda: self.resize_progress.setVisible(False))
            except Exception as e:
                QMessageBox.critical(self, "오류", f"이미지를 로드할 수 없습니다: {str(e)}")
    
    def replace_image(self):
        """
        선택한 이미지로 텍스처 교체
        """
        if not self.current_texture_obj or not self.current_texture_data or not self.new_image_path:
            return
        
        try:
            # 진행 상태 표시
            self.resize_progress.setRange(0, 100)
            self.resize_progress.setValue(0)
            self.resize_progress.setVisible(True)
            
            # 선택한 이미지를 원본 텍스처와 동일한 크기로 리사이징
            target_width = self.current_texture_data.m_Width
            target_height = self.current_texture_data.m_Height
            
            # 리사이징 작업 실행
            self.resize_image(target_width, target_height)
            
        except Exception as e:
            self.resize_progress.setVisible(False)
            QMessageBox.critical(self, "오류", f"이미지 교체 중 오류가 발생했습니다: {str(e)}")
            print(f"이미지 교체 오류: {str(e)}")
    
    def _optimize_resize(self, image, target_width, target_height):
        """대용량 이미지 처리를 위한 단계적 리사이징"""
        curr_width, curr_height = image.size
        
        # 작은 이미지는 바로 리사이징
        if curr_width < target_width * 2 and curr_height < target_height * 2:
            return image.resize((target_width, target_height), Image.LANCZOS)
        
        # 큰 이미지는 단계적으로 리사이징
        while curr_width > target_width * 2 or curr_height > target_height * 2:
            curr_width = max(curr_width // 2, target_width)
            curr_height = max(curr_height // 2, target_height)
            image = image.resize((curr_width, curr_height), 
                               Image.BILINEAR if curr_width > target_width * 2 else Image.LANCZOS)
        
        # 최종 크기로 조정
        return image.resize((target_width, target_height), Image.LANCZOS)
    
    def _copy_transparency(self, source_img, target_img):
        """
        원본 이미지의 투명도를 대상 이미지에 적용합니다.
        
        Args:
            source_img: 원본 이미지 (투명도 포함, RGBA 모드)
            target_img: 대상 이미지 (RGB 또는 RGBA 모드)
            
        Returns:
            Image: 투명도가 적용된 대상 이미지
        """
        # 원본 이미지가 투명도를 가지고 있지 않으면 그대로 반환
        if source_img.mode != 'RGBA':
            return target_img
        
        # 원본 이미지의 알파 채널 추출
        alpha_channel = source_img.split()[3]  # 알파 채널 추출
        
        # 크기가 다른 경우 원본 이미지의 알파 채널을 대상 이미지 크기에 맞게 리사이징
        if alpha_channel.size != target_img.size:
            alpha_channel = alpha_channel.resize(target_img.size, Image.LANCZOS)
        
        # 대상 이미지의 RGB 채널 추출
        if target_img.mode == 'RGBA':
            # RGBA 모드인 경우 처음 3개 채널만 사용
            r, g, b, _ = target_img.split()
        else:
            # RGB 모드인 경우 먼저 RGBA로 변환
            r, g, b = target_img.split()
            
        # 새 이미지 생성 (RGB 채널은 대상 이미지에서, 알파 채널은 원본 이미지에서)
        return Image.merge('RGBA', (r, g, b, alpha_channel))
    
    def _load_image(self, path, target_mode=None):
        """이미지 로딩 최적화 메서드"""
        # 캐시 확인
        if path in self.image_cache:
            cached_img = self.image_cache[path][0]
            if target_mode and cached_img.mode != target_mode:
                return cached_img.convert(target_mode)
            return cached_img.copy()
            
        # 새로 로드
        try:
            img = Image.open(path)
            # 필요하면 모드 변환
            if target_mode and img.mode != target_mode:
                img = img.convert(target_mode)
            # 캐시에 추가
            import time
            self.image_cache[path] = (img.copy(), time.time())
            # 캐시 크기 제한
            if len(self.image_cache) > self.max_cache_size:
                # 가장 오래된 항목 제거 (간단한 구현)
                oldest = min(self.image_cache.items(), key=lambda x: x[1][1])
                del self.image_cache[oldest[0]]
            return img
        except Exception as e:
            print(f"이미지 로드 오류: {str(e)}")
            return None
    
    def _clean_temp_files(self):
        # 임시 파일 정리
        for file in os.listdir(self.image_resizer.temp_dir):
            if file.startswith("resized_") and file.endswith((".png", ".jpg", ".jpeg")):
                os.remove(os.path.join(self.image_resizer.temp_dir, file))
    
    def resize_image(self, target_width, target_height):
        """
        이미지 리사이징 및 텍스처 교체 처리 (최적화 버전)
        
        Args:
            target_width: 대상 너비
            target_height: 대상 높이
        """
        try:
            # 리사이징 프로세스 시작 - 이미지 준비 25%
            self.resize_progress.setValue(25)
            QApplication.processEvents()  # UI 업데이트
            
            # 캐시된 이미지 먼저 확인
            cache_key = f"{self.new_image_path}_{target_width}x{target_height}"
            if cache_key in self.resize_cache:
                path = self.resize_cache[cache_key]
                if os.path.exists(path):
                    self.resized_image_path = path
                    self.resize_progress.setValue(75)
                    QApplication.processEvents()
                    # 텍스처 교체로 바로 진행
                    goto_texture_replace = True
                else:
                    # 캐시에 있지만 파일이 없는 경우 제거
                    del self.resize_cache[cache_key]
                    goto_texture_replace = False
            else:
                goto_texture_replace = False
            
            # 캐시에 없거나 파일이 없는 경우 리사이징 수행
            if not goto_texture_replace:
                img = self._load_image(self.new_image_path)
                if not img:
                    raise Exception("이미지를 로드할 수 없습니다")
                
                # 리사이징 프로세스 50%
                self.resize_progress.setValue(50)
                QApplication.processEvents()  # UI 업데이트
                
                # 최적화된 리사이징 적용
                resized_img = self._optimize_resize(img, target_width, target_height)
                
                # 원본 이미지의 투명도 확인 및 적용
                if self.original_texture_image and self.original_texture_image.mode == 'RGBA':
                    apply_transparency = False
                    
                    if resized_img.mode != 'RGBA':
                        # 새 이미지에 투명도가 없는 경우
                        transparency_msg = "원본 이미지는 투명도가 있지만, 선택한 이미지는 투명도가 없습니다.\n"
                        transparency_msg += "원본 이미지의 투명도를 선택한 이미지에 적용하시겠습니까?"
                        apply_transparency = True
                    else:
                        # 두 이미지 모두 투명도가 있는 경우
                        transparency_msg = "선택한 이미지와 원본 이미지 모두 투명도가 있습니다.\n"
                        transparency_msg += "원본 이미지의 투명도 패턴으로 교체하시겠습니까?"
                        apply_transparency = True
                        
                    if apply_transparency:
                        # 투명도 적용 옵션 대화상자
                        reply = QMessageBox.question(
                            self, 
                            "투명도 적용", 
                            transparency_msg,
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )
                        
                        if reply == QMessageBox.Yes:
                            # 원본 이미지 크기를 대상에 맞게 조정
                            if self.original_texture_image.size != (target_width, target_height):
                                original_resized = self.original_texture_image.resize((target_width, target_height), Image.LANCZOS)
                            else:
                                original_resized = self.original_texture_image
                                
                            # 투명도 복사
                            resized_img = self._copy_transparency(original_resized, resized_img)
                
                # 임시 파일로 저장
                file_name = os.path.basename(self.new_image_path)
                base_name, ext = os.path.splitext(file_name)
                
                # 투명도가 있는 이미지는 PNG로 저장
                if resized_img.mode == 'RGBA' and ext.lower() in ['.jpg', '.jpeg']:
                    ext = '.png'
                
                self.resized_image_path = os.path.join(
                    self.image_resizer.temp_dir, 
                    f"{base_name}_resized_{target_width}x{target_height}{ext}"
                )
                
                # 최적화된 저장 옵션
                save_options = {}
                if ext.lower() in ['.jpg', '.jpeg']:
                    save_options['quality'] = 90
                    save_options['optimize'] = True
                elif ext.lower() == '.png':
                    save_options['optimize'] = True
                    save_options['compress_level'] = 9  # 최대 압축 레벨 설정
                
                resized_img.save(self.resized_image_path, **save_options)
                
                # 캐시에 저장
                self.resize_cache[cache_key] = self.resized_image_path
                
                # 리사이징 프로세스 75%
                self.resize_progress.setValue(75)
                QApplication.processEvents()  # UI 업데이트
            
            # 리사이징된 이미지로 텍스처 교체
            if self.resized_image_path and os.path.exists(self.resized_image_path):
                # 텍스처 교체
                self.texture_processor.replace_texture(
                    self.current_texture_obj, self.current_texture_data, self.resized_image_path
                )
                
                # 교체 완료 100%
                self.resize_progress.setValue(100)
                QApplication.processEvents()  # UI 업데이트
                
                # 완료 메시지는 상태바에만 표시
                main_window = self.window()  # 현재 위젯의 최상위 윈도우 가져오기
                if hasattr(main_window, 'statusBar'):
                    main_window.statusBar().showMessage("이미지 교체 완료", 3000)
                QTimer.singleShot(1000, lambda: self.resize_progress.setVisible(False))
                
                # 상태 업데이트
                self.restore_button.setEnabled(True)
                
                # 텍스처 교체 시그널 발생
                self.texture_replaced.emit()
            else:
                raise Exception("리사이징된 이미지를 저장할 수 없습니다.")
                
        except Exception as e:
            # 오류 발생 시 UI 숨김
            self.resize_progress.setVisible(False)
            
            # 오류 메시지 표시
            QMessageBox.critical(self, "오류", f"이미지 리사이징 중 오류가 발생했습니다:\n{str(e)}")
            print(f"이미지 리사이징 오류: {str(e)}")
    
    def restore_original(self):
        """
        가장 최근에 저장 시 생성된 백업 파일로 복원합니다.
        """
        # MainWindow 참조 및 현재 파일 경로 확인
        main_window = self.window()
        if not hasattr(main_window, 'current_file_path') or not main_window.current_file_path:
            QMessageBox.warning(self, "경고", "현재 로드된 파일 경로를 찾을 수 없습니다.")
            return
        current_file_path = main_window.current_file_path

        # 가장 최신의 저장 백업 파일 찾기 ('_save_' 포함)
        # print(f"[DEBUG] restore_original: 초기 백업 검색 대상 파일 경로: {current_file_path}") # 이전 로그 주석 처리
        latest_save_backup_path = self.backup_manager.find_latest_save_backup(current_file_path)
        
        if not latest_save_backup_path or not os.path.exists(latest_save_backup_path):
            # print(f"[DEBUG] restore_original: 초기 백업 파일을 찾지 못함 (find_initial_backup 결과: {initial_backup_path})") # 이전 로그 주석 처리
            print(f"[DEBUG] restore_original: 최신 저장 백업 파일을 찾지 못함 (find_latest_save_backup 결과: {latest_save_backup_path})")
            QMessageBox.warning(self, "경고", "가장 최근에 저장된 백업 파일을 찾을 수 없습니다. 원본을 복원할 수 없습니다.\n(파일 저장 시 백업을 생성했는지 확인하세요.)")
            return

        # 복원 확인 메시지
        reply = QMessageBox.question(
            self, 
            "파일 복원", 
            f"현재 파일을 가장 최근 저장 시 생성된 백업 파일({os.path.basename(latest_save_backup_path)})로 덮어쓰시겠습니까?\n\n"
            f"현재 편집 중인 내용은 사라집니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
            
        try:
            # 백업 파일을 현재 파일 경로로 복사 (덮어쓰기)
            import shutil
            shutil.copy2(latest_save_backup_path, current_file_path)
            
            QMessageBox.information(self, "성공", f"파일이 가장 최근 저장 백업({os.path.basename(latest_save_backup_path)})으로 복원되었습니다.\n파일을 다시 로드합니다.")
            
            # MainWindow의 파일 로딩 함수 호출하여 변경사항 반영
            # (주의: AssetsManager는 MainWindow가 관리하므로 직접 호출)
            main_window.start_loading(current_file_path)
            
            # 복원 후 버튼 비활성화
            self.restore_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 복원 중 오류 발생: {str(e)}")
            print(f"파일 복원 오류: {str(e)}")
