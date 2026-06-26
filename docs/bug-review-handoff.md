# SPT Asset Editor — 버그 리뷰 / 수정 계획 (인계 문서)

> 새 세션 시작점. 코드 분석과 1~5번 수정이 적용된 상태. 6~8번은 새 기능 범위라 보류.
> 배경: 이 툴은 SPT 아이템 텍스처 한글화 작업(GoLani.ItemTextureKoreanChange)의 추출/리팩 백본으로 재사용 예정.
> 관련 환경: 게임 `D:\SPT`, UnityPy+texture2ddecoder+Pillow+PyQt5.

## 핵심 진단

증상 "교체하면 밝아짐 / 깨짐 / 보라색 / 적용 안됨"의 뿌리는 대부분 **하나** — 저장 시 원본 텍스처 포맷을 안 지킴.

`replace_texture`([src/core/texture_processor.py:446](src/core/texture_processor.py))에서 예전 코드는:
- `original_format = data.m_TextureFormat`로 원본 포맷을 기억만 하고
- `data.image = new_image` 로 덮어씀
- UnityPy 버전에 따라 image setter 동작이 달라 포맷 손실/밉맵 불일치 위험이 있었음
- DXT5 폴백도 `m_TextureFormat=12` 후 `data.image=`를 다시 써서 같은 위험이 있었음

현재 수정: `data.set_image(new_image, target_format=original_format, mipmap_count=mip_count)`로 원본 포맷과 밉맵을 명시. UnityPy 1.25.0 소스 확인 결과 `set_image()`가 `m_TextureFormat`, `m_MipCount`, `m_CompleteImageSize`, `m_StreamData`를 함께 갱신함.

## 우선순위 수정 목록

| 순위 | 항목 | 위치 | 증상/근거(사용자 댓글) |
|------|------|------|----------------------|
| 1 | **원본 포맷 유지** `data.image=` → `set_image(target_format=원본)` | texture_processor.py:481, 499-500 | 밝아짐, 보라색, BC7에러(thefatraccoon) |
| 2 | **밉맵(m_MipCount) 갱신** — 포맷 바뀌며 밉맵 불일치 | texture_processor.py replace_texture | "적용 안됨", "게임엔 옛 알파"(_ANUBIS_) |
| 3 | **알파 처리 + 대화상자 문구 수정** | image_editor.py:452(_copy_transparency), 558 | 최다 불만(_ANUBIS_ 좋아요1·답글6, Spe4r). "Yes"가 내 알파 버리고 원본 알파 씀 — 문구 헷갈림, 기본값 잘못. PNG가 알파 합쳐버림(DarkonX 우회: TGA+No) |
| 4 | **교체 실패 시 에러 표시** (조용한 실패) | image_editor.py:602 (리턴값 무시) | "적용된 줄 알았는데 안 됨" |
| 5 | **UnityPy 버전 고정** | requirements.txt (`UnityPy>=1.9.0`) | BC7에러 재발 위험(버전별 API 상이) |
| 6 | **아틀라스 부분 교체** — 전체 리사이즈 말고 sub-rect 합성 | texture_processor.py:474-476 | 포스터팩 크롭 깨짐(LiquidGold·sublick03·Rabid Gerbil, 미해결) |
| 7 | **텍스처 검색 기능** — 이름/아이템으로 번들 찾기 | 신규 | 5286개 번들 수동 탐색 고통(callmechanka, thefatraccoon) |
| 8 | 포스터 회전 옵션 / 큰 .assets 저장 안정화 | texture_processor.py:256, assets_manager.py:257 | johnpelfrey(회전), DarkonX(4.0.13 sharedassets) |

**1번이 댓글 절반(밝아짐·보라색·BC7·밉맵)을 동시에 해결.** 한글화 작업만이면 1·2·4면 충분, 일반 배포 개선은 3·6·7까지.

## 먼저 확인할 것 (수정 전)
- 설치된 UnityPy 실제 버전 → `set_image` 시그니처/존재 여부 (버전별 API 다름). `python -c "import UnityPy; print(UnityPy.__version__)"`
- BC7/DXT 인코더 동작 여부(재압축 가능한지) — POC로 마요네즈 추출→그대로 리팩→게임에서 원본과 동일하게 보이는지 검증.

## 참고
- 마지막 커밋: `9dd9217 Update 1.1.1 (2025-04-21)`. 방치 상태, 버그 다수.
- 한글화 모드 쪽 설계 문서: GoLani.ItemTextureKoreanChange/docs/automation-design.md
