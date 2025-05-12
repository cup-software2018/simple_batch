# job.py

import subprocess
import time
import os
import psutil

class Job:
    def __init__(self, name, script_path, job_id, extra_args=None):
        self.name = name
        self.script_path = script_path
        self.job_id = str(job_id)
        self.extra_args = extra_args if extra_args else []
        self.status = 'Pending'

        self.finished_time = None    # When job ends
        self.cpu_usage = 0.0          # CPU usage %
        self.memory_mb = 0.0          # Memory usage in MB

        self.process = None           # Popen object
        self.psutil_proc = None        # psutil Process object

    def run_async(self):
        try:
            command = [self.script_path, self.job_id] + self.extra_args
            self.process = subprocess.Popen(command)
            self.psutil_proc = psutil.Process(self.process.pid)
            self.status = 'Running'
            print(f"[{self.name}] Started (PID: {self.process.pid})")
        except Exception as e:
            print(f"[{self.name}] Failed to start: {e}")
            self.status = 'Failed'
            self.finished_time = time.time()
            self.process = None

    def is_finished(self):
        if self.process is None:
            return True

        ret = self.process.poll()
        if ret is None:
            return False  # Still running

        if ret == 0:
            self.status = 'Done'
        else:
            self.status = 'Failed'

        if self.finished_time is None:
            self.finished_time = time.time()

        return True

    def update_resource_usage(self):
        if self.psutil_proc and self.process and self.status == 'Running':
            try:
                self.cpu_usage = self.psutil_proc.cpu_percent(interval=1.0)
                self.memory_mb = self.psutil_proc.memory_info().rss / (1024 * 1024)
            except psutil.NoSuchProcess:
                pass
