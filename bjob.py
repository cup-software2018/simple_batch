# job.py

import subprocess
import time
import os
import psutil
import config

class Job:
    def __init__(self, name, script_path, job_id, extra_args=None):
        self.name = name
        self.script_path = script_path
        self.job_id = str(job_id)
        self.extra_args = extra_args if extra_args else []
        self.status = 'Pending'

        self.finished_time = None
        self.cpu_usage = 0.0
        self.memory_mb = 0.0
        self.exit_code = None
        self.log_path = None

        self.process = None
        self.psutil_proc = None
        self._log_fd = None
        self._child_cache = {}   # pid → psutil.Process (keeps cpu_percent counters alive)

    def run_async(self, log_dir=None):
        try:
            command = [self.script_path, self.job_id] + self.extra_args

            p_core_ids = getattr(config, 'P_CORE_IDS', None)

            def _preexec():
                if p_core_ids:
                    try:
                        os.sched_setaffinity(0, p_core_ids)
                    except (AttributeError, OSError):
                        pass

            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                self.log_path = os.path.join(log_dir, f"{self.name}.log")
                self._log_fd = open(self.log_path, 'w')
                self.process = subprocess.Popen(command,
                                                stdout=self._log_fd,
                                                stderr=self._log_fd,
                                                preexec_fn=_preexec)
            else:
                self.process = subprocess.Popen(command, preexec_fn=_preexec)

            self.psutil_proc = psutil.Process(self.process.pid)
            self.psutil_proc.cpu_percent(interval=None)  # prime the counter (first call always 0)
            self._child_cache = {}
            self.status = 'Running'
            print(f"[{self.name}] Started (PID: {self.process.pid})")
        except Exception as e:
            print(f"[{self.name}] Failed to start: {e}")
            self.status = 'Failed'
            self.exit_code = -1
            self.finished_time = time.time()
            if self._log_fd:
                self._log_fd.close()
                self._log_fd = None
            self.process = None

    def is_finished(self):
        if self.process is None:
            return True

        ret = self.process.poll()
        if ret is None:
            return False

        self.exit_code = ret
        if self._log_fd:
            self._log_fd.close()
            self._log_fd = None

        self.status = 'Done' if ret == 0 else 'Failed'
        if self.finished_time is None:
            self.finished_time = time.time()
        return True

    def update_resource_usage(self):
        if not (self.psutil_proc and self.process and self.status == 'Running'):
            return
        try:
            # Collect live descendant processes
            try:
                children = self.psutil_proc.children(recursive=True)
            except psutil.NoSuchProcess:
                children = []

            current_pids = {p.pid for p in children}

            # Drop dead children from cache
            self._child_cache = {pid: p for pid, p in self._child_cache.items()
                                  if pid in current_pids}

            # Register new children and prime their cpu_percent counter
            for p in children:
                if p.pid not in self._child_cache:
                    try:
                        p.cpu_percent(interval=None)
                        self._child_cache[p.pid] = p
                    except psutil.NoSuchProcess:
                        pass

            # Aggregate CPU and memory across main process + all descendants
            cpu = 0.0
            mem = 0.0
            for p in [self.psutil_proc] + list(self._child_cache.values()):
                try:
                    cpu += p.cpu_percent(interval=None)
                    mem += p.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            self.cpu_usage = cpu
            self.memory_mb = mem / (1024 * 1024)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
