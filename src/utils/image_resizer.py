import os
import sys
from PIL import Image
from typing import Optional, Tuple, Union
from io import BytesIO
import threading
import time

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.texture_processor import TextureProcessor


class ImageResizer:
    """
    이미지 리사이징 기능을 제공하는 유틸리티 클래스
    """
    
    def __init__(self, texture_processor: TextureProcessor):
        self.texture_processor = texture_processor
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 리사이징 결과 캐시: {(소스경로, 타겟너비, 타겟높이): 결과경로}
        self.resize_cache = {}
        self.cache_lock = threading.Lock()
        self.max_cache_entries = 20
    
    def resize_image(self, source_image: Union[str, Image.Image], target_width: int, target_height: int) -> Optional[str]:
        """
        이미지를 대상 해상도에 맞게 리사이징합니다.
        
        Args:
            source_image: 소스 이미지 파일 경로 또는 PIL Image 객체
            target_width: 대상 너비
            target_height: 대상 높이
            
        Returns:
            Optional[str]: 리사이징된 이미지 파일 경로 또는 None
        """
        # 이미지가 경로인 경우 캐시 확인
        cache_key = None
        if isinstance(source_image, str):
            cache_key = (source_image, target_width, target_height)
            with self.cache_lock:
                if cache_key in self.resize_cache:
                    cached_path = self.resize_cache[cache_key]
                    if os.path.exists(cached_path):
                        # 캐시 히트
                        return cached_path
        
        try:
            # 소스 이미지 로드
            if isinstance(source_image, str):
                img = Image.open(source_image)
                source_path = source_image
            else:
                img = source_image
                # 임시 파일 만들어서 저장
                source_path = os.path.join(self.temp_dir, f"temp_source_{int(time.time())}.png")
                img.save(source_path, "PNG")
            
            # 이미지 포맷과 모드 확인
            source_format = getattr(img, 'format', 'PNG')
            source_mode = img.mode
            
            # 이미지 모드 유지하면서 리사이징
            if source_mode not in ['RGB', 'RGBA']:
                # 알파 채널이 필요하면 RGBA로, 아니면 RGB로 변환
                if 'A' in source_mode or source_mode == 'P' and img.info.get('transparency'):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            # 리사이징 작업 수행
            # 성능 최적화: 큰 이미지는 단계적으로 리사이징
            current_size = img.size
            max_step = 2.0  # 한 번에 최대 1/2로 축소
            
            # 단계적으로 이미지 크기 조정 (너무 큰 이미지를 한 번에 리사이징하면 품질 저하 발생)
            if current_size[0] > target_width * 2 or current_size[1] > target_height * 2:
                # 단계적으로 줄이기
                while current_size[0] > target_width * 2 or current_size[1] > target_height * 2:
                    new_width = max(current_size[0] // 2, target_width)
                    new_height = max(current_size[1] // 2, target_height)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    current_size = img.size
            
            # 최종 크기로 리사이징
            if current_size[0] != target_width or current_size[1] != target_height:
                img = img.resize((target_width, target_height), Image.LANCZOS)
            
            # 임시 파일 경로 생성
            file_name = os.path.basename(source_path)
            base_name, ext = os.path.splitext(file_name)
            
            # 투명도가 있는 이미지는 PNG로 저장 (JPG는 알파 채널을 지원하지 않음)
            if img.mode == 'RGBA' and ext.lower() in ['.jpg', '.jpeg']:
                ext = '.png'
            
            resized_path = os.path.join(self.temp_dir, f"{base_name}_resized_{target_width}x{target_height}{ext}")
            
            # 이미지 저장 - 퀄리티 설정으로 최적화
            save_options = {}
            if ext.lower() in ['.jpg', '.jpeg']:
                save_options['quality'] = 90  # JPG 퀄리티
                save_options['optimize'] = True
            elif ext.lower() == '.png':
                save_options['optimize'] = True
                if img.mode == 'RGBA':
                    # 알파 채널이 있는 PNG 최적화
                    save_options['format'] = 'PNG'
            
            img.save(resized_path, **save_options)
            
            # 캐시 업데이트
            if cache_key:
                with self.cache_lock:
                    self.resize_cache[cache_key] = resized_path
                    # 캐시 크기 제한
                    if len(self.resize_cache) > self.max_cache_entries:
                        # 가장 오래된 항목 제거
                        oldest_key = next(iter(self.resize_cache))
                        del self.resize_cache[oldest_key]
            
            return resized_path
        except Exception as e:
            print(f"이미지 리사이징 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_image_dimensions(self, image_path: str) -> Optional[Tuple[int, int]]:
        """
        이미지 파일의 해상도를 반환합니다.
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            Optional[Tuple[int, int]]: (너비, 높이) 또는 None
        """
        try:
            with Image.open(image_path) as img:
                return img.width, img.height
        except Exception as e:
            print(f"이미지 해상도 확인 오류: {str(e)}")
            return None
    
    def compare_dimensions(self, source_path: str, target_width: int, target_height: int) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """
        소스 이미지와 대상 해상도를 비교합니다.
        
        Args:
            source_path: 소스 이미지 파일 경로
            target_width: 대상 너비
            target_height: 대상 높이
            
        Returns:
            Tuple[bool, Optional[Tuple[int, int]]]: (해상도 일치 여부, 소스 해상도)
        """
        source_dims = self.get_image_dimensions(source_path)
        if not source_dims:
            return False, None
        
        return (source_dims[0] == target_width and source_dims[1] == target_height), source_dims
