Thorlabs Kinesis placeholder
============================

This folder is intentionally not used to store the full Thorlabs Kinesis
installation in git.

K10CR1 support expects the Thorlabs Kinesis DLLs to be available in one of
these locations:

1. Standard Windows install:
   C:\Program Files\Thorlabs\Kinesis

2. Project-local copy:
   <zmeter root>\Kinesis

3. Device-local copy:
   <zmeter root>\k10cr1\Kinesis

The required DLL for the K10CR1 loader is:
Thorlabs.MotionControl.IntegratedStepperMotors.dll

The full Kinesis installation usually also includes dependency DLLs such as:
Thorlabs.MotionControl.DeviceManager.dll

If K10CR1 fails to import, download and install Thorlabs Kinesis from Thorlabs,
or copy the Kinesis installation folder into one of the local paths above.
