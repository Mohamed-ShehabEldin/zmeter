#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt6 import QtWidgets, uic
import serial.tools.list_ports
from nidaq.nidaq_hardware import NIDAQHardWare
from auto_focus.autofocus_logic import stepper_and_galvo_xyz, autofocus_logic

class autofocus_main(QtWidgets.QWidget):
    def __init__(self):
        super(autofocus_main, self).__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "autofocus_GUI.ui")
        uic.loadUi(ui_path, self)
        self.xyz_sys = None
        self.logic = autofocus_logic(self.xyz_sys) ## that specific logic instance will be used in the scan ##

        # connecting to the COM
        for port in serial.tools.list_ports.comports():
            self.comboComPort.addItem(port.device)
        self.connect_com_btn.clicked.connect(self.connect_sys)
        self.disconnect_com_btn.clicked.connect(self.disconnect_sys)

        self.update_settings_btn.clicked.connect(self.update_settings)
        self.btnAutofocus.clicked.connect(self.start_autofocus)
        self.update_settings()

    def set_xyz_sys(self, xyz_sys):
        self.xyz_sys = xyz_sys
        self.logic.xyz_sys = xyz_sys

    def _set_status(self, text):
        if hasattr(self, "label_status"):
            self.label_status.setText(text)
        elif hasattr(self, "ard_label_status"):
            self.ard_label_status.setText(text)

    def connect_sys(self):
        if self.logic.xyz_sys is None:
            self._set_status("No system")
            return
        self.logic.xyz_sys.com_port = self.comboComPort.currentText()
        try:
            self.logic.xyz_sys.connect_system()
            self._set_status("Connected")
        except Exception as e:
            self._set_status("Error")
            print(e)

    def disconnect_sys(self):
        if self.logic.xyz_sys is None:
            self._set_status("No system")
            return
        try:
            self.logic.xyz_sys.disconnect_system()
            self._set_status("Disconnected")
        except Exception as e:
            self._set_status("Error")
            print(e)

    def update_settings(self):
        ''' Update the settings from the GUI inputs to the logic class. '''
        #the daq instance should be passed directly to the class to avoid conflics
        # self.logic.xyz_sys.ao_x = self.txtGalvoX.toPlainText().strip() # I don't have buttons for these yet
        # self.logic.xyz_sys.ao_y = self.txtGalvoY.toPlainText().strip()
        # self.logic.xyz_sys.ai = self.txtPDIn.toPlainText().strip()
        if self.xyz_sys:
            self.logic.xyz_sys.motor_rpm = self.spinMotorRPM.value()
        self.logic.initial_z_step = self.spinInitialStep.value()
        self.logic.threshold_z_step = self.spinThreshold.value()
        #self.logic.threshold_metric_step = self.spinThresholdMetric.value() #I have no function for this now
        self.logic.x_center = self.spinXCenter.value()
        self.logic.y_center = self.spinYCenter.value()
        self.logic.x_range = self.spinXRange.value()
        self.logic.y_range = self.spinYRange.value()
        self.logic.x_pts = int(self.spinXPts.value())
        self.logic.y_pts = int(self.spinYPts.value())
        self.logic.save_dir = self.txtSaveDir.toPlainText().strip()
        if hasattr(self, "kernel_spin"):
            self.logic.kernel_size = int(self.kernel_spin.value())
        if hasattr(self, "sigma_spin"):
            self.logic.sigma = float(self.sigma_spin.value())
        if hasattr(self, "cut"):
            self.logic.cut = int(self.cut.value())

    def start_autofocus(self): 
        self.update_settings()
        self.logic.set_AutoFocus()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    daq = NIDAQHardWare()
    xyz = stepper_and_galvo_xyz(daq)
    window = autofocus_main()
    window.set_xyz_sys(xyz)
    window.show()
    sys.exit(app.exec_())
