import logging
import subprocess

import cv2
import mediapipe as mp
from obsws_python import ReqClient

logging.basicConfig(level=logging.INFO)


# Constants for camera scenes
CAM_CENTER = "CENTER CAMERA"
CAM_RIGHT = "RIGHT CAMERA"

# OBS connection settings
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "test1234"

# Camera settings - change this index if needed (0, 1, or 2)
PRIMARY_CAMERA_INDEX = 1  # Usually index 1 is the primary/built-in camera on macOS


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
                    if nose_x >= 0.475 and last_camera != CAM_CENTER:
                        logging.info(f"Switching to {CAM_CENTER}")
                        client.set_current_program_scene(CAM_CENTER)
                        last_camera = CAM_CENTER
                    elif nose_x < 0.475 and last_camera != CAM_RIGHT:
                        logging.info(f"Switching to {CAM_RIGHT}")
                        client.set_current_program_scene(CAM_RIGHT)
                        last_camera = CAM_RIGHT
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
