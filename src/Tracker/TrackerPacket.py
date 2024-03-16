from crypt import methods
from io import TextIOWrapper
import json
from mimetypes import init
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import socket
import threading
from io import BufferedRandom
from typing import List, Callable, final
import requests
import base64
from settings import ESP_VALUES_DTYPE

class TrackerPacket:
    def __init__(self, raw_data: bytes) -> None:
        self.device_id: int = 0
        self.timestamp_sec: int = 0
        self.timestamp_nsec: int = 0

        self.gyro_sensitivity: float = 0

        self.acc_sensitivity: float = 0
        self.order: str = ""

        self.nb_readings: int = 0
        self.packet_index: int = 0
        self.press_index: list = []
        self.hz: int = 0
        self.session_id: str = ""
        self.raw_data: bytes = raw_data

        # self.raw_data:bytes = raw_data
        dt = np.dtype(ESP_VALUES_DTYPE)  # type:ignore
        header_len = raw_data.find(0)
        
        header_dict: dict = json.loads(raw_data[0:header_len].decode('utf-8'))
        self.header_dict = header_dict
        for key, val in header_dict.items():
            setattr(self, key, val)
        if(len(self.order) == 0):
            self.order = "XYZABC"
        self.readings = np.frombuffer(raw_data, dtype=dt,
                                          count=self.nb_readings * len(self.order),
                                          offset=header_len+1).reshape((6,25))


    def as_packet(self) -> dict:
        data = {
            "device_id": self.device_id,
            "timestamp_sec": self.timestamp_sec,
            "timestamp_nsec": self.timestamp_nsec,
            "gyro_sensitivity": self.gyro_sensitivity,
            "acc_sensitivity": self.acc_sensitivity,
            "streams_order": "acc xyz gyro xyz",
            "nb_readings": self.nb_readings,
            "packet_index": self.packet_index,
            "press_index": self.press_index,
            "hz": self.hz,
            "session_id": self.session_id
        }
        packet = {"streams": self.readings.tolist(), "header": data}
        
        
        return packet


def tracker_packet_binary_from_dict(packets: dict, packet_size: int):
    raw_data_packet = bytearray(packet_size)
    dt = np.dtype(ESP_VALUES_DTYPE)
    acc_readings = np.array(packets.pop("acc_readings"), dtype=dt).tobytes()
    gyro_readings = np.array(packets.pop("gyro_readings"), dtype=dt).tobytes()

    # append this to the beginning
    json_packets = json.dumps(packets).encode('utf-8')

    raw_data_packet[:len(json_packets)] = json_packets
    raw_data_packet[len(json_packets)] = 0
    raw_data_packet[len(json_packets) + 1:len(json_packets) +
                    1 + len(acc_readings)] = acc_readings
    raw_data_packet[len(json_packets) + 1 + len(acc_readings):len(json_packets) +
                    1 + len(acc_readings) + len(gyro_readings)] = gyro_readings

    return raw_data_packet

def packet_copy(packets:TrackerPacket):
    new_packet = bytearray(len(packets.raw_data))
    dt = np.dtype(ESP_VALUES_DTYPE)

    
    json_packets = json.dumps(packets.header_dict).encode('utf-8')

    new_packet[:len(json_packets)] = json_packets
    new_packet[len(json_packets)] = 0
    count = len(json_packets) + 1
    for stream in packets.readings:
        acc_readings = np.array(stream, dtype=dt).tobytes()
        new_packet[count:count+len(acc_readings)] = acc_readings
        count += len(acc_readings)

    for stream in packets.readings:
        gyro_readings = np.array(stream, dtype=dt).tobytes()
        new_packet[count:count+len(gyro_readings)] = gyro_readings
        count += len(gyro_readings)
        
    return new_packet