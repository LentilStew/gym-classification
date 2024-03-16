import pickle
from tslearn.barycenters.dba import dtw_barycenter_averaging
from Server.http_interface import socketio, app
from Tracker.Tracker import TrackerControls
from Tracker.TrackerPacket import TrackerPacket
from Tracker.Motion import Motion
import json
import threading
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
# LOAD MOTIONS
from settings import MOTIONS_FILE_PATH, MOTIONS_FILE_PATH_LOCK, MOTIONS_FOLDER
import json
import os
from tslearn.metrics import cdist_dtw


def moving_average(data, window_size=3):
    weights = np.repeat(1.0, window_size) / window_size
    smoothed_data = np.convolve(data, weights, 'valid')
    return smoothed_data


def interpolate(s, m=140):
    if len(s) < m:
        f = interp1d(np.linspace(0, 1, len(s)), s, kind='linear')
        interpolated_stream = f(np.linspace(0, 1, m))
    else:
        interpolated_stream = s[:m]
    return interpolated_stream


def preprocess(s):
    s = interpolate(s)
    # s = moving_average(s)
    return s

# LOAD OLD MOTIONS


with MOTIONS_FILE_PATH_LOCK:
    with open(MOTIONS_FILE_PATH, "r") as f:
        motions_header = json.load(f)

labeled_motions: dict = {

}

for motion_header in motions_header["stored_motions"]:
    new_motion = Motion.from_file(os.path.join(
        MOTIONS_FOLDER, motion_header["id"]))
    if new_motion is None:
        print("Failed to open motion")
        exit(0)

    labeled_motions[motion_header["label"]] = labeled_motions.get(motion_header["label"], [
        [], [], [], [], [], [],
    ])

    for shape in motion_header["shapes_acce"]:
        streams = new_motion.as_linear()

        for i, stream in enumerate(streams):
            cut_motion = stream[shape["start"]:shape["end"]]
            if len(cut_motion) == 0:
                continue
            labeled_motions[motion_header["label"]
                            ][i].append(preprocess(cut_motion))

pickle_file = 'averages.pickle'

if os.path.exists(pickle_file):
    with open(pickle_file, 'rb') as f:
        averages = pickle.load(f)
else:

    colors = sns.color_palette("Paired")

    fig, axs = plt.subplots(6, 2)
    fig.set_figheight(30)
    fig.set_figwidth(15)
    averages = [
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    for i, (key, val) in enumerate(labeled_motions.items()):

        for j, streams in enumerate(val):
            center = dtw_barycenter_averaging(streams).ravel()
            for s in streams:
                axs[j, i].plot(s, alpha=.4, color="#585858")
            axs[j, i].plot(center, label=f"Centroid", alpha=1,
                           color=colors[7], linestyle="-")

            averages[j].append(center)

    with open(pickle_file, 'wb') as f:
        pickle.dump(averages, f)

    plt.savefig("OUT")

# LOAD OLD MOTIONS


def normalize(data, min_val, max_val):
    if min_val > 0:
        min_val = 0

    res = []
    for val in data:
        res.append((val - int(min_val)) / (int(max_val) - min_val))

    return res

import locale
locale.setlocale(locale.LC_ALL, '')

if __name__ == "__main__":
    my_tracker: TrackerControls = TrackerControls(
        "192.168.86.29", "192.168.86.247", 3002)
    my_tracker.receiver_init()

    sliding_window: None | list = None
    sliding_window_size_packets = 15

    def motion_thread_func():
        while True:
            new_motion: Motion = my_tracker.get_motion()
            motion_json = json.dumps(new_motion.as_packet())
            socketio.emit("new_motion", motion_json)

    def packet_thread_func():
        global sliding_window
        # cdist_dtw
        while True:
            new_packet: TrackerPacket = my_tracker.get_packet()
            # if reconnects to diff id, packet size may change
            readings_per_packet = my_tracker.get_settings(
                "readings_per_packet")

            if sliding_window is None and readings_per_packet is not None:
                sliding_window = [
                    np.zeros(readings_per_packet*sliding_window_size_packets) for _ in range(6)]
            elif readings_per_packet is None:
                sliding_window = None
                continue

            streams = new_packet.as_linear()

            for i, (new_arr, stream) in enumerate(zip(sliding_window, streams)):
                sliding_window[i] = np.roll(new_arr, -readings_per_packet)
                sliding_window[i][-readings_per_packet:] = stream

            distance_to_centroids = [cdist_dtw(
                centroids, stream) for centroids, stream in zip(averages, sliding_window)]

            results = []
            for i in range(len(distance_to_centroids[0])):
                results.append(np.sum(
                    [distance_to_centroid[i] for distance_to_centroid in distance_to_centroids], axis=0) / len(distance_to_centroids[0]))

            for n in results:
                formated = locale.format_string("%.2f", n[0], grouping=True)
                print("".join(["#"] * (15-len(formated) )) + formated, end=" ")
            print()

            packet_json = json.dumps(new_packet.as_packet())
            socketio.emit("new_packet", packet_json)

    motion_thread = threading.Thread(target=motion_thread_func, daemon=True)
    packet_thread = threading.Thread(target=packet_thread_func, daemon=True)
    motion_thread.start()
    packet_thread.start()
    socketio.run(app, use_reloader=False, log_output=True)
