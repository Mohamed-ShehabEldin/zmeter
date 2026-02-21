import os
import sys

from PyQt6 import QtWidgets

from core.scan_info import ScanInfo
from core.mainWindow import MainWindow

# ------------------------------------------------------------
# Import the equipment modules you plan to use below.  Comment out any
# devices that are not required in your particular setup.
# ------------------------------------------------------------
from sr830.sr830_main import SR830
from sr860.sr860_main import SR860
# from hp34401a.hp34401a_main import HP34401A
from nidaq.nidaq_main import NIDAQ
from keithley24xx.keithley24xx_main import Keithley24xx
from k10cr1.k10cr1_main import K10CR1
# from tlpm.tlpm_main import TLPM
# from auto_focus.autofocus_main import autofocus_main
# from auto_focus.autofocus_logic import stepper_and_galvo_xyz
from opticool.opticool_main import OptiCool

from winspec_remote.remote_winspec_main import ethernet_winspec
from non_instrumental.noninstrumental_main import noninstrumental



save_path = os.path.join(os.getcwd(), "data")
backup_main_path = r""

def create_equipment():
    """Instantiate and connect to all equipment required for the session."""

    equips = {
        "lockin_1": SR830(),
        # "lockin_2": SR830(),
        # "sr860_test": SR860(),
        "nidaq_0": NIDAQ(),
        # "nidaq_1": NIDAQ(),
        # "DMM_A": HP34401A(),
        "KR_in": K10CR1(),
        "KR_spec": K10CR1(),
        "Keithley_0": Keithley24xx(),
        "Keithley_1": Keithley24xx(),
        # "tlpm_0": TLPM(),
        "opticool": OptiCool(),
        "winspec" : ethernet_winspec(),
        "noninstrumental" : noninstrumental()
    }

    # ------------------------------------------------------------
    # Connection commands – adjust to match your instrument addresses.
    # ------------------------------------------------------------
    equips["nidaq_0"].connect("Dev1")
    # equips["nidaq_1"].connect("Dev2")
    # equips["KR_in"].connect(serial="55000923")
    # equips["KR_spec"].connect(serial="55539634")
    # equips["lockin_1"].connect_visa("GPIB0::8::INSTR")
    # equips["lockin_2"].connect_visa("GPIB0::9::INSTR")
    # equips["DMM_A"].connect_visa("GPIB0::21::INSTR")
    equips["Keithley_0"].connect_visa("GPIB0::1::INSTR")
    # equips["Keithley_1"].connect_visa("GPIB::18::INSTR")
    # equips["sr860_test"].connect_visa("GPIB0::2::INSTR")
    # equips["tlpm_0"].connect()

    return equips


artificial_channels = {
    "A": "A=nidaq_0_AO0+nidaq_0_AO1",
    "B": "B=nidaq_0_AO0-nidaq_0_AO1"
}

def main():
    """Application entry point.  Edit this function to customise paths and devices."""

    # Paths where data and backups are stored – adjust as needed.

    # ------------------------------------------------------------
    # Qt must be initialised *before* instantiating any QWidget-based
    # equipment such as SR860().
    # ------------------------------------------------------------
    app = QtWidgets.QApplication(sys.argv)

    # Hardware setup (widgets can be created safely now)
    equips = create_equipment()

    window = MainWindow(
        info=ScanInfo,
        save_path=save_path,
        backup_main_path=backup_main_path,
        equips=equips,
        artificial_channels=artificial_channels,
    )
    window.show()
    window.setWindowTitle("Main Window")
    app.exec()


if __name__ == "__main__":
    main() 