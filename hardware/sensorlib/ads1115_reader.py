from __future__ import annotations


def read_ads1115_channel(channel: int, address: int = 0x48) -> tuple[int, float]:
    if channel not in (0, 1, 2, 3):
        raise ValueError("channel must be one of 0, 1, 2, 3")

    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.ads1x15 import Pin
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=address)
    channel_map = {0: Pin.A0, 1: Pin.A1, 2: Pin.A2, 3: Pin.A3}
    chan = AnalogIn(ads, channel_map[channel])
    return int(chan.value), float(chan.voltage)

