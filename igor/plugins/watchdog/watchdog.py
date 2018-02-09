"""Linux kernel watchdog support"""
import time
import thread

class WatchdogClass:
    def __init__(self):
        self.watchdog_device = None
        self.watchdog_timeout = 60
        self.stop_feeding = time.time() + self.watchdog_timeout
        watchdogClass._singleton = self
        
    def index(self, timeout=None, device='/dev/watchdog', token=None):
        """Initialize and/or feed the watchdog"""
        # Close the watchdog, if that is what is wanted
        if timeout == 0:
            if self.watchdog_device:
                self.watchdog_device.magic_close()
                self.watchdog_device = None
                return "watchdog closed\n"
        # Open the watchdog, if needed
        rv = ""
        if not self.watchdog_device:
            import watchdogdev
            self.watchdog_device = watchdogdev.watchdog(device)
            thread.start_new_thread(_feeder, ())
            rv += "watchdog opened\n"
        # Set the timeout, if needed
        if timeout:
            self.watchdog_timeout = int(timeout)
            rv += "watchdog timeout set to %d\n" % self.watchdog_timeout
        # Feed the dog
        self.watchdog_device.write('\n')
        self.stop_feeding = time.time()+self.watchdog_timeout
        rv += "watchdog fed\n"
        return rv

    def _feeder(self):
        while self.watchdog_device:
            if time.time() < self.stop_feeding:
                self.watchdog_device.write('\n')
            time.sleep(2)

def igorPlugin(pluginName, pluginData):
    if not WatchdogClass._singleton:
        WatchdogClass._singleton = WatchdogClass()
    return WatchdogClass._singleton
    
