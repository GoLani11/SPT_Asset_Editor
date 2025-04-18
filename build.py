import os
import platform
import subprocess
import shutil
import re  # 정규표현식 모듈 추가
import UnityPy

# --- 설정 ---
APP_NAME = "SPTAssetEditor"
APP_VERSION = "1.0.4"  # <<--- 버전 정보 정의 (이곳만 수정하면 됩니다)
ENTRY_POINT = os.path.join("src", "main.py")
ICON_FILE = os.path.join("resources", "icon.ico") # 아이콘 파일 경로 (실제 파일 확인 필요)
DIST_PATH = "dist" # 빌드 결과물이 저장될 폴더
BUILD_PATH = "build" # 빌드 과정 임시 폴더
VERSION_INFO_FILE = "version_info.txt" # 버전 정보 파일 이름

# 포함할 데이터 파일 및 폴더 (pyinstaller 형식: '원본경로;대상경로')
# 대상경로는 실행 파일 기준 상대 경로
# src/config/settings.json 파일과 resources 폴더 전체를 포함합니다.
DATA_FILES = [
    (os.path.join("src", "config", "settings.json"), "config"),
    ("resources", "resources"), # resources 폴더 전체를 실행 파일 옆 resources 폴더로 복사
    (os.path.join("src", "locale"), "locale") # locale 폴더 추가
]

# --- 버전 정보 파일 업데이트 함수 ---
def update_version_info(version_str, filename=VERSION_INFO_FILE):
    """version_info.txt 파일을 주어진 버전 문자열로 업데이트합니다."""
    try:
        # 버전 문자열 파싱 (major.minor.patch)
        parts = list(map(int, version_str.split('.')))
        while len(parts) < 3:
            parts.append(0)
        major, minor, patch = parts[:3]
        build = 0 # 빌드 번호는 0으로 고정하거나 필요시 별도 관리
        
        version_tuple = f"({major}, {minor}, {patch}, {build})"
        version_string_file = f"{major}.{minor}.{patch}.{build}"
        version_string_product = f"{major}.{minor}.{patch}"

        print(f"버전 정보 업데이트 중: {filename} -> {version_string_product}")

        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # 정규표현식을 사용하여 버전 정보 수정
        content = re.sub(r"filevers=\(\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\)", f"filevers={version_tuple}", content)
        content = re.sub(r"prodvers=\(\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\)", f"prodvers={version_tuple}", content)
        content = re.sub(r"(StringStruct\(u'FileVersion',\s*u')([^']*)('\))", rf"\g<1>{version_string_file}\g<3>", content)
        content = re.sub(r"(StringStruct\(u'ProductVersion',\s*u')([^']*)('\))", rf"\g<1>{version_string_product}\g<3>", content)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("버전 정보 업데이트 완료.")
        return True

    except FileNotFoundError:
        print(f"[오류] 버전 정보 파일 '{filename}'을 찾을 수 없습니다.")
        return False
    except Exception as e:
        print(f"[오류] 버전 정보 파일 업데이트 중 오류 발생: {e}")
        return False

# --- _version.py 파일 생성 함수 ---
def create_version_py(version_str):
    """src 폴더에 __version__ 변수가 포함된 _version.py 파일을 생성합니다."""
    # 현재 날짜 가져오기
    from datetime import datetime
    current_year = datetime.now().year
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    version_py_content = f'''# Automatically generated by build.py on {current_date}
# This file contains version information for SPT Asset Editor

__version__ = "{version_str}"
__app_name__ = "{APP_NAME}"
__description__ = "SPT Asset Editor is a tool for viewing and editing textures in Tarkov game files."
__author__ = "Golani11"
__copyright__ = "© {current_year} Golani11. All rights reserved."
__license__ = "MIT"
__build_date__ = "{current_date}"
__website__ = "https://github.com/Golani11/SPT_Asset_Editor"
'''
    version_py_path = os.path.join("src", "_version.py")
    try:
        with open(version_py_path, "w", encoding="utf-8") as f:
            f.write(version_py_content)
        print(f"버전 파일 생성 완료: {version_py_path}")
        return True
    except Exception as e:
        print(f"[오류] _version.py 파일 생성 중 오류 발생: {e}")
        return False

# --- 빌드 시작 전 버전 업데이트 수행 ---
print("-" * 30)
if not create_version_py(APP_VERSION):
    print("[오류] _version.py 생성 실패. 빌드를 중단합니다.")
    exit(1)
    
if not update_version_info(APP_VERSION):
    print("[오류] 버전 정보 파일 업데이트 실패. 빌드를 중단합니다.")
    exit(1) # 업데이트 실패 시 빌드 중단
print("-" * 30)

