STYLE_SHEET = """
/* 파스텔 테마 기본 스타일 */
QWidget {
    background-color: #E3E5FA; /* 파스텔 라벤더/블루 */
    color: #424242; /* 진한 회색 */
    font-family: "맑은 고딕", "Malgun Gothic", "Arial", sans-serif;
    font-size: 9pt;
}

/* 메인 윈도우 */
QMainWindow {
    background-color: #E3E5FA;
}

QMainWindow::separator {
    background-color: #DADADA;
    width: 1px;
    height: 1px;
}

/* 도킹 위젯 */
QDockWidget {
    background-color: #D4D6F0;
    border-radius: 8px;
    border: 1px solid #DADADA;
    padding: 4px;
}

QDockWidget::title {
    background-color: #B8B5E1;
    padding: 5px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

/* 탭 위젯 */
QTabWidget::pane {
    border: 1px solid #DADADA;
    border-radius: 8px;
    background-color: #E3E5FA;
    padding: 4px;
}

QTabBar::tab {
    background: #D4D6F0;
    border: 1px solid #DADADA;
    border-bottom: none; 
    padding: 8px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 100px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #B5C7E1;
    border-color: #DADADA;
    border-bottom-color: #B5C7E1;
    margin-bottom: -1px;
}

QTabBar::tab:!selected {
    margin-top: 2px;
}

QTabBar::tab:hover {
    background: #C5D5E9;
}

/* 툴바 */
QToolBar {
    background: #D4D6F0;
    border: none;
    padding: 5px;
    spacing: 3px;
    border-radius: 8px;
}

/* 툴바 버튼 */
QToolButton {
    background-color: #A7C7E7;
    border: 1px solid transparent;
    padding: 5px;
    border-radius: 6px;
}

QToolButton:hover {
    background-color: #96B6D9;
    border: 1px solid #DADADA;
}

QToolButton:pressed {
    background-color: #B5C7E1;
    padding: 6px 4px 4px 6px; /* 눌림 효과 */
}

/* 푸시 버튼 */
QPushButton {
    background-color: #A7C7E7;
    border: 1px solid #DADADA;
    padding: 8px 15px;
    border-radius: 6px;
    min-width: 80px;
    color: #424242;
}

QPushButton:hover {
    background-color: #96B6D9;
}

QPushButton:pressed {
    background-color: #B5C7E1;
    padding: 9px 14px 7px 16px; /* 눌림 효과 */
}

QPushButton:disabled {
    background-color: #E8E8E8;
    color: #A0A0A0;
    border: 1px solid #DADADA;
}

/* 입력 필드 */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #DADADA;
    border-radius: 6px;
    padding: 5px;
    selection-background-color: #B5C7E1;
}

QLineEdit:focus {
    border: 1px solid #B8B5E1;
}

/* 텍스트 에디터 */
QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #DADADA;
    border-radius: 6px;
    padding: 5px;
    selection-background-color: #B5C7E1;
}

QTextEdit:focus {
    border: 1px solid #B8B5E1;
}

/* 스플리터 핸들 */
QSplitter::handle {
    background-color: #DADADA;
}

QSplitter::handle:horizontal {
    width: 5px;
    border-radius: 2px;
}

QSplitter::handle:vertical {
    height: 5px;
    border-radius: 2px;
}

QSplitter::handle:hover {
    background-color: #B8B5E1;
}

/* 메뉴바 */
QMenuBar {
    background-color: #D4D6F0;
    border-bottom: 1px solid #DADADA;
    padding: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
    border-radius: 6px;
}

QMenuBar::item:selected {
    background: #B5C7E1;
}

QMenuBar::item:pressed {
    background: #96B6D9;
}

/* 메뉴 */
QMenu {
    background-color: #E3E5FA;
    border: 1px solid #DADADA;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 25px 6px 20px;
    border-radius: 4px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #B5C7E1;
}

QMenu::separator {
    height: 1px;
    background-color: #DADADA;
    margin: 4px 10px;
}

QMenu::indicator {
    width: 15px;
    height: 15px;
}

/* 상태바 */
QStatusBar {
    background-color: #D4D6F0;
    border-top: 1px solid #DADADA;
    padding: 3px;
    color: #424242;
}

QStatusBar::item {
    border: none;
}

/* 스크롤바 */
QScrollBar:vertical {
    border: none;
    background: #E3E5FA;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #B8B5E1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #A7A3D1;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #E3E5FA;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #B8B5E1;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #A7A3D1;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* 리스트 및 트리 위젯 */
QListWidget, QTreeWidget {
    background-color: #E3E5FA;
    border: 1px solid #DADADA;
    border-radius: 6px;
    padding: 5px;
}

QListWidget::item, QTreeWidget::item {
    padding: 5px;
    border-radius: 4px;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #B5C7E1;
}

QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #D4D6F0;
}

/* 콤보박스 */
QComboBox {
    background-color: #A7C7E7;
    border: 1px solid #DADADA;
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 100px;
}

QComboBox:hover {
    background-color: #96B6D9;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: right;
    width: 20px;
    border-left: 1px solid #DADADA;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
    image: url(design/icons/down_arrow.png);
}

QComboBox QAbstractItemView {
    background-color: #E3E5FA;
    border: 1px solid #DADADA;
    border-radius: 6px;
    selection-background-color: #B5C7E1;
}

/* 그룹박스 */
QGroupBox {
    border: 1px solid #DADADA;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0px 5px;
    background-color: #E3E5FA;
}

/* 체크박스 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #DADADA;
    border-radius: 4px;
}

QCheckBox::indicator:unchecked {
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #B8B5E1;
    image: url(design/icons/check.png);
}

QCheckBox::indicator:hover {
    border: 1px solid #B8B5E1;
}

/* 라디오 버튼 */
QRadioButton {
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #DADADA;
    border-radius: 9px;
}

QRadioButton::indicator:unchecked {
    background-color: #FFFFFF;
}

QRadioButton::indicator:checked {
    background-color: #FFFFFF;
    image: url(design/icons/radio_checked.png);
}

QRadioButton::indicator:hover {
    border: 1px solid #B8B5E1;
}

/* 프로그레스 바 */
QProgressBar {
    border: 1px solid #DADADA;
    border-radius: 5px;
    text-align: center;
    background-color: #FFFFFF;
}

QProgressBar::chunk {
    background-color: #B8B5E1;
    border-radius: 4px;
}

/* 슬라이더 */
QSlider::groove:horizontal {
    border: 1px solid #DADADA;
    height: 6px;
    background: #FFFFFF;
    margin: 0px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #A7C7E7;
    border: 1px solid #DADADA;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #96B6D9;
}

/* 메시지 박스 */
QMessageBox {
    background-color: #E3E5FA;
}

QMessageBox QPushButton {
    min-width: 70px;
    min-height: 25px;
}
""" 