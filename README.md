# ZMeter

A Python-based toolkit for precision electro-optical measurements.

Last updated: May 11th, 2026

---

## Overview

**zmeter** is designed to simplify automated electrical measurements in research and industrial settings. It provides a user-friendly interface and scripts for controlling DAQ and VISA-compatible instruments via Python, supporting a variety of measurement protocols and data analysis workflows.

**List of supported instruments:**
- Opticool cryostat from Quantum design
- Lock-in amplifier SR830
- Lock-in amplifier SR860
- Source-meter Keithley 2400
- Source-meter Keithley 2450
- National Instrument Data Aquaistion Nidaq
- Thorlabs power meter PM100x series
- Andor camera and Shamrock spectrometer through pylablib
  
**Upcoming updates:**

https://docs.google.com/spreadsheets/d/1Z7CwgLiQfW-cj0vrgtMSLtcA21VU4lwzqTvWpBX69pw/edit?usp=sharing
- Montana instruments cryostat
- Attodry crystat
- Four9 Cryostat
- Digital Multimeter 34401A (Agilent)
- Lock-in amplifier MFLI (Zurich Instruments)
- RF generator SynthHD (Windfreak Technologies)
- Spectrum Analyzer N9324C (Keysight)
- Insight X3
---

## Features

- Simple GUI for measurement configuration and live plotting
- Scripting support for custom protocols
- Automatic data saving and export (CSV, Excel)
- Modular design for easy device or protocol extension
- Scan getters can return either scalar values or array spectra. Array spectra
  are stored in the scan data and plotted as spectrum maps, with wavelength or
  pixel axis on X, scan/count/wait axis on Y, and intensity as color.

---

## Andor Spectrum Scans

The Andor module is optional in `start_zmeter.py` and uses the newer
`Andor/andor_hardware_new.py` pylablib backend. If the Andor dependencies or
vendor drivers are missing, the rest of ZMeter can still start.

Scan-facing Andor channels include:
- Setters: `temperature`, `exposure_time`, `center_wavelength`
- Getters: `temperature`, `exposure_time`, `center_wavelength`, `spectrum`,
  `spectrum_mean`, `spectrum_sum`

`get_spectrum()` returns a `2 x N` array:
- row 0: wavelength calibration from Shamrock when available, otherwise pixel
  index
- row 1: measured intensity

For a voltage/time/count sweep with spectra, make a line plot with the scan
axis as the selected X channel and `andor_0_spectrum` as the selected Y channel.
The plot automatically switches to a spectrum map instead of trying to draw a
single scalar line.

---

## Installation


Follow these steps to get **zmeter** up and running on Windows. These instructions assume you’re using Command Prompt.

### 1. Install Python 3.13+

1. Download the latest stable release (e.g. 3.13.5) from [python.org](https://python.org).
2. During installation, **check** “Add Python 3.13 to PATH.”

Verify:

```cmd
python --version
```

### 2. Install Miniconda

Miniconda will simplify package and environment management.

1. Download and install silently:

   ```cmd
   curl -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe \
     -o .\miniconda.exe
   start /wait "" .\miniconda.exe /S
   del .\miniconda.exe
   ```
2. Add Conda to your PATH by selecting the checkbox during installation or by running:

   ```cmd
   conda init
   ```

Verify:

```cmd
conda --version
```

### 3. Install NI Package Manager & Runtimes

You’ll need National Instruments drivers to communicate with instruments. Grab a coffee -- it may take a while.

1. Download the NI Package Manager installer from:
   [https://www.ni.com/en/support/downloads/software-products/download/unpackaged.package-manager.322516.html](https://www.ni.com/en/support/downloads/software-products/download/unpackaged.package-manager.322516.html)
2. Run the installer and then, via NI Package Manager, install:

   * **NI‑VISA**
   * **NI‑DAQmx Runtime**

### 4. Install Git

If you don’t already have it:

1. Download and install from [git-scm.com](https://git-scm.com/downloads).
2. Confirm with:

```cmd
git --version
```

### 5. Clone the Repository

```cmd
cd $HOME\Documents
git clone https://github.com/lictailer/zmeter.git
cd zmeter
```

### 6. Create & Activate the Conda Environment

```cmd
conda env create -f environment.yml
conda activate zmeter_July2025
```

> If this is your first time using Conda in this shell, you may need to run `conda init` and restart your terminal.

### 7. First Launch

With the environment active, start **zmeter**:

```cmd
python start_zmeter.py
```

You’re all set! If you encounter any issues, please check the [Troubleshooting](#troubleshooting) section or open an issue on GitHub.



# Comments 

You also need to install drivers for USB-GPIB cable

Check if this adapter shows up in the NI-MAX app

Then if driver is missing, use NI Package manager to install the driver


# Things that need to be added:

bugfix SR830

add Montana

add hp34401a
