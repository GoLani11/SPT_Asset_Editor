import os
from PIL import Image
from typing import Optional, Tuple, Dict, Any
import logging
import numpy as np
import io
import sys
import time

logger = logging.getLogger(__name__)

# texture2ddecoder 라이브러리를 안전하게 가져오기
texture2ddecoder_available = False
try:
    from texture2ddecoder import decode_bc1, decode_bc3, decode_bc4, decode_bc5, decode_bc6, decode_bc7, decode_etc1, decode_etc2, decode_astc
    texture2ddecoder_available = True
    logger.info("texture2ddecoder 라이브러리 로드 성공")
except ImportError:
    logger.warning("texture2ddecoder 라이브러리를 로드할 수 없습니다. 기본 디코딩만 사용됩니다.")
except Exception as e:
    logger.warning(f"texture2ddecoder 라이브러리 로드 중 오류 발생: {str(e)}")

class TextureProcessor:
    """
    Texture2D 이미지를 추출, 수정 및 리사이징하는 클래스
    """
    
    def __init__(self):
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 이미지 캐시 추가 - 메모리 사용량과 성능의 균형을 위해 크기 제한
        self.image_cache = {}  # 키: texture_data 객체 ID, 값: (이미지, 타임스탬프)
        self.max_cache_size = 30  # 최대 캐시 크기
    
    def _clear_old_cache_entries(self):
        """
        캐시가 너무 커지면 가장 오래된 항목을 제거합니다.
        """
        if len(self.image_cache) <= self.max_cache_size:
            return
            
        # 타임스탬프 기준으로 정렬하여 가장 오래된 항목 제거
        items = sorted(self.image_cache.items(), key=lambda x: x[1][1])
        
        # 삭제할 항목 수 계산
        to_remove = len(self.image_cache) - self.max_cache_size
        for i in range(to_remove):
            if i < len(items):
                del self.image_cache[items[i][0]]
    
    def _get_texture_raw_data(self, texture_data: Any) -> Optional[bytes]:
        """
        Texture2D 객체에서 원시 이미지 데이터를 추출합니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            
        Returns:
            Optional[bytes]: 원시 이미지 데이터 또는 None
        """
        texture_name = getattr(texture_data, 'm_Name', 'Unknown')
        
        try:
            # UnityPy의 내부 속성 확인
            for attr_name in ['image_data', 'image_data_block', 'data', 'image_data_file', 'm_Data']:
                if hasattr(texture_data, attr_name):
                    logger.info(f"텍스처 '{texture_name}'에서 '{attr_name}' 속성 발견, 사용 시도")
                    try:
                        data = getattr(texture_data, attr_name)
                        if data:
                            return data
                    except Exception as e:
                        logger.warning(f"텍스처 '{texture_name}'의 '{attr_name}' 속성 접근 실패: {str(e)}")
            
            # Unity 버전에 따라 'image_data', 'image_data_block', 'data'에 접근 시도
            if hasattr(texture_data, 'image_data'):
                data = texture_data.image_data
                if data:
                    logger.info(f"텍스처 '{texture_name}'의 image_data 속성 사용 (크기: {len(data)}바이트)")
                    return data
            
            # Unity 5.x 이상 버전에서 사용하는 방식
            if hasattr(texture_data, 'image_data_block'):
                data = texture_data.image_data_block
                if data:
                    logger.info(f"텍스처 '{texture_name}'의 image_data_block 속성 사용 (크기: {len(data)}바이트)")
                    return data
                
            # 원본 데이터 블록에 접근
            if hasattr(texture_data, 'data'):
                data = texture_data.data
                if data:
                    logger.info(f"텍스처 '{texture_name}'의 data 속성 사용 (크기: {len(data)}바이트)")
                    return data
            
            # m_StreamData에 접근 시도
            if hasattr(texture_data, 'm_StreamData'):
                stream_data = texture_data.m_StreamData
                if hasattr(stream_data, 'size') and stream_data.size > 0:
                    logger.info(f"텍스처 '{texture_name}'의 m_StreamData 사용 (크기: {stream_data.size}바이트)")
                    offset = stream_data.offset
                    size = stream_data.size
                    path = getattr(stream_data, 'path', '')
                    
                    # 경로가 있으면 외부 파일에서 데이터 로드
                    if path:
                        # 리소스 파일 경로 유추
                        if hasattr(texture_data, 'assets_file') and hasattr(texture_data.assets_file, 'path'):
                            resource_path = os.path.join(os.path.dirname(texture_data.assets_file.path), path)
                            if os.path.exists(resource_path):
                                logger.info(f"외부 리소스 파일 읽기: {resource_path}")
                                with open(resource_path, 'rb') as f:
                                    f.seek(offset)
                                    data = f.read(size)
                                    if data:
                                        return data
                            else:
                                logger.warning(f"외부 리소스 파일이 존재하지 않음: {resource_path}")
                        else:
                            logger.warning(f"assets_file 또는 path 속성이 없어 외부 리소스를 로드할 수 없음")
            
            # Unity 4.x 이하 버전에서 사용하는 방식
            if hasattr(texture_data, 'm_DataSize') and hasattr(texture_data, 'm_Data'):
                if texture_data.m_DataSize > 0:
                    data = texture_data.m_Data
                    if data:
                        logger.info(f"텍스처 '{texture_name}'의 m_Data 속성 사용 (크기: {len(data)}바이트)")
                        return data
                    
            # 바이트 배열 직접 접근 시도
            for possible_byte_attr in ['data_items', 'byte_array', 'raw_data', 'binary_data']:
                if hasattr(texture_data, possible_byte_attr):
                    logger.info(f"텍스처 '{texture_name}'의 {possible_byte_attr} 속성 시도")
                    try:
                        data = getattr(texture_data, possible_byte_attr)
                        if data and isinstance(data, (bytes, bytearray)):
                            return data
                    except Exception as e:
                        logger.warning(f"{possible_byte_attr} 속성 접근 실패: {str(e)}")
                    
            logger.warning(f"텍스처 '{texture_name}'의 이미지 데이터를 찾을 수 없습니다.")
            return None
                
        except Exception as e:
            logger.error(f"텍스처 '{texture_name}' 데이터 접근 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _decode_texture_data(self, texture_data: Any) -> Optional[Image.Image]:
        """
        texture2ddecoder를 사용하여 텍스처 데이터를 디코딩합니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            
        Returns:
            Optional[Image.Image]: 디코딩된 PIL 이미지 객체 또는 None
        """
        try:
            # 기본 UnityPy image 속성 먼저 시도 (더 안정적)
            if hasattr(texture_data, 'image'):
                try:
                    img = texture_data.image
                    if img:
                        logger.info(f"UnityPy image 속성 사용 성공: {getattr(texture_data, 'm_Name', 'Unknown')}")
                        return img
                except Exception as e:
                    logger.warning(f"UnityPy image 속성 사용 실패: {str(e)}")
            
            # 텍스처 정보 가져오기
            width = getattr(texture_data, 'm_Width', 0)
            height = getattr(texture_data, 'm_Height', 0)
            texture_format = getattr(texture_data, 'm_TextureFormat', 'Unknown')
            texture_name = getattr(texture_data, 'm_Name', 'Unknown')
            
            if width <= 0 or height <= 0:
                logger.error(f"텍스처 '{texture_name}'의 크기가 유효하지 않음: {width}x{height}")
                return None
            
            # 원시 이미지 데이터 가져오기
            image_data = self._get_texture_raw_data(texture_data)
            
            if not image_data:
                logger.error(f"텍스처 '{texture_name}'의 이미지 데이터가 없습니다.")
                return None
            
            # 텍스처 포맷 확인
            logger.info(f"텍스처 '{texture_name}' 디코딩 시도: 포맷={texture_format}, 크기={width}x{height}, 데이터 크기={len(image_data)}바이트")
            
            # 포맷 문자열을 소문자로 변환하고 안전성 확보
            texture_format_lower = str(texture_format).lower() if texture_format else ""
            
            # 텍스처 포맷에 따른 디코딩
            try:
                decoded_data = None
                
                # texture2ddecoder 라이브러리가 사용 가능한 경우에만 특수 디코더 사용
                if texture2ddecoder_available:
                    logger.info(f"텍스처 '{texture_name}': texture2ddecoder 사용하여 디코딩 시도")
                    try:
                        # AssetStudio 방식처럼 직접 텍스처 포맷명으로 분기
                        if "dxt1" in texture_format_lower or "bc1" in texture_format_lower:
                            decoded_data = decode_bc1(image_data, width, height)
                        elif "dxt5" in texture_format_lower or "bc3" in texture_format_lower:
                            decoded_data = decode_bc3(image_data, width, height)
                        elif "bc4" in texture_format_lower:
                            decoded_data = decode_bc4(image_data, width, height)
                        elif "bc5" in texture_format_lower:
                            decoded_data = decode_bc5(image_data, width, height)
                        elif "bc6h" in texture_format_lower:
                            decoded_data = decode_bc6(image_data, width, height)
                        elif "bc7" in texture_format_lower:
                            decoded_data = decode_bc7(image_data, width, height)
                        elif "etc_rgb4" in texture_format_lower or "etc1" in texture_format_lower:
                            decoded_data = decode_etc1(image_data, width, height)
                        elif "etc2" in texture_format_lower:
                            decoded_data = decode_etc2(image_data, width, height)
                        elif "astc" in texture_format_lower:
                            block_size = getattr(texture_data, 'block_size', (4, 4))
                            decoded_data = decode_astc(image_data, width, height, block_size[0], block_size[1])
                    except Exception as e:
                        logger.warning(f"texture2ddecoder 특수 디코더 실패: {str(e)}")
                        decoded_data = None
                        
                # 특수 디코더가 없거나 실패한 경우 기본 변환 시도
                if decoded_data is None:
                    # 기본 변환 시도: RGB/RGBA 직접 변환
                    logger.info(f"텍스처 '{texture_name}': 특수 디코더 없음/실패, 기본 변환 시도")
                    if "rgba" in texture_format_lower or "argb" in texture_format_lower:
                        try:
                            # RGBA 모드로 변환 시도
                            return Image.frombuffer('RGBA', (width, height), image_data, 'raw', 'RGBA', 0, 1)
                        except Exception as inner_e:
                            logger.warning(f"RGBA 직접 변환 실패: {str(inner_e)}")
                    else:
                        try:
                            # RGB 모드로 변환 시도
                            return Image.frombuffer('RGB', (width, height), image_data, 'raw', 'RGB', 0, 1)
                        except Exception as inner_e:
                            logger.warning(f"RGB 직접 변환 실패: {str(inner_e)}")
                    
                    # 마지막 방법: UnityPy의 기본 이미지 속성 사용
                    try:
                        logger.info(f"텍스처 '{texture_name}': UnityPy의 기본 이미지 속성 최종 시도")
                        return texture_data.image
                    except Exception as inner_e:
                        logger.error(f"UnityPy 이미지 접근 실패: {str(inner_e)}")
                        return None
                    
                # NumPy 배열을 PIL 이미지로 변환
                if decoded_data is not None:
                    logger.info(f"텍스처 '{texture_name}': 디코더 변환 성공")
                    img = Image.frombuffer('RGBA', (width, height), decoded_data, 'raw', 'RGBA', 0, 1)
                    return img.transpose(Image.FLIP_TOP_BOTTOM)  # Unity 텍스처는 상하 반전되어 있음
                else:
                    logger.warning(f"텍스처 '{texture_name}': 디코더 변환 결과가 None")
                    return None
                    
            except Exception as e:
                logger.error(f"텍스처 '{texture_name}' 디코딩 오류 ({texture_format}): {str(e)}")
                
                # 폴백: UnityPy의 기본 디코딩 시도
                try:
                    logger.info(f"텍스처 '{texture_name}': 예외 후 UnityPy 기본 이미지 속성 시도")
                    return texture_data.image
                except Exception as inner_e:
                    logger.error(f"UnityPy 폴백 실패: {str(inner_e)}")
                    return None
                
        except Exception as e:
            texture_name = getattr(texture_data, 'm_Name', 'Unknown')
            logger.error(f"텍스처 '{texture_name}' 데이터 처리 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
        return None

    def extract_texture(self, texture_data: Any, output_path: Optional[str] = None) -> str:
        """
        Texture2D 객체에서 이미지를 추출하여 저장합니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            output_path: 저장할 파일 경로 (None이면 임시 파일 생성)
            
        Returns:
            str: 저장된 이미지 파일 경로
        """
        try:
            # 이미지 추출
            img = texture_data.image
            
            # 출력 경로 결정
            if not output_path:
                output_path = os.path.join(self.temp_dir, f"{texture_data.m_Name}.png")
            
            # 이미지 저장
            img.save(output_path)
            
            return output_path
        except Exception as e:
            print(f"텍스처 추출 오류: {str(e)}")
            return ""
    
    def get_texture_preview(self, texture_data: Any) -> Image.Image:
        """
        텍스처 미리보기 이미지를 가져옵니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            
        Returns:
            Image.Image: PIL 이미지 객체
        """
        # 캐시 확인
        texture_id = id(texture_data)
        if texture_id in self.image_cache:
            logger.info(f"캐싱된 이미지 사용: {getattr(texture_data, 'm_Name', 'Unknown')}")
            cached_img, _ = self.image_cache[texture_id]
            # 캐시된 이미지가 유효한지 확인
            if cached_img:
                return cached_img.copy()
        
        # 디코딩으로 이미지 가져오기
        img = None
        try:
            # UnityPy 내장 이미지 속성 사용 시도
            img = self._decode_texture_data(texture_data)
            
            if img:
                logger.info(f"텍스처 디코딩 성공: {getattr(texture_data, 'm_Name', 'Unknown')}")
                # 결과를 캐시에 저장
                self.image_cache[texture_id] = (img.copy(), time.time())
                # 캐시 크기 관리
                self._clear_old_cache_entries()
                return img
            else:
                logger.warning(f"텍스처 디코딩 실패: {getattr(texture_data, 'm_Name', 'Unknown')}")
                # 플레이스홀더 이미지 반환
                return self._create_placeholder_image(
                    getattr(texture_data, 'm_Width', 256), 
                    getattr(texture_data, 'm_Height', 256)
                )
                
        except Exception as e:
            logger.error(f"텍스처 미리보기 생성 오류: {str(e)}")
            # 플레이스홀더 이미지 반환
            return self._create_placeholder_image(
                getattr(texture_data, 'm_Width', 256), 
                getattr(texture_data, 'm_Height', 256)
            )
            
    def _create_placeholder_image(self, width: int, height: int) -> Image.Image:
        """
        텍스처 로드 실패 시 사용할 플레이스홀더 이미지를 생성합니다.
        
        Args:
            width: 이미지 너비
            height: 이미지 높이
            
        Returns:
            Image.Image: 플레이스홀더 이미지
        """
        # 체커보드 패턴 생성
        if width <= 0:
            width = 256
        if height <= 0:
            height = 256
            
        img = Image.new('RGB', (width, height), (200, 200, 200))
        
        # 체커보드 패턴 그리기
        square_size = max(8, min(width, height) // 16)
        
        draw = Image.new('RGB', (square_size * 2, square_size * 2))
        
        # 검은색 체커 패턴
        for y in range(2):
            for x in range(2):
                color = (150, 150, 150) if (x + y) % 2 == 0 else (100, 100, 100)
                box = (x * square_size, y * square_size, (x + 1) * square_size, (y + 1) * square_size)
                img_draw = Image.new('RGB', (square_size, square_size), color)
                draw.paste(img_draw, (x * square_size, y * square_size))
        
        # 패턴 복제
        for y in range(0, height, square_size * 2):
            for x in range(0, width, square_size * 2):
                img.paste(draw, (x, y))
        
        # "이미지 없음" 텍스트 표시
        try:
            from PIL import ImageDraw as PILImageDraw
            draw = PILImageDraw.Draw(img)
            text = "이미지 로드 실패"
            text_color = (255, 0, 0)
            
            # 중앙에 텍스트 배치
            if hasattr(draw, 'textsize'):  # PIL 9.0.0 이전
                text_width, text_height = draw.textsize(text)
                position = ((width - text_width) // 2, (height - text_height) // 2)
            else:  # PIL 9.0.0 이상
                text_width = len(text) * 8  # 글자당 평균 8픽셀로 가정
                text_height = 15  # 기본 폰트 높이로 가정
                position = ((width - text_width) // 2, (height - text_height) // 2)
                
            draw.text(position, text, text_color)
        except Exception as e:
            # 텍스트 표시 실패 시 무시
            logger.warning(f"텍스트 표시 오류: {str(e)}")
            
        return img
    
    def create_thumbnail(self, texture_data: Any, size: Tuple[int, int] = (100, 100)) -> Image.Image:
        """
        Texture2D 객체에서 썸네일 이미지를 생성합니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            size: 썸네일 크기 (width, height)
            
        Returns:
            Image: PIL 썸네일 이미지 객체
        """
        try:
            # 향상된 텍스처 디코딩 사용
            img = self.get_texture_preview(texture_data)
            
            # 이미지가 유효한지 확인
            if img is None:
                logger.warning(f"썸네일 생성 오류: 텍스처 '{getattr(texture_data, 'm_Name', 'Unknown')}' 미리보기를 가져올 수 없습니다.")
                return Image.new('RGB', size, color='gray')
                
            # 썸네일 생성
            thumb = img.copy()
            thumb.thumbnail(size, Image.LANCZOS)
            return thumb
                
        except Exception as e:
            logger.error(f"썸네일 생성 중 예상치 못한 오류: {str(e)}")
            # 오류 발생 시 빈 이미지 반환
            return Image.new('RGB', size, color='gray')
    
    def replace_texture(self, texture_obj: Any, texture_data: Any, new_image_path: str) -> bool:
        """
        Texture2D 객체의 이미지를 새 이미지로 교체합니다.
        
        Args:
            texture_obj: 텍스처 객체
            texture_data: 텍스처 데이터 객체
            new_image_path: 새 이미지 파일 경로
            
        Returns:
            bool: 교체 성공 여부
        """
        data = None  # data 변수 초기화
        original_format = None # 원본 포맷 저장 변수 초기화
        
        try:
            # 새 이미지 로드
            new_image = Image.open(new_image_path)
            
            # 텍스처 데이터 읽기 (texture_data 파라미터 활용)
            data = texture_obj.read() if texture_data is None else texture_data
            original_format = data.m_TextureFormat # 원본 포맷 저장
            
            # 원본 이미지 크기 확인
            original_width = data.m_Width
            original_height = data.m_Height
            
            # 원본 이미지 크기에 맞게 리사이징
            if (original_width != new_image.width or original_height != new_image.height):
                logger.info(f"이미지 리사이징: {new_image.width}x{new_image.height} -> {original_width}x{original_height}")
                new_image = new_image.resize((original_width, original_height), Image.LANCZOS)
            
            # 1차 시도: 원본 포맷으로 저장
            try:
                logger.info(f"텍스처 '{data.m_Name}' 교체 시도 (원본 포맷: {original_format})")
                data.image = new_image
                data.save()
                logger.info(f"텍스처 '{data.m_Name}' 교체 성공 (원본 포맷: {original_format})")
                return True
            except Exception as e:
                logger.warning(f"원본 포맷({original_format}) 저장 실패: {str(e)}. DXT5 포맷으로 재시도합니다.")
                # DXT5 저장으로 넘어감

            # 2차 시도: DXT5 포맷으로 저장
            try:
                logger.info(f"텍스처 '{data.m_Name}' 교체 재시도 (DXT5 포맷)")
                
                # DXT5는 RGBA만 지원하므로, 모드 변환
                if new_image.mode != 'RGBA':
                    logger.info(f"DXT5 저장을 위해 이미지를 RGBA 모드로 변환합니다: {new_image.mode} -> RGBA")
                    new_image = new_image.convert('RGBA')

                # 포맷 변경 및 저장 시도
                data.m_TextureFormat = 12  # TextureFormat.DXT5 (BC3)
                data.image = new_image # 이미지 다시 할당 (모드 변환 가능성 있음)
                data.save()
                logger.info(f"텍스처 '{data.m_Name}' 교체 성공 (DXT5 포맷으로 저장됨)")
                return True
            except Exception as e2:
                logger.error(f"DXT5 포맷 저장 실패: {str(e2)}")
                # 최종 실패 시 원래 오류를 출력하거나 False 반환
                print(f"텍스처 교체 오류 (원본 및 DXT5 모두 실패): 원본오류={str(e)}, DXT5오류={str(e2)}")
                # 실패 시 원본 포맷으로 되돌릴 필요는 없음 (어차피 저장 실패)
                return False

        except Exception as e_outer:
            # 이미지 로드, 데이터 읽기 등 초기 단계 오류 처리
            error_msg = f"텍스처 교체 준비 중 오류: {str(e_outer)}"
            if data and hasattr(data, 'm_Name'):
                error_msg = f"텍스처 '{data.m_Name}' 교체 준비 중 오류: {str(e_outer)}"
            elif original_format:
                 error_msg = f"텍스처 (원본 포맷: {original_format}) 교체 준비 중 오류: {str(e_outer)}"

            logger.error(error_msg)
            print(error_msg) # 콘솔에도 출력
            return False

    def restore_texture(self, texture_obj: Any, original_image: Image.Image) -> bool:
        """
        Texture2D 객체의 이미지를 원본 이미지로 복원합니다.
        
        Args:
            texture_obj: 텍스처 객체
            original_image: 원본 PIL 이미지 객체
            
        Returns:
            bool: 복원 성공 여부
        """
        try:
            if not texture_obj:
                print("텍스처 객체가 없습니다.")
                return False
                
            if not original_image:
                print("원본 이미지가 없습니다.")
                return False
                
            # 텍스처 데이터 읽기
            data = texture_obj.read()
            
            if not data:
                print("텍스처 데이터를 읽을 수 없습니다.")
                return False
                
            # 이미지 크기 일치 여부 확인
            if hasattr(data, 'm_Width') and hasattr(data, 'm_Height'):
                if data.m_Width != original_image.width or data.m_Height != original_image.height:
                    print(f"이미지 크기 불일치: 원본({original_image.width}x{original_image.height}) vs 텍스처({data.m_Width}x{data.m_Height})")
                    # 크기 조정
                    original_image = original_image.resize((data.m_Width, data.m_Height), Image.LANCZOS)
                    print(f"이미지 크기 조정됨: {data.m_Width}x{data.m_Height}")
            
            # 이미지 모드 확인
            if hasattr(data, 'image') and data.image.mode != original_image.mode:
                print(f"이미지 모드 변환: {original_image.mode} -> {data.image.mode}")
                original_image = original_image.convert(data.image.mode)
            
            # 이미지 데이터 복원
            data.image = original_image
            
            # 변경사항 저장
            data.save()
            
            print("텍스처가 원본으로 복원되었습니다.")
            return True
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"텍스처 복원 오류: {str(e)}")
            print(error_traceback)
            return False
    
    def get_texture_info(self, texture_data: Any) -> Dict[str, Any]:
        """
        Texture2D 객체의 상세 정보를 반환합니다.
        
        Args:
            texture_data: 텍스처 데이터 객체
            
        Returns:
            Dict: 텍스처 정보
        """
        try:
            # 기본 정보
            info = {
                'name': getattr(texture_data, 'm_Name', 'Unknown'),
                'width': getattr(texture_data, 'm_Width', 0),
                'height': getattr(texture_data, 'm_Height', 0),
                'format': getattr(texture_data, 'm_TextureFormat', 'Unknown'),
                'mipmap_count': getattr(texture_data, 'm_MipCount', 0),
                'is_readable': getattr(texture_data, 'm_IsReadable', False)
            }
            
            # 텍스처 설정 정보
            texture_settings = {}
            try:
                settings = texture_data.m_TextureSettings
                texture_settings = {
                    'filter_mode': getattr(settings, 'm_FilterMode', 'Unknown'),
                    'aniso_level': getattr(settings, 'm_AnisotropicFilteringLevel', 0),
                    'wrap_mode': getattr(settings, 'm_WrapMode', 'Unknown')
                }
            except (AttributeError, Exception) as e:
                # 텍스처 설정 정보 사용 불가
                texture_settings = {
                    'filter_mode': 'Unknown',
                    'aniso_level': 0,
                    'wrap_mode': 'Unknown'
                }
            
            info['texture_settings'] = texture_settings
            return info
        except Exception as e:
            print(f"텍스처 정보 추출 오류: {str(e)}")
            # 기본 정보 제공
            return {
                'name': getattr(texture_data, 'm_Name', 'Unknown'),
                'width': getattr(texture_data, 'm_Width', 0),
                'height': getattr(texture_data, 'm_Height', 0),
                'format': 'Unknown',
                'mipmap_count': 0,
                'is_readable': False,
                'texture_settings': {
                    'filter_mode': 'Unknown',
                    'aniso_level': 0,
                    'wrap_mode': 'Unknown'
                }
            }
