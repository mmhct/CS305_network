HELP = 'Create         : create an conference\n' \
       'Join [conf_id ]: join a conference with conference ID\n' \
       'Quit           : quit an on-going conference\n' \
       'Cancel         : cancel your on-going conference (only the manager)\n\n'

SERVER_IP = '10.27.105.94'
# SERVER_IP = 'localhost'
MAIN_SERVER_PORT = 8888
MAIN_SERVER_PORT2 = 8889
TIMEOUT_SERVER = 5
# DGRAM_SIZE = 1500  # UDP
LOG_INTERVAL = 2
NAME = 'LKQ'

CHUNK = 10192
CHANNELS = 1  # Channels for audio capture
RATE = 44100  # Sampling rate for audio capture

camera_width, camera_height = 480, 480  # resolution for camera capture
