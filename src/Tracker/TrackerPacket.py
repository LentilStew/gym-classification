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


class TrackerPacket:
    def __init__(self, raw_data: bytes) -> None:
        self.device_id: int = 0
        self.timestamp_sec: int = 0
        self.timestamp_nsec: int = 0

        self.gyro_sensitivity: float = 0
        self.gyro_order: str = ""

        self.acc_sensitivity: float = 0
        self.acc_order: str = ""

        self.nb_readings: int = 0
        self.packet_index: int = 0
        self.press_index: list = []
        self.hz: int = 0
        self.session_id: str = ""
        self.raw_data: bytes = raw_data

        # self.raw_data:bytes = raw_data
        dt = np.dtype('>i2')  # type:ignore
        header_len = raw_data.find(0)
        
        
        
        
        
        
        
        header_dict: dict = json.loads(raw_data[0:header_len].decode('utf-8'))
        for key, val in header_dict.items():
            setattr(self, key, val)
        
        """
        
        # Iterate over the range to print accelerometer readings
        for i in range(self.nb_readings*6):
            print(f"{raw_data[header_len + i * 2 + 1]:02X}{raw_data[header_len + i * 2]:02X}", end=" ")

        # Print a newline character after printing all readings
        print()
        print()
        USED FOR ERROR HTONS ENDIANNESS
        """

        offset = header_len+1
        count = self.nb_readings * len(self.acc_order)

        # THE NUMPY OFFSET IS IN BYTES AND THE COUNT IS IN sizeof(DT)
        self.acc_readings = np.frombuffer(raw_data, dtype=dt,
                                          count=count,
                                          offset=offset).reshape(
                                              (-1, len(self.acc_order))
        )

        offset += (self.nb_readings * len(self.acc_order) * 2)
        count = self.nb_readings * len(self.gyro_order)

        self.gyro_readings = np.frombuffer(raw_data, dtype=dt,
                                           count=count,
                                           offset=offset
                                           ).reshape(
                                               (-1, len(self.gyro_order))
        )

    def as_linear(self):
        x_acc, y_acc, z_acc = np.transpose(self.acc_readings)
        x_gyro, y_gyro, z_gyro = np.transpose(self.gyro_readings)
        
        return (x_acc, y_acc, z_acc, x_gyro, y_gyro, z_gyro)

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
        streams: List[np.ndarray] = list(self.as_linear())
        packet = {"streams": [], "header": data}
        
        for stream in streams:
            packet["streams"].append(stream.tolist())
        
        return packet


def tracker_packet_binary_from_dict(packets: dict, packet_size: int):
    raw_data_packet = bytearray(packet_size)
    dt = np.dtype('>i2')
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