# UnityPy 리소스 경로 찾기 및 데이터 추가 옵션 생성
try:
    unitypy_path = os.path.dirname(UnityPy.__file__)
    unitypy_resources_src = os.path.join(unitypy_path, "resources")
    unitypy_resources_dest = os.path.join("UnityPy", "resources") # 패키지 내 구조 유지
    if os.path.isdir(unitypy_resources_src):
        unitypy_add_data = f"{os.path.abspath(unitypy_resources_src)}{os.pathsep}{unitypy_resources_dest}"
        print(f"UnityPy 리소스 포함: {unitypy_add_data}")
    else:
        unitypy_add_data = None
        print("[경고] UnityPy 리소스 폴더를 찾을 수 없습니다. 빌드에 실패할 수 있습니다.")
except ImportError:
    unitypy_add_data = None
    print("[경고] UnityPy를 import할 수 없습니다. 리소스 포함을 건너뜁니다.")
except Exception as e: # 예상치 못한 오류 처리 추가
    unitypy_add_data = None
    print(f"[경고] UnityPy 경로 확인 중 오류 발생: {e}")

# --- Find and add UnityPy binary decoders ---
unitypy_binaries = []
# 포함할 가능성이 있는 디코더 파일 이름 목록 (UnityPy 버전에 따라 다를 수 있음)
potential_decoders = [
    "Texture2DDecoder.pyd", # 가장 일반적인 디코더 이름 (Windows)
    "astc_decomp.dll",
    "etcpack.dll",
    "pvrtc_decoder.dll",
    # 필요하다면 다른 OS 또는 다른 디코더 파일 이름 추가
]

# archspec 및 astc_encoder 패키지 찾기
archspec_data = None
astc_encoder_data = None
try:
    import archspec
    import astc_encoder
    
    # archspec 경로 찾기
    archspec_path = os.path.dirname(archspec.__file__)
    print(f"archspec 설치 경로: {archspec_path}")
    
    # archspec JSON 파일 찾기
    archspec_json_src = os.path.join(archspec_path, "json")
    if os.path.isdir(archspec_json_src):
        archspec_data = f"{os.path.abspath(archspec_json_src)}{os.pathsep}archspec/json"
        print(f"archspec JSON 데이터 포함: {archspec_data}")
    else:
        print(f"[경고] archspec JSON 디렉토리를 찾을 수 없습니다: {archspec_json_src}")
    
    # astc_encoder 경로 찾기
    astc_encoder_path = os.path.dirname(astc_encoder.__file__)
    print(f"astc_encoder 설치 경로: {astc_encoder_path}")
    
    # astc_encoder 데이터 파일 찾기 (있을 경우)
    for data_dir in ["data", "resources"]:
        astc_encoder_data_src = os.path.join(astc_encoder_path, data_dir)
        if os.path.isdir(astc_encoder_data_src):
            astc_encoder_data = f"{os.path.abspath(astc_encoder_data_src)}{os.pathsep}astc_encoder/{data_dir}"
            print(f"astc_encoder 데이터 포함: {astc_encoder_data}")
            break
except ImportError as e:
    print(f"[경고] 패키지 import 오류: {e}")
except Exception as e:
    print(f"[경고] 패키지 경로 확인 중 오류 발생: {e}")

try:
    unitypy_install_path = os.path.dirname(UnityPy.__file__)
    print(f"UnityPy 설치 경로: {unitypy_install_path}")
    for decoder_file in potential_decoders:
        src_path = os.path.join(unitypy_install_path, decoder_file)
        if os.path.exists(src_path):
            # 대상 경로 '.'는 실행 파일과 같은 폴더를 의미합니다.
            unitypy_binaries.append(f"{os.path.abspath(src_path)}{os.pathsep}.")
            print(f"UnityPy 바이너리 포함: {decoder_file} -> .")
        # else:
            # print(f"디코더 파일 없음: {src_path}") # 디버깅 시 주석 해제

except ImportError:
    print("[경고] UnityPy를 import할 수 없어 바이너리 포함을 건너뜁니다.")
except Exception as e:
    print(f"[경고] UnityPy 바이너리 경로 확인 중 오류 발생: {e}")

