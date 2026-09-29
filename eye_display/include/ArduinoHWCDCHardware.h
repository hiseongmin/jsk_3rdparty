#pragma once
#include <Arduino.h>  // Arduino 1.0

// ARDUINO_USB_MODE=1 → HWCDC (USB JTAG/Serial, TX-only friendly)
// ARDUINO_USB_MODE=0 → USBCDC (TinyUSB, bidirectional, required for rosserial RX)
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
  // Give up after this long waiting for room in the USB TX buffer.
  static const unsigned long WRITE_TIMEOUT_MS = 100;

  void write(uint8_t* data, int length)
  {
    // Never block forever. USBCDC::write() in the ESP32 core spins without a
    // timeout or a yield when the TX buffer is full and the host is not
    // draining it:
    //
    //     size_t space = tud_cdc_n_write_available(itf);
    //     if (!space) { tud_cdc_n_write_flush(itf); continue; }
    //
    // Its only exit is the host disconnecting. If it is entered from loop(),
    // the board stops drawing AND stops calling spinOnce(), so it also stops
    // draining its receive endpoint -- the host's own writes then time out. It
    // looks exactly like a dead board while USB still reports it as present,
    // and only a power cycle clears it. Seen once, eleven minutes into a run.
    //
    // Write only into the space that is actually free, and drop the message if
    // no room appears in time. A dropped message costs a resync, which the host
    // notices and recovers from in seconds. A wedged board costs a trip to the
    // robot.
    const unsigned long deadline = millis() + WRITE_TIMEOUT_MS;
    int sent = 0;
    while (sent < length)
    {
      int space = iostream->availableForWrite();
      if (space <= 0)
      {
        if ((long)(millis() - deadline) >= 0)
        {
          return;  // drop the rest; better a resync than a wedge
        }
        iostream->flush();
        delay(1);
        continue;
      }
      int chunk = (space < length - sent) ? space : (length - sent);
      iostream->write(data + sent, (size_t)chunk);
      sent += chunk;
    }
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
