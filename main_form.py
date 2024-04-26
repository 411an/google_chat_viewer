import sys
from PyQt5.QtWidgets import QApplication
from window_model import MainWindow
from messages_model import resource_path
from PyQt5.QtGui import QIcon

if __name__ == "__main__":
    # Should help for open files from a local drive
    sys.argv.append("--disable-web-security")
    
    app = QApplication(sys.argv)

    icon = resource_path('GCR.ico')
    app.setWindowIcon(QIcon(icon))
    main_form = MainWindow()
    main_form.show()
    
    sys.exit(app.exec_())
