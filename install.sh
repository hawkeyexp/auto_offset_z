#!/bin/bash

if [ ${UID} == '0' ]; then
    echo -e "Don't run this script as root! - aborting ..."
    exit 1
fi

if [ ! -d ~/klipper ]; then
   echo -e "Klipper must be installed on your system - aborting ..."
   exit 1
else
   echo "Klipper detected - let's go ..."
fi

if [ ! -d ~/auto_offset_z ]; then
   echo -e "AUTO_OFFSET_Z is missing - aborting ..."
   exit 1
else
   echo -e "AUTO_OFFSET_Z - let's go ..."
   rm -f ~/klipper/klippy/extras/auto_offset_z.py 2>&1>/dev/null
   ln -s ~/auto_offset_z/auto_offset_z.py ~/klipper/klippy/extras/auto_offset_z.py
   sudo /bin/sh -c "cat > /etc/systemd/system/auto_offset_z.service" << EOF
   [Unit]
   Description=Dummy Service for auto_offset_z plugin
   After=klipper.service
   [Service]
   Type=oneshot
   RemainAfterExit=yes
   ExecStart=/bin/sleep 1
   ExecStartPost=/usr/sbin/service klipper restart
   [Install]
   WantedBy=multi-user.target
   EOF
   sudo systemctl daemon-reload
   sudo systemctl enable auto_offset_z
   sudo systemctl restart auto_offset_z
   echo -e "done."
fi

exit 0
