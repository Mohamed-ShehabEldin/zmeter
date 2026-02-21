# Move this to folder as instrument "winspec ethernet"
import os
import time
from PyQt6.QtTest import QTest
from PyQt6 import QtCore, uic
try:
    from .remote_winspec_logic import ethernet_winspec_logic
except:
    from remote_winspec_logic import ethernet_winspec_logic
from PyQt6 import QtWidgets, uic, QtCore
import sys

# CHANGE 1: Inherit from QWidget (or QMainWindow), NOT QThread
class ethernet_winspec(QtWidgets.QWidget): 
    def __init__(self):
        # CHANGE 2: Initialize the QWidget parent
        super(ethernet_winspec, self).__init__() 
        
        # This loads the UI file. It expects 'self' to be a widget, which it now is.
        # uic.loadUi("keithley24xx.ui", self) 
        
        self.logic = ethernet_winspec_logic()

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = ethernet_winspec()
#     window.show()
#     app.exec()