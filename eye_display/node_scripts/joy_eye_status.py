#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point

pub_status_right = rospy.Publisher('/right/eye_display/eye_status', String, queue_size=1)
pub_status_left  = rospy.Publisher('/left/eye_display/eye_status',  String, queue_size=1)
pub_look_right   = rospy.Publisher('/right/eye_display/look_at', Point, queue_size=1)
pub_look_left    = rospy.Publisher('/left/eye_display/look_at',  Point, queue_size=1)

pub_look   = rospy.Publisher('/eye_display/look_at', Point, queue_size=1)
pub_status = rospy.Publisher('/eye_display/eye_status', String, queue_size=1)

left_edge = rospy.get_param('~left_edge', -10.0)
right_edge = rospy.get_param('~right_edge', 40.0)
upper_edge = rospy.get_param('~upper_edge', -15.0)
bottom_edge = rospy.get_param('~bottom_edge', 40.0)
eye_x_diff = rospy.get_param('~x_diff', 30.0)
eye_y_diff = rospy.get_param('~y_diff', 5.0)

eye_status = "normal"
look_at_x = 0.0
look_at_y = 0.0
prev_buttons = []

duration =rospy.Duration(rospy.get_param('~duration',0.05))
last_look_pub_time = rospy.Time(0)
last_status_pub_time = rospy.Time(0)
last_status = ""

def publish_status(status,now):
    global last_status_pub_time, last_status
    if look_at_x == 0.0 and look_at_y == 0.0:
        if status != last_status or (now - last_status_pub_time) >= duration:
            if pub_status_left.get_num_connections() > 0:
                pub_status_left.publish(status)
                pub_status_right.publish(status)
            else:
                pub_status.publish(status)
        last_status_pub_time = now
        last_status = status

def publish_look(l_x, l_y, r_x, r_y,now):
    global last_look_pub_time

    if (now - last_look_pub_time) < duration:
        return

    l_msg = Point()
    r_msg = Point()
    l_msg.x = l_x
    l_msg.y = l_y
    r_msg.x = r_x
    r_msg.y = r_y
    if pub_look_left.get_num_connections() > 0:
        pub_look_left.publish(l_msg)
        pub_look_right.publish(r_msg)
    else:
        pub_look.publish(r_msg)

    last_look_pub_time = now
    rospy.loginfo("x_diff:{}".format(eye_x_diff))

# TODO: Publish the topic each eye status like rotation and reflect the different pos of each pupil by the rotation of eye pictures.
def joy_cb(msg):
    global eye_status, look_at_x, look_at_y, prev_buttons
    now = rospy.Time.now()

    if len(msg.axes) > 1 and eye_status == "normal":
        if float(msg.axes[0]) >= 0.0:
            look_at_x = float(msg.axes[0]) * left_edge
            look_at_l_x = float(msg.axes[0]) * (left_edge - eye_x_diff)
        elif float(msg.axes[0]) < 0.0:
            look_at_x = -float(msg.axes[0]) * right_edge
            look_at_l_x = -float(msg.axes[0]) * (right_edge - eye_x_diff)

        if float(msg.axes[1]) >= 0.0:
            look_at_y = float(msg.axes[1]) * upper_edge
            look_at_l_y = float(msg.axes[1]) * (upper_edge - eye_y_diff)
        elif float(msg.axes[1]) < 0.0:
            look_at_y = -float(msg.axes[1]) * bottom_edge
            look_at_l_y = -float(msg.axes[1]) * (bottom_edge + eye_y_diff)
        # print(look_at.x)

        # look_at_x = float(msg.axes[0]) * 20.0 + 2.0
        # look_at_y = -float(msg.axes[1]) * 20.0 + 2.0
        publish_look(look_at_l_x, look_at_l_y,look_at_x, look_at_y, now)

    if not prev_buttons:
        prev_buttons = [0] * len(msg.buttons)

    n = min(len(prev_buttons), len(msg.buttons))
    for i in range(n):
        if prev_buttons[i] == 0 and msg.buttons[i] == 1:
            if i == 0:
                eye_status = "normal"
            elif i == 1:
                eye_status = "blink"
            elif i == 2:
                eye_status = "surprised"
            elif i == 3:
                eye_status = "sleepy"
            elif i == 4:
                eye_status = "angry"
            elif i == 5:
                eye_status = "sad"
            elif i == 6:
                eye_status = "happy"
    publish_status(eye_status, now)

    prev_buttons = list(msg.buttons)

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    rospy.Subscriber('/joy', Joy, joy_cb, queue_size=1)
    rospy.spin()
