#pragma once
#include <Arduino.h>  // Arduino 1.0

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
  void write(uint8_t* data, int length)
  {
    // Batch, then flush. TinyUSB CDC sends in 64 byte packets, and without the
    // flush a rosserial message longer than one packet arrives truncated.
    iostream->write(data, (size_t)length);
    iostream->flush();
  }

  unsigned long time()
  {
    return millis();
  }

protected:
  SERIAL_CLASS* iostream;
  long baud_;
};
