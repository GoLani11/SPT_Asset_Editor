import os
import sys

def get_resource_path(relative_path):
    """ 개발 환경과 PyInstaller 환경 모두에서 리소스 절대 경로를 반환합니다. """
    try:
        # PyInstaller는 임시 폴더를 생성하고 _MEIPASS에 경로를 저장합니다.
        # 이 경로는 빌드 시 --add-data로 추가된 파일들이 위치하는 곳입니다.
        base_path = sys._MEIPASS
    except AttributeError:
        # 개발 환경: __file__을 기준으로 프로젝트 루트를 찾습니다.
        # 이 파일(resource_helper.py)은 src/utils/ 안에 있으므로,
        # 두 단계 위로 올라가면 프로젝트 루트입니다.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # resources 폴더 내의 상대 경로와 base_path를 결합합니다.
    # 예: base_path/resources/icon.ico
    resource_full_path = os.path.join(base_path, relative_path)
    
    # print(f"DEBUG: get_resource_path called with '{relative_path}'")
    # print(f"DEBUG: base_path = '{base_path}'")
    # print(f"DEBUG: Returning resource path = '{resource_full_path}'")
    
    return resource_full_path 