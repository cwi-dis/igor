"""Linux kernel watchdog support"""
import time
import thread

watchdog_device = None
watchdog_timeout = 60
stop_feeding = time.time() + watchdog_timeout

def watchdog(timeout=None, device='/dev/watchdog'):
    """Initialize and/or feed the watchdog"""
    global watchdog_device
    global watchdog_timeout
    global stop_feeding
    # Close the watchdog, if that is what is wanted
    if timeout == 0:
        if watchdog_device:
            watchdog_device.magic_close()
            watchdog_device = None
            return "watchdog closed\n"
    # Open the watchdog, if needed
    rv = ""
    if not watchdog_device:
        import watchdogdev
        watchdog_device = watchdogdev.watchdog(device)
        thread.start_new_thread(_feeder, ())
        rv += "watchdog opened\n"
    # Set the timeout, if needed
    if timeout:
        watchdog_timeout = int(timeout)
        rv += "watchdog timeout set to %d\n" % watchdog_timeout
    # Feed the dog
    watchdog_device.write('\n')
    stop_feeding = time.time()+watchdog_timeout
    rv += "watchdog fed\n"
    return rv

def _feeder():
    while watchdog_device:
        if time.time() < stop_feeding:
            watchdog_device.write('\n')
        time.sleep(2)
