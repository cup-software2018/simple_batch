# config.py

import os

# Base directory (absolute path where scripts are)
BASE_DIR = '/home/cupsoft/utils/batch'

# Job request folder
JOB_REQUEST_FOLDER = os.path.join(BASE_DIR, "job_requests")

# Kill request folder
KILL_REQUEST_FOLDER = os.path.join(BASE_DIR, "kill_requests")

# Status file path
STATUS_FILE = os.path.join(BASE_DIR, "status.json")

# Logs folder (future use)
LOG_FOLDER = os.path.join(BASE_DIR, "logs")

# Maximum number of concurrent running jobs
MAX_RUNNING_JOBS = 18

# Time to keep finished (done/failed) jobs before cleaning, in seconds
CLEANUP_TIMEOUT = 60

# Default job id format width
JOB_ID_FORMAT_WIDTH = 6  # Meaning "%06d"
