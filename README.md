# pypilot_ray
Raymarine st2000 ui emulator for pypilot

Allows hooking up the origial buttons of the raymarine st2000 to pypilot, using the same button combinations, but having some extra facilities for adjusting pid gains.

Keys and LED are connected to GPIO and ground.
```
KEY   BCM
====  =======
STBY  GPIO-21
AUTO  GPIO-26
-1    GPIO-5
+1    GPIO-13
-10   GPIO-6
+10   GPIO-12
LED   GPIO-19
```
To install:
- cd ~tc/pypilot/
- git clone git://github.com/marcobergman/pypilot_ray
- change /etc/sv/pypilot_lcd/run
      exec nice -n 5 chpst python /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/ray.py
      
To start
- Will autostart
- manual: sudo sv restart pypilot


Example:
```
# copy ray.py to tinypilot:
tc@pypilot:~$ mkdir /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/
tc@pypilot:~$ scp pi@10.10.10.1:ray.py /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/ray.py

# test:
tc@pypilot:~$ sudo python3 /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/ray.py
init...
connected
key = 2, mode = 0
Auto

# adjust pypilot_hat service:
# replace with: exec nice -n 5 chpst -b pypilot_ray python3.6 /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/ray.py
tc@pypilot:~$ sudo vi /etc/sv/pypilot_hat/run
# make change persistent:
tc@pypilot:~$ filetool.sh -b
tc@pypilot:~$ sudo reboot

tc@pypilot:~$ ps -ef | grep ray
4023 root     {python3.6} pypilot_ray /mnt/mmcblk0p2/tinypilot/pypilot/pypilot_ray/ray.py
```
