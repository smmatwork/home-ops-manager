import subprocess
import sys

def run():
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
        check=True
    )

if __name__ == "__main__":
    run()
