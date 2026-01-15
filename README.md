# simple_batch

A very simple and lightweight batch queuing system designed for a single machine. This project allows users to manage multiple computational tasks efficiently without the overhead of complex cluster-based systems like SLURM or PBS.

## Features

* Easy Setup: No complex configuration or database required.
* Job Scheduling: Queue multiple tasks and execute them sequentially or in parallel based on local resources.
* Monitoring: Real-time monitoring of job status (Pending, Running, Finished).
* Multiple Interfaces: Supports both Command Line Interface (CLI) and Graphical User Interface (GUI).
* Control: Ability to kill or terminate running jobs instantly.

## Architecture

The system follows a simple client-server model on a local machine:

1. Manager (bmanager): The core engine that manages the job queue and handles task execution.
2. Client (bclient): Submits new tasks to the manager.
3. Monitor (bmon): Displays the current status of the queue.



## Installation

Ensure you have Python 3.x installed. Clone the repository to your local machine:

    git clone [https://github.com/cup-software2018/simple_batch.git](https://github.com/cup-software2018/simple_batch.git)
    cd simple_batch

## Usage

1. Start the Manager
The manager must be running in the background to handle jobs. Open a terminal and run:

    python bmanager

2. Submit a Job
To submit a task (e.g., a script or a command), use the bclient tool:

    python bclient "python3 my_analysis_script.py"

3. Monitor Jobs
Check the status of your submitted jobs (Job ID, Command, Status, and Runtime):

    python bmon

4. Kill a Job
If you need to stop a specific job, use the bkill command with the corresponding Job ID:

    python bkill <job_id>

5. GUI Mode
For a more visual experience, you can launch the GUI-based client:

    python bclient_gui

## File Structure

* bmanager: The server-side script that schedules and runs jobs.
* bclient: CLI tool for job submission.
* bclient_gui: GUI tool for job submission and management.
* bmon: Monitoring tool to check the queue status.
* bkill: Tool to terminate jobs.
* bjob.py: Defines the job class and its properties.
* config.py: Configuration settings (e.g., port numbers, max concurrent jobs).

## Configuration

You can modify config.py to adjust system parameters such as:

* Port for communication between client and manager.
* Maximum number of parallel jobs (slots).
* Log file paths and storage settings.

---
© 2026 cup-software2018
