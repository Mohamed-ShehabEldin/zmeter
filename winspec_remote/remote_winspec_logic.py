# Move this to folder as instrument "winspec ethernet"
import os
import time
from PyQt6.QtTest import QTest
from PyQt6 import QtCore



class ethernet_winspec_logic:
    def set_print_A(self, val):
        print("print val: ", val)
    def set_winspec_acquire(self, val):
        print("inside it now")
        """
        Creates 'trigger.txt' in the given directory,
        waits up to 2 minutes for 'done.txt' to appear,
        deletes it when found, and returns 0.
        Returns 1 if timeout occurs.
        """
        dir = r"\\192.168.0.1\trigger"
        try:
            os.makedirs(dir, exist_ok=True)
            trigger_path = os.path.join(dir, "trigger.txt")
            done_path = os.path.join(dir, "done.txt")
            # delete done file if it is there
            if os.path.exists(done_path):
                os.remove(done_path)
                print("old done.txt deleted by python")
            # Create trigger.txt
            with open(trigger_path, "w") as f:
                f.write("triggered\n")
            print("trigger.txt created by python")
            QTest.qWait(200)
            os.remove(trigger_path)
            print("trigger.txt deleted by python")

            # Wait up to 120 seconds for done.txt
            timeout = 120  # seconds
            start_time = time.time()

            while time.time() - start_time < timeout:
                if os.path.exists(done_path):
                    os.remove(done_path)
                    return 0
                QTest.qWait(200)  # wait 200 ms while keeping Qt responsive
            print("time out!")
            return 1  # timeout
        except Exception as e:
            print("Error:", e)
            return -1
        
if __name__ == "__main__":
    logic=ethernet_winspec_logic()
    logic.set_winspec_acquire(12)