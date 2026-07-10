import os
import glob

def print_python_processes():
    for p in glob.glob('/proc/[0-9]*/cmdline'):
        try:
            with open(p, 'r') as f:
                cmd = f.read().replace('\x00', ' ')
                if 'python' in cmd or 'uvicorn' in cmd:
                    print(f"PID {p.split('/')[2]}: {cmd}")
        except Exception:
            pass

if __name__ == '__main__':
    print_python_processes()
