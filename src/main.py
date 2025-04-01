#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SPT Asset Editor
A tool for SPT Tarkov asset management

Author: Golani11
Copyright: © 2025 Golani11
Version: 1.0.3
License: MIT
Description: SPT Asset Editor is a tool for viewing and editing textures in SPT Tarkov game files.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
import platform

# _version.py에서 버전 정보 가져오기 시도
try:
    from _version import __version__, __app_name__, __description__, __author__, __copyright__
    # 버전 정보 헤더 업데이트
    program_header = f"""
{__app_name__}
A tool for SPT Tarkov asset management

Author: {__author__}
{__copyright__}
Version: {__version__}
License: MIT
Description: {__description__}
"""
    print(program_header)
except ImportError:
    print("Version information could not be loaded. This might be a development build.")

# 시작 시간 측정
start_time = time.time()

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 성능 최적화: Python의 메모리 관리 및 GC 설정 개선
import gc
gc.disable()  # 필요할 때만 GC 수행하도록 설정

# UnityPy C 타입트리 리더 비활성화
from UnityPy.helpers import TypeTreeHelper
TypeTreeHelper.read_typetree_boost = False

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer
from gui.main_window import MainWindow
from gui.styles import STYLE_SHEET  # 스타일시트 임포트
from utils.error_handler import create_error_handler, setup_temp_directory, load_settings
from utils.resource_helper import get_resource_path  # 리소스 헬퍼 임포트

# 로그 디렉토리 설정
def setup_logging():
    """로깅 설정 및 로그 파일 생성"""
    # 운영체제별 사용자 문서 폴더 경로 설정
    if platform.system() == "Windows":
        doc_dir = os.path.join(os.environ["USERPROFILE"], "Documents")
    elif platform.system() == "Darwin":  # macOS
        doc_dir = os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux 등
        doc_dir = os.path.expanduser("~")
    
    # 로그 디렉토리 생성
    log_dir = os.path.join(doc_dir, "TarkovAssetEditor", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일명 설정 (날짜_시간.log)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{timestamp}.log")
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 콘솔에도 로그 표시
        ]
    )
    
    logger = logging.getLogger("TarkovAssetEditor")
    logger.info(f"로그 파일 생성: {log_file}")
    logger.info(f"시스템 정보: {platform.platform()}, Python {platform.python_version()}")
    
    # 기존 stderr 출력을 로그 파일로 리다이렉트
    sys.stderr = LogRedirector(logger)
    
    return logger, log_file

class LogRedirector:
    """stderr 출력을 로깅 시스템으로 리다이렉트하는 클래스"""
    def __init__(self, logger):
        self.logger = logger
        
    def write(self, message):
        if message and not message.isspace():
            self.logger.error(message)
    
    def flush(self):
        pass

def excepthook(exc_type, exc_value, exc_traceback):
    """예외 처리 핸들러 - 프로그램 충돌 시 상세 정보 로깅"""
    logger = logging.getLogger("TarkovAssetEditor")
    logger.critical("예외 발생(Uncaught Exception):", exc_info=(exc_type, exc_value, exc_traceback))
    traceback_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"상세 정보:\n{traceback_details}")
    
    # 기본 예외 처리기도 호출
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def main():
    """
    애플리케이션 메인 진입점
    """
    # 로깅 설정
    logger, log_file = setup_logging()
    logger.info("애플리케이션 시작")
    
    # 전역 예외 핸들러 설정
    sys.excepthook = excepthook
    
    # 에러 핸들러 설정 (기존 코드)
    error_handler = create_error_handler()
    
    # 임시 디렉토리 설정
    temp_dir = setup_temp_directory()
    logger.info(f"임시 디렉토리: {temp_dir}")
    
    # 설정 로드
    settings = load_settings()
    logger.info("설정 로드 완료")
    
    try:
        # QApplication 생성
        app = QApplication(sys.argv)
        
        # 애플리케이션 아이콘 설정
        # icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icon.ico")
        icon_path = get_resource_path("resources/icon.ico") # 리소스 헬퍼 사용
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"애플리케이션 아이콘 적용: {icon_path}")
        else:
            logger.warning(f"아이콘 파일을 찾을 수 없습니다: {icon_path}")
        
        # 스타일시트 적용
        app.setStyleSheet(STYLE_SHEET)
        logger.info("스타일시트 적용 완료")
        
        # 메인 윈도우 생성
        window = MainWindow()
        logger.info("메인 윈도우 생성 완료")
        
        # 로딩 시간 출력
        loading_time = time.time() - start_time
        logger.info(f"애플리케이션 로딩 시간: {loading_time:.2f}초")
        
        window.show()
        logger.info("메인 윈도우 표시")
        
        # GC 재활성화
        gc.enable()
        
        # 애플리케이션 실행
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"애플리케이션 초기화 중 오류 발생: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
