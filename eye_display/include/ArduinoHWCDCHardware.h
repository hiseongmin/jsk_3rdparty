#pragma once
#include <Arduino.h>  // Arduino 1.0
#include "crash_trace.h"

// ARDUINO_USB_MODE=1 -> HWCDC (USB JTAG/Serial, TX-only friendly)
// ARDUINO_USB_MODE=0 -> USBCDC (TinyUSB, bidirectional, required for rosserial RX)
#if defined(ARDUINO_USB_MODE) && ARDUINO_USB_MODE == 1
#define SERIAL_CLASS HWCDC
#else
#include <USBCDC.h>
#define SERIAL_CLASS USBCDC
#endif

class ArduinoHardware
{
public:
  ArduinoHardware(SERIAL_CLASS* io, long baud = 57600)
  {
    iostream = io;
    baud_ = baud;
  }
  ArduinoHardware()
  {
    iostream = &Serial;
    baud_ = 57600;
  }
  ArduinoHardware(ArduinoHardware& h)
  {
    this->iostream = h.iostream;
    this->baud_ = h.baud_;
  }

  void setBaud(long baud)
  {
    this->baud_ = baud;
  }

  int getBaud()
  {
    return baud_;
  }

  void init()
  {
    iostream->begin(baud_);
  }

  int read()
  {
    return iostream->read();
  };
  // rosserial topic id of rosout (rosserial_msgs::TopicInfo::ID_LOG).
  static const uint16_t TOPIC_LOG = 7;
  // TinyUSB CDC TX FIFO (CONFIG_TINYUSB_CDC_TX_BUFSIZE in the prebuilt core).
  static const int TX_FIFO_SIZE = 64;

  // Logs that were not sent because the link was busy. Reported in the status line.
  unsigned long dropped_logs = 0;
  // Set around a log that must get through (the crash trace report).
  bool force_logs = false;

  void write(uint8_t* data, int length)
  {
    trace_tx_begin(data, length);
#if !defined(ARDUINO_USB_MODE) || ARDUINO_USB_MODE == 0
    // A log is never worth wedging the board for. USBCDC::write() in the ESP32
    // core spins with no timeout and no yield while the TX FIFO is full, and
    // crash_trace.h caught boards stuck exactly there, writing a log, more than
    // once: in the draw (a 168 byte debug line, since removed) and during the
    // burst of short logs sent while the assets are re-read on connect.
    //
    // So a log is written only when it cannot block: it fits in the free FIFO
    // space, or, if it is longer than the FIFO, the FIFO is empty. Otherwise it
    // is dropped whole -- never half-written, so the host stays in sync.
    //
    // Only logs. Every other frame (TopicInfo during negotiation, time sync,
    // parameter requests) still blocks as before: losing a single TopicInfo
    // leaves look_at with no subscriber for the rest of the run, silently.
    // That is what the 2026-09-29 attempts got wrong. The watchdog in
    // crash_trace.h is the backstop for those.
    if (!force_logs && length >= 7 && (uint16_t)(data[5] | (data[6] << 8)) == TOPIC_LOG)
    {
      int space = iostream->availableForWrite();
      bool fits = (length <= TX_FIFO_SIZE) ? (space >= length) : (space >= TX_FIFO_SIZE);
      if (!fits)
      {
        dropped_logs++;
        trace_tx_end();
        return;
      }
    }
#endif
    // Batch, then flush. TinyUSB CDC sends in 64 byte packets, and without the
    // flush a rosserial message longer than one packet arrives truncated.
    iostream->write(data, (size_t)length);
    trace_tx_flush();
    iostream->flush();
    trace_tx_end();
  }

  unsigned long time()
  {
    return millis();
  }

protected:
  SERIAL_CLASS* iostream;
  long baud_;
};
