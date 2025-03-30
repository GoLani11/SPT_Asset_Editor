# 타르코프 에셋 에디터

SPT 타르코프(Escape From Tarkov) 게임의 `.assets`, `.bundle` 파일에서 텍스처(Texture2D) 이미지를 추출, 미리보기, 수정 및 복원할 수 있는 도구입니다.

## 기능

- Unity `.assets` 및 `.bundle` 파일 로드 및 분석
- 파일 내 Texture2D 텍스처 자동 감지 및 목록화
- 텍스처 미리보기 및 속성 확인
- 커스텀 이미지로 텍스처 교체
- 원본 해상도에 맞게 자동 리사이징
- 투명도(알파 채널) 자동 처리
- 원본 상태로 텍스처 복원
- 자동 백업 기능으로 안전한 편집

## 설치 및 실행 방법

### 실행 파일 (권장)

1. [릴리스 페이지](https://github.com/yourusername/tarkov-asset-editor/releases)에서 최신 버전의 실행 파일을 다운로드합니다.
2. 다운로드한 파일을 압축 해제합니다.
3. `SPTAssetEditor.exe` 파일을 실행합니다.

### 소스 코드에서 실행 (개발자용)

개발에 참여하거나 소스 코드를 직접 실행하려면 다음 요구 사항이 필요합니다:

#### 요구 사항
- Python 3.7 이상
- PyQt5
- Pillow (PIL Fork)
- UnityPy
- texture2ddecoder (특수 텍스처 포맷 지원)

#### 설치 단계
1. 이 저장소를 클론합니다:
   ```
   git clone https://github.com/yourusername/tarkov-asset-editor.git
   cd tarkov-asset-editor
   ```

2. 필요한 패키지를 설치합니다:
   ```
   pip install -r requirements.txt
   ```

3. 프로그램 실행:
   ```
   python src/main.py
   ```

## 사용 방법

### 에셋 파일 열기

1. "파일 → 열기" 메뉴 또는 Ctrl+O 단축키를 사용하여 `.assets` 또는 `.bundle` 파일을 엽니다.
2. 파일을 처음 열 때 백업 폴더를 선택합니다. 백업은 자동으로 생성됩니다.
3. 왼쪽 사이드바에 파일 내 발견된 모든 텍스처가 표시됩니다.

### 텍스처 수정

1. 목록에서 텍스처를 선택하여 상단 패널에서 미리봅니다.
2. 하단 패널에서 "이미지 선택..." 버튼을 클릭하여 교체할 이미지를 선택합니다.
3. 선택한 이미지가 원본 텍스처의 해상도에 맞게 자동으로 리사이징됩니다.
4. "이미지 교체" 버튼을 클릭하여 텍스처를 교체합니다.
5. 수정된 에셋 파일을 저장하려면 "파일 → 저장" 메뉴 또는 Ctrl+S 단축키를 사용합니다.

### 텍스처 복원

1. "원본 복원" 버튼을 클릭하여 수정된 텍스처를 원래 상태로 복원할 수 있습니다.
2. 복원은 가장 최근에 저장된 백업 파일에서 이루어집니다.

## 주의사항

- 본 도구는 SPT(Single Player Tarkov) 버전에서 사용하기 위해 설계되었습니다.
- 라이브 서버 게임 파일 수정은 권장하지 않으며, BattlEye 안티치트에 의해 계정이 제재될 수 있습니다.
- 항상 작업 전에 원본 파일을 백업하세요.
- `.assets` 파일을 수정할 때 관련된 `.resS` 파일도 함께 있어야 합니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 크레딧

- Unity 에셋 파싱을 위한 [UnityPy](https://github.com/K0lb3/UnityPy)
- 텍스처 디코딩을 위한 [texture2ddecoder](https://github.com/K0lb3/texture2ddecoder)
- 이미지 처리를 위한 [Pillow (PIL Fork)](https://python-pillow.org/)
- UI 프레임워크 [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) 

## 참고 프로그램
- AssetStudio (https://github.com/Perfare/AssetStudio)
- UABEA (https://github.com/nesrak1/UABEA)