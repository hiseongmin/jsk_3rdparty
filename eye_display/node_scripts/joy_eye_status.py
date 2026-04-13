#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from std_msgs.msg import Float32
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point

eye_status = "normal"
look_at_x = 0.0
look_at_y = 0.0

prev_eye_status = "normal"
prev_look_at_x = 0.0
prev_look_at_y = 0.0
prev_buttons = []

last_status_pub_time = rospy.Time(0)
last_look_pub_time = rospy.Time(0)

def publish_status(status, now):
    global last_status_pub_time
    if look_at_x == 0.0 and look_at_y == 0.0:
        if status != prev_eye_status or (now - last_status_pub_time) >= duration:
            # for dual eye mode
            if pub_status_left.get_num_connections() > 0:
                pub_status_left.publish(status)
                pub_status_right.publish(status)
            # for single eye mode
            else:
                pub_status.publish(status)
            last_status_pub_time = now

def publish_look(l_x, l_y, r_x, r_y, now):
    global last_look_pub_time

    if (now - last_look_pub_time) < duration:
        return

    l_msg = Point()
    r_msg = Point()
    l_msg.x = l_x
    l_msg.y = l_y
    r_msg.x = r_x
    r_msg.y = r_y

    # for dual eye mode
    if pub_look_left.get_num_connections() > 0:
        pub_look_left.publish(l_msg)
        pub_look_right.publish(r_msg)
    
    # for single eye mode
    else:
        pub_look.publish(r_msg)

    last_look_pub_time = now
    rospy.loginfo("x_diff:{}".format(eye_x_diff))

def joy_cb(msg):

    rospy.loginfo("in the callback")
    global eye_status
    global look_at_x
    global look_at_y

    global prev_eye_status
    global prev_look_at_x
    global prev_look_at_y
    global prev_buttons
    now = rospy.Time.now()
    
    if len(msg.axes) > 1:
        if eye_status == "normal":
            if float(msg.axes[0]) >= 0.0:
                look_at_x = float(msg.axes[0]) * left_edge
                look_at_l_x = float(msg.axes[0]) * (left_edge - eye_x_diff)
            elif float(msg.axes[0]) < 0.0:
                look_at_x = - float(msg.axes[0]) * right_edge
                look_at_l_x = - float(msg.axes[0]) * (right_edge - eye_x_diff)

            if float(msg.axes[1]) >= 0.0:
                look_at_y = float(msg.axes[1]) * upper_edge
                look_at_l_y = float(msg.axes[1]) * (upper_edge - eye_y_diff)
            elif float(msg.axes[1]) < 0.0:
                look_at_y = - float(msg.axes[1]) * bottom_edge
                look_at_l_y = - float(msg.axes[1]) * (bottom_edge + eye_y_diff)

            publish_look(look_at_l_x, look_at_l_y, look_at_x, look_at_y, now)

    if not prev_buttons:
        prev_buttons = [0] * len(msg.buttons)

    n = min(len(prev_buttons), len(msg.buttons))
    if len(msg.buttons)> 0:
        if msg.buttons[0] == 1:
            eye_status = "normal"
        elif n >= 0 and msg.buttons[1] == 1:
            eye_status = "blink"
        elif n >= 1 and msg.buttons[2] == 1:
            eye_status = "surprised"
        elif n >= 2 and msg.buttons[3] == 1:
            eye_status = "sleepy"
        elif n >= 3 and msg.buttons[4] == 1:
            eye_status = "angry"
        elif n >= 4 and msg.buttons[5] == 1:
            eye_status = "sad"
        elif n >= 5 and msg.buttons[6] == 1:
            eye_status = "happy"
        else:
            eye_status = "normal"
    else:
        eye_status = "normal"

    if eye_status != prev_eye_status:
        publish_status(eye_status, now)
        prev_buttons = list(msg.buttons)
        prev_eye_status = eye_status

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    rospy.loginfo("node is initialized")

    # for dual eye mode
    pub_status_right = rospy.Publisher('/right/eye_display/eye_status',String,queue_size=1)
    pub_status_left = rospy.Publisher('/left/eye_display/eye_status',String,queue_size=1)
    pub_look_right = rospy.Publisher('/right/eye_display/look_at',Point,queue_size=1)
    pub_look_left = rospy.Publisher('/left/eye_display/look_at',Point,queue_size=1)

    # for single eye mode
    pub_look = rospy.Publisher('/eye_display/look_at',Point,queue_size=1)
    pub_status = rospy.Publisher('/eye_display/eye_status',String,queue_size=1)

    # set the region where the eye can move
    left_edge = rospy.get_param('~left_edge', 10.0)
    right_edge = rospy.get_param('~right_edge', 40.0)
    upper_edge = rospy.get_param('~upper_edge', -15.0)
    bottom_edge = rospy.get_param('~bottom_edge', 40.0)

    # ????
    eye_x_diff = rospy.get_param('~x_diff', 30.0)
    eye_y_diff = rospy.get_param('~y_diff', 5.0)

    # set duration to decrease the publishing rate
    duration = rospy.Duration(rospy.get_param('~duration',0.05))

    rospy.Subscriber('/joy',Joy, joy_cb, queue_size=1)
    rospy.spin()
