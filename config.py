# config.py — loads config.yaml and exposes settings as module-level variables

import os
import re
import psutil
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))

# Search order: explicit env var → system install → next to config.py (dev)
_candidates = [
    os.environ.get('SIMPLE_BATCH_CONFIG', ''),
    '/etc/simple_batch/config.yaml',
    os.path.join(_HERE, 'config.yaml'),
]
_config_path = next((p for p in _candidates if p and os.path.isfile(p)), None)
if _config_path is None:
    raise FileNotFoundError(
        "config.yaml not found. Searched:\n" +
        "\n".join(f"  {p}" for p in _candidates if p)
    )

with open(_config_path, 'r') as _f:
    _cfg = yaml.safe_load(_f) or {}

# Base directory — SIMPLE_BATCH_DIR env var takes precedence over config.yaml
BASE_DIR = os.path.expanduser(
    os.environ.get('SIMPLE_BATCH_DIR', _cfg.get('base_dir', '~/utils/batch'))
)

# Derived runtime paths (not user-configurable individually)
JOB_REQUEST_FOLDER  = os.path.join(BASE_DIR, 'job_requests')
KILL_REQUEST_FOLDER = os.path.join(BASE_DIR, 'kill_requests')
STATUS_FILE         = os.path.join(BASE_DIR, 'status.json')
LOG_FOLDER          = os.path.join(BASE_DIR, 'logs')
LOG_FILE            = os.path.join(LOG_FOLDER, 'bmanager.log')
LOCK_FILE           = os.path.join(BASE_DIR, 'bmanager.lock')

def _get_p_core_ids():
    """Return sorted list of CPU IDs that belong to P-core clusters.

    P-core clusters have ≤ 2 logical CPUs (Arrow Lake: 1, Alder/Raptor Lake: 2 with HT).
    E-core clusters have 4.  Returns None when sysfs is unavailable or no
    hybrid topology is detected (Xeon, AMD, etc.).
    """
    from collections import Counter
    cpu_to_cluster = {}
    for i in range(os.cpu_count() or 0):
        try:
            with open(f'/sys/devices/system/cpu/cpu{i}/topology/cluster_id') as _f:
                cpu_to_cluster[i] = int(_f.read())
        except OSError:
            return None
    if not cpu_to_cluster:
        return None
    cluster_sizes = Counter(cpu_to_cluster.values())
    p_ids = sorted(cpu for cpu, cid in cpu_to_cluster.items()
                   if cluster_sizes[cid] <= 2)
    return p_ids if p_ids else None


def _p_logical_from_sysfs():
    """Count logical CPUs on P-cores via sysfs cluster topology.

    Cluster sizes on Intel hybrid:
      P-core clusters: 1 (Arrow Lake, no HT)  or  2 (Alder/Raptor Lake, HT)
      E-core clusters: 4
    Summing logical CPUs in small clusters gives the correct slot count
    regardless of whether HT is enabled on P-cores.
    Returns None when sysfs is unavailable.
    """
    from collections import Counter
    ids = []
    for i in range(os.cpu_count() or 0):
        try:
            with open(f'/sys/devices/system/cpu/cpu{i}/topology/cluster_id') as _f:
                ids.append(int(_f.read()))
        except OSError:
            return None
    if not ids:
        return None
    counts = Counter(ids)
    # Sum of logical CPUs in P-core clusters (cluster size ≤ 2)
    p_logical = sum(n for n in counts.values() if n <= 2)
    return p_logical or None   # None → caller falls back


def _detect_max_jobs():
    physical = psutil.cpu_count(logical=False) or os.cpu_count()
    logical  = psutil.cpu_count(logical=True)  or os.cpu_count()

    model = ''
    try:
        with open('/proc/cpuinfo', 'r') as _f:
            _m = re.search(r'model name\s*:\s*(.+)', _f.read())
            if _m:
                model = _m.group(1)
    except OSError:
        pass

    if 'Xeon' in model:
        # 90% of physical cores (HT not counted — Xeon HT threads left for OS)
        return max(1, int(physical * 0.9))

    # Try sysfs cluster topology (Linux 5.x+, handles Arrow Lake / Alder Lake / Raptor Lake)
    p = _p_logical_from_sysfs()
    if p is not None:
        return p

    # Fallback for older kernels or non-hybrid CPUs:
    #   HT on    → use all logical CPUs  (both threads per P-core)
    #   HT off   → use physical cores
    return logical if logical > physical else physical


# P-core CPU IDs for affinity pinning (None = not applicable / not detectable)
P_CORE_IDS = _get_p_core_ids()

# Tunable parameters
_max_jobs_cfg = _cfg.get('max_running_jobs')
MAX_RUNNING_JOBS    = int(_max_jobs_cfg) if _max_jobs_cfg is not None else _detect_max_jobs()
CLEANUP_TIMEOUT     = int(_cfg.get('cleanup_timeout',     60))
JOB_ID_FORMAT_WIDTH = int(_cfg.get('job_id_format_width',  6))
