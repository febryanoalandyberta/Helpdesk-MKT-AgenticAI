import subprocess
import sys

def main():
    try:
        result = subprocess.run(["docker", "logs", "mkt_backend"], capture_output=True, text=True)
        lines = result.stdout.splitlines() + result.stderr.splitlines()
        for line in lines[-2000:]:
            if "Telegram" in line:
                print(line)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
