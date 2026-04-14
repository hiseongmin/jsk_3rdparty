#!/usr/bin/env python3
"""
joy_eye_status_ye.py
--------------------
Converts joystick (sensor_msgs/Joy) input into eye display commands.
Designed for SINGLE eye mode — run two instances with namespaces for dual-eye.

Uses timer-based publishing (not callback-based) for consistent rate.
Eye asset names are read from rosparam (registered by firmware), not hardcoded.

Based on k-okada's namespace refactoring.
Original joystick control by hiseongmin.
Dual-mode and edge parameters by heissereal (miyamichi).
"""

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
prev_eye_status = "normal"
prev_look_at = Point()
joy_msg = Joy()

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def joy_cb(msg):
    """Store latest joystick message for timer to process."""
    global joy_msg
    joy_msg = msg


def snap_axis(value):
    """Snap joystick axis value to 0.0 if within dead-band threshold."""
    return 0.0 if abs(value) < SNAP_THRESHOLD else value


def timer_cb(event):
    global prev_eye_status
    global prev_look_at
    global joy_msg
    msg = joy_msg

    # Get eye asset names from rosparam (registered by firmware)
    if rospy.has_param("eye_display/eye_asset/names"):
        eye_asset_names = rospy.get_param("eye_display/eye_asset/names")
    else:
        rospy.logwarn_throttle(5, "no eye_asset_names found from rosparam 'eye_display/eye_asset/names'")
        return

    # Need at least 2 axes for gaze control
    if len(msg.axes) <= 1:
        return

    # -- Expression (buttons) ----------------------------------------------
    eye_status = eye_asset_names[0]  # default to first (usually "normal")
    for i, name in enumerate(eye_asset_names):
        if i < len(msg.buttons) and msg.buttons[i] == 1:
            eye_status = name
            break

    # Publish eye status only when it changes
    if prev_eye_status != eye_status:
        rospy.loginfo("publish eye status: {}".format(eye_status))
        pub_status.publish(eye_status)
    prev_eye_status = eye_status

    # -- Gaze (axes) -------------------------------------------------------
    # mode_right: True = right side from front view = robot's left eye
    if rospy.has_param("eye_display/mode_right"):
        left_eye = rospy.get_param("eye_display/mode_right")
    else:
        rospy.logwarn_throttle(5, "no mode_right found from rosparam 'eye_display/mode_right'")
        return

    ax = snap_axis(float(msg.axes[0])) * -1  # invert so stick-left = eye-left
    ay = snap_axis(float(msg.axes[1]))

    # Mirror X axis based on which eye this instance controls
    axes_x = ax * (1 if left_eye else -1)
    axes_y = ay * -1

    look_at_x = (axes_x * (left_edge if axes_x > 0 else right_edge)) * (-1 if left_eye else 1)
    look_at_y = (axes_y * (bottom_edge if axes_y > 0 else upper_edge))

    # Apply calibration offset
    look_at_x += offset_x
    look_at_y += offset_y

    look_at = Point(look_at_x, look_at_y, 0)

    # Publish only when position actually changed
    if abs(prev_look_at.x - look_at.x) > 1e-4 or \
       abs(prev_look_at.y - look_at.y) > 1e-4:
        pub_look.publish(look_at)
    prev_look_at = look_at


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    rospy.loginfo("eye_st_from_joy node started")

    # Publishers — relative topic names (namespace added by launch file)
    pub_look = rospy.Publisher('eye_display/look_at', Point, queue_size=1)
    pub_status = rospy.Publisher('eye_display/eye_status', String, queue_size=1)

    # Eye movement range (pixels)
    left_edge   = rospy.get_param('~left_edge',    30.0)
    right_edge  = rospy.get_param('~right_edge',   30.0)
    upper_edge  = rospy.get_param('~upper_edge',   30.0)
    bottom_edge = rospy.get_param('~bottom_edge',  30.0)

    # Publish interval
    duration = rospy.Duration(rospy.get_param('~duration', 0.05))

    # Stick return dead-band compensation
    SNAP_THRESHOLD = rospy.get_param('~snap_threshold', 0.1)

    # Calibration offset — per-eye neutral position adjustment
    offset_x = rospy.get_param('~offset_x', 0.0)
    offset_y = rospy.get_param('~offset_y', 0.0)

    rospy.Subscriber('/joy', Joy, joy_cb, queue_size=1)
    timer = rospy.Timer(duration, timer_cb)
    rospy.spin()
