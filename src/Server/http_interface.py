import socket
from threading import Lock, Thread
import requests
from flask import Flask, jsonify
import json
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from flask import request, Response
import os
from datetime import datetime
from settings import MOTIONS_FILE_PATH, MOTIONS_FILE_PATH_LOCK, MOTIONS_FOLDER
from uuid import uuid4
import numpy as np
from scipy.signal import medfilt
from Tracker.Motion import Motion
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

file_handler = RotatingFileHandler('/home/guiso/code/gymTracker/python/src/logs/app.log', maxBytes=10000000, backupCount=1)
file_handler.setLevel(logging.DEBUG)  # Log all messages, including DEBUG

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
#save output to file called app.log
logging.root.handlers = [file_handler]
@socketio.on("connect")
def connected():
    print("Connected~!")


@socketio.on("disconnected")
def disconnected():
    print("Disconnected~!")


"""
@app.route('/save_motions', methods=['POST'])
def save_motions():
    motion_data = request.get_json()
    motion_id = str(uuid4())
    with open(os.path.join( MOTIONS_FOLDER,motion_id),"wb") as f:
        for packet in motion_data["packets"]:
            f.write(MpuPacket.binary_from_json(packet))
    
    motion_identifier = {
        "label":motion_data["label"],
        "shapes_acce":motion_data["shapes_acce"],
        "shapes_gyro":motion_data["shapes_gyro"],
        "id":motion_id
    }
    with MOTIONS_FILE_PATH_LOCK:
        with open(MOTIONS_FILE_PATH,"r+") as f:
            motions = json.load(f)
            motions["stored_motions"].append(motion_identifier)
            f.seek(0)
            json.dump(motions,f)
            f.truncate()
    
    return "200"
"""


@app.route("/recorded_motions", methods=["GET"])
def get_recorded_motions_head():
    label: str | None = request.args.get("label")
    if label is None:
        return Response("Send label", status=404)

    db = None

    with MOTIONS_FILE_PATH_LOCK:
        try:
            with open(MOTIONS_FILE_PATH, "r+") as f:
                db = json.load(f)
        except FileNotFoundError:
            return Response(f"Label \"{label}\" not found", status=404)

    selected_motions = []
    for motion in db["stored_motions"]:
        if not (label == "any" or motion.label == db):
            continue
        selected_motions.append(motion)

    return selected_motions


@app.route("/recorded_motions/get_motion", methods=["GET"])
def get_motion():
    id: str | None = request.args.get("id")
    filters: str | None = request.args.get("filters")
    
    if id is None:
        return Response(f"Id not found", status=404)
    
    motion = Motion.from_file(os.path.join(MOTIONS_FOLDER, id))
    
    if motion is None:
        return Response(f"id {id} not found", status=404)
        
    return json.dumps(motion.as_packet())
