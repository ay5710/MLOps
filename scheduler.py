import schedule
import time
import subprocess

def run_main_py():
    """Runs the main.py script."""
    try:
        subprocess.run(["python", "main.py"], check=True) # Raise an exception if the subprocess returns a nonzero exit code
        print("main.py executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error executing main.py: {e}")
    except FileNotFoundError:
        print("Error: main.py not found")

# Schedule the job to run every hour
schedule.every().hour.do(run_main_py)

while True:
    schedule.run_pending()
    time.sleep(1)