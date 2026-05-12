from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np
from PyQt6 import QtCore, QtWidgets, uic  # type: ignore
import pyqtgraph as pg

if __package__:
    from .andor_logic import AndorCameraLogic
else:
    from andor_logic import AndorCameraLogic


class Andor(QtWidgets.QWidget):
    stop_signal = QtCore.pyqtSignal()
    start_signal = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        ui_path = os.path.join(os.path.dirname(__file__), "andor.ui")
        uic.loadUi(ui_path, self)  # type: ignore[arg-type]

        self.camera_logic = AndorCameraLogic()
        self.logic = self.camera_logic
        self._monitor_enabled = True

        self._wire_controls()
        self._wire_logic_signals()
        self._initialize_status()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._monitor)
        self.timer.start(5000)
        self.camera_logic.refresh_device_counts()

    def _wire_controls(self):
        self.connectCamera_pushButton.clicked.connect(self._on_connect_camera_clicked)
        self.disconnectCamera_pushButton.clicked.connect(self._on_disconnect_camera_clicked)
        self.connectSpectrometer_pushButton.clicked.connect(
            self._on_connect_spectrometer_clicked
        )
        self.disconnectSpectrometer_pushButton.clicked.connect(
            self._on_disconnect_spectrometer_clicked
        )

        self.setTemperature_pushButton.clicked.connect(self._on_set_temperature_clicked)
        self.stopCooling_pushButton.clicked.connect(self._on_stop_cooling_clicked)
        self.setExposureTime_pushButton.clicked.connect(
            self._on_set_exposure_time_clicked
        )
        self.acquisitionMode_comboBox.currentTextChanged.connect(
            self._on_acquisition_mode_changed
        )
        self.readMode_comboBox.currentTextChanged.connect(self._on_read_mode_changed)
        self.accumFrameNumber_spinBox.valueChanged.connect(
            self._on_accum_setting_changed
        )
        self.accumFrequency_spinBox.valueChanged.connect(self._on_accum_setting_changed)

        self.startAcquisition_pushButton.clicked.connect(
            self._on_start_acquisition_clicked
        )
        self.stopAcquisition_pushButton.clicked.connect(
            self._on_stop_acquisition_clicked
        )
        self.snap_pushButton.clicked.connect(self._on_snap_clicked)

    def _wire_logic_signals(self):
        self.camera_logic.sig_camera_count.connect(self._update_camera_count)
        self.camera_logic.sig_spectrometer_count.connect(self._update_spectrometer_count)
        self.camera_logic.sig_connected.connect(self._update_camera_connection_status)
        self.camera_logic.sig_spectrometer_connected.connect(
            self._update_spectrometer_connection_status
        )
        self.camera_logic.sig_device_info.connect(self._update_camera_info)
        self.camera_logic.sig_spectrometer_info.connect(self._update_spectrometer_info)
        self.camera_logic.sig_temperature.connect(self._update_temperature)
        self.camera_logic.sig_acquisition_mode.connect(self._update_acquisition_mode)
        self.camera_logic.sig_exposure_time.connect(self._update_exposure_time)
        self.camera_logic.sig_read_mode.connect(self._update_read_mode)
        self.camera_logic.sig_detector_size.connect(self._update_detector_size)
        self.camera_logic.sig_image_acquired.connect(self._update_plot)
        self.camera_logic.sig_is_changing.connect(self.log_message)

    def _initialize_status(self):
        self.cameraStatus_label.setText("disconnected")
        self.spectrometerStatus_label.setText("disconnected")
        self.numCamera_label.setText("0")
        self.numSpectrometer_label.setText("0")

    def _start_logic_job(self, job: str, finished_slot=None):
        self.camera_logic.stop()
        self.camera_logic.job = job
        if finished_slot is not None:
            try:
                self.camera_logic.finished.disconnect(finished_slot)
            except TypeError:
                pass
            self.camera_logic.finished.connect(finished_slot)
        self.camera_logic.start()

    def _on_connect_camera_clicked(self):
        if self.camera_logic.connected:
            self.log_message("Camera is already connected")
            return

        index = int(self.cameraIndex_spinBox.value())
        self.camera_logic.setpoint_camera_index = index
        self.connectCamera_pushButton.setEnabled(False)
        self.cameraStatus_label.setText("connecting")
        self.log_message(f"Connecting camera {index}")
        self._start_logic_job("connect_camera", self._on_camera_connection_finished)

    def _on_camera_connection_finished(self):
        try:
            self.camera_logic.finished.disconnect(self._on_camera_connection_finished)
        except TypeError:
            pass
        self.connectCamera_pushButton.setEnabled(True)

        if not self.camera_logic.connected:
            self.cameraStatus_label.setText("connection failed")
            return

        try:
            self._update_detector_size(self.camera_logic.query_detector_size())
        except Exception as exc:
            self.log_message(f"Camera connected, but detector query failed: {exc}")

    def _on_disconnect_camera_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("No camera is connected")
            return

        self.camera_logic.disconnect_camera()
        self.cameraStatus_label.setText("disconnected")
        self.log_message("Camera disconnected")

    def _on_connect_spectrometer_clicked(self):
        if self.camera_logic.spectrometer_connected:
            self.log_message("Spectrometer is already connected")
            return

        index = int(self.spectrometerIndex_spinBox.value())
        self.camera_logic.setpoint_spectrometer_index = index
        self.connectSpectrometer_pushButton.setEnabled(False)
        self.spectrometerStatus_label.setText("connecting")
        self.log_message(f"Connecting spectrometer {index}")
        self._start_logic_job(
            "connect_spectrometer",
            self._on_spectrometer_connection_finished,
        )

    def _on_spectrometer_connection_finished(self):
        try:
            self.camera_logic.finished.disconnect(
                self._on_spectrometer_connection_finished
            )
        except TypeError:
            pass
        self.connectSpectrometer_pushButton.setEnabled(True)

        if not self.camera_logic.spectrometer_connected:
            self.spectrometerStatus_label.setText("connection failed")
            return

        self.spectrometerStatus_label.setText(
            f"connected to {self.camera_logic.setpoint_spectrometer_index}"
        )

    def _on_disconnect_spectrometer_clicked(self):
        if not self.camera_logic.spectrometer_connected:
            self.log_message("No spectrometer is connected")
            return

        self.camera_logic.disconnect_spectrometer()
        self.spectrometerStatus_label.setText("disconnected")
        self.log_message("Spectrometer disconnected")

    def _on_set_temperature_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("Connect the camera before setting temperature")
            return
        self.camera_logic.setpoint_temperature = int(self.temperature_spinBox.value())
        self.camera_logic.setpoint_cooler = True
        self._start_logic_job("set_temperature")

    def _on_stop_cooling_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("Connect the camera before changing cooler state")
            return
        self.camera_logic.setpoint_cooler = False
        self._start_logic_job("setup_cooler")

    def _on_set_exposure_time_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("Connect the camera before setting exposure time")
            return
        self.camera_logic.setpoint_exposure_time = float(self.exposureTime_spinBox.value())
        self._start_logic_job("setup_exposure_time")

    def _on_acquisition_mode_changed(self, *_):
        if not self.camera_logic.connected:
            return

        mode = self.acquisitionMode_comboBox.currentText()
        if mode == "accumulate":
            mode = "accum"
            self.accumFrameNumber_spinBox.setEnabled(True)
            self.accumFrequency_spinBox.setEnabled(True)
        else:
            self.accumFrameNumber_spinBox.setEnabled(False)
            self.accumFrequency_spinBox.setEnabled(False)

        self.camera_logic.setpoint_acquisition_mode = mode
        self._start_logic_job("setup_acquisition_mode")

    def _on_accum_setting_changed(self, *_):
        if not self.camera_logic.connected:
            return
        if self.acquisitionMode_comboBox.currentText() != "accumulate":
            return
        self.camera_logic.setpoint_accum_num_frames = int(
            self.accumFrameNumber_spinBox.value()
        )
        self.camera_logic.setpoint_accum_cycle_time = float(
            self.accumFrequency_spinBox.value()
        )
        self._start_logic_job("setup_accumulation_mode")

    def _on_read_mode_changed(self, *_):
        if not self.camera_logic.connected:
            return
        self.camera_logic.setpoint_read_mode = self.readMode_comboBox.currentText()
        self._start_logic_job("setup_read_mode")

    def _on_start_acquisition_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("Connect the camera before starting acquisition")
            return
        self._start_logic_job("start_acquisition")

    def _on_stop_acquisition_clicked(self):
        if not self.camera_logic.connected:
            return
        self._start_logic_job("stop_acquisition")

    def _on_snap_clicked(self):
        if not self.camera_logic.connected:
            self.log_message("Connect the camera before snapping an image")
            return
        self._start_logic_job("snap_image")

    def _update_camera_count(self, count: Any):
        self.numCamera_label.setText(str(count))

    def _update_spectrometer_count(self, count: Any):
        self.numSpectrometer_label.setText(str(count))

    def _update_camera_connection_status(self, status: Any):
        text = str(status)
        if self.camera_logic.connected:
            head_model = self._get_device_info_value(
                self.camera_logic.device_info,
                "head_model",
                f"camera {self.camera_logic.setpoint_camera_index}",
            )
            self.cameraStatus_label.setText(f"connected to {head_model}")
        elif "failed" in text:
            self.cameraStatus_label.setText("connection failed")
        else:
            self.cameraStatus_label.setText("disconnected")
        self.log_message(text)

    def _update_spectrometer_connection_status(self, status: Any):
        text = str(status)
        if self.camera_logic.spectrometer_connected:
            self.spectrometerStatus_label.setText(
                f"connected to {self.camera_logic.setpoint_spectrometer_index}"
            )
        elif "failed" in text:
            self.spectrometerStatus_label.setText("connection failed")
        else:
            self.spectrometerStatus_label.setText("disconnected")
        self.log_message(text)

    def _update_camera_info(self, info: Any):
        self.log_message(f"Camera info: {info}")

    def _update_spectrometer_info(self, info: Any):
        self.log_message(f"Spectrometer info: {info}")

    def _update_temperature(self, val: Any):
        if self.temperature_spinBox.hasFocus():
            return
        self.currentTemperature_label.setText(f"{float(val):.1f} C")

    def _update_acquisition_mode(self, val: Any):
        if self.acquisitionMode_comboBox.hasFocus():
            return
        display = "accumulate" if str(val) == "accum" else str(val)
        self.acquisitionMode_comboBox.setCurrentText(display)

    def _update_exposure_time(self, val: Any):
        if self.exposureTime_spinBox.hasFocus():
            return
        self.exposureTime_spinBox.setValue(float(val))

    def _update_read_mode(self, val: Any):
        if self.readMode_comboBox.hasFocus():
            return
        self.readMode_comboBox.setCurrentText(str(val))

    def _update_detector_size(self, val: Any):
        if val is None:
            return
        self.detectorSize_label.setText(f"{val[0]}x{val[1]}")

    def _update_plot(self, val: Any):
        self.andor_PlotWidget.clear()
        self._remove_crosshairs()

        if val.ndim == 2 and val.shape[0] != 1:
            self.img_item = pg.ImageItem()
            self.andor_PlotWidget.addItem(self.img_item)
            self.img_item.setImage(val.T)
            self.img_item.setLevels([float(np.nanmin(val)), float(np.nanmax(val))])
            self._current_2d_data = val
            self.andor_PlotWidget.autoRange()
            self._add_2d_crosshair()
            return

        data = val[0] if val.ndim == 2 else val
        self.line_item = pg.PlotDataItem()
        self.andor_PlotWidget.addItem(self.line_item)
        self.line_item.setData(data)
        self._current_1d_data = data
        self.andor_PlotWidget.autoRange()
        self._add_1d_crosshair()

    def _remove_crosshairs(self):
        for name in ("v_line_2d", "h_line_2d", "v_line_1d"):
            item = getattr(self, name, None)
            if item is not None:
                try:
                    item.sigPositionChanged.disconnect()
                except TypeError:
                    pass
                self.andor_PlotWidget.removeItem(item)
                delattr(self, name)

        for name in ("value_label_2d", "value_label_1d"):
            item = getattr(self, name, None)
            if item is not None:
                self.andor_PlotWidget.removeItem(item)
                delattr(self, name)

    def _add_2d_crosshair(self):
        self.v_line_2d = pg.InfiniteLine(angle=90, movable=True, pen="r")
        self.h_line_2d = pg.InfiniteLine(angle=0, movable=True, pen="r")
        data_shape = self._current_2d_data.shape
        self.v_line_2d.setPos(data_shape[1] / 2)
        self.h_line_2d.setPos(data_shape[0] / 2)
        self.andor_PlotWidget.addItem(self.v_line_2d, ignoreBounds=True)
        self.andor_PlotWidget.addItem(self.h_line_2d, ignoreBounds=True)
        self.value_label_2d = pg.TextItem(anchor=(0, 1), color="r")
        self.andor_PlotWidget.addItem(self.value_label_2d)
        self.v_line_2d.sigPositionChanged.connect(self._update_2d_crosshair_text)
        self.h_line_2d.sigPositionChanged.connect(self._update_2d_crosshair_text)
        self._update_2d_crosshair_text()

    def _add_1d_crosshair(self):
        self.v_line_1d = pg.InfiniteLine(angle=90, movable=True, pen="r")
        self.v_line_1d.setPos(len(self._current_1d_data) / 2)
        self.andor_PlotWidget.addItem(self.v_line_1d, ignoreBounds=True)
        self.value_label_1d = pg.TextItem(anchor=(0, 1), color="r")
        self.andor_PlotWidget.addItem(self.value_label_1d)
        self.v_line_1d.sigPositionChanged.connect(self._update_1d_crosshair_text)
        self._update_1d_crosshair_text()

    def _update_2d_crosshair_text(self):
        if not hasattr(self, "_current_2d_data"):
            return
        x_pos = self.v_line_2d.pos().x()
        y_pos = self.h_line_2d.pos().y()
        x = int(round(x_pos))
        y = int(round(y_pos))
        data_shape = self._current_2d_data.shape
        if 0 <= x < data_shape[1] and 0 <= y < data_shape[0]:
            value = self._current_2d_data[y, x]
            text = f"x={x}, y={y}\nvalue={value:.4e}"
        else:
            text = "Out of bounds"
        self.value_label_2d.setPos(x_pos + 1, y_pos + 1)
        self.value_label_2d.setText(text)

    def _update_1d_crosshair_text(self):
        if not hasattr(self, "_current_1d_data"):
            return
        x_pos = self.v_line_1d.pos().x()
        x = int(round(x_pos))
        if 0 <= x < len(self._current_1d_data):
            value = self._current_1d_data[x]
            text = f"x={x}\nvalue={value:.4e}"
            y_pos = value
        else:
            text = "Out of bounds"
            y_pos = np.nanmean(self._current_1d_data) if len(self._current_1d_data) else 0
        self.value_label_1d.setPos(x_pos + 1, y_pos)
        self.value_label_1d.setText(text)

    @staticmethod
    def _get_device_info_value(device_info, key, default=None):
        if isinstance(device_info, dict):
            return device_info.get(key, default)
        return getattr(device_info, key, default)

    def _monitor(self):
        if not self._monitor_enabled:
            return
        if not self.camera_logic.connected:
            return
        if self.camera_logic.isRunning():
            return
        self._start_logic_job("get_all")

    def stop_timer(self):
        self._monitor_enabled = False
        if self.timer.isActive():
            self.timer.stop()

    def start_timer(self):
        self._monitor_enabled = True
        if not self.timer.isActive():
            self.timer.start(5000)

    def stop_monitor(self):
        self.stop_timer()
        if self.camera_logic.isRunning() and self.camera_logic.job == "get_all":
            self.camera_logic.stop()

    def stop_scan(self):
        self.stop_monitor()

    def start_scan(self):
        self.start_timer()

    def disconnect_device(self):
        self.stop_monitor()
        self.camera_logic.shutdown()

    def force_stop(self):
        self.disconnect_device()

    def terminate_dev(self):
        self.disconnect_device()

    def log_message(self, message):
        self.log_textEdit.append(str(message))
        self.log_textEdit.verticalScrollBar().setValue(
            self.log_textEdit.verticalScrollBar().maximum()
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = Andor()
    win.show()
    sys.exit(app.exec())
