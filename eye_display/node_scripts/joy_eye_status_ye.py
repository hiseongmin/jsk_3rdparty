#!/usr/bin/env python3
"""
joy_eye_status_ye.py
--------------------
Converts joystick (sensor_msgs/Joy) input into eye display commands:
  - Look-at position  → /left|right/eye_display/look_at  (geometry_msgs/Point)
  - Eye status string → /left|right/eye_display/eye_status (std_msgs/String)

Supports both dual-eye mode (left + right topics) and single-eye mode
(/eye_display/* topics). Mode is selected automatically based on which
subscribers are active.

Original author : heissereal / miyamichi
Modified by     : hiseongmin (ye)
"""

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
eye_status = "normal"
look_at_x  = 0.0
look_at_y  = 0.0

prev_eye_status = "normal"
prev_buttons    = []

# Initialized after rospy.init_node() to avoid pre-init Time errors
last_status_pub_time = None
last_look_pub_time   = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_dual_mode():
    """Return True when dual-eye subscribers are connected."""
    return pub_status_left.get_num_connections() > 0


def publish_status(status, now):
    """Publish eye status, rate-limited and only when gaze is at center."""
    global last_status_pub_time

    # Only change expression when the eye is looking straight ahead
    if look_at_x != 0.0 or look_at_y != 0.0:
        return

    # Publish only on status change or after the throttle duration
    if status == prev_eye_status and (now - last_status_pub_time) < duration:
        return

    if _is_dual_mode():
        pub_status_left.publish(status)
        pub_status_right.publish(status)
    else:
        pub_status.publish(status)

    last_status_pub_time = now


def publish_look(l_x, l_y, r_x, r_y, now):
    """Publish gaze position for both eyes, rate-limited by duration."""
    global last_look_pub_time

    if (now - last_look_pub_time) < duration:
        return

    # Apply calibration offset so neutral joystick = centered eye position
    l_msg = Point(l_x + l_offset_x, l_y + l_offset_y, 0.0)
    r_msg = Point(r_x + r_offset_x, r_y + r_offset_y, 0.0)

    if _is_dual_mode():
        pub_look_left.publish(l_msg)
        pub_look_right.publish(r_msg)
    else:
        pub_look.publish(r_msg)

    last_look_pub_time = now


def snap_axis(value):
    """Snap joystick axis value to 0.0 if within dead-band threshold.
    Prevents eyes from drifting off-center when the stick is released.
    """
    return 0.0 if abs(value) < SNAP_THRESHOLD else value


# ---------------------------------------------------------------------------
# Joystick callback
# ---------------------------------------------------------------------------

def joy_cb(msg):
    global eye_status, look_at_x, look_at_y
    global prev_eye_status, prev_buttons

    now = rospy.Time.now()

    # ── Gaze (axes) ──────────────────────────────────────────────────────
    # Only move the eyes when expression is normal (prevents crash on blink etc.)
    if len(msg.axes) > 1 and eye_status == "normal":
        ax = snap_axis(float(msg.axes[0]))
        ay = snap_axis(float(msg.axes[1]))

        # Right eye: use full edge values
        # Positive axis → left_edge scale; negative axis → right_edge scale
        look_at_x = ax * left_edge  if ax >= 0.0 else -ax * right_edge
        look_at_y = ay * upper_edge if ay >= 0.0 else -ay * bottom_edge

        # Left eye: subtract x_diff / y_diff to compensate physical offset
        look_at_l_x = ax * (left_edge  - eye_x_diff) if ax >= 0.0 else -ax * (right_edge  - eye_x_diff)
        look_at_l_y = ay * (upper_edge - eye_y_diff) if ay >= 0.0 else -ay * (bottom_edge + eye_y_diff)

        publish_look(look_at_l_x, look_at_l_y, look_at_x, look_at_y, now)

    # ── Buttons (expression) ─────────────────────────────────────────────
    # Initialize prev_buttons on first message
    if not prev_buttons:
        prev_buttons = [0] * len(msg.buttons)

    STATUS_MAP = {
        0: "normal",
        1: "blink",
        2: "surprised",
        3: "sleepy",
        4: "angry",
        5: "sad",
        6: "happy",
    }

    new_status = "normal"
    for btn_idx, status_name in STATUS_MAP.items():
        if btn_idx < len(msg.buttons) and msg.buttons[btn_idx] == 1:
            new_status = status_name
            break

    eye_status = new_status

    if eye_status != prev_eye_status:
        publish_status(eye_status, now)
        prev_buttons    = list(msg.buttons)
        prev_eye_status = eye_status


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    rospy.loginfo("eye_st_from_joy node started")

    # Time stamps — must be created after init_node
    last_status_pub_time = rospy.Time(0)
    last_look_pub_time   = rospy.Time(0)

    # Publishers — dual-eye mode
    pub_status_right = rospy.Publisher('/right/eye_display/eye_status', String, queue_size=1)
    pub_status_left  = rospy.Publisher('/left/eye_display/eye_status',  String, queue_size=1)
    pub_look_right   = rospy.Publisher('/right/eye_display/look_at',    Point,  queue_size=1)
    pub_look_left    = rospy.Publisher('/left/eye_display/look_at',     Point,  queue_size=1)

    # Publishers — single-eye mode fallback
    pub_look   = rospy.Publisher('/eye_display/look_at',    Point,  queue_size=1)
    pub_status = rospy.Publisher('/eye_display/eye_status', String, queue_size=1)

    # Eye movement range (pixels). Positive = outward, negative = inward.
    # Tune these to match the physical display mounting.
    left_edge   = rospy.get_param('~left_edge',    30.0)
    right_edge  = rospy.get_param('~right_edge',  -30.0)
    upper_edge  = rospy.get_param('~upper_edge',  -30.0)
    bottom_edge = rospy.get_param('~bottom_edge',  30.0)

    # Positional offset between left and right eye (hardware calibration)
    eye_x_diff = rospy.get_param('~x_diff', 0.0)
    eye_y_diff = rospy.get_param('~y_diff', 0.0)

    # Minimum interval between publishes (seconds) — prevents message flooding
    duration = rospy.Duration(rospy.get_param('~duration', 0.05))

    # Axes below this threshold are treated as zero (stick return compensation)
    SNAP_THRESHOLD = rospy.get_param('~snap_threshold', 0.1)

    # Calibration offsets — neutral joystick position maps to these pixel values
    r_offset_x = rospy.get_param('~r_offset_x',  10.0)
    r_offset_y = rospy.get_param('~r_offset_y',   5.0)
    l_offset_x = rospy.get_param('~l_offset_x', -10.0)
    l_offset_y = rospy.get_param('~l_offset_y',   5.0)

    rospy.Subscriber('/joy', Joy, joy_cb, queue_size=1)
    rospy.spin()
