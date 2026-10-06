#!/usr/bin/env bash
# start_eyes.sh
# Automatically finds left/right eye modules by serial number and launches demo_dual.

set -e

# Serial numbers burned into hardware — do not change
SERIAL_LEFT="70:04:1D:D3:DD:7C"
SERIAL_RIGHT="F4:12:FA:9D:8E:94"

# Direction (physical mounting orientation)
DIRECTION=${1:-4}

PORT_LEFT=""
PORT_RIGHT=""

for dev in /dev/ttyACM[0-9]*; do
    serial=$(udevadm info "$dev" 2>/dev/null | grep "ID_SERIAL_SHORT" | cut -d= -f2)
    if [ "$serial" = "$SERIAL_LEFT" ]; then
        PORT_LEFT="$dev"
    elif [ "$serial" = "$SERIAL_RIGHT" ]; then
        PORT_RIGHT="$dev"
    fi
done

if [ -z "$PORT_LEFT" ] || [ -z "$PORT_RIGHT" ]; then
    echo "ERROR: Could not find both eye modules."
    [ -z "$PORT_LEFT" ]  && echo "  LEFT  ($SERIAL_LEFT)  : not found"
    [ -z "$PORT_RIGHT" ] && echo "  RIGHT ($SERIAL_RIGHT) : not found"
    echo "Check USB connection and try again."
    exit 1
fi

echo "LEFT  eye → $PORT_LEFT"
echo "RIGHT eye → $PORT_RIGHT"
echo ""

# Center both eyes after rosserial connects (runs in background)
(sleep 5 && rosrun eye_display eye_set_pose_once.py --x 0 --y 0) &

roslaunch eye_display demo_dual.launch \
    port_left:="$PORT_LEFT" \
    port_right:="$PORT_RIGHT" \
    direction_left:="$DIRECTION" \
    direction_right:="$DIRECTION"
