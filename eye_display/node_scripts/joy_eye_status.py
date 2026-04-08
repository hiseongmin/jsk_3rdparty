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

def joy_cb(msg):
    print("in callback")
    
    global eye_status
    global look_at_x
    global look_at_y

    global prev_eye_status
    global prev_look_at_x
    global prev_look_at_y
    
    look_at_pub_msg = Point()
    
    if len(msg.buttons)> 0:
        if msg.buttons[0] == 1:
            eye_status = "normal"
        elif msg.buttons[1] == 1:
            eye_status = "blink"
        elif msg.buttons[2] == 1:
            eye_status = "surprised"
        elif msg.buttons[3] == 1:
            eye_status = "sleepy"
        elif msg.buttons[4] == 1:
            eye_status = "angry"
        elif msg.buttons[5] == 1:
            eye_status = "sad"
        elif msg.buttons[6] == 1:
            eye_status = "happy"
        else:
            eye_status = "normal"
    else:
        eye_status = "normal"
    if eye_status != prev_eye_status:
        pub_status_right.publish(eye_status)
        pub_status_left.publish(eye_status)
        prev_eye_status = eye_status

    SNAP_THRESHOLD = 0.1  # 이 값 미만이면 0으로 처리 (스틱 복귀 오차 제거)
    if len(msg.axes) > 0:
        ax = float(msg.axes[0])
        ay = float(msg.axes[1])
        look_at_x =   (ax if abs(ax) >= SNAP_THRESHOLD else 0.0) * 30.0
        look_at_y = - (ay if abs(ay) >= SNAP_THRESHOLD else 0.0) * 30.0

    look_at_x = round(look_at_x, 2)
    look_at_y = round(look_at_y, 2)

    if look_at_x != prev_look_at_x or look_at_y != prev_look_at_y:
        look_at_pub_msg.x = look_at_x
        look_at_pub_msg.y = look_at_y
        pub_look_left.publish(look_at_pub_msg)
        pub_look_right.publish(look_at_pub_msg)
        prev_look_at_x = look_at_x
        prev_look_at_y = look_at_y

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    pub_status_right = rospy.Publisher('/right/eye_display/eye_status',String,queue_size=1)
    pub_status_left = rospy.Publisher('/left/eye_display/eye_status',String,queue_size=1)
    pub_look_right = rospy.Publisher('/right/eye_display/look_at',Point,queue_size=1)
    pub_look_left = rospy.Publisher('/left/eye_display/look_at',Point,queue_size=1)
    rospy.Subscriber('/joy',Joy, joy_cb, queue_size=1)
    rospy.spin()
