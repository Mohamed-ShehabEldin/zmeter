from PyQt6 import QtCore

try:
    from .sp150_hardware import SP150_Hardware
except ImportError:
    from sp150_hardware import SP150_Hardware


class SP150_Logic(QtCore.QThread):
    sig_last_wavelength = QtCore.pyqtSignal(object)
    sig_setting_wavelength = QtCore.pyqtSignal(object)
    sig_connected = QtCore.pyqtSignal(object)

    def __init__(self, address="GPIB1::11::INSTR"):
        super().__init__()
        self.address = address
        self.hardware = SP150_Hardware()
        self.connected = False
        self.reject_signal = False
        self.job = ""
        self.setpoint_wavelength = 0

    def connect_visa(self, address=None):
        if address:
            self.address = address
        self.hardware.connect(self.address)
        self.connected = True
        self.sig_connected.emit(f"connected to {self.address}")

    def ensure_connected(self):
        if not self.connected:
            self.connect_visa(self.address)

    def set_wavelength(self, value=None):
        if value is not None:
            self.setpoint_wavelength = value
        self.ensure_connected()
        self.sig_setting_wavelength.emit("setting wavelength...")
        self.hardware.set_wavelength(self.setpoint_wavelength)
        return self.get_wavelength()

    def get_wavelength(self):
        self.ensure_connected()
        wavelength = self.hardware.get_wavelength()
        self.sig_last_wavelength.emit(wavelength)
        return wavelength

    def disconnect(self):
        self.reject_signal = True
        self.job = ""

        if self.isRunning():
            self.wait()

        self.hardware.disconnect()
        if self.connected:
            self.connected = False
            self.sig_connected.emit("disconnected")
        self.reject_signal = False

    def stop(self):
        self.reject_signal = True
        self.quit()
        self.wait()
        self.reject_signal = False

    def run(self):
        if self.reject_signal:
            return

        if self.job:
            fn = getattr(self, self.job, None)
            if callable(fn):
                try:
                    fn()
                except Exception as exc:
                    self.sig_setting_wavelength.emit(f"sp150 error: {exc}")
            self.job = ""


if __name__ == "__main__":
    p = SP150_Logic()
    p.setpoint_wavelength = 700
    print(p.set_wavelength())
