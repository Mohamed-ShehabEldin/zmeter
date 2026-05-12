from pylablib.devices import Andor
import time


cam = Andor.AndorSDK2Camera(temperature=-90, fan_mode="full")  # connect to the camera  # camera should be connected first
spec = Andor.ShamrockSpectrograph()

cam.set_temperature(temperature=-90, enable_cooler=True)
while True:
    time.sleep(10)
    Tem=cam.get_temperature()
    print('Temperature=',Tem)
    if Tem<-80:
        break

# while cam.get_temperature_status() != "stabilized":
#     print(cam.get_temperature())
#     time.sleep(10)
cam.set_read_mode("fvb")
cam.set_trigger_mode("int")
cam.set_vsspeed(0)
cam.set_amp_mode(channel=1, hsspeed=0, preamp=0)
cam.set_acquisition_mode("single", setup_params=True)
cam.set_exposure(100)





spec.setup_pixels_from_camera(cam)  # setup camera sensor parameters (number and size of pixels) for wavelength calibration
spec.set_wavelength(633E-9)  # set center wavelength
wavelengths = spec.get_calibration()  # return array of wavelength corresponding to each pixel
h=4.135667696e-15
c=299792458
energy_meV=h*c/wavelengths*1000
laser_meV=h*c/632.81e-9*1000
energy_meV=laser_meV-energy_meV

print(cam.get_all_vsspeeds())
print(cam.get_all_amp_modes())
# 1D array of the corresponding spectrum intensities
spectrum = cam.snap(timeout=1000)[0] # after setting fvb, snap gives a 1*1024 array




import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(energy_meV,spectrum)

plt.show()

cam.close()
spec.close()


# setup_accum_mode(num_acc, cycle_time_acc=0)
# 

# start_acquisition(*args, **kwargs)
# stop_acquisition()