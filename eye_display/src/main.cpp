#include <Arduino.h>

#include "eye.hpp"

#if defined(USE_I2C)
#include "i2c_lib.h"
#endif
#if defined(USE_ROS)
#include "ros_lib.h"
#endif

#if defined(STAMPS3)
#include "ArduinoHWCDCHardware.h"  // also brings crash_trace.h
#elif defined(STAMPC3)
#include "ArduinoHardware.h"
#endif

#define TFT_BL 10 // LED back-light control pin

#if defined(STAMPS3)
#define TRACE_STAGE(s) trace_stage(s)
#define TRACE_FRAME(f) trace_frame(f)
#else
#define TRACE_STAGE(s)
#define TRACE_FRAME(f)
#endif

const int image_width = 139;
const int image_height = 139;

EyeManager eye = EyeManager();

std::string eye_asset_text =
  "eye_asset_names: normal, blink, happy\n"
  "eye_asset_position: normal: upperlid: 9\n"
  "eye_asset_position: blink: upperlid: 9, 9, 130, 130, 9, 9\n"
  "eye_asset_image_path: happy: iris: /white.jpg\n"
  "eye_asset_image_path: happy: pupil: /white.jpg\n"
  "eye_asset_image_path: happy: reflex: /white.jpg\n"
  "eye_asset_image_path: happy: upperlid: /reflex_happy.jpg\n"
  "eye_asset_position: happy: upperlid: 130, 131, 132, 133, 134, 135\n";


void setup()
{
#if defined(STAMPS3)
  trace_setup();  // first: keep the trail from before this boot, arm the watchdog
#endif
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  SPIFFS.begin();
  Serial.begin(115200);

#if defined(USE_ROS)  // USE_ROS
  setup_ros();
#elif defined(USE_I2C)
  setup_i2c();
#endif

  // initialize eye manager with current eye asset
  eye.init();
  // initialize eye_asset_map and set current_eye_status
  eye.setup_asset(eye_asset_text);

  // Optional: start at a known gaze instead of wherever the asset leaves it.
  // Off by default so the stock behaviour is unchanged. Set the two flags in
  // platformio.ini to use it, e.g. -DEYE_BOOT_GAZE_X=12.5 -DEYE_BOOT_GAZE_Y=7.0
  //
  // Worth having when the board resets often: without it the iris sits wherever
  // the asset left it until the first look_at arrives, so every reset shows a
  // jump. The right values are per-robot (they are the measured iris neutral),
  // which is why they are flags and not a literal here.
#if defined(EYE_BOOT_GAZE_X) && defined(EYE_BOOT_GAZE_Y)
  eye.set_gaze_direction(EYE_BOOT_GAZE_X, EYE_BOOT_GAZE_Y, 0.0);
#endif

  // draw eye image
  eye.update_look();

  unsigned long next_time = eye.update_next_time();
  loginfo("[%8ld] setup() done: next_time = %ld", next_time);
}

void loop()
{
#if defined(STAMPS3)
  trace_feed();
#endif
#if defined(USE_ROS)  // USE_ROS
  TRACE_STAGE(ST_RECONNECT);
  reconnect_ros(eye);
#endif
  // Wait for the next frame slot, but keep servicing the serial link while we
  // wait. This used to be a single blocking delay() of ~84 ms, and spinOnce()
  // was not called once during it: look_at messages piled up in the receive
  // buffer (the host log shows them arriving three at a time), and when the
  // buffer overflowed the link desynchronised and the host reported "Lost sync
  // with device". The idle time was already being spent in delay(), so
  // spinning through it costs nothing and the iris follows without the lag of
  // a whole frame.
  long sleep_time = eye.time_until_next();
#if defined(USE_ROS)
  TRACE_STAGE(ST_SPIN_WAIT);
  while ( eye.time_until_next() > 0 ) {
    nh.spinOnce();
    delay(2);
  }
#else
  if ( sleep_time > 0 ) {
    delay(sleep_time);
  }
#endif
  eye.advance_next_time();

  // update emotion, this calls update_look to display
  TRACE_STAGE(ST_DRAW);
  int frame = eye.update_emotion();
  TRACE_FRAME(frame);

#if defined(USE_ROS)
  TRACE_STAGE(ST_SPIN_AFTER);
  nh.spinOnce();
#endif
  // One line a second, not one a frame. Every log line is a rosserial message
  // written back over the same USB link, and that write waits for the host to
  // take it -- inside the frame budget, which has about 10 ms of slack. It is
  // also the bulk of what fills the TX buffer, and a full TX buffer is what
  // wedges the board. The frame counter is in the message, so two samples still
  // give the frame rate.
  static unsigned long last_status_log = 0;
  if ( millis() - last_status_log >= 1000 ) {
    last_status_log = millis();
    TRACE_STAGE(ST_LOG);
#if defined(STAMPS3) && defined(USE_ROS)
    loginfo("[%8ld] Eye status: %s (%d) (sleep %ld ms) (dropped logs %lu)", millis(), eye.get_emotion().c_str(), frame, sleep_time,
            nh.getHardware()->dropped_logs);
#else
    loginfo("[%8ld] Eye status: %s (%d) (sleep %ld ms)", millis(), eye.get_emotion().c_str(), frame, sleep_time);
#endif
  }

#if !defined(USE_I2C) && !defined(USE_ROS) // sample code for eye asset
  static float look_x = 0;
  static float look_y = 0;
  look_x = 10.0 * sin(frame * 0.1);
  look_y = 10.0 * cos(frame * 0.1) ;
  eye.set_gaze_direction(look_x, look_y, 0.0);

  if (frame % 10 == 0) {
    static auto eye_asset = eye.eye_asset_map.begin();
    eye_asset++;
    if (eye_asset == eye.eye_asset_map.end()) eye_asset = eye.eye_asset_map.begin();
    eye.set_emotion(eye_asset->first);
  }
#endif
}
