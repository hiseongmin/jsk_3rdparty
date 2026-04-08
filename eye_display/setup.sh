#!/usr/bin/env bash
# Eye Display 새 컴퓨터 셋업 스크립트
# 사용법: bash setup.sh [--flash] [--udev] [--all]
#   --flash : 펌웨어 + SPIFFS 플래시까지 한번에
#   --udev  : udev 심링크 규칙 설치 (sudo 필요)
#   --all   : 위 모두 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDEV_RULES_SRC="$SCRIPT_DIR/99-eyemodule.rules"
UDEV_RULES_DST="/etc/udev/rules.d/99-eyemodule.rules"

DO_FLASH=false
DO_UDEV=false

for arg in "$@"; do
  case $arg in
    --flash) DO_FLASH=true ;;
    --udev)  DO_UDEV=true  ;;
    --all)   DO_FLASH=true; DO_UDEV=true ;;
  esac
done

echo "====================================="
echo " Eye Display Setup"
echo "====================================="

# ── 1. ROS 의존 패키지 ────────────────────────────────
echo ""
echo "[1/4] ROS 의존 패키지 설치..."
ROS_DISTRO=${ROS_DISTRO:-noetic}
sudo apt-get install -y \
  ros-${ROS_DISTRO}-rosserial-python \
  ros-${ROS_DISTRO}-rosserial-arduino \
  ros-${ROS_DISTRO}-joy \
  ros-${ROS_DISTRO}-teleop-twist-joy

# ── 2. catkin 빌드 ────────────────────────────────────
echo ""
echo "[2/4] catkin 빌드..."
WS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$WS_DIR"
catkin_make --only-pkg-with-deps eye_display
source devel/setup.bash
echo "빌드 완료: $WS_DIR"

# ── 3. PlatformIO ─────────────────────────────────────
echo ""
echo "[3/4] PlatformIO 확인..."
if ! command -v pio &>/dev/null; then
  echo "PlatformIO 설치 중..."
  pip3 install --user platformio
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "PlatformIO 이미 설치됨: $(pio --version)"
fi

# ── 4. udev 규칙 ──────────────────────────────────────
echo ""
echo "[4/4] udev 심링크 규칙..."
if [ "$DO_UDEV" = true ]; then
  if [ ! -f "$UDEV_RULES_SRC" ]; then
    echo "ERROR: $UDEV_RULES_SRC 없음."
    echo ""
    echo "눈 모듈 시리얼 번호 확인:"
    echo "  udevadm info /dev/ttyACM0 | grep serial"
    echo "  udevadm info /dev/ttyACM1 | grep serial"
    echo ""
    echo "그 다음 $UDEV_RULES_SRC 파일 생성:"
    echo '  SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="1001", ATTRS{serial}=="<LEFT_SERIAL>",  SYMLINK+="ttyACM-lefteye",  GROUP="dialout"'
    echo '  SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="1001", ATTRS{serial}=="<RIGHT_SERIAL>", SYMLINK+="ttyACM-righteye", GROUP="dialout"'
    exit 1
  fi
  sudo cp "$UDEV_RULES_SRC" "$UDEV_RULES_DST"
  sudo udevadm control --reload-rules && sudo udevadm trigger
  echo "udev 규칙 설치 완료"
  echo "  /dev/ttyACM-lefteye  → 왼쪽 눈"
  echo "  /dev/ttyACM-righteye → 오른쪽 눈"
else
  echo "스킵 (--udev 옵션으로 실행하면 설치)"
fi

# ── 5. 펌웨어 플래시 (옵션) ──────────────────────────
if [ "$DO_FLASH" = true ]; then
  echo ""
  echo "[+] 펌웨어 플래시..."
  cd "$SCRIPT_DIR"

  echo "빌드 중..."
  pio run -e stamps3-ros

  for PORT in /dev/ttyACM-lefteye /dev/ttyACM-righteye; do
    if [ -e "$PORT" ]; then
      echo "플래시: $PORT"
      pio run -e stamps3-ros -t upload --upload-port "$PORT"
      echo "SPIFFS: $PORT"
      pio run -e stamps3-ros -t uploadfs --upload-port "$PORT"
    else
      echo "WARNING: $PORT 없음, 스킵"
    fi
  done
  echo "펌웨어 플래시 완료"
fi

# ── 완료 ──────────────────────────────────────────────
echo ""
echo "====================================="
echo " 셋업 완료!"
echo "====================================="
echo ""
echo "실행 방법:"
echo "  터미널 1 (눈 모듈):"
echo "    roslaunch eye_display demo_dual.launch direction_left:=4 direction_right:=4"
echo ""
echo "  터미널 2 (조이스틱):"
echo "    roslaunch eye_display control_eye_with_joystick_robot.launch"
echo ""
echo "  눈 중앙 맞추기:"
echo "    rosrun eye_display eye_set_pose_once.py --x 0 --y 0"
