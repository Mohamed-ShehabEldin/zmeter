"""
Remote WinSpec GUI – single & continuous capture + interactive spectrum plot.

Features:
  • capture_once  – single acquire + plot
  • capture_cont  – repeating acquire + plot until stop is pressed
  • stop          – halts continuous capture after current acquisition finishes
  • Crosshair cursor, zoom/pan, avg window (pyqtgraph)
  • Updates EXPOSURE_SEC and ACCUMS in acquire.vbs before each capture
  • All I/O runs in a QThread so the GUI stays responsive
"""

import sys
import re
import numpy as np

from PyQt6 import QtWidgets, uic, QtCore, QtGui
import pyqtgraph as pg

try:
    from .remote_winspec_logic import ethernet_winspec_logic
except ImportError:
    from remote_winspec_logic import ethernet_winspec_logic

import imageio.v2 as imageio
from pathlib import Path


# ── pyqtgraph global config ─────────────────────────────────────
pg.setConfigOptions(antialias=True)

# ── Path to the VBS script on the network share ─────────────────
ACQUIRE_VBS_PATH = r"\\192.168.0.1\trigger\acquire.vbs"


# ───────────────────────── VBS updater ───────────────────────────
def update_acquire_vbs(int_time: float, accumulations: int):
    vbs = Path(ACQUIRE_VBS_PATH)
    text = vbs.read_text(encoding="utf-8")

    text = re.sub(
        r'(Dim\s+EXPOSURE_SEC\s*:\s*EXPOSURE_SEC\s*=\s*)[\d.]+',
        rf'\g<1>{int_time}',
        text,
    )
    text = re.sub(
        r'(Dim\s+ACCUMS\s*:\s*ACCUMS\s*=\s*)\d+',
        rf'\g<1>{accumulations}',
        text,
    )

    vbs.write_text(text, encoding="utf-8")


# ───────────────────────── worker thread ─────────────────────────
class AcquireWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)   # (wl, spectrum_1d, avg) or None
    status   = QtCore.pyqtSignal(str)

    def __init__(self, logic: ethernet_winspec_logic,
                 int_time: float, accumulations: int):
        super().__init__()
        self.logic = logic
        self.int_time = int_time
        self.accumulations = accumulations

    def run(self):
        try:
            self.status.emit(
                f"Setting exposure={self.int_time}s, accums={self.accumulations} …"
            )
            update_acquire_vbs(self.int_time, self.accumulations)

            self.status.emit("Triggering acquisition …")
            rc = self.logic.set_winspec_acquire(0)
            if rc != 0:
                self.status.emit(f"Acquisition failed (rc={rc})")
                self.finished.emit(None)
                return

            self.status.emit("Reading spectrum …")

            wl = self.logic._load_wavelength_axis_from_txt(
                self.logic.REF_WL_TXT_PATH
            )

            spe_path = Path(self.logic.last_spe_path)
            if not self.logic._wait_until_readable_and_stable(spe_path):
                self.status.emit("Timeout waiting for stable SPE file")
                self.finished.emit(None)
                return

            local_spe = self.logic._copy_to_local(spe_path)
            arr = np.asarray(imageio.imread(local_spe))
            frame = arr[0] if arr.ndim == 3 else arr
            spectrum_1d = frame.mean(axis=0).astype(float)

            out_txt = Path(self.logic.DATS_TXT_DIR) / (local_spe.stem + ".txt")
            self.logic._spe_to_winspec_ascii(local_spe, out_txt, wl)

            mask = (wl >= self.logic.AVG_WL_MIN_NM) & (wl <= self.logic.AVG_WL_MAX_NM)
            avg = float(spectrum_1d[mask].mean()) if np.any(mask) else float("nan")

            self.status.emit(
                f"Done – {spe_path.name}  |  avg {self.logic.AVG_WL_MIN_NM:.0f}–"
                f"{self.logic.AVG_WL_MAX_NM:.0f} nm = {avg:.1f} counts"
            )
            self.finished.emit((wl, spectrum_1d, avg))

        except Exception as exc:
            self.status.emit(f"Error: {exc}")
            self.finished.emit(None)


