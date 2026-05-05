import os
import re
import time
import shutil
from pathlib import Path

import numpy as np
import imageio.v2 as imageio
from PyQt6.QtTest import QTest


class ethernet_winspec_logic:
    # ----------------------------
    # Paths (edit these)
    # ----------------------------
    TRIGGER_DIR = r"\\192.168.0.1\trigger"
    # TRIGGER_DIR = r"Y:"

    DATS_DIR = r"\\192.168.0.1\trigger\data\spe"
    # DATS_DIR = r"Y:\data\spe"

    DATS_TXT_DIR = r"\\192.168.0.1\trigger\data\txt"
    # DATS_TXT_DIR = r"Y:\data\txt"

    REF_WL_TXT_PATH = r"\\192.168.0.1\trigger\data\negative_tempelate.txt"
    # REF_WL_TXT_PATH = r"Y:\data\negative_tempelate.txt"

    # Local cache / local copied SPE files
    LOCAL_DATA_DIR = r"C:\Users\opticool\Documents\Mohamed\winspec_data"
    LAST_INDEX_CACHE_PATH = r"C:\Users\opticool\Documents\Mohamed\winspec_data\last_spe_index.txt"

    # ----------------------------
    # File naming (adjust if needed)
    # ----------------------------
    SPE_PREFIX = "ss"
    SPE_INDEX_REGEX = re.compile(r"^ss(\d+)\.spe$", re.IGNORECASE)

    # ----------------------------
    # Timing
    # ----------------------------
    TRIAL_TIMEOUT_S = 120.0
    OVERALL_TIMEOUT_S = 600.0
    MAX_TRIALS = None

    TRIGGER_PULSE_MS = 200
    POLL_AFTER_TRIAL_MS = 100
    BETWEEN_TRIALS_MS = 100

    # After trigger: wait for expected next filename to appear
    NEXT_FILE_APPEAR_TIMEOUT_S = 120.0
    NEXT_FILE_INDEX_WINDOW = 8  # checks idx+1 ... idx+8 (cheap)

    # Wait for writer to release + finish file
    FILE_UNLOCK_TIMEOUT_S = 600.0
    FILE_POLL_MS = 250
    SIZE_STABLE_CHECKS = 4
    MIN_SPE_SIZE_BYTES = 4096  # avoid tiny partial files

    # Averaging range
    AVG_WL_MIN_NM = 700.0
    AVG_WL_MAX_NM = 790.0

    def __init__(self):
        self.last_spe_path = None
        self.last_spe_index = None

    # ----------------------------
    # Cache helpers (fast startup)
    # ----------------------------
    def _load_cached_last_index(self):
        try:
            p = Path(self.LAST_INDEX_CACHE_PATH)
            if not p.exists():
                return None
            return int(p.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def _save_cached_last_index(self, idx: int):
        try:
            p = Path(self.LAST_INDEX_CACHE_PATH)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(int(idx)), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Could not save last index cache: {e}")

    # ----------------------------
    # Fast folder/index helpers
    # ----------------------------
    def _iter_spe_entries(self):
        """Fast iteration for huge folders using os.scandir."""
        try:
            with os.scandir(self.DATS_DIR) as it:
                for entry in it:
                    if entry.is_file() and entry.name.lower().endswith(".spe"):
                        yield entry
        except FileNotFoundError:
            return

    def _get_max_spe_index(self) -> int:
        """
        Expensive fallback scan (used only if cache is missing/wrong).
        """
        max_idx = -1
        for entry in self._iter_spe_entries():
            m = self.SPE_INDEX_REGEX.match(entry.name)
            if m:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
        if max_idx < 0:
            raise FileNotFoundError(
                f"No matching .SPE files found in {self.DATS_DIR} with prefix '{self.SPE_PREFIX}'"
            )
        return max_idx

    def _candidate_spe_paths(self, idx: int):
        base = Path(self.DATS_DIR) / f"{self.SPE_PREFIX}{idx}"
        return [base.with_suffix(".SPE"), base.with_suffix(".spe")]

    def _find_existing_candidate(self, idx: int):
        for p in self._candidate_spe_paths(idx):
            if p.exists():
                return p
        return None

    def _wait_for_next_index_file(self, start_idx: int):
        """
        Check only a small index window ahead (very fast).
        """
        t0 = time.time()
        while time.time() - t0 < self.NEXT_FILE_APPEAR_TIMEOUT_S:
            for idx in range(start_idx + 1, start_idx + 1 + self.NEXT_FILE_INDEX_WINDOW):
                p = self._find_existing_candidate(idx)
                if p is not None:
                    return idx, p
            QTest.qWait(self.FILE_POLL_MS)
        return None, None

    def _wait_until_readable_and_stable(self, p: Path) -> bool:
        """
        Wait until:
          - file can be opened (not locked)
          - size >= MIN_SPE_SIZE_BYTES
          - size stays unchanged for SIZE_STABLE_CHECKS polls
        """
        t0 = time.time()
        last_size = None
        stable = 0

        while time.time() - t0 < self.FILE_UNLOCK_TIMEOUT_S:
            try:
                with open(p, "rb"):
                    pass  # lock check

                size = p.stat().st_size
                if size < self.MIN_SPE_SIZE_BYTES:
                    stable = 0
                    last_size = size
                    QTest.qWait(self.FILE_POLL_MS)
                    continue

                if last_size is not None and size == last_size:
                    stable += 1
                else:
                    stable = 0
                last_size = size

                if stable >= self.SIZE_STABLE_CHECKS:
                    return True

            except (PermissionError, FileNotFoundError, OSError):
                stable = 0

            QTest.qWait(self.FILE_POLL_MS)

        return False

    def _copy_to_local(self, src: Path) -> Path:
        local_dir = Path(self.LOCAL_DATA_DIR)
        local_dir.mkdir(parents=True, exist_ok=True)

        dst = local_dir / src.name
        if dst.exists():
            dst = local_dir / f"{src.stem}_{int(time.time())}{src.suffix}"

        shutil.copy2(src, dst)
        return dst

    # ----------------------------
    # Trigger / acquisition
    # ----------------------------
    def winspec_acquire_trial(self, val) -> int:
        """
        Single trigger pulse and wait for done.txt.
        Returns:
          0 success (done.txt seen)
          1 timeout
         -1 error
        """
        try:
            os.makedirs(self.TRIGGER_DIR, exist_ok=True)
            trigger_path = os.path.join(self.TRIGGER_DIR, "trigger.txt")
            done_path = os.path.join(self.TRIGGER_DIR, "done.txt")

            if os.path.exists(done_path):
                os.remove(done_path)

            with open(trigger_path, "w") as f:
                f.write("triggered\n")
            print("trigger.txt created by python")

            QTest.qWait(self.TRIGGER_PULSE_MS)

            if os.path.exists(trigger_path):
                os.remove(trigger_path)
            print("trigger.txt deleted by python")

            t0 = time.time()
            while time.time() - t0 < self.TRIAL_TIMEOUT_S:
                if os.path.exists(done_path):
                    os.remove(done_path)
                    return 0
                QTest.qWait(200)

            print("trial timeout waiting for done.txt!")
            return 1

        except Exception as e:
            print("Error in winspec_acquire_trial:", e)
            return -1

    def set_winspec_acquire(self, val) -> int:
        """
        Fast working approach:
          - Use cached last index (no full scan on normal runs)
          - Trigger
          - Check only expected next file names
          - Fallback full scan only if cache path fails
        """
        # 1) Use cache first (fast)
        baseline_idx = self._load_cached_last_index()
        if baseline_idx is not None:
            print(f"Using cached SPE index: {baseline_idx}")
        else:
            # expensive fallback only if no cache
            try:
                baseline_idx = self._get_max_spe_index()
                print(f"Scanned baseline max SPE index: {baseline_idx}")
            except FileNotFoundError as e:
                print(e)
                return -1

        start_overall = time.time()
        trials = 0
        did_fallback_rescan = False

        while True:
            if self.MAX_TRIALS is not None and trials >= self.MAX_TRIALS:
                print("Stopped: reached MAX_TRIALS")
                return 1
            if time.time() - start_overall > self.OVERALL_TIMEOUT_S:
                print("Stopped: overall timeout")
                return 1

            trials += 1
            print(f"Trial #{trials}...")

            rc = self.winspec_acquire_trial(val)
            if rc == -1:
                return -1

            QTest.qWait(self.POLL_AFTER_TRIAL_MS)

            new_idx, new_path = self._wait_for_next_index_file(baseline_idx)
            if new_path is not None:
                self.last_spe_index = new_idx
                self.last_spe_path = Path(new_path)
                self._save_cached_last_index(new_idx)
                print(f"Success: new SPE detected: {Path(new_path).name}")
                return 0

            # Cache may be stale (numbering reset, skipped far ahead, etc.)
            # Do one fallback rescan, then continue checking from the fresh max.
            if not did_fallback_rescan:
                try:
                    fresh_idx = self._get_max_spe_index()
                    print(f"[Fallback scan] fresh max SPE index: {fresh_idx}")
                    baseline_idx = fresh_idx
                    self._save_cached_last_index(fresh_idx)
                    did_fallback_rescan = True
                except FileNotFoundError:
                    pass

            QTest.qWait(self.BETWEEN_TRIALS_MS)

    # ----------------------------
    # Spectrum processing
    # ----------------------------
    def _load_wavelength_axis_from_txt(self, ref_txt_path: str) -> np.ndarray:
        # WinSpec exported txt: columns [wl, x, y, intensity]
        return np.loadtxt(ref_txt_path, delimiter="\t")[:, 0].astype(float)

    def _spe_to_winspec_ascii(self, spe_path: Path, out_txt_path: Path, wl_nm: np.ndarray, frame_index: int = 0):
        arr = np.asarray(imageio.imread(spe_path))
        frame = arr[frame_index] if arr.ndim == 3 else arr
        ny, nx = frame.shape

        if len(wl_nm) != nx:
            raise ValueError(f"{spe_path.name}: wl length {len(wl_nm)} != nx {nx}")

        out = np.empty((ny * nx, 4), dtype=float)
        k = 0
        for y in range(ny):
            for x in range(nx):
                out[k] = (wl_nm[x], x + 1, y + 1, frame[y, x])
                k += 1

        out_txt_path.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(
            out_txt_path,
            out,
            fmt=["%.6f", "%d", "%d", "%d"],
            delimiter="\t",
            newline="\r\n",
        )

    def get_avg_spectrum(self) -> float:
        """
        Uses the exact file found in set_winspec_acquire():
          - waits until file is unlocked/stable on the network share
          - copies to local folder
          - converts to txt in DATS_TXT_DIR
          - returns average counts over 700-790 nm
        """
        wl = self._load_wavelength_axis_from_txt(self.REF_WL_TXT_PATH)

        if self.last_spe_path is None:
            raise RuntimeError("No last SPE file recorded. Call set_winspec_acquire() first.")

        net_spe = Path(self.last_spe_path)

        if not self._wait_until_readable_and_stable(net_spe):
            raise TimeoutError(f"SPE file still locked/not stable: {net_spe}")

        local_spe = self._copy_to_local(net_spe)

        # convert to txt (network txt folder, as you wanted)
        out_dir = Path(self.DATS_TXT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_txt_path = out_dir / (local_spe.stem + ".txt")
        self._spe_to_winspec_ascii(local_spe, out_txt_path, wl)

        # average counts in wl window
        arr = np.asarray(imageio.imread(local_spe))
        frame = arr[0] if arr.ndim == 3 else arr
        if frame.ndim != 2:
            raise ValueError(f"Unexpected SPE shape for {local_spe.name}: {frame.shape}")

        spec_1d = frame.mean(axis=0).astype(float)
        if len(spec_1d) != len(wl):
            raise ValueError(f"{local_spe.name}: spectrum length {len(spec_1d)} != wl length {len(wl)}")

        mask = (wl >= self.AVG_WL_MIN_NM) & (wl <= self.AVG_WL_MAX_NM)
        if not np.any(mask):
            raise ValueError(
                f"No wavelengths in range {self.AVG_WL_MIN_NM}-{self.AVG_WL_MAX_NM} nm "
                f"(wl spans {wl.min()}-{wl.max()} nm)"
            )

        avg_spectrum = float(spec_1d[mask].mean())
        return avg_spectrum
    

    def get_GET_after_SET(self):
        logic = ethernet_winspec_logic()

        rc = logic.set_winspec_acquire(0)
        if rc == 0:
            avg = logic.get_avg_spectrum()
            return avg
        else:
            print("Acquire failed, rc =", rc)
            return -1

if __name__ == "__main__":
    logic = ethernet_winspec_logic()

    rc = logic.set_winspec_acquire(12)
    if rc == 0:
        avg = logic.get_avg_spectrum()
        print("avg_spectrum:", avg)
    else:
        print("Acquire failed, rc =", rc)