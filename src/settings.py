from threading import Lock

MOTIONS_FOLDER = "/home/guiso/code/gymTracker/python/motions/"
MOTIONS_FILE_PATH = "/home/guiso/code/gymTracker/python/motions.json"

MOTIONS_FILE_PATH_LOCK = Lock()

CENTROIDS_FILE_PATH = "/home/guiso/code/gymTracker/python/centroids.json"
CENTROIDS_FILE_PATH_LOCK = Lock()


ESP_VALUES_DTYPE = '>i2'

NB_STREAMS = 6 # acce_x acce_y acce_z gyro_x gyro_y gyro_z