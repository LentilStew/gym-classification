from asyncio import Lock
from concurrent.futures import thread
from io import BufferedRandom
import json
import socket
from typing import Callable
import threading
from queue import Queue
from time import monotonic as time
import queue
from Tracker.TrackerPacket import TrackerPacket
import requests
import struct
from Tracker.Motion import Motion


class FastPutQueue(Queue):
    def fast_put(self, item):
        with self.not_full:
            if self.maxsize > 0:
                while self._qsize() >= self.maxsize:
                    self.queue.popleft()
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()

    def print_full_queue(self):
        print("Full Queue:")
        for index, item in enumerate(list(self.queue)):
            item: TrackerPacket
            print(item.packet_index, end=" ")

        print()


class Tracker():
    def __init__(self, tracker_ip: str, receiver_ip: str, receiver_port: int, max_packet_in_q=5, socket_timeout: int = 4) -> None:
        self.tracker_ip: str = tracker_ip
        self.receiver_ip: str = receiver_ip
        self.receiver_port: int = receiver_port
        self._packet_q: FastPutQueue = FastPutQueue(max_packet_in_q)
        self.receiver_thread: threading.Thread | None = None
        self.packet_size: int | None = None
        self.stop_receiver_event: threading.Event = threading.Event()
        self.socket_timeout: int = socket_timeout
        self._tracker_settings = None
        """
        {
"{");
"\"quaternion_row_len\":%i", QUATERNION_ROW_LEN);
",\"accelerometer_row_len\":%i", ACCELEROMETER_ROW_LEN);
",\"gyro_row_len\":%i", GYRO_ROW_LEN);
",\"buffer_max_size\":%i\n", BUFFER_SIZE);
",\"hz\":%i", HZ);
",\"readings_per_packet\":%i", READINGS_PER_PACKET);
",\"stream_port\":%i", STREAM_PORT);
",\"session_id\":\"%s\"", SESSION_ID);
"}");
        }
        """
        self.connection_id = ""
        self.tracker_id = ""

        self.socket_fd: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_fd.bind((self.receiver_ip, self.receiver_port))
        self.socket_fd.settimeout(self.socket_timeout)

    # returns ID of device if running
    def tracker_is_alive(self) -> bool | str:
        res: requests.Response
        try:
            res = requests.get(f"http://{self.tracker_ip}/is_alive")
        except requests.exceptions.ConnectionError as errc:
            print("Tracker not found")
            return False
        except requests.exceptions.RequestException as err:
            print(err)
            return False
        return str(res.text)

    # returns settings of device if running
    def tracker_get_settings(self) -> None | dict:
        res: requests.Response
        try:
            res = requests.get(f"http://{self.tracker_ip}/get_settings")
        except requests.exceptions.ConnectionError as errc:
            print("Tracker not found")
            return None
        except requests.exceptions.RequestException as err:
            print(err)
            return None

        return json.loads(res.text)

    def tracker_add_client(self, ip: str, port: int) -> bool | str:
        ipv4_binary = socket.inet_pton(socket.AF_INET, ip)
        port_binary = struct.pack('!H', port)
        payload = ipv4_binary + port_binary
        try:
            res: requests.Response = requests.post(
                f"http://{self.tracker_ip}/add_client", data=payload)
        except requests.exceptions.ConnectionError as errc:
            print("Tracker not fount")
            return False
        except requests.exceptions.RequestException as err:
            print(err)
            return False
        if res.status_code == 200:
            return res.text
        else:
            return False

    def tracker_keep_client(self, connection_id) -> bool:
        try:
            res: requests.Response = requests.post(
                f"http://{self.tracker_ip}/keep_client", data=connection_id)
        except requests.exceptions.ConnectionError as errc:
            print("Tracker not fount")
            return False
        except requests.exceptions.RequestException as err:
            print(err)
            return False

        return res.status_code == 200

    def receiver_connect(self):

        tracker_id = self.tracker_is_alive()
        if tracker_id is False:
            return False
        self.tracker_id = tracker_id

        _tracker_settings = self.tracker_get_settings()
        print(_tracker_settings)
        if _tracker_settings is None:
            return False
        self._tracker_settings = _tracker_settings

        connection_id = self.tracker_add_client(
            self.receiver_ip, self.receiver_port)
        if connection_id == False:
            return False
        self.connection_id = connection_id

        return True
    
    def _packet_receiver(self,autoreconect: bool = True):
        is_connected: bool = self.receiver_connect()
        if (not autoreconect and not is_connected):
            return

        while (not self.stop_receiver_event.is_set()):
            index = 0
            if autoreconect:
                if not self.tracker_keep_client(self.connection_id):
                    self.receiver_connect()
            else:
                break

            while not self.stop_receiver_event.is_set():
                # EVERY 10 SECONDS CLIENT GETS REMOVED
                # AT .5 packets/s EVERY 20 PACKETS SEND MSSG
                # EVERY TEN PACKETS RECEIVED (5 SECONDS) KEEP ALIVE
                # IF CLIENT LOST BREAK
                if index % 10 == 0 and not self.tracker_keep_client(self.connection_id):
                    break

                try:
                    data, addr = self.socket_fd.recvfrom(
                        self._tracker_settings["buffer_max_size"])# type: ignore
                except (socket.error, socket.timeout) as e:
                    print("Stopped")
                    break

                self._packet_q.fast_put(TrackerPacket(data))
                index += 1
                
    def receiver_init(self, autoreconect: bool = True):
        """
        autoreconnect: nb of timeout retries before resending client, if None don't retry
        """
        self.receiver_thread = threading.Thread(target=self._packet_receiver,args=(autoreconect,))
        self.receiver_thread.daemon = True
        self.receiver_thread.start()
        return True

    def receiver_stop(self):

        if self.receiver_thread is not None and self.receiver_thread.is_alive():
            self.stop_receiver_event.set()
            self.receiver_thread.join()
            self.stop_receiver_event.clear()

    def receiver_join(self):
        if self.receiver_thread is not None and self.receiver_thread.is_alive():
            self.receiver_thread.join()
        return False

    def get_packet(self) -> TrackerPacket:
        return self._packet_q.get()


