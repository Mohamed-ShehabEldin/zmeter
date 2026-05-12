# Move this to folder as instrument "winspec ethernet"
import os
import time
from PyQt6.QtTest import QTest
from PyQt6 import QtCore
import random



class noninstrumental_logic:
    def set_wait(self,val):
        print("waiting: ", val, "s")
        # QTest.qWait(val*1000)
        time.sleep(val)

    def get_random(self):
        return random.random()
    
if __name__ == "__main__":
    logic = noninstrumental_logic()
    logic.set_wait(2)
    print("Random value:", logic.get_random())