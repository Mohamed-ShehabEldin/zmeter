import pyvisa
import time


class SP150_Hardware():
    def __init__(self):
        self.rm = None
        self.inst = None
        self.last_nm = 0.0

    def connect(self, address='GPIB1::11::INSTR'):
        if self.inst is not None:
            return

        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(address)
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\r'
            self.inst.timeout = 10000
        except Exception as exc:
            self.disconnect()
            raise RuntimeError(f"Could not connect SP150 at {address}: {exc}") from exc

    def ensure_connected(self):
        if self.inst is None:
            self.connect()

    def set_wavelength(self, nm):
        self.ensure_connected()
        if not (isinstance(nm, int) or isinstance(nm, float)):
            raise ValueError('SP150 wavelength should be a number')
        if nm < 0 or nm > 3000:
            raise ValueError('SP150 wavelength range is 0 to 3000 nm')
        if nm < self.get_wavelength():
            self.inst.write(f'{nm:.2f} <GOTO>')
            time.sleep(10)
        else:
            self.inst.write(f'{nm:.2f} <GOTO>')
            time.sleep(1)
        self.last_nm = nm

    def get_wavelength(self):
        self.ensure_connected()
        try:
            read = self.inst.query("?NM", delay=1)
            self.last_nm = float(str(read).strip())
        except Exception as exc:
            raise RuntimeError(f"Could not read SP150 wavelength: {exc}") from exc
        return self.last_nm

    def disconnect(self):
        if self.inst is not None:
            try:
                self.inst.close()
            except Exception:
                pass
            self.inst = None

        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
        self.rm = None

        # if 'ok' in read:
        #     nm = float(read.split('ok')[0].split('?NM ')[1])
        #     return nm
        # else:
        #     return -1


if __name__ == "__main__":
    s = SP150_Hardware()
    import numpy as np
    # nms=np.linspace(400,700,61)
    nms=[633]
    for nm in nms:
        print(nm)
        s.set_wavelength(nm)
