import sys
from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow
from controllers.app_controller import AppController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Crear componentes MVC
    window = MainWindow()
    controller = AppController(window)
    
    window.show()
    sys.exit(app.exec_())