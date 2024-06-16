import sys
from PyQt5.QtWidgets import QApplication 
from GUI import FileSystemGUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = FileSystemGUI()
    ex.show()
    sys.exit(app.exec_())
