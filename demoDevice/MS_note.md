Device_logic: is where the app looks for "get" and "set"
Device_main: is a gui, self contained (can run alone as a .py file), used to set up parameters

mainwindow: contains instance of Device_main GUI, Device_main itself set up an instance of Device_logic which is the final level where "get" and "set" is adressed.