from Tracker.TrackerPacket import TrackerPacket
from typing import List, Tuple
from io import BufferedWriter
import json
import threading
import numpy as np


class Motion:
    def __init__(self, file_name: str | None = None, tracker_settings: None | dict = None):
        self.packets: List[TrackerPacket] = []

        self.settings_lock: threading.Lock = threading.Lock()
        self._is_open: bool = False
        self.settings_file_name: str | None = file_name
        self.settings_file_descriptor: BufferedWriter | None = None

        self._tracker_settings: dict | None = None

        if not tracker_settings is None:
            self._tracker_settings = {
                **tracker_settings, "is_tracker_settings": True}

    @property
    def tracker_settings(self):
        with self.settings_lock:

            if self._tracker_settings is None:
                return None

            return {**self._tracker_settings}

    def is_open(self) -> bool:
        if self.settings_file_name is None:
            return True

        return self._is_open

    @tracker_settings.setter
    def tracker_settings(self, tracker_settings: None | dict):
        with self.settings_lock:
            self._tracker_settings = tracker_settings

    def as_linear(self) -> np.ndarray:
        with self.settings_lock:
            return np.concatenate([packet.readings for packet in self.packets], axis=1)

    def as_packet(self):
        final_packet: dict = {"streams": []}

        packets = self.as_linear()
        final_packet["streams"] = packets.tolist()
        if self.tracker_settings:
            final_packet["tracker_settings"] = self._tracker_settings
        # TODO if not tracker_settings read some packets and find data

        return final_packet

    def add_packet(self, new_packet: TrackerPacket):
        with self.settings_lock:
            if (not self.settings_file_name is None and not self.settings_file_descriptor is None):
                self.settings_file_descriptor.write(new_packet.raw_data)
        self.packets.append(new_packet)

    # only needs to be open and close if self.settings_file_name is not None
    def open(self):
        with self.settings_lock:

            if not isinstance(self.settings_file_name, str):
                return False

            self.settings_file_descriptor = open(self.settings_file_name, "wb")
            self._is_open = True
            if not self._tracker_settings is None:
                tracker_settings_str = json.dumps(self._tracker_settings)
                tracker_binary = tracker_settings_str.encode(
                    encoding="ascii", errors="ignore")
                self.settings_file_descriptor.write(tracker_binary)
                self.settings_file_descriptor.write(b'\x00')
        return True
    
    def close(self):
        with self.settings_lock:
            if (not self.settings_file_descriptor is None):
                self.settings_file_descriptor.close()
                self._is_open = False

    # if packet size is None will use packet size from tracker settings

    @classmethod
    def from_file(cls, file_path: str, packet_size: int | None = None):

        with open(file_path, "rb") as file:

            tracker_settings: None | dict = None
            while (1):
                byte = file.read(1)
                if not byte:
                    return None
                elif byte == b'\0':
                    dict_end = file.tell()
                    file.seek(0)
                    header_dict: dict | None = None
                    try:
                        tracker_settings_bytes = file.read(dict_end-1)
                        file.read(1)  # skip the /0 for the second part

                        header_dict = json.loads(tracker_settings_bytes)
                    except Exception as e:
                        print("Invalid file")
                        print(e)
                        return None

                    if not header_dict is None and header_dict.get("is_tracker_settings", False) == False:
                        file.seek(0)
                        break

                    tracker_settings = header_dict

                    break

            new_motion: Motion = cls(tracker_settings=tracker_settings)
            if packet_size is None and not tracker_settings is None and tracker_settings.get("buffer_max_size", False) != False:
                packet_size = tracker_settings["buffer_max_size"]
            # at this point the file points either to the end of the header, or the begining of the file

            while (1):
                packet_data = file.read(packet_size)
                if not packet_data:
                    break
                new_motion.add_packet(TrackerPacket(packet_data))

        return new_motion

    @classmethod
    def from_list(cls, packets):
        new_motion: Motion = cls()
        for packet in packets:
            new_motion.add_packet(TrackerPacket(packet))

        return new_motion
