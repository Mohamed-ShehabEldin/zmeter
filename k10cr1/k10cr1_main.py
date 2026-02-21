from PyQt6 import QtWidgets, uic, QtCore
import sys
from k10cr1.k10cr1_logic import K10CR1Logic
import numpy as np
import pyqtgraph as pg


class K10CR1(QtWidgets.QWidget):
    def __init__(self):
        super(K10CR1, self).__init__()
        uic.loadUi(r"k10cr1/k10cr1.ui", self)
        self.logic = K10CR1Logic()
        self.connect_sig_slot()
        self.lineEdit.setText("55000923")

    def connect_sig_slot(self):
        self.connect_button.clicked.connect(self.connect)
        self.disconnect_button.clicked.connect(self.disconnect)
        self.go_button.clicked.connect(self.move_absolute)
        self.home_button.clicked.connect(self.home)
        self.logic.sig_last_pos.connect(self.update_pos)
        self.logic.sig_info.connect(self.update_info)
        self.logic.sig_connect.connect(self.set_on_off)

        self.pos_to_go_doubleSpinBox.valueChanged.connect(
            self.pos_to_go_changed)
        self.pos_to_go_device_unit_spinBox.valueChanged.connect(
            self.pos_to_go_device_unit_changed)

    def pos_to_go_changed(self, deg):
        self.pos_to_go_device_unit_spinBox.blockSignals(True)
        self.pos_to_go_device_unit_spinBox.setValue(int(deg * 49152000 / 360))
        self.pos_to_go_device_unit_spinBox.blockSignals(False)

    def pos_to_go_device_unit_changed(self, dev_u):
        self.pos_to_go_doubleSpinBox.blockSignals(True)
        self.pos_to_go_doubleSpinBox.setValue(dev_u * 360 / 49152000)
        self.pos_to_go_doubleSpinBox.blockSignals(False)

    def set_on_off(self, status):
        if status:
            self.label_on_off.setText("ON")
        else:
            self.label_on_off.setText("OFF")

    def update_pos(self, pos):
        deg = "%.3f" % float(pos * 360 / 49152000)
        self.last_pos_label.setText(f"last positon: {deg} deg <-- {pos}")

    def update_info(self, info):
        #self.info_label.setText(info)
        print(info)
    def connect(self):
        self.logic.do_connect = True
        serial = self.lineEdit.text()
        self.logic.set_serial(serial)
        self.logic.start()

    def disconnect(self):
        if self.logic.is_connected is True:
            self.logic.do_disconnect = True
            self.logic.start()

    def home(self):
        self.logic.do_home = True
        self.logic.start()

    def move_absolute(self):
        pos = self.pos_to_go_device_unit_spinBox.value()
        self.logic.set_destination(pos)
        self.logic.do_move_absolute = True
        self.logic.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = K10CR1()
    window.show()
    window.lineEdit.setText("55000923")
    app.exec_()
