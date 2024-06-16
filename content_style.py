from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QPushButton,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt


class FileContentDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        content_widget = QLabel(content, scroll_area)
        content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        content_widget.setWordWrap(True)
        content_widget.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()
        self.full_screen_button = QPushButton("Full Screen", self)
        self.full_screen_button.clicked.connect(self.toggle_full_screen)
        button_layout.addWidget(self.full_screen_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.resize(600, 400)

    def toggle_full_screen(self):
        if self.isFullScreen():
            self.showNormal()
            self.full_screen_button.setText("Full Screen")
        else:
            self.showFullScreen()
            self.full_screen_button.setText("Exit Full Screen")
