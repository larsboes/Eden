from __future__ import annotations


def read_bmp280(address: int = 0x76) -> dict[str, float]:
    import board
    import busio
    import adafruit_bmp280

    i2c = busio.I2C(board.SCL, board.SDA)
    bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=address)
    return {
        "pressure_hpa": float(bmp.pressure),
        "temperature_c": float(bmp.temperature),
    }

