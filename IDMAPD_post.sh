#!/bin/sh
#==============================================================================
#
#       Change Log:
#
#       When             Who            What
#       ====             ===            ====
#       23-Mar-2011      Ryan Yard      IDMAPD setup Post-install Script
#
#==============================================================================
export PATH=$PATH:/bin:/usr/bin:/sbin:/usr/sbin
if [ ! -f /etc/env-custom.conf ]; then
        echo "No /etc/env-custom.conf found.   That's needed to run $0"
        exit 1
fi
. /etc/env-custom.conf

echo ---------------------------------------------
echo IDMAPD setup Post-install Script
echo ---------------------------------------------

sed -i -r -e 's|^#?Domain.*|Domain = '$DOMAIN'|g' \
          -e 's|^Nobody-User.*|Nobody-User = root|g' \
          -e 's|^Nobody-Group.*|Nobody-Group = root|g' \
          /etc/idmapd.conf

# make sure rpcidmapd runs at startup
chkconfig rpcidmapd on > /dev/null 2>&1

# check if rpcidmapd is running
service rpcidmapd status > /dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "Starting rpcidmapd..."
	service rpcidmapd start
fi

#Set NFSv3 as default autoneg mount option
sed -i 's/^# Defaultvers=4.*$/Defaultvers=3/' /etc/nfsmount.conf

echo Completed
echo