class TrackerControls(Tracker):
    def __init__(self, tracker_ip: str, receiver_ip: str, receiver_port: int,max_motion_in_q:int=10, file_template: str="{INDEX}", *args, **kwargs):
        super().__init__(tracker_ip, receiver_ip, receiver_port, *args, **kwargs)
        self.file_template = file_template
        """
        TODO file_template add fill in options 
        f"{YEAR}-{MONTH}-{DAY} ..."
        f"-{INDEX}-"
        """
        self._motion_q: FastPutQueue = FastPutQueue(max_motion_in_q)
        self.input_actions: dict = {
            "switch": self.recording_switch
        }

        def controls():
            while (True):
                
                new_input: str = input()
                
                
                action: Callable | None = self.input_actions.get(new_input.split()[0], None)
                if not action is None:
                    action(new_input)
                else:
                    print(f"Invalid action {new_input}")

        controls_thread:threading.Thread = threading.Thread(target=controls, daemon=True)
        controls_thread.start()
        self.index = 0
        self.settings_lock: threading.Lock = threading.Lock()
        self.settings_file_template: str = file_template
        self.settings_record: bool = False
        self.settings_motion: Motion | None = None

    def recording_switch(self,input_str:str):
        
        split_str = input_str.split()
        save_file:bool = "--save-file" in split_str
        
        with self.settings_lock:
            if (self.settings_record and not self.settings_motion is None):
                self.index += 1
                
                self.settings_motion.close()
                self._motion_q.fast_put(self.settings_motion)
                self.settings_motion = None
            else:
                file_name = None
                if save_file:
                    file_name = self.settings_file_template.format(INDEX=self.index)

                self.settings_motion = Motion(file_name=file_name, tracker_settings=self._tracker_settings)

            self.settings_record = not self.settings_record
            
    def get_motion(self) -> Motion:
        return self._motion_q.get()
            
    def on_packet(self, packet: TrackerPacket):
        with self.settings_lock:
            if self.settings_motion is not None and not self.settings_motion.is_open():
                self.settings_motion.open()

            if (self.settings_record == True and isinstance(self.settings_motion, Motion)):
                packet.press_index = ['1'] * len(packet.press_index)
                self.settings_motion.add_packet(packet)
            
        return packet
    
    #replaces the _packet_receiver function
    def _packet_receiver(self,autoreconect: bool = True):
        is_connected: bool = self.receiver_connect()
        if (not autoreconect and not is_connected):
            return

        while (not self.stop_receiver_event.is_set()):
            index = 0
            if autoreconect:
                if not self.tracker_keep_client(self.connection_id):
                    self.receiver_connect()
            else:
                break

            while not self.stop_receiver_event.is_set():
                # EVERY 10 SECONDS CLIENT GETS REMOVED
                # AT .5 packets/s EVERY 20 PACKETS SEND MSSG
                # EVERY TEN PACKETS RECEIVED (5 SECONDS) KEEP ALIVE
                # IF CLIENT LOST BREAK
                if index % 10 == 0 and not self.tracker_keep_client(self.connection_id):
                    
                    break

                try:
                    data, addr = self.socket_fd.recvfrom(
                        self._tracker_settings["buffer_max_size"])# type: ignore
                except (socket.error, socket.timeout) as e:
                    print("Stopped")
                    break
                new_packet = TrackerPacket(data)
                    
                self.on_packet(new_packet)
                self._packet_q.fast_put(new_packet)
                index += 1




