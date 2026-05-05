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

try:
    from hp34401a.hp34401a_main import HP34401A
    HP34401A_AVAILABLE = True
except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
    print(f"⚠️  HP34401A module unavailable on this platform: {e}")
    HP34401A_AVAILABLE = False
    HP34401A = None

# PyDAQmx only works on Windows and Linux, not macOS
try:
    from nidaq.nidaq_main import NIDAQ
    NIDAQ_AVAILABLE = True
except (ImportError, NotImplementedError) as e:
    print(f"⚠️  NIDAQ module unavailable on this platform: {e}")
    NIDAQ_AVAILABLE = False
    NIDAQ = None

from keithley24xx.keithley24xx_main import Keithley24xx

# NI6432 uses the modern nidaqmx package. Keep optional for Mac/UI testing.
try:
    from ni6432.ni6432_main import NI6432
    NI6432_AVAILABLE = True
except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
    print(f"⚠️  NI6432 module unavailable on this platform: {e}")
    NI6432_AVAILABLE = False
    NI6432 = None

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

# Montana and autofocus are optional newer devices.
try:
    from montana2.montana2_main import Montana2
    MONTANA2_AVAILABLE = True
except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
    print(f"⚠️  Montana2 module unavailable on this platform: {e}")
    MONTANA2_AVAILABLE = False
    Montana2 = None

try:
    from autofocus_xuguo.autofocusXZ_main import AutofocusXZMain
    AUTOFOCUS_XZ_AVAILABLE = True
except (ImportError, ModuleNotFoundError, NotImplementedError) as e:
    print(f"⚠️  AutofocusXZ module unavailable on this platform: {e}")
    AUTOFOCUS_XZ_AVAILABLE = False
    AutofocusXZMain = None



save_path = os.path.join(os.getcwd(), "data")
backup_main_path = None

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

    # Optional newer NI DAQ device from zmeter.
    # if NI6432_AVAILABLE:
    #     equips["ni6432_0"] = NI6432()
    
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
        "winspec" : ethernet_winspec(),
        "noninstrumental" : noninstrumental()
    })
    
    # Only add OptiCool if available (Windows only)
    if OPTICOOL_AVAILABLE:
        equips["opticool"] = OptiCool()

    # Optional newer devices from zmeter.
    # if MONTANA2_AVAILABLE:
    #     equips["montana2"] = Montana2()
    # if AUTOFOCUS_XZ_AVAILABLE:
    #     equips["autofocusXZ"] = AutofocusXZMain()

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
    # if NI6432_AVAILABLE and "ni6432_0" in equips:
    #     equips["ni6432_0"].connect("Dev7")
    
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

    # Optional scan-channel filters by equipment label.
    # If a label is missing, all get_/set_ channels from that device logic are exposed.
    # Unknown channel names are silently skipped.
    equips_set_channels = {}
    equips_get_channels = {}
    # Example for NI6432 scan-channel filtering:
    # equips_set_channels["ni6432_0"] = ["AO0", "AO1"]
    # equips_get_channels["ni6432_0"] = ["AI9", "AI12", "counter8", "counter12"]
    # Full NI6432 channel families are:
    # set: AO0-AO3
    # get: AI0-AI31, counter0-counter3, AO0-AO3 feedback
    # Recommended legacy NIDAQ filters if "nidaq_0" is enabled:
    # equips_set_channels["nidaq_0"] = ["AO0", "AO1"]
    # equips_get_channels["nidaq_0"] = ["AI0", "AI1", "AI2", "AI3", "AI4", "AI5", "AI6", "AI7", "count"]
    # Recommended HP34401A filters if you enable "DMM_A" above:
    # equips_set_channels["DMM_A"] = ["nplc", "display_on"]
    # equips_get_channels["DMM_A"] = ["dc_voltage", "voltage", "nplc"]
    # Recommended Montana2 filters if you enable "montana2" above:
    # equips_set_channels["montana2"] = ["platform_target_temperature"]
    # equips_get_channels["montana2"] = [
    #     "platform_temperature",
    #     "platform_target_temperature",
    #     "platform_temperature_stable",
    # ]
    # Recommended OptiCool filters if you enable "opticool" above:
    # equips_set_channels["opticool"] = [
    #     "temperature",
    #     "temperature_stable",
    #     "field",
    #     "field_stable",
    # ]
    # equips_get_channels["opticool"] = ["temperature", "field"]
    # Recommended SP150 filters:
    # equips_set_channels["sp150_0"] = ["wavelength"]
    # equips_get_channels["sp150_0"] = ["wavelength"]
    # Recommended SR830 filters:
    # equips_set_channels["lockin_1"] = [
    #     "frequency",
    #     "amplitude",
    #     "phase",
    #     "time_constant",
    #     "sensitivity",
    #     "aux_1",
    #     "aux_2",
    # ]
    # equips_get_channels["lockin_1"] = [
    #     "X",
    #     "Y",
    #     "R",
    #     "Theta",
    #     "frequency",
    #     "amplitude",
    #     "phase",
    #     "time_constant",
    #     "sensitivity",
    #     "unlocked",
    #     "input_overload",
    #     "time_constant_overload",
    #     "output_overload",
    #     "aux_1",
    #     "aux_2",
    # ]
    # Recommended SR860 filters if you enable "sr860_test" above:
    # equips_set_channels["sr860_test"] = [
    #     "frequency",
    #     "amplitude",
    #     "phase",
    #     "time_constant",
    #     "sensitivity",
    #     "ref_mode",
    #     "ext_trigger",
    #     "sync_filter",
    #     "harmonic",
    #     "signal_input_config",
    #     "dc_level",
    #     "dc_level_mode",
    #     "filter_slope",
    # ]
    # equips_get_channels["sr860_test"] = [
    #     "X",
    #     "Y",
    #     "R",
    #     "Theta",
    #     "frequency",
    #     "amplitude",
    #     "phase",
    #     "time_constant",
    #     "sensitivity",
    #     "input_overload",
    #     "sensitivity_overload",
    # ]
    # Recommended TLPM filters:
    # equips_set_channels["tlpm_0"] = ["wavelength"]
    # equips_get_channels["tlpm_0"] = ["power"]
    equips_set_channels["Keithley_0"] = ["voltage", "current"]
    equips_get_channels["Keithley_0"] = ["voltage", "current"]
    equips_set_channels["Keithley_1"] = ["voltage", "current"]
    equips_get_channels["Keithley_1"] = ["voltage", "current"]

    return equips, equips_set_channels, equips_get_channels

def main():
    """Application entry point.  Edit this function to customise paths and devices."""

    # Paths where data and backups are stored – adjust as needed.

    # ------------------------------------------------------------
    # Qt must be initialised *before* instantiating any QWidget-based
    # equipment such as SR860().
    # ------------------------------------------------------------
    app = QtWidgets.QApplication(sys.argv)

    # Hardware setup (widgets can be created safely now)
    equips, equips_set_channels, equips_get_channels = create_equipment()

    window = MainWindow(
        info=ScanInfo,
        save_path=save_path,
        backup_main_path=backup_main_path,
        equips=equips,
        equips_set_channels=equips_set_channels,
        equips_get_channels=equips_get_channels,
    )
    window.show()
    window.setWindowTitle("Main Window")
    app.exec()


if __name__ == "__main__":
    main() 
