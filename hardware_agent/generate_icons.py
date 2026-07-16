import os
from PIL import Image
import shutil

src = "/home/mkt-bryan/Downloads/MKT LOGO 1.png"
base = "/home/mkt-bryan/DATA/Helpdesk MKT Agentic AI Automation/hardware_agent/src-tauri/icons"
assets = "/home/mkt-bryan/DATA/Helpdesk MKT Agentic AI Automation/hardware_agent/src/assets"

os.makedirs(assets, exist_ok=True)
shutil.copy(src, os.path.join(assets, "logo.png"))

img = Image.open(src)
img.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(base, "32x32.png"))
img.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(base, "128x128.png"))
img.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(base, "128x128@2x.png"))
img.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(base, "256x256.png"))
img.save(os.path.join(base, "icon.png"))
img.save(os.path.join(base, "icon.ico"), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
img.save(os.path.join(base, "icon.icns"), format="ICNS") if hasattr(Image, 'SAVE') else None # Optional
print("Icons generated!")
