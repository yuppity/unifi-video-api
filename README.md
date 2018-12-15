# unifi-video-api
Python API for interfacing with Unifi NVR v3.9.12.

## Usage
```python
from unifi_video import UnifiVideoAPI

# Default kwargs: port = 7080, schema = http
uva = UnifiVideoAPI('username', 'password', 'localhost')

# Save snapshot from camera whose id, name or onscreen display text
# is "Garage"
uva.get_camera('Garage').snapshot('some/path/snapshot.jpg')

# Save snapshot from all cameras to ./snapshot_camera id_timestamp.jpg
for camera in uva.cameras:
  camera.snapshot()

# Change onscreen display text
uva.get_camera('Garage').set_onscreen_text('Home garage')

# Turn off IR leds
uva.get_camera('Garage').ir_leds(False)

# Set IR leds to auto mode
uva.get_camera('Garage').ir_leds('auto')

# Set camera to record at all times but disable separate recordings
# for motion
uva.get_camera('Garage').set_recording_settings(full_time_record_enabled=True,
  motion_record_enabled=False)

# Enable motion recordings and set the pre capture period to five seconds
uva.get_camera('Garage').set_recording_settings(motion_record_enabled=False,
  pre_padding_secs=5)
```


## Requirements
Python2 or python3 (tested with 2.7, 3.7). No third-party dependencies.

# Warning
This software has been tested against Unifi NVR v3.9.12 and a single UVC G3
camera. While unlikely, should any of the POST payloads result in software or
hardware failure, the maintainer of this package is not liable.

Proceed at your own risk.
