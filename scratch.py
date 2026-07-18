import urllib.request
import sys

try:
    with urllib.request.urlopen('http://localhost:8000/api/crewai-health') as response:
        html = response.read()
        with open('scratch_output.txt', 'w') as f:
            f.write(html.decode('utf-8'))
except Exception as e:
    with open('scratch_output.txt', 'w') as f:
        f.write(f"Error: {e}")
