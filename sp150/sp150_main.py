import sys
import os

from PyQt6 import QtWidgets, uic

try:
    from .sp150_logic import SP150_Logic
except ImportError:
    from sp150_logic import SP150_Logic


class SP150(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "sp150.ui")
        uic.loadUi(ui_path, self)

        self.logic = SP150_Logic()
        self.connect_sig_slot()
        self.label_3.setText("ready")

    def connect_sig_slot(self):
        self.pushButton.clicked.connect(self.set_wavelength)
        self.pushButton_3.clicked.connect(self.get_wavelength)

        self.logic.sig_last_wavelength.connect(self.update_wavelength)
        self.logic.sig_setting_wavelength.connect(self.setting_wavelength)
        self.logic.sig_connected.connect(self.update_status)

    def set_wavelength(self):
        try:
            wavelength = float(self.lineEdit.text())
        except ValueError:
            self.label_3.setText("enter a numeric wavelength")
            return

        self.logic.stop()
        self.logic.setpoint_wavelength = wavelength
        self.logic.job = "set_wavelength"
        self.logic.start()

    def get_wavelength(self):
        self.logic.stop()
        self.logic.job = "get_wavelength"
        self.logic.start()

    def update_wavelength(self, value):
        self.label_3.setText(f"last read: {value:.2f} nm")

    def setting_wavelength(self, text):
        self.label_3.setText(str(text))

    def update_status(self, text):
        self.label_3.setText(str(text))

    def terminate_dev(self):
        self.logic.disconnect()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SP150()
    window.show()
    sys.exit(app.exec())
