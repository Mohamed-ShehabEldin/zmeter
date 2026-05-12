# Andor Camera And Shamrock Spectrometer

This module provides the Andor camera widget, scan-facing logic, and pylablib
hardware wrappers.

## Files

- `andor_main.py`: PyQt widget wrapper and UI bindings.
- `andor_logic.py`: scan-facing logic, Qt signals, acquisition jobs, and
  `get_*` / `set_*` methods discovered by ZMeter.
- `andor_hardware_new.py`: compact pylablib wrapper for Andor SDK2 cameras and
  Shamrock spectrometers.
- `simple_minimal.py` and `zumeng_script.py`: local hardware diagnostic scripts.

## Scan Channels

Recommended setters:
- `temperature`
- `exposure_time`
- `center_wavelength`

Recommended getters:
- `temperature`
- `exposure_time`
- `center_wavelength`
- `spectrum`
- `spectrum_mean`
- `spectrum_sum`

`start_zmeter.py` contains commented channel filters for enabling only these
channels when `andor_0` is added to the equipment dictionary.

## Spectrum Getter

`AndorCameraLogic.get_spectrum()` is the main measurement getter for spectroscopy.
It snaps one camera image and returns a `2 x N` numpy array:

- row 0: Shamrock wavelength calibration when available, otherwise pixel index
- row 1: measured intensity

The getter stores the latest axis and intensity in `last_spectrum_axis` and
`last_spectrum` for UI-side reuse.

For scalar scans, use:
- `get_spectrum_mean()`
- `get_spectrum_sum()`

These call `get_spectrum()` and return a single intensity summary.

## Plotting Behavior

ZMeter scan storage now accepts array-valued getter results. When a line plot
uses `andor_0_spectrum` as its Y channel, `core/all_plots.py` automatically
switches to a spectrum map:

- X axis: wavelength or pixel axis
- Y axis: selected scan/count/wait axis
- Color: intensity

This keeps old scalar line plots unchanged while allowing voltage/time/count
sweeps to collect full spectra at each scan point.
