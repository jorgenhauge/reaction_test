# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/micropython-esp32-bluetooth-low-energy-ble/

import asyncio
import aioble
import bluetooth
import random
import time
from machine import Pin, PWM
from random import randint


# Init MAGNET PINS
pin_dict = dict.fromkeys((0, 1), PWM(Pin(16, Pin.OUT)))
pin_dict.update(dict.fromkeys((2, 3), PWM(Pin(17, Pin.OUT))))
pin_dict.update(dict.fromkeys((4, 5), PWM(Pin(18, Pin.OUT))))
pin_dict.update(dict.fromkeys((6, 7), PWM(Pin(19, Pin.OUT))))
pin_dict.update(dict.fromkeys((8, 9), PWM(Pin(21, Pin.OUT))))
for pin in pin_dict.values():
    pin.duty(0)

# Init random value
value = 0

# See the following for generating UUIDs:
# https://www.uuidgenerator.net/
_BLE_SERVICE_UUID = bluetooth.UUID("19b10000-e8f2-537e-4f6c-d104768a1214")
_BLE_SENSOR_CHAR_UUID = bluetooth.UUID("19b10001-e8f2-537e-4f6c-d104768a1214")
_BLE_GPIO_UUID = bluetooth.UUID("19b10002-e8f2-537e-4f6c-d104768a1214")
# How frequently to send advertising beacons.
_ADV_INTERVAL_MS = 250_000

# Register GATT server, the service and characteristics
ble_service = aioble.Service(_BLE_SERVICE_UUID)
sensor_characteristic = aioble.Characteristic(
    ble_service, _BLE_SENSOR_CHAR_UUID, read=True, notify=True
)
gpio_characteristic = aioble.Characteristic(
    ble_service, _BLE_GPIO_UUID, read=True, write=True, notify=True, capture=True
)

# Register service(s)
aioble.register_services(ble_service)


# Helper to encode the data characteristic UTF-8
def _encode_data(data):
    return str(data).encode("utf-8")


# Helper to decode the LED characteristic encoding (bytes).
def _decode_data(data):
    try:
        if data is not None:
            # Decode the UTF-8 data
            number = int.from_bytes(data, "big")
            return number
    except Exception as e:
        print("Error decoding temperature:", e)
        return None


# Get sensor readings
def get_random_value():
    return randint(0, 100)


# Get new value and update characteristic
async def sensor_task():
    while True:
        value = get_random_value()
        sensor_characteristic.write(_encode_data(value), send_update=True)
        print("New random value written: ", value)
        await asyncio.sleep_ms(1000)


# Serially wait for connections. Don't advertise while a central is connected.
async def peripheral_task():
    while True:
        try:
            async with await aioble.advertise(
                _ADV_INTERVAL_MS,
                name="ESP32",
                services=[_BLE_SERVICE_UUID],
            ) as connection:
                print("Connection from", connection.device)
                await connection.disconnected()
        except asyncio.CancelledError:
            # Catch the CancelledError
            print("Peripheral task cancelled")
        except Exception as e:
            print("Error in peripheral_task:", e)
        finally:
            # Ensure the loop continues to the next iteration
            await asyncio.sleep_ms(100)


def set_duty_from_data(data: int) -> None:
    mp = None
    if data % 2 == 0:
        d = 512
        print("Turning MAGNET ON")
    else:
        d = 0
        print("Turning MAGNET OFF")
    mp = pin_dict.get(data)
    if not mp:
        print(f"Unknown data: {data}")
    else:
        mp.duty(d)


def set_all_pins_off():
    print("Resetting all pins with duty = 0")
    for pin in pin_dict.values():
        pin.duty(0)


def sleep(seconds: int, reason="...just waiting..."):
    print(f"Sleeping for: '{seconds}' secs. Reason: '{reason}'")
    time.sleep(seconds)


def set_random_pin_off():
    pin: machine.PWM = random.choice(list(pin_dict.values()))
    random_seconds = random.randint(30, 60)
    sleep(random_seconds)
    print(f"Setting {pin} to OFF")
    pin.duty(0)


def set_all_pins_on():
    print("Enabling all pins with duty = 512")
    for pin in pin_dict.values():
        pin.duty(512)


async def wait_for_write():
    while True:
        try:
            connection, data = await gpio_characteristic.written()
            print("BEFORE decode: ", data, type(data))
            data = _decode_data(data)
            print("AFTER, Connection: ", connection, "Data: ", data)
            if data == 99:
                set_all_pins_off()
            elif data == 98:
                set_all_pins_on()
            elif data == 97:
                set_random_pin_off()
            else:
                set_duty_from_data(data=data)
        except asyncio.CancelledError:
            # Catch the CancelledError
            print("Peripheral task cancelled")
        except Exception as e:
            print("Error in peripheral_task:", e)
        finally:
            # Ensure the loop continues to the next iteration
            await asyncio.sleep_ms(100)


# Run tasks
async def main():
    t1 = asyncio.create_task(sensor_task())
    t2 = asyncio.create_task(peripheral_task())
    t3 = asyncio.create_task(wait_for_write())
    await asyncio.gather(t1, t2, t3)


asyncio.run(main())
