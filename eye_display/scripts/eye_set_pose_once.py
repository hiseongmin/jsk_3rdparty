#!/usr/bin/env python3
"""
eye_set_pose_once.py
--------------------
Send a single look_at position to one or both eyes, then exit.
Useful for calibration — test a specific eye position without using the joystick.

Usage examples:
  # Move both eyes to center
  python3 eye_set_pose_once.py --x 0 --y 0

  # Move right eye only, 10px right and 5px down
  python3 eye_set_pose_once.py --right --x 10 --y 5

  # Move left eye only
  python3 eye_set_pose_once.py --left --x -10 --y 5
"""
import rospy, argparse
from geometry_msgs.msg import Point

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x',        type=float, required=True,  help='X position in pixels')
    parser.add_argument('--y',        type=float, required=True,  help='Y position in pixels')
    parser.add_argument('--left',     action='store_true',        help='Send to left eye only')
    parser.add_argument('--right',    action='store_true',        help='Send to right eye only')
    parser.add_argument('--left-ns',  default='/left/eye_display',  help='Left eye namespace')
    parser.add_argument('--right-ns', default='/right/eye_display', help='Right eye namespace')
    args = parser.parse_args()

    rospy.init_node('eyes_set_pose_once', anonymous=True)

    # Decide which eyes to publish to
    # If neither --left nor --right is specified, publish to both
    pubs = []
    if not args.left and not args.right:
        pubs = [
            rospy.Publisher(args.left_ns  + '/look_at', Point, queue_size=1),
            rospy.Publisher(args.right_ns + '/look_at', Point, queue_size=1),
        ]
    else:
        if args.left:
            pubs.append(rospy.Publisher(args.left_ns  + '/look_at', Point, queue_size=1))
        if args.right:
            pubs.append(rospy.Publisher(args.right_ns + '/look_at', Point, queue_size=1))

    # Wait up to 0.2s for subscribers to connect before publishing
    rate = rospy.Rate(100)
    for _ in range(20):
        if all(p.get_num_connections() > 0 for p in pubs):
            break
        rate.sleep()

    # Publish the target position once and exit
    pt = Point(args.x, args.y, 0.0)
    for p in pubs:
        p.publish(pt)

if __name__ == '__main__':
    main()
