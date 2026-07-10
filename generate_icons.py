import sys
import subprocess
import os

try:
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image

icons_dir = "hardware_agent/src-tauri/icons"
os.makedirs(icons_dir, exist_ok=True)

img = Image.new("RGBA", (256, 256), color=(41, 128, 185, 255))
img.resize((32, 32)).save(f"{icons_dir}/32x32.png", format="PNG")
img.resize((128, 128)).save(f"{icons_dir}/128x128.png", format="PNG")
img.resize((256, 256)).save(f"{icons_dir}/128x128@2x.png", format="PNG")

img.save(f"{icons_dir}/icon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Icons successfully generated!")
