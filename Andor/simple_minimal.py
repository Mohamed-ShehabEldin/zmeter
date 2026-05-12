from pylablib.devices import Andor

print("Number of SDK2 cameras:", Andor.get_cameras_number_SDK2())
print("Spectrographs:", Andor.list_shamrock_spectrographs())

from pylablib.devices import Andor
from pprint import pprint

def safe_print(label, func):
    try:
        value = func()
        print(f"{label}:")
        pprint(value)
    except Exception as e:
        print(f"{label}: FAILED -> {type(e).__name__}: {e}")

print("SDK2 cameras detected:", Andor.get_cameras_number_SDK2())

try:
    print("Andor SDK version:", Andor.get_SDK_version())
except Exception as e:
    print("Could not read SDK version:", e)

n = Andor.get_cameras_number_SDK2()

for idx in range(n):
    print("\n" + "=" * 70)
    print(f"Testing camera idx={idx}")
    print("=" * 70)

    cam = None
    try:
        # For identification only:
        # temperature="off" prevents starting cooling.
        # fan_mode="full" just keeps the fan high while connected.
        cam = Andor.AndorSDK2Camera(
            idx=idx,
            temperature="off",
            fan_mode="full",
        )

        safe_print("Device info", cam.get_device_info)
        safe_print("Detector size, pixels", cam.get_detector_size)
        safe_print("Pixel size, meters", cam.get_pixel_size)
        safe_print("Temperature range, C", cam.get_temperature_range)
        safe_print("Current temperature, C", cam.get_temperature)
        safe_print("Temperature setpoint, C", cam.get_temperature_setpoint)
        safe_print("Temperature status", cam.get_temperature_status)
        safe_print("Cooler on?", cam.is_cooler_on)
        safe_print("Current status", cam.get_status)
        safe_print("Current ROI", cam.get_roi)
        safe_print("Current amplifier mode", cam.get_amp_mode)
        safe_print("Available amplifier modes", cam.get_all_amp_modes)
        safe_print("Available vertical shift speeds", cam.get_all_vsspeeds)

    finally:
        if cam is not None:
            cam.close()
            print(f"Closed camera idx={idx}")