# --- PyInstaller 명령 구성 ---
pyinstaller_cmd = [
    "pyinstaller",
    "--name", APP_NAME,
    "--onefile", # 모든 파일을 하나의 실행 파일로 패키징
    "--console", # 콘솔 창 표시 (로그 디버깅용)
    "--clean", # 빌드 전 이전 빌드 파일 정리
    "--noconfirm", # 기존 빌드 폴더를 자동으로 덮어씁니다
    "--noupx", # UPX 압축을 사용하지 않음 (탐지율 감소에 도움)
    "--disable-windowed-traceback", # 윈도우 모드 트레이스백 비활성화
    # "--win-private-assemblies", # 제거됨 - PyInstaller v6.0에서 지원 중단
    # "--win-no-prefer-redirects", # 제거됨 - PyInstaller v6.0에서 지원 중단
    # 필요한 히든 임포트 추가
    "--hidden-import", "UnityPy.resources",
    "--hidden-import", "UnityPy.helpers",
    "--hidden-import", "UnityPy.streams",
    "--hidden-import", "UnityPy.files",
    "--hidden-import", "UnityPy.enums",
    "--hidden-import", "UnityPy.export",
    "--hidden-import", "UnityPy.export.Texture2DConverter",
    "--hidden-import", "astc_encoder",
    "--hidden-import", "astc_encoder.encoder",
    "--hidden-import", "archspec",
    "--hidden-import", "archspec.cpu",
    "--hidden-import", "archspec.cpu.detect",
    "--hidden-import", "archspec.cpu.microarchitecture",
    f"--version-file={os.path.abspath(VERSION_INFO_FILE)}", # 업데이트된 버전 정보 파일 사용
    "--distpath", DIST_PATH, # 빌드 결과물 경로 지정
    "--workpath", BUILD_PATH, # 빌드 작업 경로 지정
]

# --- 생성된 UnityPy 바이너리 추가 옵션을 pyinstaller_cmd 리스트에 추가 ---
for binary_data in unitypy_binaries:
    pyinstaller_cmd.extend(["--add-binary", binary_data])

# 생성된 UnityPy 리소스 데이터 추가 옵션을 pyinstaller_cmd 리스트에 추가
if unitypy_add_data:
    pyinstaller_cmd.extend(["--add-data", unitypy_add_data])

# archspec 데이터 추가
if archspec_data:
    pyinstaller_cmd.extend(["--add-data", archspec_data])

# astc_encoder 데이터 추가 (있을 경우)
if astc_encoder_data:
    pyinstaller_cmd.extend(["--add-data", astc_encoder_data])

# 데이터 파일 추가
for src, dest in DATA_FILES:
    # 데이터 파일 경로가 실제로 존재하는지 확인
    if os.path.exists(src):
        pyinstaller_cmd.extend(["--add-data", f"{os.path.abspath(src)}{os.pathsep}{dest}"])
    else:
        print(f"[경고] 데이터 경로를 찾을 수 없습니다: '{src}'. 빌드에서 제외됩니다.")

# 아이콘 파일 존재 여부 확인 및 추가
if os.path.exists(ICON_FILE):
    pyinstaller_cmd.extend(["--icon", ICON_FILE])
else:
    print(f"[경고] 아이콘 파일 '{ICON_FILE}'을 찾을 수 없습니다. 기본 아이콘이 사용됩니다.")


# 엔트리 포인트 추가
pyinstaller_cmd.append(ENTRY_POINT)

# --- 빌드 실행 ---
print("빌드를 시작합니다...")
print(f"PyInstaller 명령: {' '.join(pyinstaller_cmd)}")

try:
    # 빌드 디렉토리 생성 (존재하지 않을 경우)
    os.makedirs(DIST_PATH, exist_ok=True)

    # PyInstaller 실행
    subprocess.check_call(pyinstaller_cmd)

    print("-" * 30)
    print(f"빌드가 성공적으로 완료되었습니다!")
    exe_path = os.path.abspath(os.path.join(DIST_PATH, f"{APP_NAME}.exe"))
    print(f"실행 파일은 '{exe_path}' 에서 확인할 수 있습니다.")
    print("-" * 30)

except FileNotFoundError:
    print("\n[오류] pyinstaller를 찾을 수 없습니다.")
    print("빌드를 진행하기 전에 pyinstaller를 설치해주세요.")
    print("설치 명령어: pip install pyinstaller")
    print("또는 'pip install -r requirements.txt' 명령어로 모든 의존성을 설치하세요.")
except subprocess.CalledProcessError as e:
    print(f"\n[오류] 빌드 중 오류가 발생했습니다: {e}")
    print("PyInstaller 로그를 확인하여 문제를 해결하세요.")
    print("필요하다면 build.py 스크립트의 '--log-level=DEBUG' 주석을 해제하고 다시 시도해보세요.")
except Exception as e:
    print(f"\n[오류] 예상치 못한 오류가 발생했습니다: {e}")

finally:
    # 임시 빌드 폴더 및 .spec 파일 정리
    if os.path.exists(BUILD_PATH):
        print(f"임시 빌드 폴더 '{BUILD_PATH}'를 정리합니다.")
        try:
            shutil.rmtree(BUILD_PATH)
        except OSError as e:
            print(f"[경고] 임시 빌드 폴더 정리에 실패했습니다: {e}")
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        print(f"SPEC 파일 '{spec_file}'을 정리합니다.")
        try:
            os.remove(spec_file)
        except OSError as e:
            print(f"[경고] SPEC 파일 정리에 실패했습니다: {e}")
