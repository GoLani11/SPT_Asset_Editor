import os
import shutil
import time
import fnmatch
import json
from typing import Optional, List, Dict, Any
from datetime import datetime


class BackupManager:
    """
    원본 .assets 파일을 백업하고 복원하는 클래스
    """
    
    def __init__(self):
        # 기본 백업 폴더 설정
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.backup_history = {}  # 파일 경로: [백업 경로 목록]
    
    def set_backup_directory(self, directory_path: str) -> bool:
        """
        백업 파일이 저장될 디렉토리를 설정합니다.
        
        Args:
            directory_path: 백업 디렉토리 경로
            
        Returns:
            bool: 설정 성공 여부
        """
        try:
            # 지정된 경로가 존재하지 않으면 생성
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
            
            # 디렉토리가 맞는지 확인
            if not os.path.isdir(directory_path):
                print(f"오류: 지정된 경로가 디렉토리가 아닙니다 - {directory_path}")
                return False
                
            # 디렉토리 쓰기 권한 확인
            if not os.access(directory_path, os.W_OK):
                print(f"오류: 지정된 디렉토리에 쓰기 권한이 없습니다 - {directory_path}")
                return False
                
            # 백업 디렉토리 설정
            self.backup_dir = directory_path
            print(f"백업 디렉토리가 설정되었습니다: {directory_path}")
            return True
            
        except Exception as e:
            print(f"백업 디렉토리 설정 오류: {str(e)}")
            return False
    
    def get_backup_directory(self) -> str:
        """
        현재 설정된 백업 디렉토리를 반환합니다.
        디렉토리가 유효하지 않으면 기본 디렉토리를 생성하고 반환합니다.
        
        Returns:
            str: 백업 디렉토리 경로
        """
        # 백업 디렉토리가 존재하고 쓰기 가능한지 확인
        if not os.path.exists(self.backup_dir) or not os.path.isdir(self.backup_dir) or not os.access(self.backup_dir, os.W_OK):
            # 기본 디렉토리로 재설정
            self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")
            os.makedirs(self.backup_dir, exist_ok=True)
            print(f"백업 디렉토리가 유효하지 않아 기본 디렉토리로 재설정: {self.backup_dir}")
            
        return self.backup_dir
    
    def ensure_backup_directory(self) -> bool:
        """
        백업 디렉토리가 있고 쓰기 가능한지 확인하고 필요시 생성합니다.
        
        Returns:
            bool: 디렉토리가 유효하고 사용 가능하면 True
        """
        directory = self.get_backup_directory()
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"백업 디렉토리 생성: {directory}")
            
            # 쓰기 권한 테스트
            test_file = os.path.join(directory, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            return True
        except Exception as e:
            print(f"백업 디렉토리 확인 실패: {str(e)}")
            return False
    
    def _get_file_extension(self, file_path):
        """
        파일 확장자를 반환합니다.
        
        Args:
            file_path: 파일 경로
            
        Returns:
            str: 파일 확장자 (소문자)
        """
        return os.path.splitext(file_path)[1].lower()
    
    def _is_supported_file(self, file_path):
        """
        지원되는 파일 형식인지 확인합니다.
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            bool: 지원되는 파일이면 True
        """
        ext = self._get_file_extension(file_path)
        return ext in ['.assets', '.bundle']

    def create_backup(self, file_path: str, backup_path: Optional[str] = None) -> Optional[str]:
        """
        지정된 에셋 파일의 백업을 생성합니다.

        Args:
            file_path: 백업할 에셋 파일 경로
            backup_path: 백업 파일의 전체 경로 (None이면 자동 생성된 이름으로 backup_dir에 저장)

        Returns:
            str: 생성된 백업 파일 경로 또는 실패 시 None
        """
        if not os.path.exists(file_path):
            print(f"백업할 파일이 존재하지 않습니다: {file_path}")
            return None

        # 지원되는 파일인지 확인
        if not self._is_supported_file(file_path):
            print(f"지원되지 않는 파일 형식입니다: {file_path}")
            return None

        try:
            if backup_path:
                # 지정된 경로가 있으면 해당 경로 사용
                backup_dir = os.path.dirname(backup_path)
                # 백업 디렉토리 확인 및 생성
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)
                elif not os.path.isdir(backup_dir):
                     print(f"오류: 백업 경로의 디렉토리가 유효하지 않습니다: {backup_dir}")
                     return None

                backup_target_path = backup_path
            else:
                # 지정된 경로가 없으면 기존 로직 사용
                backup_dir = self.get_backup_directory()
                if not backup_dir:
                    print("백업 디렉토리가 설정되지 않았습니다.")
                    return None
                if not self.ensure_backup_directory(): # 백업 디렉토리 유효성 및 쓰기 권한 재확인
                    print(f"백업 디렉토리가 유효하지 않거나 쓰기 권한이 없습니다: {backup_dir}")
                    return None

                # 파일 이름 추출 및 백업 파일명 생성
                file_name = os.path.basename(file_path)
                file_base, file_ext = os.path.splitext(file_name)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_file_name = f"{file_base}_{timestamp}{file_ext}"
                backup_target_path = os.path.join(backup_dir, backup_file_name)

            # 파일 복사
            shutil.copy2(file_path, backup_target_path)

            # 백업 히스토리 업데이트 (기존 파일 경로 기준)
            if file_path not in self.backup_history:
                self.backup_history[file_path] = []
            # 히스토리에는 자동 생성된 이름 규칙과 상관없이 실제 저장된 경로를 저장
            self.backup_history[file_path].append(backup_target_path)

            print(f"백업 완료: {backup_target_path}")
            return backup_target_path

        except Exception as e:
            print(f"백업 오류 발생: {str(e)}")
            return None
    
    def create_automatic_backup(self, file_path: str) -> Optional[str]:
        """
        에셋 로드 시 자동으로 백업을 생성합니다.
        
        Args:
            file_path: 백업할 파일 경로
            
        Returns:
            Optional[str]: 백업 파일 경로 또는 None
        """
        if not os.path.exists(file_path):
            print(f"오류: 백업할 파일을 찾을 수 없습니다 - {file_path}")
            return None
        
        try:
            # 파일 이름 추출
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            # 자동 백업용 파일명 생성 (auto_ 접두사 추가)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_file_name = f"auto_{file_base}_{timestamp}{file_ext}"
            backup_path = os.path.join(self.backup_dir, backup_file_name)
            
            # 로그 추가: 생성 시도하는 백업 경로
            print(f"[DEBUG] 자동 백업 생성 시도: {backup_path}")
            
            # 파일 복사
            shutil.copy2(file_path, backup_path)
            
            # 백업 히스토리 업데이트
            if file_path not in self.backup_history:
                self.backup_history[file_path] = []
            self.backup_history[file_path].append(backup_path)
            
            print(f"자동 백업 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            # 로그 추가: 백업 실패 시 오류
            print(f"[DEBUG] 자동 백업 실패: {str(e)}, 파일 경로: {file_path}")
            print(f"자동 백업 오류 발생: {str(e)}")
            return None
    
    def restore_backup(self, backup_dir, target_path=None):
        """
        백업을 복원합니다.
        
        Args:
            backup_dir: 백업 디렉토리 경로
            target_path: 복원 대상 경로 (None이면 원본 위치로 복원)
            
        Returns:
            bool: 복원 성공 여부
        """
        if not os.path.isdir(backup_dir):
            print(f"백업 디렉토리가 존재하지 않습니다: {backup_dir}")
            return False
            
        # 백업 정보 파일 확인
        info_file = os.path.join(backup_dir, self.BACKUP_INFO_FILE)
        if not os.path.exists(info_file):
            print(f"백업 정보 파일이 존재하지 않습니다: {info_file}")
            return False
            
        # 백업 정보 로드
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
        except Exception as e:
            print(f"백업 정보 파일을 로드할 수 없습니다: {str(e)}")
            return False
            
        # 원본 파일 경로
        original_file = backup_info.get('original_file')
        if not original_file:
            print("백업 정보에 원본 파일 경로가 없습니다.")
            return False
            
        # 백업된 에셋 파일 경로
        file_ext = self._get_file_extension(original_file)
        backup_file = os.path.join(backup_dir, f"backup{file_ext}")
        if not os.path.exists(backup_file):
            print(f"백업 파일이 존재하지 않습니다: {backup_file}")
            return False
        
        try:
            # 복원 대상 경로 결정
            if not target_path:
                # 백업 히스토리에서 원본 경로 찾기
                for original_path, backups in self.backup_history.items():
                    if backup_file in backups:
                        target_path = original_path
                        break
                
                if not target_path:
                    print("오류: 복원 대상 경로를 찾을 수 없습니다.")
                    return False
            
            # 파일 복사
            shutil.copy2(backup_file, target_path)
            
            print(f"복원 완료: {target_path}")
            return True
            
        except Exception as e:
            print(f"복원 오류 발생: {str(e)}")
            return False
    
    def get_backup_history(self, file_path: Optional[str] = None) -> Dict[str, List[str]]:
        """
        백업 히스토리를 반환합니다.
        
        Args:
            file_path: 특정 파일의 백업 히스토리를 조회할 경로 (None이면 전체 히스토리)
            
        Returns:
            Dict: 백업 히스토리 (파일 경로: [백업 경로 목록])
        """
        if file_path:
            if file_path in self.backup_history:
                return {file_path: self.backup_history[file_path]}
            return {}
        
        return self.backup_history
    
    def get_latest_backup(self, file_path: str) -> Optional[str]:
        """
        특정 파일의 최신 백업 경로를 반환합니다.
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            Optional[str]: 최신 백업 파일 경로 또는 None
        """
        if file_path not in self.backup_history or not self.backup_history[file_path]:
            return None
        
        # 가장 최근에 추가된 백업 반환
        return self.backup_history[file_path][-1]
    
    def cleanup_old_backups(self, file_path: str, keep_count: int = 5) -> int:
        """
        오래된 백업 파일을 정리합니다.
        
        Args:
            file_path: 원본 파일 경로
            keep_count: 유지할 최신 백업 수
            
        Returns:
            int: 삭제된 백업 파일 수
        """
        if file_path not in self.backup_history or not self.backup_history[file_path]:
            return 0
        
        backups = self.backup_history[file_path]
        if len(backups) <= keep_count:
            return 0
        
        # 삭제할 백업 파일 목록
        to_delete = backups[:-keep_count]
        deleted_count = 0
        
        # 파일 삭제
        for backup_path in to_delete:
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                    deleted_count += 1
            except Exception as e:
                print(f"백업 파일 삭제 오류: {str(e)}")
        
        # 백업 히스토리 업데이트
        self.backup_history[file_path] = backups[-keep_count:]
        
        return deleted_count
    
    def cleanup_temp_resource_files(self) -> int:
        """
        백업 디렉토리에서 임시 리소스 파일(.resS)을 정리합니다.
        
        Returns:
            int: 삭제된 파일 수
        """
        backup_dir = self.get_backup_directory()
        if not os.path.exists(backup_dir) or not os.path.isdir(backup_dir):
            print(f"백업 디렉토리가 존재하지 않습니다: {backup_dir}")
            return 0
        
        # 임시 파일 패턴 (temp_*.resS 및 sharedassets*.assets.resS)
        patterns = ["temp_*.resS", "sharedassets*.assets.resS"]
        deleted_count = 0
        
        try:
            for pattern in patterns:
                # 해당 패턴과 일치하는 모든 파일 찾기
                for file_name in os.listdir(backup_dir):
                    if fnmatch.fnmatch(file_name, pattern):
                        file_path = os.path.join(backup_dir, file_name)
                        try:
                            # 파일 삭제
                            os.remove(file_path)
                            deleted_count += 1
                            print(f"임시 리소스 파일 삭제: {file_name}")
                        except Exception as e:
                            print(f"파일 삭제 오류: {str(e)} - {file_path}")
            
            return deleted_count
        except Exception as e:
            print(f"임시 리소스 파일 정리 오류: {str(e)}")
            return deleted_count

    def find_initial_backup(self, file_path: str) -> Optional[str]:
        """
        파일 로드 시 생성된 가장 오래된 자동 백업 파일을 찾습니다.
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            Optional[str]: 가장 오래된 자동 백업 파일 경로 또는 None
        """
        backup_dir = self.get_backup_directory()
        # 로그 추가: 검색 대상 디렉토리
        print(f"[DEBUG] 초기 백업 검색 시작 - 디렉토리: {backup_dir}, 원본 파일: {file_path}")
        
        if not os.path.exists(backup_dir) or not os.path.isdir(backup_dir):
            # 로그 추가: 디렉토리 없음
            print(f"[DEBUG] 초기 백업 검색 중단: 백업 디렉토리 없음 ({backup_dir})")
            return None
        
        # 원본 파일 이름 기반으로 자동 백업 패턴 생성
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        backup_pattern = f"auto_{file_base}_*{file_ext}"
        # 로그 추가: 사용할 검색 패턴
        print(f"[DEBUG] 초기 백업 검색 패턴: {backup_pattern}")
        
        potential_backups = []
        try:
            # 로그 추가: 디렉토리 내용 리스팅 시작
            print(f"[DEBUG] 백업 디렉토리 내용 검색 시작...")
            found_files_log = [] # 찾은 파일 로그용 리스트
            for filename in os.listdir(backup_dir):
                if fnmatch.fnmatch(filename, backup_pattern):
                    full_path = os.path.join(backup_dir, filename)
                    found_files_log.append(filename) # 로그용 리스트에 추가
                    # 생성 시간 가져오기 (실패 시 현재 시간)
                    try:
                        creation_time = os.path.getctime(full_path)
                    except OSError:
                        creation_time = time.time()
                    potential_backups.append((full_path, creation_time))
            
            # 로그 추가: 패턴과 일치하는 파일 목록
            if found_files_log:
                print(f"[DEBUG] 패턴과 일치하는 파일 찾음 ({len(found_files_log)}개): {', '.join(found_files_log)}")
            else:
                print("[DEBUG] 패턴과 일치하는 파일 없음")
                
            # 생성 시간 기준으로 오름차순 정렬
            potential_backups.sort(key=lambda x: x[1])
            
            # 가장 오래된 백업 반환
            if potential_backups:
                found_backup_path = potential_backups[0][0]
                # 로그 추가: 찾은 초기 백업 경로
                print(f"[DEBUG] 찾은 초기 백업 파일: {found_backup_path}")
                return found_backup_path
            else:
                # 로그 추가: 최종적으로 초기 백업 못 찾음
                print("[DEBUG] 초기 백업 파일 최종 검색 실패")
            
        except Exception as e:
            print(f"초기 백업 파일 검색 오류: {str(e)}")
            # 로그 추가: 검색 중 예외 발생
            print(f"[DEBUG] 초기 백업 검색 중 예외 발생: {str(e)}")
            
        return None

    def find_latest_save_backup(self, file_path: str) -> Optional[str]:
        """
        파일 저장 시 생성된 가장 최신의 백업 파일을 찾습니다 ('_save_' 포함).
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            Optional[str]: 가장 최신의 저장 백업 파일 경로 또는 None
        """
        backup_dir = self.get_backup_directory()
        print(f"[DEBUG] 최신 저장 백업 검색 시작 - 디렉토리: {backup_dir}, 원본 파일: {file_path}")
        
        if not os.path.exists(backup_dir) or not os.path.isdir(backup_dir):
            print(f"[DEBUG] 최신 저장 백업 검색 중단: 백업 디렉토리 없음 ({backup_dir})")
            return None
        
        # 원본 파일 이름 기반으로 저장 백업 패턴 생성 ('_save_' 포함)
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        backup_pattern = f"{file_base}_save_*{file_ext}"
        print(f"[DEBUG] 최신 저장 백업 검색 패턴: {backup_pattern}")
        
        potential_backups = []
        try:
            print(f"[DEBUG] 백업 디렉토리 내용 검색 시작...")
            found_files_log = []
            for filename in os.listdir(backup_dir):
                if fnmatch.fnmatch(filename, backup_pattern):
                    full_path = os.path.join(backup_dir, filename)
                    found_files_log.append(filename)
                    try:
                        creation_time = os.path.getctime(full_path)
                    except OSError:
                        creation_time = time.time()
                    potential_backups.append((full_path, creation_time))
            
            if found_files_log:
                print(f"[DEBUG] 패턴과 일치하는 저장 백업 파일 찾음 ({len(found_files_log)}개): {', '.join(found_files_log)}")
            else:
                print("[DEBUG] 패턴과 일치하는 저장 백업 파일 없음")
                
            # 생성 시간 기준으로 *내림차순* 정렬 (최신 파일이 먼저 오도록)
            potential_backups.sort(key=lambda x: x[1], reverse=True)
            
            # 가장 최신 백업 반환
            if potential_backups:
                latest_backup_path = potential_backups[0][0]
                print(f"[DEBUG] 찾은 최신 저장 백업 파일: {latest_backup_path}")
                return latest_backup_path
            else:
                print("[DEBUG] 최신 저장 백업 파일 최종 검색 실패")
                
        except Exception as e:
            print(f"최신 저장 백업 파일 검색 오류: {str(e)}")
            print(f"[DEBUG] 최신 저장 백업 검색 중 예외 발생: {str(e)}")
            
        return None
