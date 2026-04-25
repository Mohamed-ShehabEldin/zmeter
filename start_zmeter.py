import os
import sys

from PyQt6 import QtWidgets

from core.scan_info import ScanInfo
from core.mainWindow import MainWindow

# ------------------------------------------------------------
# Import the equipment modules you plan to use below.  Comment out any
# devices that are not required in your particular setup.
# IMPORTANT: Some modules require Windows-only drivers (e.g., PyDAQmx).
# These are wrapped in try-except to allow the app to run on macOS.
# ------------------------------------------------------------
from sr830.sr830_main import SR830
from sr860.sr860_main import SR860
# from hp34401a.hp34401a_main import HP34401A

# PyDAQmx only works on Windows and Linux, not macOS
try:
    from nidaq.nidaq_main import NIDAQ
    NIDAQ_AVAILABLE = True
except (ImportError, NotImplementedError) as e:
    print(f"⚠️  NIDAQ module unavailable on this platform: {e}")
    NIDAQ_AVAILABLE = False
    NIDAQ = None

from keithley24xx.keithley24xx_main import Keithley24xx

# K10CR1 (Thorlabs stepper motor) only works on Windows with DLL
try:
    from k10cr1.k10cr1_main import K10CR1
    K10CR1_AVAILABLE = True
except (ImportError, NameError, NotImplementedError) as e:
    print(f"⚠️  K10CR1 module unavailable on this platform: {e}")
    K10CR1_AVAILABLE = False
    K10CR1 = None

from sp150.sp150_main import SP150
from tlpm.tlpm_main import TLPM
from tplm_old.tlpm_main import TLPM as TPLMOld

# OptiCool (Windows only - requires pythonnet)
try:
    from opticool.opticool_main import OptiCool
    OPTICOOL_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    print(f"⚠️  OptiCool module unavailable on this platform: {e}")
    OPTICOOL_AVAILABLE = False
    OptiCool = None

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
    }
    
    # Only add NIDAQ if available (not supported on macOS)
    if NIDAQ_AVAILABLE:
        equips["nidaq_0"] = NIDAQ()
        # equips["nidaq_1"] = NIDAQ(),
    
    # Only add K10CR1 if available (Windows only)
    if K10CR1_AVAILABLE:
        equips.update({
            "KR_in": K10CR1(),
            "KR_spec": K10CR1(),
        })
    
    equips.update({
        # "DMM_A": HP34401A(),
        "sp150_0": SP150(),
        "Keithley_0": Keithley24xx(),
        "Keithley_1": Keithley24xx(),
        "tlpm_0": TLPM(),
        "tplm_old_0": TPLMOld(),
        "winspec" : ethernet_winspec(),
        "noninstrumental" : noninstrumental()
    })
    
    # Only add OptiCool if available (Windows only)
    if OPTICOOL_AVAILABLE:
        equips["opticool"] = OptiCool()

    # ------------------------------------------------------------
    # Connection commands – adjust to match your instrument addresses.
    # Wrap in try-except to handle missing/unavailable instruments gracefully.
    # ------------------------------------------------------------
    if NIDAQ_AVAILABLE:
        try:
            equips["nidaq_0"].connect("Dev1")
        except Exception as e:
            print(f"⚠️  Could not connect NIDAQ: {e}")
        # equips["nidaq_1"].connect("Dev2")
    
    if K10CR1_AVAILABLE:
        # equips["KR_in"].connect(serial="55000923")
        # equips["KR_spec"].connect(serial="55539634")
        pass
    
    # equips["lockin_1"].connect_visa("GPIB0::8::INSTR")
    # equips["lockin_2"].connect_visa("GPIB0::9::INSTR")
    # equips["DMM_A"].connect_visa("GPIB0::21::INSTR")
    try:
        equips["Keithley_0"].connect_visa("GPIB0::1::INSTR")
    except Exception as e:
        print(f"⚠️  Could not connect Keithley_0: {e}")
    
    try:
        equips["Keithley_1"].connect_visa("GPIB0::18::INSTR")
    except Exception as e:
        print(f"⚠️  Could not connect Keithley_1: {e}")
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
