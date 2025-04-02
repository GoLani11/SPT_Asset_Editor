import os
import json
import sys
import locale
import logging

logger = logging.getLogger(__name__)

# 지원하는 언어 코드
SUPPORTED_LANGUAGES = ["ko", "en"]

# 기본 언어 설정
DEFAULT_LANGUAGE = "ko"

# 번역 데이터 저장 딕셔너리
translations = {}
current_language = DEFAULT_LANGUAGE

# 로케일 디렉토리 경로
LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale")

# 설정 파일 경로
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "language_settings.json")

def get_system_language():
    """시스템 기본 언어를 감지합니다."""
    try:
        # locale 모듈 사용
        lang_code, _ = locale.getdefaultlocale()
        if lang_code:
            lang_code = lang_code.split('_')[0].lower()
            if lang_code in SUPPORTED_LANGUAGES:
                logger.info(f"시스템 언어 감지 성공: {lang_code}")
                return lang_code
    except Exception as e:
        logger.warning(f"시스템 언어 감지 실패: {str(e)}")
    
    # 감지 실패 시 기본 언어 반환
    logger.info(f"시스템 언어 감지 실패, 기본 언어 사용: {DEFAULT_LANGUAGE}")
    return DEFAULT_LANGUAGE

def load_language_settings():
    """설정 파일에서 언어 설정을 로드합니다."""
    global current_language
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                language = settings.get('language')
                if language in SUPPORTED_LANGUAGES:
                    logger.info(f"설정 파일에서 언어 로드: {language}")
                    current_language = language
                    return
                else:
                    logger.warning(f"설정 파일의 언어 코드가 유효하지 않음: {language}")
        else:
            logger.info("언어 설정 파일 없음, 시스템 언어 사용 시도")
            
    except Exception as e:
        logger.error(f"언어 설정 로드 오류: {str(e)}, 시스템 언어 사용 시도")
        
    # 설정 로드 실패 시 시스템 언어 사용
    current_language = get_system_language()
    # 기본 언어 설정 저장
    save_language_settings(current_language)

def save_language_settings(language_code: str):
    """현재 언어 설정을 파일에 저장합니다."""
    if language_code not in SUPPORTED_LANGUAGES:
        logger.error(f"지원하지 않는 언어 코드는 저장할 수 없음: {language_code}")
        return
        
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        settings = {'language': language_code}
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
        logger.info(f"언어 설정 저장 완료: {language_code}")
    except Exception as e:
        logger.error(f"언어 설정 저장 오류: {str(e)}")

def load_translations(language_code: str):
    """지정된 언어의 번역 파일을 로드합니다."""
    global translations, current_language
    
    if language_code not in SUPPORTED_LANGUAGES:
        logger.warning(f"지원하지 않는 언어 코드: {language_code}. 기본 언어({DEFAULT_LANGUAGE}) 사용.")
        language_code = DEFAULT_LANGUAGE
        
    file_path = os.path.join(LOCALE_DIR, f"{language_code}.json")
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            current_language = language_code
            logger.info(f"{language_code} 언어 번역 로드 완료")
        else:
            logger.error(f"번역 파일을 찾을 수 없음: {file_path}")
            # 기본 언어 시도
            if language_code != DEFAULT_LANGUAGE:
                 logger.info(f"기본 언어({DEFAULT_LANGUAGE}) 로드 시도")
                 load_translations(DEFAULT_LANGUAGE)
            else:
                 translations = {}
                 current_language = language_code
    except json.JSONDecodeError as e:
        logger.error(f"번역 파일 JSON 파싱 오류 ({file_path}): {str(e)}")
        translations = {}
        current_language = language_code # 오류 발생해도 현재 언어는 유지
    except Exception as e:
        logger.error(f"번역 파일 로드 오류 ({file_path}): {str(e)}")
        translations = {}
        current_language = language_code

def set_language(language_code: str):
    """애플리케이션 언어를 설정하고 설정을 저장합니다."""
    if language_code == current_language:
        logger.info(f"이미 현재 언어({language_code})가 설정되어 있습니다.")
        return
        
    if language_code not in SUPPORTED_LANGUAGES:
        logger.error(f"지원하지 않는 언어 코드로 변경할 수 없음: {language_code}")
        return
        
    load_translations(language_code)
    save_language_settings(language_code)
    logger.info(f"애플리케이션 언어 변경됨: {language_code}")
    # TODO: UI 업데이트 시그널 또는 콜백 호출 추가 필요

def get_string(key: str, **kwargs) -> str:
    """번역된 문자열을 반환합니다. 키가 없으면 키 자체를 반환합니다."""
    # 번역 데이터가 로드되지 않은 경우 기본 로드 시도
    if not translations:
        logger.warning("번역 데이터가 로드되지 않았습니다. 현재 언어로 로드를 시도합니다.")
        load_translations(current_language)
        # 그래도 없으면 반환할 수 없음
        if not translations:
            logger.error(f"번역 데이터 로드 실패, 키 반환: {key}")
            return key
            
    # 번역된 문자열 가져오기
    translated = translations.get(key, key)
    
    # 키워드 인수로 포맷팅
    try:
        if kwargs:
            translated = translated.format(**kwargs)
    except KeyError as e:
        logger.warning(f"번역 문자열 포맷팅 오류: 키 '{key}'에 필요한 인수가 없음 - {e}")
    except Exception as e:
         logger.warning(f"번역 문자열 포맷팅 중 예상치 못한 오류: 키='{key}', 오류='{str(e)}'")
         
    # 키가 없는 경우 경고 로그
    if translated == key and key not in translations:
        logger.warning(f"번역 키를 찾을 수 없음: '{key}' in language '{current_language}'")
        
    return translated

def get_current_language() -> str:
    """현재 설정된 언어 코드를 반환합니다."""
    return current_language

# 모듈 로드 시 언어 설정 및 번역 로드
load_language_settings()
load_translations(current_language) 