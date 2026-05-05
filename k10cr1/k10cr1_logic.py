from . import k10cr1_hardware as ism
from time import sleep
from collections import deque
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

    COUNTS_PER_REVOLUTION = 49152000
    POSITION_TOLERANCE = 10
    POLL_INTERVAL_MS = 50
    MAX_MOVE_POLLS = 1000
    MAX_HOME_POLLS = 1000
    STUCK_READS = 5

    def __init__(self):
        QtCore.QThread.__init__(self)
        # self.serial_no = c_char_p(bytes("55243324", "utf-8"))
        self.channel = c_short(1)

        self.is_connected = False
        self.destination = 0
        self.last_deg = 0
        self.reset_flags()

    def set_serial(self, serial):
        self.serial_no = c_char_p(bytes(serial, "utf-8"))

    def assign_serial(self, serial):
        self.set_serial(serial)

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
        self.configure_velocity()
        self.sig_connect.emit(True)
        self.is_connected = True

        return True

    def disconnect(self):
        self.pass_info(f"Closing connection {ism.ISC_Close(self.serial_no)}")
        self.sig_connect.emit(False)
        self.is_connected = False

    def configure_velocity(self):
        inf = ism.MOT_VelocityParameters()
        ism.ISC_GetVelParamsBlock(self.serial_no, byref(inf))
        self.pass_info(
            f"Current velocity: min={inf.minVelocity}, acc={inf.acceleration}, max={inf.maxVelocity}"
        )

        inf.minVelocity = 0
        inf.acceleration = 15020
        inf.maxVelocity = 73300335
        err = ism.ISC_SetVelParamsBlock(self.serial_no, byref(inf))
        self.pass_info(f"Setting velocity {err}")

    def _start_polling(self):
        milliseconds = c_int(self.POLL_INTERVAL_MS)
        self.pass_info(
            f"Starting polling {ism.ISC_StartPolling(self.serial_no, milliseconds)}")
        self.pass_info(
            f"Clearing message queue {ism.ISC_ClearMessageQueue(self.serial_no)}")
        sleep(0.2)

    def _stop_polling(self):
        self.pass_info(
            f"Stopping polling {ism.ISC_StopPolling(self.serial_no)}")

    def _read_position(self, label="Current pos"):
        pos = int(ism.ISC_GetPosition(self.serial_no))
        self.last_deg = pos / self.COUNTS_PER_REVOLUTION * 360
        self.pass_info(f"{label}: {pos}")
        self.sig_last_pos.emit(pos)
        return pos

    def _is_at_target(self, pos, target):
        direct_error = abs(pos - target)
        wrap_error = min(
            (pos - target) % self.COUNTS_PER_REVOLUTION,
            (target - pos) % self.COUNTS_PER_REVOLUTION,
        )
        return min(direct_error, wrap_error) <= self.POSITION_TOLERANCE

    def home(self):
        self._start_polling()

        try:
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
            last_positions = deque(maxlen=self.STUCK_READS)
            for _ in range(self.MAX_HOME_POLLS):
                pos = self._read_position("Current pos")
                if abs(pos) <= self.POSITION_TOLERANCE:
                    self.pass_info("Home complete.")
                    break
                last_positions.append(pos)
                if len(last_positions) == last_positions.maxlen and len(set(last_positions)) == 1:
                    self.pass_info(f"Position unchanged for {self.STUCK_READS} reads. Stopping home wait.")
                    break
                sleep(self.POLL_INTERVAL_MS / 1000)
            else:
                self.pass_info("Home wait limit exceeded. Stopping home wait.")
        finally:
            self._stop_polling()

    def set_destination(self, destination):
        self.destination = int(destination)

    def set_absolute(self, val):
        pos = val * self.COUNTS_PER_REVOLUTION / 360
        self.set_destination(pos)
        self.move_absolute()

    def assign_target(self, target):
        self.set_absolute(target)

    def set_angle(self, angle):
        self.set_absolute(angle)

    def move_absolute(self):
        self._start_polling()

        try:
            move_to = int(self.destination)
            self.pass_info(
                f"Setting Absolute Position {ism.ISC_SetMoveAbsolutePosition(self.serial_no, c_int(move_to))}")
            sleep(0.2)

            self.pass_info(
                f"Moving to {move_to}  {ism.ISC_MoveAbsolute(self.serial_no)}")
            sleep(0.2)
            last_positions = deque(maxlen=self.STUCK_READS)
            reached_count = 0

            for _ in range(self.MAX_MOVE_POLLS):
                pos = self._read_position("Current pos")
                if self._is_at_target(pos, move_to):
                    reached_count += 1
                    if reached_count >= 3:
                        self.pass_info("Reached target.")
                        break
                else:
                    reached_count = 0

                last_positions.append(pos)
                if len(last_positions) == last_positions.maxlen and len(set(last_positions)) == 1:
                    self.pass_info(f"Position unchanged for {self.STUCK_READS} reads. Stopping move wait.")
                    break
                sleep(self.POLL_INTERVAL_MS / 1000)
            else:
                self.pass_info("Move wait limit exceeded. Stopping move wait.")
        finally:
            self._stop_polling()

    def get_deg(self):
        pos = int(ism.ISC_GetPosition(self.serial_no))
        return pos / self.COUNTS_PER_REVOLUTION * 360

    def get_angle(self):
        return self.get_deg()

    def stop(self):
        self.pass_info(
            f"Stopping immediately {ism.ISC_StopImmediate(self.serial_no)}")
    
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
