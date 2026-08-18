#!/usr/bin/env python3
"""Publish a latched look_at point to both eye namespaces (right and left).

latch=True means a subscriber that connects later still gets the message --
but only while this node is alive. The eye modules come up over rosserial and
take several seconds to subscribe (serial connect ~2 s, then the board boots
and registers its topics), so publishing and exiting on a fixed timer is a
race: whichever board is slower misses the pose and stays wherever it was.

So wait for the subscribers to actually connect before giving up. Publish as
soon as each side is up, keep the latch alive for --hold seconds afterwards,
and say plainly which eyes were reached.
"""
import argparse

import rospy
from geometry_msgs.msg import Point

TOPICS = [
    ("right", "/right/eye_display/look_at"),
    ("left",  "/left/eye_display/look_at"),
]


def wait_for_subscribers(pubs, timeout, poll=0.2):
    """Block until every publisher has a subscriber, or timeout. Returns
    the names still unconnected."""
    deadline = rospy.get_time() + timeout
    pending = list(pubs)
    while pending and rospy.get_time() < deadline and not rospy.is_shutdown():
        still = [(name, pub) for name, pub in pending
                 if pub.get_num_connections() == 0]
        for name, _ in [p for p in pending if p not in still]:
            rospy.loginfo("[eye_set_pose_once] %s eye connected", name)
        pending = still
        if pending:
            rospy.sleep(poll)
    return [name for name, _ in pending]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=0.0)
    parser.add_argument("--z", type=float, default=0.0)
    parser.add_argument("--wait", type=float, default=40.0,
                        help="seconds to wait for the eye modules to subscribe "
                             "(they come up over rosserial); 0 = do not wait")
    parser.add_argument("--hold", type=float, default=5.0,
                        help="seconds to keep the latch alive after publishing")
    args = parser.parse_args()

    rospy.init_node("eye_set_pose_once", anonymous=True)

    pubs = [(name, rospy.Publisher(topic, Point, queue_size=1, latch=True))
            for name, topic in TOPICS]
    rospy.sleep(0.3)  # wait for publisher registration

    missing = wait_for_subscribers(pubs, args.wait) if args.wait > 0 else []
    if missing:
        rospy.logwarn("[eye_set_pose_once] no subscriber after %.0fs: %s "
                      "(module frozen? cold-boot it -- a powered hub keeps "
                      "VBUS, so unplug the hub too)",
                      args.wait, ", ".join(missing))

    msg = Point(x=args.x, y=args.y, z=args.z)
    for _, pub in pubs:
        pub.publish(msg)
    rospy.loginfo("[eye_set_pose_once] look_at (%.1f, %.1f)", args.x, args.y)

    # Keep the latch alive a little longer so a board that reconnects right
    # after (rosserial retries the handshake) still receives the pose.
    rospy.sleep(args.hold)


if __name__ == "__main__":
    main()
