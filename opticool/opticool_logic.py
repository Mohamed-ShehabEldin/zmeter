from PyQt6 import QtCore
from .opticool_hardware import OptiCool_Hardware
import time
import numpy as np


class OptiCoolLogic(QtCore.QThread):
    sig_last_temperature = QtCore.pyqtSignal(object)
    sig_last_field = QtCore.pyqtSignal(object)
    sig_setting_temperature = QtCore.pyqtSignal(object)
    sig_setting_field = QtCore.pyqtSignal(object)

    hardware = OptiCool_Hardware()
    job = ''
    setpoint_temperature = 0
    setpoint_tesla = 0

    def __init__(self):
        QtCore.QThread.__init__(self)

    def set_temperature(self, val):
        """Scan-facing temperature setter in Kelvin."""
        self.setpoint_temperature = float(val)
        self._apply_temperature()

    def set_temperature_stable(self, val):
        """Scan-facing temperature setter in Kelvin; waits until stable."""
        self.setpoint_temperature = float(val)
        self._apply_temperature_stable()

    def set_field(self, val):
        """Scan-facing field setter in Tesla."""
        self.setpoint_tesla = float(val)
        self._apply_field()

    def set_field_stable(self, val):
        """Scan-facing field setter in Tesla; waits until field is holding."""
        self.setpoint_tesla = float(val)
        self._apply_field_stable()

    def _apply_temperature(self):
        self.sig_setting_temperature.emit('setting...')
        self.hardware.set_temperature(self.setpoint_temperature)
        self.get_temperature()

    def _apply_temperature_stable(self):
        self._apply_temperature()
        read_arr = np.zeros(50)
        while True:
            [status, val, TemperatureStatusString] = self.hardware.get_temperature()
            self.sig_last_temperature.emit(val)
            read_arr[-1] = val
            read_arr[0:-1] = read_arr[1::]
            
            # print(read_arr)
            # print(np.std(read_arr))
            if TemperatureStatusString in ['Stable']:
                break
            elif np.std(read_arr) < 0.0001:
                break
            time.sleep(0.1)

    def get_temperature(self):
        [status, val, TemperatureStatus] = self.hardware.get_temperature()
        self.sig_last_temperature.emit(val)
        return val

    def _apply_field(self):
        self.sig_setting_field.emit('setting...')
        self.hardware.set_field(self.setpoint_tesla * 10000)

    def _apply_field_stable(self):
        self._apply_field()
        while True:
            [status, val, FieldStatusString] = self.hardware.get_field()
            self.sig_last_field.emit(val)
            if FieldStatusString == 'Holding':
                break
            time.sleep(0.001)

    def set_SET_field_stable(self, *args):
        """Backward-compatible alias for old Mohamed scan code.

        The varargs signature intentionally keeps this legacy name out of the
        new scan-channel discovery, which expects exactly one positional arg.
        """
        if not args:
            raise TypeError("set_SET_field_stable requires a Tesla value")
        val = args[0]
        self.set_field_stable(val)

    def get_field(self):
        [status, val, FieldStatus] = self.hardware.get_field()
        self.sig_last_field.emit(val)
        return val / 10000

    def run(self):
        try:
            if self.job == "set_temperature":
                self._apply_temperature()

            elif self.job == "set_temperature_stable":
                self._apply_temperature_stable()

            elif self.job == "set_field":
                self._apply_field()

            elif self.job == "set_field_stable":
                self._apply_field_stable()

            elif self.job == "get_temperature":
                self.get_temperature()

            elif self.job == "get_field":
                self.get_field()

        finally:
            self.job = ''


OptiCool_Logic = OptiCoolLogic


if __name__ == "__main__":
    o = OptiCoolLogic()
    o.setpoint_tesla = 1e-3
    o._apply_field()
    # o.setpoint_temperature = 1.55
    # o.set_temperature()
