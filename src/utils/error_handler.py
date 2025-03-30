import os
import sys
import shutil
from pathlib import Path

# 에러 처리 및 예외 상황 관리 추가
def create_error_handler():
    """
    애플리케이션 전역 에러 핸들러 생성
    """
    error_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(error_log_path, exist_ok=True)
    
    error_log_file = os.path.join(error_log_path, "error.log")
    
    # 로그 파일 핸들러 설정
    import logging
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=error_log_file,
        filemode='a'
    )
    
    # 전역 예외 처리기 설정
    def global_exception_handler(exctype, value, traceback):
        logging.error("Uncaught exception", exc_info=(exctype, value, traceback))
        sys.__excepthook__(exctype, value, traceback)
    
    sys.excepthook = global_exception_handler
    
    return logging.getLogger('tarkov_asset_editor')

# 임시 디렉토리 관리
def setup_temp_directory():
    """
    임시 디렉토리 설정 및 정리
    """
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 이전 임시 파일 정리
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        try:
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"임시 파일 정리 중 오류: {e}")
    
    return temp_dir

# 애플리케이션 설정 관리
def load_settings():
    """
    애플리케이션 설정 로드
    """
    import json
    
    settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    os.makedirs(settings_dir, exist_ok=True)
    
    settings_file = os.path.join(settings_dir, "settings.json")
    
    # 기본 설정
    default_settings = {
        "recent_files": [],
        "backup_count": 5,
        "theme": "system",
        "language": "ko_KR"
    }
    
    # 설정 파일이 없으면 기본 설정으로 생성
    if not os.path.exists(settings_file):
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=4)
        return default_settings
    
    # 설정 파일 로드
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        print(f"설정 로드 중 오류: {e}")
        return default_settings

def save_settings(settings):
    """
    애플리케이션 설정 저장
    """
    import json
    
    settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    settings_file = os.path.join(settings_dir, "settings.json")
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"설정 저장 중 오류: {e}")
        return False

# 애플리케이션 경로 관리
def get_application_paths():
    """
    애플리케이션 관련 경로 반환
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    paths = {
        "base": base_dir,
        "temp": os.path.join(base_dir, "temp"),
        "logs": os.path.join(base_dir, "logs"),
        "config": os.path.join(base_dir, "config"),
        "backups": os.path.join(base_dir, "backups")
    }
    
    # 필요한 디렉토리 생성
    for path in paths.values():
        os.makedirs(path, exist_ok=True)
    
    return paths
