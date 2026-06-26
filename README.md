# simple_batch

A lightweight batch job queuing system for a single machine. Manages multiple computational tasks in parallel without the overhead of cluster systems like SLURM or PBS.

## Features

- **No database required** — filesystem-based IPC via shared directories
- **Job scheduling** — queue tasks up to a concurrency limit auto-tuned to CPU type
- **Real-time monitoring** — live job status with CPU/memory usage, progress bar, and color output
- **Multiple interfaces** — CLI and GUI (PySide6) clients
- **Job control** — kill individual jobs or all jobs at once
- **Daemon mode** — background daemon with `start/stop/restart/status` subcommands
- **Systemd integration** — installs as a system service for all users

## Architecture

```
bclient / bclient_gui
    └─▶ job_requests/*.txt  ──▶  bmanager (polls every 1s)
                                     └─▶ status.json  ──▶  bmon
bkill
    └─▶ kill_requests/*.txt ──▶  bmanager
```

All inter-process communication uses the local filesystem. No sockets or network required.

| Component | Role |
|-----------|------|
| `bmanager` | Core daemon — schedules and runs jobs, updates status |
| `bclient` | CLI client — submits a range of jobs |
| `bclient_gui` | PySide6 GUI client |
| `bmon` | Monitor — live queue display with color and progress bar |
| `bkill` | Kills individual jobs or all jobs |
| `bjob.py` | Job class (subprocess + psutil) |
| `config.py` | Loads `config.yaml` and exposes settings |
| `config.yaml` | Human-editable configuration file |

## Installation (system-wide, all users)

```bash
git clone https://github.com/cup-software2018/simple_batch.git
cd simple_batch
sudo bash install.sh
```

The installer:
1. Installs Python dependencies (`psutil`, `pyyaml`, `pyside6`)
2. Copies library files to `/opt/simple_batch/`
3. Installs config to `/etc/simple_batch/config.yaml`
4. Creates runtime directories under `/var/lib/simple_batch/`
5. Places wrapper commands in `/usr/local/bin/` (available to all users)
6. Registers a systemd service (`simple_batch.service`)

To uninstall:

```bash
sudo bash install.sh remove
```

### Start the service

```bash
sudo systemctl start simple_batch
sudo systemctl status simple_batch

# Enable auto-start on boot (optional, administrator's choice)
sudo systemctl enable simple_batch
```

## Development / single-user use

No installation needed. Run directly from the project directory:

```bash
python bmanager run     # foreground mode
```

Override the data directory at runtime:

```bash
SIMPLE_BATCH_DIR=/tmp/mybatch python bmanager run
```

## Configuration

Edit `/etc/simple_batch/config.yaml` (system install) or `config.yaml` (local use):

```yaml
base_dir: /var/lib/simple_batch   # runtime data directory
max_running_jobs: null            # null = auto-detect from CPU type (recommended)
cleanup_timeout: 60               # seconds to keep finished jobs in the status view
job_id_format_width: 6            # zero-padded ID width  (6 → 000001)
```

### Auto-detection of `max_running_jobs`

When set to `null`, the limit is derived from the CPU type at startup:

| CPU type | Limit |
|----------|-------|
| Intel consumer (hybrid: Alder Lake / Raptor Lake) | P-core logical count (HT counted) |
| Intel consumer (Arrow Lake, no HT) | P-core count |
| Intel Xeon | 90% of physical cores |
| Other | All logical CPUs |

Set an explicit integer to override auto-detection.

### Config search order

1. `$SIMPLE_BATCH_CONFIG` environment variable
2. `/etc/simple_batch/config.yaml` (system install)
3. `config.yaml` next to `config.py` (development fallback)

## Usage

### 1. Manage the daemon

```bash
bmanager start      # start as background daemon
bmanager stop       # stop gracefully (terminates running jobs cleanly)
bmanager restart    # restart
bmanager status     # show PID and running state
bmanager run        # run in foreground (useful for debugging)
```

When managed by systemd:

```bash
sudo systemctl start  simple_batch
sudo systemctl stop   simple_batch
sudo systemctl status simple_batch
journalctl -u simple_batch -f    # live log
```

### 2. Submit jobs

```bash
bclient <job_name> <first_id> <last_id> <script> [args...]
```

Each integer in `[first_id, last_id]` becomes an independent job. The script is called as `<script> <job_id> [args...]`.

```bash
# Submit jobs 1–100
bclient analysis 1 100 ./run_analysis.sh

# With extra arguments (quote if they contain spaces)
bclient recon 1 500 ./reconstruct.py "--config setup.yaml"
```

### 3. Monitor

```bash
bmon              # one-shot snapshot
bmon -w           # refresh every 2 seconds (Ctrl-C to exit)
bmon -w 5         # refresh every 5 seconds
```

Output (colors omitted here):

```
════════════════════════════════════════════════════════════════════════════════
                              Batch System Monitor
════════════════════════════════════════════════════════════════════════════════
  Running: 8        Pending: 92       Done: 0         Failed: 0
[████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  0%
────────────────────────────────────────────────────────────────────────────────
  Job                                 Status         CPU       Mem
────────────────────────────────────────────────────────────────────────────────
  analysis_000001                     Running      98.2%   312.4MB
  analysis_000002                     Running      95.7%   298.1MB
  ...
  analysis_000009                     Pending       0.0%     0.0MB
────────────────────────────────────────────────────────────────────────────────
  Total: 100   2026-06-26 10:00:00
```

### 4. Kill jobs

```bash
bkill analysis 3 7      # kill jobs 3 through 7 of job group "analysis"
bkill 0                 # kill ALL pending and running jobs
```

### 5. GUI client

```bash
bclient_gui
```

Requires PySide6. Uses the system GTK3 theme on GNOME if `qt6-qtstyleplugins` (Fedora) or `qt6-gtk-platformtheme` (Ubuntu) is installed.

## File structure (after system install)

```
/opt/simple_batch/          # library files
/etc/simple_batch/
    config.yaml             # system configuration
/var/lib/simple_batch/
    job_requests/           # job submission inbox  (world-writable, sticky bit)
    kill_requests/          # kill request inbox    (world-writable, sticky bit)
    status.json             # live queue status     (world-readable)
    logs/
        bmanager.log        # daemon log
/usr/local/bin/
    bmanager  bclient  bclient_gui  bmon  bkill
/etc/systemd/system/
    simple_batch.service
```

---

© 2026 cup-software2018