# ───────────────────────── main widget ───────────────────────────
class ethernet_winspec(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("remote_winspec.ui", self)

        self.logic = ethernet_winspec_logic()

        # ── Replace QGraphicsView with pyqtgraph PlotWidget ──
        gv = self.graphicsView
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setParent(self)
        self.plot_widget.setGeometry(gv.geometry())
        self.plot_widget.setBackground("w")
        gv.hide()

        self.plot_widget.setLabel("bottom", "Wavelength", units="nm")
        self.plot_widget.setLabel("left", "Counts")
        self.plot_widget.setTitle("Spectrum")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        self.spectrum_curve = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color=(31, 119, 180), width=1.5)
        )

        self.avg_region = pg.LinearRegionItem(
            values=[self.logic.AVG_WL_MIN_NM, self.logic.AVG_WL_MAX_NM],
            movable=False,
            brush=pg.mkBrush(255, 0, 0, 30),
        )
        self.avg_region.setZValue(-10)
        self.plot_widget.addItem(self.avg_region)
        self.avg_region.hide()

        self.avg_line = pg.InfiniteLine(
            angle=0, pen=pg.mkPen("r", width=1, style=QtCore.Qt.PenStyle.DashLine)
        )
        self.plot_widget.addItem(self.avg_line)
        self.avg_line.hide()

        # ── Crosshair cursor ──
        self.vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen("gray", width=0.8, style=QtCore.Qt.PenStyle.DotLine),
        )
        self.hline = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen("gray", width=0.8, style=QtCore.Qt.PenStyle.DotLine),
        )
        self.plot_widget.addItem(self.vline, ignoreBounds=True)
        self.plot_widget.addItem(self.hline, ignoreBounds=True)

        self.cursor_label = pg.TextItem(anchor=(0, 0), color="k")
        self.cursor_label.setFont(QtGui.QFont("Consolas", 9))
        self.plot_widget.addItem(self.cursor_label, ignoreBounds=True)

        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        self._wl = np.array([])
        self._spec = np.array([])

        # ── Status label ──
        self.status_label = QtWidgets.QLabel("Ready", self)
        btn_geom = self.capture_once.geometry()
        self.status_label.setGeometry(
            gv.geometry().x(),
            btn_geom.y() + btn_geom.height() + 10,
            gv.geometry().width(),
            20,
        )
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # ── Continuous-capture state ──
        self._continuous = False
        self._capture_count = 0

        # ── Connect buttons ──
        self.capture_once.clicked.connect(self._on_capture_once)
        self.capture_cont.clicked.connect(self._on_capture_cont)
        self.stop.clicked.connect(self._on_stop)

        # ── Thread bookkeeping ──
        self._worker_thread = None
        self._worker = None

    # ...................... button state helpers ..................
    def _set_buttons_capturing(self, continuous: bool):
        self.capture_once.setEnabled(False)
        self.capture_cont.setEnabled(False)
        self.stop.setEnabled(continuous)
        self.int_time.setEnabled(not continuous)
        self.accumilations.setEnabled(not continuous)

    def _set_buttons_idle(self):
        self.capture_once.setEnabled(True)
        self.capture_cont.setEnabled(True)
        self.stop.setEnabled(False)
        self.int_time.setEnabled(True)
        self.accumilations.setEnabled(True)

    # ...................... cursor tracking ......................
    def _on_mouse_moved(self, pos):
        if len(self._wl) == 0:
            return

        vb = self.plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()

        idx = int(np.clip(np.searchsorted(self._wl, x), 0, len(self._wl) - 1))
        snap_x = self._wl[idx]
        snap_y = self._spec[idx]

        self.vline.setPos(snap_x)
        self.hline.setPos(snap_y)

        self.cursor_label.setText(f" λ = {snap_x:.2f} nm\n counts = {snap_y:.1f}")
        view_range = vb.viewRange()
        self.cursor_label.setPos(view_range[0][0], view_range[1][1])

    # ...................... single capture .......................
    def _on_capture_once(self):
        if self._worker_thread is not None and self._worker_thread.isRunning():
            return
        self._continuous = False
        self._set_buttons_capturing(continuous=False)
        self._launch_worker()

    # ...................... continuous capture ....................
    def _on_capture_cont(self):
        if self._worker_thread is not None and self._worker_thread.isRunning():
            return
        self._continuous = True
        self._capture_count = 0
        self._set_buttons_capturing(continuous=True)
        self.status_label.setText("Continuous capture started …")
        self._launch_worker()

    def _on_stop(self):
        self._continuous = False
        self.status_label.setText("Stopping after current acquisition …")

    # ...................... shared worker launch ..................
    def _launch_worker(self):
        int_time = self.int_time.value()
        accumulations = self.accumilations.value()

        thread = QtCore.QThread()
        worker = AcquireWorker(self.logic, int_time, accumulations)
        worker.moveToThread(thread)

        # worker.finished  → update the plot (thread still alive here, that's fine)
        # thread.finished  → maybe launch next cycle (thread is fully stopped)
        thread.started.connect(worker.run)
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_acquire_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)

        # prevent garbage collection – store references
        self._worker_thread = thread
        self._worker = worker

        thread.start()

    # ...................... callbacks ............................
    def _on_status(self, msg: str):
        if self._continuous:
            self.status_label.setText(f"[#{self._capture_count + 1}] {msg}")
        else:
            self.status_label.setText(msg)

    def _on_acquire_done(self, result):
        """Called when the worker emits finished – thread is still alive.
        Safe to update the plot here, but do NOT create a new thread yet."""
        if result is None:
            # On error in continuous mode, stop the loop
            if self._continuous:
                self._continuous = False
            return

        self._capture_count += 1
        wl, spectrum, avg = result

        self._wl = wl
        self._spec = spectrum

        self.spectrum_curve.setData(wl, spectrum)

        self.avg_region.setRegion(
            [self.logic.AVG_WL_MIN_NM, self.logic.AVG_WL_MAX_NM]
        )
        self.avg_region.show()
        self.avg_line.setValue(avg)
        self.avg_line.show()

        self.plot_widget.setTitle(
            f"Spectrum – {Path(self.logic.last_spe_path).name}"
        )
        self.plot_widget.autoRange()

    def _on_thread_finished(self):
        """Called after the QThread has fully stopped.
        Safe to launch a new thread here if continuous mode is active."""
        if self._continuous:
            self._launch_worker()
        else:
            self._set_buttons_idle()
            if self._capture_count > 1:
                self.status_label.setText(
                    f"Stopped after {self._capture_count} captures."
                )


# ───────────────────────── entry point ───────────────────────────
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ethernet_winspec()
    window.show()
    sys.exit(app.exec())