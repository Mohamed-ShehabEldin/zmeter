from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from PyQt6 import QtCore
from pylablib.devices import Andor as PylablibAndor

if __package__:
    from .andor_hardware_new import AndorCameraHardware, ShamrockSpectrogramHardware
else:
    from andor_hardware_new import AndorCameraHardware, ShamrockSpectrogramHardware


class AndorCameraLogic(QtCore.QThread):
    """pylablib-only camera/spectrometer controller for the Andor widget."""

    sig_acquisition_mode = QtCore.pyqtSignal(object)
    sig_exposure_time = QtCore.pyqtSignal(object)
    sig_temperature = QtCore.pyqtSignal(object)
    sig_read_mode = QtCore.pyqtSignal(object)
    sig_detector_size = QtCore.pyqtSignal(object)
    sig_device_info = QtCore.pyqtSignal(object)

    sig_image_acquired = QtCore.pyqtSignal(object)
    sig_acquisition_started = QtCore.pyqtSignal(object)
    sig_acquisition_stopped = QtCore.pyqtSignal(object)
    sig_frame_ready = QtCore.pyqtSignal(object)
    sig_acquisition_timings = QtCore.pyqtSignal(object)
    sig_cooler = QtCore.pyqtSignal(object)
    sig_accum_frame_num = QtCore.pyqtSignal(object)
    sig_accum_cycle_time = QtCore.pyqtSignal(object)

    sig_camera_count = QtCore.pyqtSignal(object)
    sig_spectrometer_count = QtCore.pyqtSignal(object)
    sig_spectrometer_info = QtCore.pyqtSignal(object)

    sig_is_changing = QtCore.pyqtSignal(object)
    sig_connected = QtCore.pyqtSignal(object)
    sig_spectrometer_connected = QtCore.pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()

        self.job = ""

        self.setpoint_camera_index = 0
        self.setpoint_spectrometer_index = 0
        self.setpoint_acquisition_mode = "single"
        self.setpoint_exposure_time = 0.1
        self.setpoint_temperature = -80
        self.setpoint_read_mode = "image"
        self.setpoint_cooler = False

        self.setpoint_accum_num_frames = 10
        self.setpoint_accum_cycle_time = 0.0
        self.setpoint_cont_cycle_time = 0.0
        self.setpoint_kinetic_num_cycle = 10
        self.setpoint_kinetic_cycle_time = 0.0
        self.setpoint_kinetic_num_acc = 1
        self.setpoint_kinetic_cycle_time_acc = 0.0
        self.setpoint_kinetic_num_prescan = 0
        self.setpoint_center_wavelength = 633e-9

        self.connected = False
        self.spectrometer_connected = False
        self.reject_signal = False
        self.acquiring = False

        self.device_info: Any = None
        self.spectrometer_info: Any = None
        self.last_spectrum_axis = None
        self.last_spectrum = None
        self.hardware: AndorCameraHardware | None = None
        self.spectrometer_hardware: ShamrockSpectrogramHardware | None = None

    def _emit_status(self, message: str):
        self.sig_is_changing.emit(str(message))

    def _close_camera_hardware(self):
        if self.hardware is None:
            return
        try:
            if self.acquiring:
                self.hardware.stop_acquisition()
                self.acquiring = False
            self.hardware.disconnect()
        except Exception as exc:
            logging.warning("Error closing Andor camera: %s", exc)
            self._emit_status(f"Camera close warning: {exc}")
        finally:
            self.hardware = None

    def _close_spectrometer_hardware(self):
        if self.spectrometer_hardware is None:
            return
        try:
            self.spectrometer_hardware.disconnect()
        except Exception as exc:
            logging.warning("Error closing Shamrock spectrometer: %s", exc)
            self._emit_status(f"Spectrometer close warning: {exc}")
        finally:
            self.spectrometer_hardware = None

    def refresh_device_counts(self):
        camera_count = self.query_camera_count()
        spectrometer_count = self.query_spectrometer_count()
        return camera_count, spectrometer_count

    def query_camera_count(self):
        try:
            count = int(PylablibAndor.get_cameras_number_SDK2())
        except Exception as exc:
            logging.warning("Could not query Andor camera count: %s", exc)
            count = 0
            self._emit_status(f"Could not query camera count: {exc}")
        self.sig_camera_count.emit(count)
        return count

    def query_spectrometer_count(self):
        try:
            spectrometers = PylablibAndor.list_shamrock_spectrographs()
            count = len(spectrometers) if spectrometers is not None else 0
        except Exception as exc:
            logging.warning("Could not query Shamrock spectrometer count: %s", exc)
            count = 0
            self._emit_status(f"Could not query spectrometer count: {exc}")
        self.sig_spectrometer_count.emit(count)
        return count

    def connect_camera(self, camera_index: int | None = None):
        if camera_index is not None:
            self.setpoint_camera_index = int(camera_index)
        if self.connected:
            self._emit_status("Camera is already connected")
            return True

        self._emit_status(f"Connecting camera {self.setpoint_camera_index}")
        self._close_camera_hardware()
        self.connected = False
        self.device_info = None

        try:
            self.hardware = AndorCameraHardware(
                self.setpoint_camera_index,
                temperature="off",
                fan_mode="full",
            )
            self.device_info = self.query_device_info()
            self.connected = True
            self.sig_connected.emit(f"connected to camera {self.setpoint_camera_index}")
            self._emit_status(f"Camera {self.setpoint_camera_index} connected")
            return True
        except Exception as exc:
            logging.exception("Andor camera connection failed")
            self._close_camera_hardware()
            self.connected = False
            self.sig_connected.emit("camera connection failed")
            self._emit_status(f"Camera connection failed: {exc}")
            return False

    def disconnect_camera(self):
        self.reject_signal = True
        self.job = ""
        if self.isRunning() and QtCore.QThread.currentThread() is not self:
            self.wait()
        self._close_camera_hardware()
        if self.connected:
            self.connected = False
            self.sig_connected.emit("camera disconnected")
        self.device_info = None
        self.reject_signal = False

    def disconnect(self):
        self.disconnect_camera()

    def connect_spectrometer(self, spectrometer_index: int | None = None):
        if spectrometer_index is not None:
            self.setpoint_spectrometer_index = int(spectrometer_index)
        if self.spectrometer_connected:
            self._emit_status("Spectrometer is already connected")
            return True

        self._emit_status(f"Connecting spectrometer {self.setpoint_spectrometer_index}")
        self._close_spectrometer_hardware()
        self.spectrometer_connected = False
        self.spectrometer_info = None

        try:
            self.spectrometer_hardware = ShamrockSpectrogramHardware(
                idx=self.setpoint_spectrometer_index
            )
            self.spectrometer_info = self.query_spectrometer_device_info()
            self.spectrometer_connected = True
            self.sig_spectrometer_connected.emit(
                f"connected to spectrometer {self.setpoint_spectrometer_index}"
            )
            self._emit_status(f"Spectrometer {self.setpoint_spectrometer_index} connected")
            return True
        except Exception as exc:
            logging.exception("Shamrock spectrometer connection failed")
            self._close_spectrometer_hardware()
            self.spectrometer_connected = False
            self.sig_spectrometer_connected.emit("spectrometer connection failed")
            self._emit_status(f"Spectrometer connection failed: {exc}")
            return False

    def disconnect_spectrometer(self):
        self._close_spectrometer_hardware()
        if self.spectrometer_connected:
            self.spectrometer_connected = False
            self.sig_spectrometer_connected.emit("spectrometer disconnected")
        self.spectrometer_info = None

    def get_temperature(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.temperature(read=True)
        self.sig_temperature.emit(val)
        return val

    def set_temperature(self, value=None):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        if value is not None:
            self.setpoint_temperature = int(value)
        self.hardware.temperature(self.setpoint_temperature, write=True)
        self.sig_temperature.emit(self.setpoint_temperature)
        self._emit_status(f"temperature set to {self.setpoint_temperature} C")

    def get_exposure_time(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.exposure_time(read=True)
        self.sig_exposure_time.emit(val)
        return val

    def set_exposure_time(self, value):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.setpoint_exposure_time = float(value)
        self.hardware.exposure_time(self.setpoint_exposure_time, write=True)
        self.sig_exposure_time.emit(self.setpoint_exposure_time)
        self._emit_status(f"exposure_time set to {self.setpoint_exposure_time} s")

    def get_center_wavelength(self):
        if self.spectrometer_hardware is None:
            raise RuntimeError("Spectrometer is not connected")
        return self.spectrometer_hardware.center_wavelength(read=True)

    def set_center_wavelength(self, value):
        if self.spectrometer_hardware is None:
            raise RuntimeError("Spectrometer is not connected")
        self.setpoint_center_wavelength = float(value)
        self.spectrometer_hardware.center_wavelength(
            self.setpoint_center_wavelength,
            write=True,
        )
        self._emit_status(
            f"center_wavelength set to {self.setpoint_center_wavelength}"
        )

    def get_spectrum(self):
        """Scan getter for the full spectrum.

        Returns
        -------
        numpy.ndarray
            A 2 x N array. Row 0 is wavelength calibration when the Shamrock is
            connected, otherwise pixel index. Row 1 is measured intensity.
        """
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")

        image = self.hardware.snap_image()
        spectrum = np.asarray(image).squeeze()
        if spectrum.ndim != 1:
            spectrum = spectrum.reshape(-1)

        axis = self._get_spectrum_axis(len(spectrum))
        self.last_spectrum_axis = axis
        self.last_spectrum = spectrum
        return np.vstack([axis, spectrum])

    def get_spectrum_mean(self):
        """Scalar scan getter for users who want one intensity number."""
        spectrum_trace = self.get_spectrum()
        return float(np.nanmean(spectrum_trace[1]))

    def get_spectrum_sum(self):
        """Scalar scan getter for users who want integrated intensity."""
        spectrum_trace = self.get_spectrum()
        return float(np.nansum(spectrum_trace[1]))

    def _get_spectrum_axis(self, spectrum_length: int):
        """Return wavelength calibration if possible, otherwise pixel index."""
        if self.spectrometer_hardware is None:
            return np.arange(spectrum_length, dtype=float)
        try:
            self.spectrometer_hardware.setup_pixels_from_camera(self.hardware)
            calibration = np.asarray(self.spectrometer_hardware.get_calibration()).squeeze()
            if calibration.size == spectrum_length:
                return calibration.astype(float)
        except Exception as exc:
            logging.warning("Could not read Shamrock wavelength calibration: %s", exc)
            self._emit_status(f"Using pixel axis for spectrum: {exc}")
        return np.arange(spectrum_length, dtype=float)

    def setup_cooler(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.cooler(self.setpoint_cooler, write=True)
        self.sig_cooler.emit(self.setpoint_cooler)
        self._emit_status(f"cooler set to {self.setpoint_cooler}")

    def query_device_info(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.get_device_info()
        self.sig_device_info.emit(val)
        return val

    def query_spectrometer_device_info(self):
        if self.spectrometer_hardware is None:
            raise RuntimeError("Spectrometer is not connected")
        info = {
            "device_info": self.spectrometer_hardware.get_device_info(),
            "optical_parameters": self._read_optional_spectrometer_value(
                "optical_parameters",
                self.spectrometer_hardware.get_optical_parameters,
            ),
            "status": self._read_optional_spectrometer_value(
                "status",
                self.spectrometer_hardware.get_status,
            ),
        }
        self.sig_spectrometer_info.emit(info)
        return info

    def _read_optional_spectrometer_value(self, name: str, reader):
        try:
            return reader()
        except Exception as exc:
            logging.warning("Could not read spectrometer %s: %s", name, exc)
            return None

    def query_acquisition_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.acquisition_mode(read=True)
        self.sig_acquisition_mode.emit(val)
        return val

    def query_exposure_time(self):
        return self.get_exposure_time()

    def query_read_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.read_mode(read=True)
        self.sig_read_mode.emit(val)
        return val

    def query_detector_size(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.get_detector_size()
        self.sig_detector_size.emit(val)
        return val

    def query_acquisition_timings(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        val = self.hardware.get_acquisition_timings()
        self.sig_acquisition_timings.emit(val)
        return val

    def query_accum_settings(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        frame_num, cycle_time = self.hardware.setup_accumulation_mode(read=True)
        self.sig_accum_frame_num.emit(frame_num)
        self.sig_accum_cycle_time.emit(cycle_time)
        return frame_num, cycle_time

    def setup_acquisition_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.acquisition_mode(self.setpoint_acquisition_mode, write=True)
        self.sig_acquisition_mode.emit(self.setpoint_acquisition_mode)
        self._emit_status(f"acquisition_mode set to {self.setpoint_acquisition_mode}")

    def setup_exposure_time(self):
        self.set_exposure_time(self.setpoint_exposure_time)

    def setup_read_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.read_mode(self.setpoint_read_mode, write=True)
        self.sig_read_mode.emit(self.setpoint_read_mode)
        self._emit_status(f"read_mode set to {self.setpoint_read_mode}")

    def setup_accumulation_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.setup_accumulation_mode(
            int(self.setpoint_accum_num_frames),
            self.setpoint_accum_cycle_time,
            write=True,
        )
        self._emit_status(
            f"accumulation mode setup: {int(self.setpoint_accum_num_frames)} frames, "
            f"cycle_time {self.setpoint_accum_cycle_time} s"
        )

    def setup_continuous_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.setup_continuous_mode(self.setpoint_cont_cycle_time, write=True)
        self._emit_status(
            f"continuous mode setup: cycle_time {self.setpoint_cont_cycle_time} s"
        )

    def setup_kinetic_mode(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.setup_kinetic_mode(
            self.setpoint_kinetic_num_cycle,
            self.setpoint_kinetic_cycle_time,
            self.setpoint_kinetic_num_acc,
            self.setpoint_kinetic_cycle_time_acc,
            self.setpoint_kinetic_num_prescan,
            write=True,
        )
        self._emit_status(
            f"kinetic mode setup: {self.setpoint_kinetic_num_cycle} cycles, "
            f"{self.setpoint_kinetic_num_acc} accumulations"
        )

    def start_acquisition(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.start_acquisition()
        self.acquiring = True
        self.sig_acquisition_started.emit("acquisition started")
        self._emit_status("acquisition started")

    def stop_acquisition(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.stop_acquisition()
        self.acquiring = False
        self.sig_acquisition_stopped.emit("acquisition stopped")
        self._emit_status("acquisition stopped")

    def snap_image(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        image = self.hardware.snap_image()
        self.sig_image_acquired.emit(image)
        self._emit_status(f"image acquired: shape {image.shape}")
        return image

    def wait_for_frame(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.wait_for_frame()
        self.sig_frame_ready.emit("frame ready")

    def read_oldest_image(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        image = self.hardware.read_oldest_image()
        self.sig_image_acquired.emit(image)
        return image

    def read_newest_image(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        image = self.hardware.read_newest_image()
        self.sig_image_acquired.emit(image)
        return image

    def clear_acquisition(self):
        if self.hardware is None:
            raise RuntimeError("Camera is not connected")
        self.hardware.clear_acquisition()
        self._emit_status("acquisition buffer cleared")

    def query_all(self):
        self.query_acquisition_mode()
        self.query_exposure_time()
        self.get_temperature()
        self.query_read_mode()
        self.query_detector_size()
        self.query_acquisition_timings()
        self.query_accum_settings()
        time.sleep(0.05)

    def setup_current_mode(self):
        mode = self.setpoint_acquisition_mode
        if mode in ("accumulate", "accum"):
            self.setup_accumulation_mode()
        elif mode in ("continuous", "cont"):
            self.setup_continuous_mode()
        elif mode == "kinetic":
            self.setup_kinetic_mode()

    def get_all(self, _monitor=True):
        self.query_all()

    def run(self):
        if self.reject_signal:
            return
        current_job = self.job
        if not current_job:
            return

        fn = getattr(self, current_job, None)
        if not callable(fn):
            self._emit_status(f"Andor job '{current_job}' does not exist")
            self.job = ""
            return

        try:
            self._emit_status(f"{current_job} started")
            fn()
            self._emit_status(f"{current_job} completed")
        except Exception as exc:
            logging.exception("Andor job '%s' failed", current_job)
            self._emit_status(f"Andor job '{current_job}' failed: {exc}")
        finally:
            self.job = ""

    def stop(self):
        self.reject_signal = True
        if self.acquiring and self.hardware is not None:
            try:
                self.hardware.stop_acquisition()
                self.acquiring = False
            except Exception as exc:
                logging.warning("Error stopping acquisition: %s", exc)
                self._emit_status(f"Warning: error stopping acquisition: {exc}")
        self.quit()
        if self.isRunning() and QtCore.QThread.currentThread() is not self:
            self.wait()
        self.reject_signal = False

    def shutdown(self):
        self.stop()
        self.disconnect_camera()
        self.disconnect_spectrometer()
