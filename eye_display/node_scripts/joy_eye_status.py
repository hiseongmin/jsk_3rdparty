#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from std_msgs.msg import Float32
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point

prev_eye_status = "normal"
prev_look_at = Point()
joy_msg = Joy()

def joy_cb(msg):
    global joy_msg
    joy_msg = msg

def timer_cb(event):
    global prev_eye_status
    global prev_look_at
    global joy_msg
    msg = joy_msg
    # get name of eye state mode
    if rospy.has_param("eye_display/eye_asset/names"):
        eye_asset_names = rospy.get_param("eye_display/eye_asset/names")
    else:
        rospy.logwarn("no eye_asset_names found from rosparm '/eye_display/eye_asset/names'")
        return

    # check axes button
    if len(msg.axes) <= 1:
        rospy.logwarn("msg.axes only have {} elemnt, so skip sending look_at".format(len(msg.axes)))
        return
    # debug message
    debug_msg = "{:4.1f} {:4.1f}, ".format(msg.axes[0], msg.axes[1])
    for name, button in zip(eye_asset_names, msg.buttons):
        debug_msg += "{}:{}, ".format(name[:3], button)
    # update eye_status
    eye_status = eye_asset_names[0]
    for i, name in enumerate(eye_asset_names):
        if i < len(msg.buttons) and msg.buttons[i] == 1:
            eye_status = name
            break
    debug_msg += "status:{} ".format(eye_status)
    rospy.loginfo(debug_msg)

    # publish eye status only when it has changed
    if prev_eye_status != eye_status:
        rospy.loginfo("publish eye status : {}".format(eye_status))
        pub_status.publish(eye_status)
    prev_eye_status = eye_status

    # mode_right is try by default and it is the eye on the right side from the front,
    # that is, the left eye from the robot’s point of view.
    # When looking at the display from the front, the origin is slightly to the left of the center.
    if rospy.has_param("eye_display/mode_right"):
        left_eye = rospy.get_param("eye_display/mode_right")
    else:
        rospy.logwarn("no mode_right found from rosparm 'eye_display/mode_right'")
    # On right eye : when msg.axes[0] > 0, the eyes turn inward (cross-eyed)
    axes_x = float(msg.axes[0]) * (1 if left_eye else -1)
    axes_y = float(msg.axes[1]) * -1
    look_at_x = (axes_x * (left_edge if axes_x > 0 else right_edge)) * (-1 if left_eye else 1)
    look_at_y = (axes_y * (bottom_edge if axes_y > 0 else upper_edge))

    look_at = Point(look_at_x, look_at_y, 0)
    if abs(prev_look_at.x - look_at.x) > 1e-4 or \
       abs(prev_look_at.y - look_at.y) > 1e-4:
        rospy.loginfo("publish eye position : {:7.2f} {:7.2f}".format(look_at.x, look_at.y))
        pub_look.publish(look_at)
    prev_look_at = look_at

if __name__ == '__main__':
    rospy.init_node('eye_st_from_joy')
    rospy.loginfo("node is initialized")

    # for single eye mode
    pub_look = rospy.Publisher('eye_display/look_at',Point,queue_size=1)
    pub_status = rospy.Publisher('eye_display/eye_status',String,queue_size=1)

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
    timer = rospy.Timer(duration, timer_cb)
    rospy.spin()
