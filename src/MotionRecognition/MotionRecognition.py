import numpy as np
from typing import List
from settings import ESP_VALUES_DTYPE
from tslearn.metrics import cdist_dtw
from tslearn.clustering import TimeSeriesKMeans

class MotionRecognitionDTW():
    def __init__(self, centroids: List[np.ndarray], sliding_window_size=140, nb_streams=6,divided=None) -> None:
        self.sliding_windows: np.ndarray = np.zeros(
            (nb_streams, sliding_window_size), dtype=np.dtype(ESP_VALUES_DTYPE))

        self.sliding_window_size = sliding_window_size
        self.nb_streams = nb_streams
        self.centroids: List[np.ndarray] = centroids  # centroid shape is (6,)

    # shifts all values from the sliding window, and puts the new ones in its place
    def slide_window(self, streams: np.ndarray):
        """
        streams: ndarray shape must match (any,nb_streams), all streams must match size
        """

        self.sliding_windows[:, :-
                             streams[0].size] = self.sliding_windows[:, streams[0].size:]
        self.sliding_windows[:, -streams[0].size:] = streams[:, :]

    def cmpr(self):
        results = []
        for i in range(6):
            results.append(cdist_dtw([centroid[i] for centroid in self.centroids], self.sliding_windows[i].reshape((1,-1,1))))
        return results

class MotionRecognitionKMEANS():
    def __init__(self, train_data: List, sliding_window_size=150, nb_streams=6,nb_clusters=2) -> None:
        self.sliding_windows: np.ndarray = np.zeros(
            (nb_streams, sliding_window_size), dtype=np.dtype(ESP_VALUES_DTYPE))

        self.sliding_window_size = sliding_window_size
        self.nb_streams = nb_streams

        self.stream_km:List[TimeSeriesKMeans] = []
        
        for i in range(nb_streams):
            new_km = TimeSeriesKMeans(n_clusters=nb_clusters ,metric="dtw",verbose=False,random_state=0)
            
            new_km.fit(train_data[i])
            self.stream_km.append(new_km)
        
    def slide_window(self, streams: np.ndarray):
        """
        streams: ndarray shape must match (any,nb_streams), all streams must match size
        """

        self.sliding_windows[:, :-
                             streams[0].size] = self.sliding_windows[:, streams[0].size:]
        self.sliding_windows[:, -streams[0].size:] = streams[:, :]

    def cmpr(self):
        results = []
        for kmeans,window in zip(self.stream_km,self.sliding_windows):
            results.append(kmeans.predict([window.reshape(-1, 1)]))
        return results
