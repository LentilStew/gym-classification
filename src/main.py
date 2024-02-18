from Server.http_interface import socketio, app
from Tracker.Tracker import TrackerControls
from Tracker.TrackerPacket import TrackerPacket
from Tracker.Motion import Motion
import json
import threading

if __name__ == "__main__":
    my_tracker: TrackerControls = TrackerControls("192.168.86.22", "192.168.86.247", 3002)
    my_tracker.receiver_init()
    
    def motion_thread_func():
        while True:
            new_motion: Motion = my_tracker.get_motion()
            motion_json = json.dumps(new_motion.as_packet())
            socketio.emit("new_motion", motion_json)

    def packet_thread_func():
        while True:
            new_packet: TrackerPacket = my_tracker.get_packet()
            packet_json =json.dumps( new_packet.as_packet())
            socketio.emit("new_packet", packet_json)
            
    motion_thread = threading.Thread(target=motion_thread_func,daemon=True)
    packet_thread = threading.Thread(target=packet_thread_func,daemon=True)
    motion_thread.start()
    packet_thread.start()
    socketio.run(app,use_reloader=False,log_output=True)