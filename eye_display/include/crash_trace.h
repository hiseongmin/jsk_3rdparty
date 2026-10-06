#pragma once
// Where was the board when it stopped?
//
// The boards freeze without a trace: the display stops, the host reads a
// rosserial frame cut short, and nothing is logged anywhere. The kernel sees no
// USB event, so the chip has not reset -- it is stuck. Until now only a power
// cycle brought it back, and the power cycle erased whatever it was doing.
//
// This does two things.
//
// 1. A task watchdog on loop(). If loop() stops coming round for
//    LOOP_WDT_TIMEOUT_S, the chip panics and restarts by itself, and
//    serial_node reconnects when the port comes back. A freeze costs a few
//    seconds instead of a trip to unplug the board.
//
// 2. A breadcrumb trail in RTC memory, which survives that restart (not a power
//    cycle). loop() records which stage it is in, and every rosserial frame
//    written records its length and topic. After the restart the trail is
//    reported once over rosout, together with the reset reason -- so the next
//    freeze says where it happened instead of only that it happened.
//
// A reset reason of BROWNOUT would point at power after all.

#include <Arduino.h>
#include <esp_attr.h>
#include <esp_system.h>
#include <esp_task_wdt.h>

#ifndef LOOP_WDT_TIMEOUT_S
#define LOOP_WDT_TIMEOUT_S 10
#endif

enum TraceStage : uint8_t {
  ST_NONE = 0,
  ST_RECONNECT,   // reconnect_ros(): may re-read every asset parameter
  ST_SPIN_WAIT,   // spinOnce() while waiting for the frame slot
  ST_DRAW,        // update_emotion(): drawing the frame
  ST_SPIN_AFTER,  // the spinOnce() after drawing
  ST_LOG,         // the once-a-second status line
};

enum TraceIo : uint8_t {
  IO_IDLE = 0,
  IO_WRITE,       // inside USBCDC::write()
  IO_FLUSH,       // inside USBCDC::flush()
};

#define TRACE_TX_RING 8
#define TRACE_MAGIC 0xE7E7C0DEu

struct CrashTrace {
  uint32_t magic;
  uint32_t boots;
  uint32_t frame;
  uint32_t ms;            // millis() at the last stage change
  uint8_t stage;
  uint8_t io;
  uint16_t io_len;        // length of the frame being written
  uint32_t io_ms;         // millis() when that write started
  uint16_t tx_len[TRACE_TX_RING];    // last frames written: payload length
  uint16_t tx_topic[TRACE_TX_RING];  // ... and topic id
  uint8_t tx_head;
};

RTC_NOINIT_ATTR CrashTrace g_trace;
static CrashTrace g_last;         // copy of the trail from before this boot
static bool g_last_valid = false;
static esp_reset_reason_t g_reset_reason = ESP_RST_UNKNOWN;

inline void trace_stage(TraceStage s) {
  g_trace.stage = s;
  g_trace.ms = millis();
}

inline void trace_frame(uint32_t f) { g_trace.frame = f; }

// Called from ArduinoHardware::write() with the whole rosserial frame.
inline void trace_tx_begin(const uint8_t *data, int length) {
  g_trace.io = IO_WRITE;
  g_trace.io_len = (uint16_t)length;
  g_trace.io_ms = millis();
  // rosserial frame: ff fe len_lo len_hi len_chk topic_lo topic_hi ...
  if (length >= 7 && data[0] == 0xff) {
    uint8_t i = g_trace.tx_head % TRACE_TX_RING;
    g_trace.tx_len[i] = (uint16_t)(data[2] | (data[3] << 8));
    g_trace.tx_topic[i] = (uint16_t)(data[5] | (data[6] << 8));
    g_trace.tx_head = (uint8_t)(i + 1);
  }
}
inline void trace_tx_flush() { g_trace.io = IO_FLUSH; }
inline void trace_tx_end() { g_trace.io = IO_IDLE; }

inline void trace_setup() {
  g_reset_reason = esp_reset_reason();
  if (g_trace.magic == TRACE_MAGIC) {
    g_last = g_trace;
    g_last_valid = true;
  } else {
    memset(&g_trace, 0, sizeof(g_trace));
    g_trace.magic = TRACE_MAGIC;
  }
  g_trace.boots++;
  g_trace.stage = ST_NONE;
  g_trace.io = IO_IDLE;

  // Re-arm the task watchdog with our timeout (IDF 4.4 reconfigures it if it
  // is already running) and subscribe the loop task to it.
  esp_task_wdt_init(LOOP_WDT_TIMEOUT_S, true);
  esp_task_wdt_add(NULL);
}

inline void trace_feed() { esp_task_wdt_reset(); }

static const char *reset_reason_name(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON:  return "POWERON";
    case ESP_RST_EXT:      return "EXT";
    case ESP_RST_SW:       return "SW";
    case ESP_RST_PANIC:    return "PANIC";
    case ESP_RST_INT_WDT:  return "INT_WDT";
    case ESP_RST_TASK_WDT: return "TASK_WDT";
    case ESP_RST_WDT:      return "WDT";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    default:               return "OTHER";
  }
}

static const char *stage_name(uint8_t s) {
  switch (s) {
    case ST_RECONNECT:  return "reconnect";
    case ST_SPIN_WAIT:  return "spin_wait";
    case ST_DRAW:       return "draw";
    case ST_SPIN_AFTER: return "spin_after";
    case ST_LOG:        return "log";
    default:            return "none";
  }
}

static const char *io_name(uint8_t s) {
  switch (s) {
    case IO_WRITE: return "write";
    case IO_FLUSH: return "flush";
    default:       return "idle";
  }
}

// Report once, after ROS is up. `log` is the board's loginfo/logwarn.
template <typename LogFn>
void trace_report(LogFn log) {
  static bool reported = false;
  if (reported) return;
  reported = true;
  if (!g_last_valid || g_reset_reason == ESP_RST_POWERON) {
    log("[trace] boot #%lu, reset %s (no trail)", (unsigned long)g_trace.boots,
        reset_reason_name(g_reset_reason));
    return;
  }
  log("[trace] boot #%lu, reset %s. Before it: stage %s since %lu ms, io %s "
      "(frame len %u, started %lu ms), frame %lu",
      (unsigned long)g_trace.boots, reset_reason_name(g_reset_reason),
      stage_name(g_last.stage), (unsigned long)g_last.ms, io_name(g_last.io),
      g_last.io_len, (unsigned long)g_last.io_ms, (unsigned long)g_last.frame);
  char buf[160];
  int n = 0;
  for (int k = 0; k < TRACE_TX_RING; k++) {
    uint8_t i = (uint8_t)((g_last.tx_head + k) % TRACE_TX_RING);
    n += snprintf(buf + n, sizeof(buf) - n, " %u/t%u", g_last.tx_len[i],
                  g_last.tx_topic[i]);
    if (n >= (int)sizeof(buf)) break;
  }
  log("[trace] last frames written (len/topic, oldest first):%s", buf);
}
