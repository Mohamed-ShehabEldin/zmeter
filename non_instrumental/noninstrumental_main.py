# Move this to folder as instrument "winspec ethernet"
import os
import time
from PyQt6.QtTest import QTest
from PyQt6 import QtCore, uic
try: # to run from outside the folder
    from .noninstrumental_logic import noninstrumental_logic
except: #to run from inside
    from noninstrumental_logic import noninstrumental_logic
from PyQt6 import QtWidgets, uic, QtCore
import sys

# CHANGE 1: Inherit from QWidget (or QMainWindow), NOT QThread
class noninstrumental(QtWidgets.QWidget): 
    def __init__(self):
        # CHANGE 2: Initialize the QWidget parent
        super(noninstrumental, self).__init__() 
        
        # This loads the UI file. It expects 'self' to be a widget, which it now is.
        # uic.loadUi("keithley24xx.ui", self) 
        
        self.logic = noninstrumental_logic()

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = ethernet_winspec()
#     window.show()
#     app.exec()