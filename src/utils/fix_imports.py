import os
import sys
from PyQt5.QtWidgets import QTimer

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.image_editor import ImageEditor


# 누락된 QTimer import 추가
def fix_image_editor():
    """
    ImageEditor 클래스의 QTimer import 문제 수정
    """
    file_path = os.path.join(os.path.dirname(__file__), 'image_editor.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # QTimer import 추가
    if 'from PyQt5.QtCore import Qt, pyqtSignal' in content:
        content = content.replace(
            'from PyQt5.QtCore import Qt, pyqtSignal',
            'from PyQt5.QtCore import Qt, pyqtSignal, QTimer'
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("ImageEditor 클래스의 QTimer import 문제가 수정되었습니다.")
    else:
        print("수정이 필요하지 않습니다.")


if __name__ == "__main__":
    fix_image_editor()
