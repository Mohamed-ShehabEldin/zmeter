# Move this to folder as instrument "winspec ethernet"
import os
import time
from PyQt6.QtTest import QTest
from PyQt6 import QtCore



class noninstrumental_logic:
    def set_wait(self,val):
        print("waiting: ", val, "s")
        # QTest.qWait(val*1000)
        time.sleep(val)