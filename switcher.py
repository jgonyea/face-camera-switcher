import logging
import subprocess

from dotenv import dotenv_values

import cv2
import mediapipe as mp
from obsws_python import ReqClient

logging.basicConfig(level=logging.INFO)

# Load .env vars.
config = dotenv_values(".env")

# Constants for camera scenes
CAM1 = config['CAM1']
CAM2 = config['CAM2']

# OBS connection settings
OBS_HOST = config['OBS_HOST']
OBS_PORT = config['OBS_PORT']
OBS_PASSWORD = config['OBS_PASSWORD']

# DELAY
CHANGE_DELAY = config['CHANGE_DELAY']

# Camera settings - change this index if needed (0, 1, or 2)
PRIMARY_CAMERA_INDEX = config['PRIMARY_CAMERA_INDEX']  # Usually index 1 is the primary/built-in camera on macOS

def get_system_cameras():
    """Get list of system cameras using system_profiler"""
    try:
        result = subprocess.run(
            ["system_profiler", "SPCameraDataType"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            cameras = []
            lines = result.stdout.split("\n")
            for line in lines:
                if ":" in line and (
                    "Camera" in line or "iSight" in line or "FaceTime" in line
                ):
                    cameras.append(line.strip())
            return cameras
    except Exception as e:
        logging.warning(f"Could not get system camera info: {e}")
    return []


def find_primary_camera_index():
    """Automatically find the primary camera index by looking for FaceTime camera"""
    cameras = get_system_cameras()

    # Look for FaceTime camera in the system info
    for camera_info in cameras:
        if "FaceTime" in camera_info:
            logging.info(f"Found primary camera: {camera_info}")

            # Test each camera index to find which one matches
            for i in range(3):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Get camera properties to help identify
                    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    fps = cap.get(cv2.CAP_PROP_FPS)

                    # FaceTime camera typically has 30 FPS and 1920x1080 resolution
                    if fps == 30.0 and width == 1920.0 and height == 1080.0:
                        cap.release()
                        logging.info(f"Identified primary camera at index {i}")
                        return i
                    cap.release()

    # Fallback to the default index if automatic detection fails
    logging.warning(
        "Could not automatically detect primary camera, using default index"
    )
    return PRIMARY_CAMERA_INDEX


def main():
    # Connect to OBS
    client = ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
    logging.info("Connected to OBS WebSocket successfully!")

    # Setup MediaPipe
    mp_face = mp.solutions.face_mesh
    face_mesh = mp_face.FaceMesh()

    # Automatically detect primary camera
    camera_index = find_primary_camera_index()
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        logging.error(f"Error: Could not open camera at index {camera_index}")
        return

    logging.info(f"Successfully opened camera at index {camera_index}")
    last_camera = None

    try:
        delay = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.error("Error: Could not read frame from camera")
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]
                nose_x = face.landmark[1].x

                logging.info(f"Nose X position: {nose_x:.3f}")
                try:
                    
                    if nose_x >= 0.435 and last_camera != CAM1:
                        delay = delay + 1
                        if delay > CHANGE_DELAY:
                            logging.info(f"Switching to {CAM1}")
                            client.set_current_program_scene(CAM1)
                            last_camera = CAM1
                            delay = 0
                        else:
                            logging.info(f"Switching in {CHANGE_DELAY - delay}")
                    elif nose_x < 0.395 and last_camera != CAM2:
                        delay = delay + 1
                        if delay > CHANGE_DELAY:
                            logging.info(f"Switching to {CAM2}")
                            client.set_current_program_scene(CAM2)
                            last_camera = CAM2
                            delay = 0
                        else:
                            logging.info(f"Switching in {CHANGE_DELAY - delay}")
                    
                    if nose_x >= 0.435 and last_camera == CAM1 and delay > 0: 
                        logging.info("Reset delay counter")
                        delay = 0

                    elif nose_x < 0.395 and last_camera == CAM2 and delay > 0:
                        logging.info("Reset delay counter")
                        delay = 0

                except Exception as e:
                    logging.error(f"Error switching scene: {e}")
            else:
                logging.debug("No face detected")

            # Add a small delay to prevent excessive CPU usage
            import time

            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
    finally:
        cap.release()
        logging.info("Disconnected from OBS WebSocket")


if __name__ == "__main__":
    main()
