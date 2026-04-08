#!/usr/bin/env python3
import rospy, argparse
from geometry_msgs.msg import Point

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', type=float, required=True)
    parser.add_argument('--y', type=float, required=True)
    parser.add_argument('--left', action='store_true', help='왼쪽 눈만 보낼 때')
    parser.add_argument('--right', action='store_true', help='오른쪽 눈만 보낼 때')
    parser.add_argument('--left-ns',  default='/left/eye_display',  help='왼쪽 눈 네임스페이스(기본: /left/eye_display)')
    parser.add_argument('--right-ns', default='/right/eye_display', help='오른쪽 눈 네임스페이스(기본: /right/eye_display)')
    args = parser.parse_args()

    rospy.init_node('eyes_set_pose_once', anonymous=True)

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

    # 짧게(최대 0.2초) 구독 연결 대기
    rate = rospy.Rate(100)
    for _ in range(20):
        if all(p.get_num_connections() > 0 for p in pubs):
            break
        rate.sleep()

    pt = Point(args.x, args.y, 0.0)
    for p in pubs:
        p.publish(pt)

if __name__ == '__main__':
    main()

