#!/bin/bash

if [ ${UID} == '0' ]; then
    echo -e "Don't run this script as root! - aborting ..."
    exit 1
fi

if [ ! -d ~/klipper ]; then
   echo "Klipper must be installed on your system - aborting ..."
   exit 1
else
   echo "Klipper detected - let's go ..."
fi

echo "AUTO_OFFSET_Z - let's go ..."
rm -f ~/klipper/klippy/extras/auto_offset_z.py 2>&1 > /dev/null
sudo systemctl disable auto_offset_z
rm -f /etc/systemd/system/auto_offset_z.service 2>&1 > /dev/null
sudo systemctl daemon-reload
echo "done."
