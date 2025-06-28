from obswebsocket import obsws
from obswebsocket import requests as obsrequests

try:
    # Connect to OBS
    ws = obsws("localhost", 4455, "test1234")
    ws.connect()
    print("Connected to OBS WebSocket successfully!")

    # Get list of scenes
    scenes = ws.call(obsrequests.GetSceneList())
    print("Available scenes:")
    for scene in scenes.getScenes():
        print(f"  - {scene['sceneName']}")

    # Get current scene
    current_scene = ws.call(obsrequests.GetCurrentScene())
    print(f"Raw current scene response: {current_scene.__dict__}")

    # Test switching to CENTER CAMERA
    print("Testing switch to CENTER CAMERA...")
    result = ws.call(obsrequests.SetCurrentScene("CENTER CAMERA"))
    print("Switch successful!")

    # Test switching to RIGHT CAMERA
    print("Testing switch to RIGHT CAMERA...")
    result = ws.call(obsrequests.SetCurrentScene("RIGHT CAMERA"))
    print("Switch successful!")

    ws.disconnect()
    print("Disconnected from OBS WebSocket")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
