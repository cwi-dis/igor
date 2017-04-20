# watchdog - reboot linux system in case of problems

Reboots the host system in case of problems. 

A plugin that opens the Linux watchdog device ```/dev/watchdog```. The parameter ```timeout``` specifies after how many seconds the watchdog will fire and reboot the system, unless the watchdog plugin is accessed again before that timeout. Can be used to make the Igor machine reboot when Igor hangs, or when anomalous conditions are detected (and there is reason to believe a reboot will resolve these issues:-).


