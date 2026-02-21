from . import k10cr1_hardware as ism
from time import sleep
from ctypes import (
    c_short,
    c_char_p,
    byref,
    c_int,
)
from PyQt6 import QtCore


class K10CR1Logic(QtCore.QThread):
    sig_last_pos = QtCore.pyqtSignal(object)
    sig_info = QtCore.pyqtSignal(object)
    sig_connect = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        # self.serial_no = c_char_p(bytes("55243324", "utf-8"))
        self.channel = c_short(1)

        self.is_connected = False
        self.destination = 0
        self.last_deg=0
        self.reset_flags()

    def set_serial(self, serial):
        self.serial_no = c_char_p(bytes(serial, "utf-8"))

    def pass_info(self, info):
        self.sig_info.emit(info)
        # print(info)

    def reset_flags(self):
        self.do_connect = False
        self.do_disconnect = False
        self.do_move_absolute = False
        self.do_home = False

    def connect(self):
        if not ism.TLI_BuildDeviceList() == 0:
            self.pass_info("Can't build device list")
            return False
        if not ism.ISC_Open(self.serial_no) == 0:
            self.pass_info("Can't open k10cr1.")
            return False
        hw_info = ism.TLI_HardwareInformation()  # container for hw info
        err = ism.ISC_GetHardwareInfoBlock(
            self.serial_no, byref(hw_info))
        if err != 0:
            self.pass_info(f"Error getting HW Info Block. Error Code: {err}")
        info = f"Serial No: {hw_info.serialNumber}\nModel No: {hw_info.modelNumber}\nFirmware Version: {hw_info.firmwareVersion}\nNumber of  Channels: {hw_info.numChannels}\nType: {hw_info.type}"
        self.pass_info(info)
        self.sig_connect.emit(True)
        self.is_connected = True

        return True

    def disconnect(self):
        self.pass_info(f"Closing connection {ism.ISC_Close(self.serial_no)}")
        self.sig_connect.emit(False)
        self.is_connected = False

    def home_original(self):
        homing_inf = ism.MOT_HomingParameters()  # container
        self.pass_info(
            f"Setting homing vel {ism.ISC_SetHomingVelocity(self.serial_no, ism.c_uint(20000000))}")
        ism.ISC_RequestHomingParams(self.serial_no)
        err = ism.ISC_GetHomingParamsBlock(
            self.serial_no, byref(homing_inf))

        if err != 0:
            self.pass_info(
                f"Error getting Homing Info Block. Error Code: {err}")
            return False
        self.pass_info(f"Direction: {homing_inf.direction}")
        self.pass_info(f"Limit Sw: {homing_inf.limitSwitch}")
        self.pass_info(f"Velocity: {homing_inf.velocity}")
        self.pass_info(f"Offset Dist: {homing_inf.offsetDistance}")

        ism.ISC_Home(self.serial_no)

    def home(self):

        milliseconds = c_int(50)

        self.pass_info(
            f"Starting polling {ism.ISC_StartPolling(self.serial_no, milliseconds)}")
        self.pass_info(
            f"Clearing message queue {ism.ISC_ClearMessageQueue(self.serial_no)}")
        sleep(0.2)

        homing_inf = ism.MOT_HomingParameters()  # container
        self.pass_info(
            f"Setting homing vel {ism.ISC_SetHomingVelocity(self.serial_no, ism.c_uint(20000000))}")
        ism.ISC_RequestHomingParams(self.serial_no)
        err = ism.ISC_GetHomingParamsBlock(
            self.serial_no, byref(homing_inf))

        if err != 0:
            self.pass_info(
                f"Error getting Homing Info Block. Error Code: {err}")
            return False
        self.pass_info(f"Direction: {homing_inf.direction}")
        self.pass_info(f"Limit Sw: {homing_inf.limitSwitch}")
        self.pass_info(f"Velocity: {homing_inf.velocity}")
        self.pass_info(f"Offset Dist: {homing_inf.offsetDistance}")

        ism.ISC_Home(self.serial_no)
        sleep(0.2)
        pos = int(ism.ISC_GetPosition(self.serial_no))
        sleep(0.2)
        self.pass_info(f"Current pos_a0: {pos}")
        # while pos != 0:
        while abs(pos - 0) > 2:
            sleep(0.05)
            pos = int(ism.ISC_GetPosition(self.serial_no))
            self.pass_info(f"Current pos_a: {pos}")
            self.last_deg=pos/ 49152000* 360
            self.sig_last_pos.emit(pos)

        self.pass_info(
            f"Stopping polling {ism.ISC_StopPolling(self.serial_no)}")

    def set_destination(self, destination):
        self.destination = destination

    def set_absolute(self, val):
        pos = val * 49152000 / 360
        self.set_destination(pos)
        self.move_absolute()


    def move_absolute(self):
        milliseconds = c_int(50)

        self.pass_info(
            f"Starting polling {ism.ISC_StartPolling(self.serial_no, milliseconds)}")
        self.pass_info(
            f"Clearing message queue {ism.ISC_ClearMessageQueue(self.serial_no)}")
        sleep(0.2)

        move_to = int(self.destination)
        self.pass_info(
            f"Setting Absolute Position {ism.ISC_SetMoveAbsolutePosition(self.serial_no, c_int(move_to))}")
        sleep(0.2)

        self.pass_info(
            f"Moving to {move_to}  {ism.ISC_MoveAbsolute(self.serial_no)}")
        sleep(0.2)
        pos = int(ism.ISC_GetPosition(self.serial_no))
        sleep(0.2)
        self.pass_info(f"Current pos_b0: {pos}")
        # while not pos == move_to:
        while abs(pos - move_to) > 2:
            sleep(0.05)
            pos = int(ism.ISC_GetPosition(self.serial_no))
            self.last_deg=pos/ 49152000* 360
            self.pass_info(f"Current pos_b: {pos}")
            self.sig_last_pos.emit(pos)

        self.pass_info(
            f"Stopping polling {ism.ISC_StopPolling(self.serial_no)}")

    def get_deg(self):
        pos = int(ism.ISC_GetPosition(self.serial_no))
        return (pos/ 49152000* 360 )
    
    def run(self):
        if self.do_connect:
            self.connect()
        elif self.do_disconnect:
            self.disconnect()
        elif self.do_move_absolute:
            self.move_absolute()
        elif self.do_home:
            self.home()
        self.reset_flags()


if __name__ == "__main__":
    a = K10CR1Logic()
    a.set_serial("55000923")
    a.connect()
    deg = 10
    dev_unit = deg / 360 * 49152000
    a.set_destination(dev_unit)
    a.move_absolute()
    a.home()
    a.disconnect()
