from settings import CENTROIDS_FILE_PATH, CENTROIDS_FILE_PATH_LOCK, MOTIONS_FILE_PATH, MOTIONS_FILE_PATH_LOCK, MOTIONS_FOLDER, ESP_VALUES_DTYPE
import json
from Tracker.Motion import Motion
import os
import numpy as np
from scipy.interpolate import interp1d
from tslearn.barycenters.dba import dtw_barycenter_averaging


def moving_average(data, window_size=3):
    weights = np.ones((window_size,))/window_size
    smoothed_data = np.convolve(data, weights, 'valid')
    return smoothed_data


def interpolate(s, m=140):
    if len(s) < m:
        f = interp1d(np.linspace(0, 1, len(s)), s, kind='linear')
        interpolated_stream = f(np.linspace(0, 1, m))
    else:
        interpolated_stream = s[:m]
    return interpolated_stream


def preprocess(s, interpolation_size=140):
    s = interpolate(s, m=interpolation_size).astype(
        dtype=np.dtype(ESP_VALUES_DTYPE))
    s = moving_average(s,5)
    return s

def load_data(preprocess=lambda x, *_: x, *args, **kwargs):
    with MOTIONS_FILE_PATH_LOCK:
        with open(MOTIONS_FILE_PATH, "r") as f:
            motions_header = json.load(f)

    labeled_motions = {}
    for motion_header in motions_header["stored_motions"]:
        new_motion = Motion.from_file(os.path.join(
            MOTIONS_FOLDER, motion_header["id"]))

        if new_motion is None:
            print("Failed to open motion")
            exit(0)
            
        labeled_motions[motion_header["label"]] = labeled_motions.get(motion_header["label"], [[],[],[],[],[],[]])
        
        for shape in motion_header["shapes_acce"]:

            streams = new_motion.as_linear()
            curr_motion_linear = np.array(streams[:,shape["start"]:shape["end"]], dtype=ESP_VALUES_DTYPE)
            if  any([array.size == 0 for array in curr_motion_linear]):
                continue
            for stream,dataset_stream in zip(curr_motion_linear,labeled_motions[motion_header["label"]]):
                dataset_stream.append(preprocess(stream,*args, **kwargs))
    
    return labeled_motions

def generate_centroids(centroid_size: int = 140):

    labeled_motions: dict = load_data(preprocess=preprocess,interpolation_size=centroid_size)

    labeled_centroids: dict = {}
    for key, val in labeled_motions.items():
        centroid = []
        for streams in val:
            centroid.append(dtw_barycenter_averaging(streams,barycenter_size=centroid_size))

        labeled_centroids[key] = centroid
    return labeled_centroids


def load_centroids():
    with CENTROIDS_FILE_PATH_LOCK:
        with open(CENTROIDS_FILE_PATH, "r") as f:
            centroids = json.load(f)
    np_labeled_centroids = {}
    for key, item in centroids.items():
        np_labeled_centroids[key] = np.array(item, dtype=ESP_VALUES_DTYPE)
    return np_labeled_centroids


