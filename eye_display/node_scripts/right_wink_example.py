#!/usr/bin/env python3
import rospy
from std_msgs.msg import String

DOC_URL = "https://github.com/jsk-ros-pkg/jsk_3rdparty/tree/119235bfaac19164e2fbc4904ab02f89cfc04c64/eye_display#description-of-direction"

def main():
    rospy.init_node("wink_node")

    params = rospy.get_param_names()
    target_ns = None

    for p in params:
        if p.endswith("/eye_display/mode_right"):
            ns = p.replace("/eye_display/mode_right", "")
            mode = rospy.get_param(p)
            port = rospy.get_param(ns + "/eye_display/port", "unknown")

            rospy.loginfo(f"[{ns}] mode_right={mode}, port={port}")
            if mode is False:
                target_ns = ns

    if target_ns is None:
        rospy.logwarn("No mode_right=false found")
        return

    rospy.loginfo(
        f"Select [{ns}] because mode_right=False. "
        f"According to the eye_display direction definition, "
        f"mode_right=True means the eye located on the right side when viewed from the front of the display, "
        f"which corresponds to the robot's left eye. "
        f"Therefore, mode_right=False corresponds to the eye located on the left side when viewed from the front, "
        f"which is the robot's right eye. "
        f"See: {DOC_URL} "
    )
    rospy.loginfo(
        f"Select [{ns}] because mode_right=False\n"
        f"(front view right eye).\n"
        f"See: {DOC_URL} "
    )

    topic = target_ns + "/eye_display/eye_status"
    pub = rospy.Publisher(topic, String, queue_size=10)

    msg = String(data="blink")

    rospy.loginfo(f"Start sending '{msg}' to {topic}")
    rospy.sleep(1.0)
    for i in range(2):
        pub.publish(msg)
        rospy.sleep(0.2)
        pub.publish(msg)
        rospy.loginfo(f"....")
        rospy.sleep(1.0)
    pub.publish(String(data="normal"))
    rospy.sleep(1.0)
    rospy.loginfo(f"Done")



if __name__ == "__main__":
    main()
