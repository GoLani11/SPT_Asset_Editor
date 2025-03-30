import os
import UnityPy
from typing import Dict, List, Tuple, Any, Optional


class AssetsManager:
    """
    .assets 파일과 .bundle 파일을 로드, 분석 및 저장하는 클래스
    """
    
    def __init__(self):
        self.env = None
        self.file_path = None
        self.texture_objects = {}  # ID: obj
        self.texture_paths = {}    # path: obj
        self.missing_texture_ids = set()  # 손상되거나 로드할 수 없는 텍스처 ID 저장
        self.file_type = None  # 'assets' 또는 'bundle'
        
    def load_file(self, file_path: str) -> bool:
        """
        .assets 또는 .bundle 파일을 로드합니다.
        
        Args:
            file_path: 로드할 파일 경로
            
        Returns:
            bool: 로드 성공 여부
        """
        if not os.path.exists(file_path):
            print(f"오류: 파일을 찾을 수 없습니다 - {file_path}")
            return False
        
        # 파일 유형 확인
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.assets':
            self.file_type = 'assets'
        elif file_ext == '.bundle':
            self.file_type = 'bundle'
        else:
            print(f"오류: 지원되지 않는 파일 형식입니다 - {file_ext}")
            return False
        
        try:
            # UnityPy는 .assets와 .bundle 모두 동일한 방식으로 로드 가능
            self.env = UnityPy.load(file_path)
            self.file_path = file_path
            
            # 번들 파일인 경우 추가 처리
            if self.file_type == 'bundle':
                try:
                    # 번들 파일의 텍스처 데이터 처리 시 발생할 수 있는 오류 처리
                    self._parse_textures()
                except Exception as e:
                    print(f"번들 파일 텍스처 파싱 오류: {str(e)}")
                    # 오류가 발생해도 계속 진행 (일부 텍스처만 로드)
                    return True
            else:
                self._parse_textures()
                # 관련된 리소스 파일 확인 (.assets 파일인 경우에만)
                self._check_resource_files()
            
            return True
        except Exception as e:
            print(f"파일 로드 오류: {str(e)}")
            return False
    
    def _parse_textures(self) -> None:
        """
        에셋 파일에서 Texture2D 객체를 찾아 저장합니다.
        """
        if not self.env:
            return
            
        try:
            # 기존 데이터 초기화
            self.texture_objects.clear()
            self.texture_paths.clear()
            self.missing_texture_ids.clear()
            
            # 모든 객체 순회
            for obj in self.env.objects:
                if obj.type.name == "Texture2D":
                    try:
                        # 텍스처 데이터 읽기 시도
                        data = obj.read()
                        
                        # 번들 파일의 경우 추가 검증
                        if self.file_type == 'bundle':
                            try:
                                # 이미지 데이터 유효성 검사
                                if hasattr(data, 'image'):
                                    # _ = data.image  # 이미지 데이터 접근 시도 (제거)
                                    pass # 이미지 속성 존재 여부만 확인
                                else:
                                    print(f"텍스처 '{data.name}' 이미지 속성 없음")
                                    self.missing_texture_ids.add(obj.path_id)
                                    continue
                            except Exception as e:
                                print(f"텍스처 '{data.name}' 이미지 데이터 오류: {str(e)}")
                                self.missing_texture_ids.add(obj.path_id)
                                continue
                        
                        # 텍스처 객체 저장
                        self.texture_objects[obj.path_id] = obj
                        
                        # 컨테이너에서 경로 정보 찾기
                        for path, container_obj in self.env.container.items():
                            if container_obj.path_id == obj.path_id:
                                self.texture_paths[path] = obj
                                break
                                
                    except Exception as e:
                        print(f"텍스처 객체 파싱 오류 (ID: {obj.path_id}): {str(e)}")
                        self.missing_texture_ids.add(obj.path_id)
                        
        except Exception as e:
            print(f"텍스처 파싱 중 오류 발생: {str(e)}")
            # 오류 발생 시 데이터 초기화
            self.texture_objects.clear()
            self.texture_paths.clear()
            self.missing_texture_ids.clear()
    
    def get_texture_list(self) -> List[Dict[str, Any]]:
        """
        로드된 .assets 파일의 Texture2D 목록을 반환합니다.
        손상된 텍스처는 건너뜁니다.
        
        Returns:
            List[Dict]: Texture2D 객체 정보 목록
        """
        result = []
        
        for obj_id, obj in self.texture_objects.items():
            # 이미 손상된 것으로 확인된 텍스처는 건너뛰기
            if obj_id in self.missing_texture_ids:
                continue
                
            try:
                data = obj.read()
                texture_info = {
                    'id': obj_id,
                    'name': data.m_Name,
                    'width': data.m_Width,
                    'height': data.m_Height,
                    'format': data.m_TextureFormat,
                    'path': self._find_path_for_object(obj)
                }
                result.append(texture_info)
            except Exception as e:
                # 오류가 발생한 텍스처는 목록에서 제외하고 ID 기록
                print(f"텍스처 ID {obj_id} 읽기 실패: {str(e)}")
                self.missing_texture_ids.add(obj_id)
            
        return result
    
    def _find_path_for_object(self, obj) -> Optional[str]:
        """
        객체에 해당하는 경로를 찾습니다.
        
        Args:
            obj: 찾을 객체
            
        Returns:
            Optional[str]: 객체 경로 또는 None
        """
        for path, path_obj in self.texture_paths.items():
            if path_obj.path_id == obj.path_id:
                return path
        return None
    
    def get_texture_by_id(self, obj_id) -> Optional[Tuple[Any, Dict]]:
        """
        ID로 Texture2D 객체를 찾습니다.
        
        Args:
            obj_id: 찾을 객체 ID
            
        Returns:
            Optional[Tuple]: (객체, 객체 데이터) 또는 None
        """
        if obj_id not in self.texture_objects or obj_id in self.missing_texture_ids:
            return None
        
        try:
            obj = self.texture_objects[obj_id]
            data = obj.read()
            return obj, data
        except Exception as e:
            print(f"텍스처 ID {obj_id} 읽기 실패: {str(e)}")
            self.missing_texture_ids.add(obj_id)
            return None
    
    def get_texture_by_name(self, name: str) -> Optional[Tuple[Any, Dict]]:
        """
        이름으로 Texture2D 객체를 찾습니다.
        
        Args:
            name: 찾을 텍스처 이름
            
        Returns:
            Optional[Tuple]: (객체, 객체 데이터) 또는 None
        """
        for obj_id, obj in self.texture_objects.items():
            if obj_id in self.missing_texture_ids:
                continue
            
            try:
                data = obj.read()
                if data.m_Name == name:
                    return obj, data
            except Exception as e:
                print(f"텍스처 ID {obj_id} 읽기 실패: {str(e)}")
                self.missing_texture_ids.add(obj_id)
        
        return None
    
    def save_file(self, output_path: str = None, copy_resource_files: bool = True) -> bool:
        """
        수정된 파일을 저장합니다.
        
        Args:
            output_path: 저장할 파일 경로 (None이면 원본 파일 덮어쓰기)
            copy_resource_files: .resS 파일도 함께 복사할지 여부
            
        Returns:
            bool: 저장 성공 여부
        """
        if not self.env:
            print("오류: 저장할 파일이 로드되지 않았습니다.")
            return False
            
        try:
            # 출력 경로가 지정되지 않으면 원본 파일 경로 사용
            if not output_path:
                output_path = self.file_path
            
            # 파일 확장자 확인 및 수정
            if self.file_type:
                expected_ext = f".{self.file_type}"
                file_ext = os.path.splitext(output_path)[1].lower()
                
                # 확장자가 없거나 다른 확장자인 경우
                if not file_ext:
                    # 확장자 추가
                    output_path = f"{output_path}{expected_ext}"
                    print(f"확장자 없음: '{expected_ext}' 확장자를 자동으로 추가합니다.")
                elif file_ext != expected_ext:
                    # 현재 파일 형식과 다른 확장자가 있는 경우
                    print(f"경고: 현재 파일 형식은 '{self.file_type}'이지만 저장 경로의 확장자는 '{file_ext}'입니다.")
                    if file_ext not in ['.assets', '.bundle']:
                        # 지원되지 않는 확장자인 경우 올바른 확장자 추가
                        output_path = f"{output_path}{expected_ext}"
                        print(f"지원되지 않는 확장자: '{expected_ext}' 확장자를 자동으로 추가합니다.")
            
            # 파일 저장
            with open(output_path, "wb") as f:
                f.write(self.env.file.save())
                
            print(f"파일 저장 완료: {output_path}")
            
            # .resS 파일 복사 (.assets 파일인 경우에만)
            if copy_resource_files and self.file_type == 'assets':
                self._copy_resource_files(output_path)
                
            return True
        except Exception as e:
            print(f"파일 저장 오류: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
            
    def _copy_resource_files(self, save_path: str) -> None:
        """
        .assets 파일과 관련된 .resS 파일을 복사합니다.
        텍스처 수정이 게임에 적용되려면 .resS 파일도 함께 복사해야 합니다.
        
        Args:
            save_path: 저장된 .assets 파일 경로
        """
        if not self.file_path or not save_path:
            return
            
        try:
            # 원본 파일 디렉토리와 파일 이름 가져오기
            src_dir = os.path.dirname(self.file_path)
            src_filename = os.path.basename(self.file_path)
            src_filename_noext = os.path.splitext(src_filename)[0]
            
            # 대상 디렉토리 가져오기
            dst_dir = os.path.dirname(save_path)
            dst_filename = os.path.basename(save_path)
            
            # 소스와 대상이 같은 경로인 경우 복사 건너뛰기
            if os.path.normpath(src_dir) == os.path.normpath(dst_dir) and src_filename == dst_filename:
                print("소스와 대상이 동일합니다. .resS 파일 복사를 건너뜁니다.")
                return
            
            # 가능한 .resS 파일 패턴들
            res_patterns = [
                f"{src_filename}.resS",                  # 기본 패턴 (예: file.assets.resS)
                f"{src_filename_noext}.resS",            # 확장자 없는 패턴 (예: file.resS)
                f"sharedassets{src_filename_noext}.resS" # 공유 에셋 패턴 (예: sharedassets0.resS)
            ]
            
            # Unity 패턴 더 추가
            for i in range(10):  # sharedassets0 ~ sharedassets9
                res_patterns.append(f"sharedassets{i}.assets.resS")
            
            # 각 패턴에 대해 파일이 존재하는지 확인하고 복사
            found_files = 0
            for pattern in res_patterns:
                src_res_path = os.path.join(src_dir, pattern)
                dst_res_path = os.path.join(dst_dir, pattern)
                
                if os.path.exists(src_res_path):
                    found_files += 1
                    print(f"리소스 파일 복사: {pattern}")
                    # 파일 복사 (파일이 클 수 있으므로 청크 단위로 복사)
                    with open(src_res_path, 'rb') as src_file, open(dst_res_path, 'wb') as dst_file:
                        chunk_size = 1024 * 1024  # 1MB 청크
                        while True:
                            chunk = src_file.read(chunk_size)
                            if not chunk:
                                break
                            dst_file.write(chunk)
            
            if found_files == 0:
                print("경고: 관련된 .resS 파일을 찾을 수 없습니다.")
                print("텍스처의 이미지 데이터는 보통 .resS 파일에 저장됩니다.")
                print("텍스처 변경사항이 게임에 제대로 적용되려면 관련된 .resS 파일이 필요합니다.")
            else:
                print(f"총 {found_files}개의 .resS 파일을 성공적으로 복사했습니다. 텍스처 변경사항이 게임에 적용됩니다.")
                
        except Exception as e:
            print(f"리소스 파일 복사 오류: {str(e)}")
    
    def _check_resource_files(self) -> None:
        """
        관련된 .resS 파일의 존재 여부를 확인합니다.
        파일이 없어도 오류를 발생시키지 않습니다.
        """
        if not self.file_path:
            return
            
        try:
            # 파일 디렉토리와 이름 가져오기
            file_dir = os.path.dirname(self.file_path)
            filename = os.path.basename(self.file_path)
            filename_noext = os.path.splitext(filename)[0]
            
            # 가능한 .resS 파일 패턴들
            res_patterns = [
                f"{filename}.resS",
                f"{filename_noext}.resS",
                f"sharedassets{filename_noext}.resS"
            ]
            
            # Unity 패턴 더 추가
            for i in range(10):
                res_patterns.append(f"sharedassets{i}.assets.resS")
            
            # 각 패턴에 대해 파일이 존재하는지 확인
            found_res_files = []
            for pattern in res_patterns:
                res_path = os.path.join(file_dir, pattern)
                if os.path.exists(res_path):
                    found_res_files.append(pattern)
            
            if found_res_files:
                print(f"발견된 리소스 파일: {', '.join(found_res_files)}")
            else:
                print("경고: 관련된 .resS 파일을 찾을 수 없습니다. 일부 텍스처가 로드되지 않을 수 있습니다.")
        except Exception as e:
            # 확인 과정에서 오류가 발생해도 프로그램 실행에 영향 없도록 처리
            print(f"리소스 파일 확인 중 오류 발생: {str(e)}")
