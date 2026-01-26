from PIL import Image
import os

base_dir = "/mnt/data/dev/packages/silvasonic/containers/dashboard/src/static/images"
# 1. Process Background Image
bg_source = os.path.join(base_dir, "login_bg_nature.jpg")
target_bg = os.path.join(base_dir, "login_bg_nature.webp")

try:
    if os.path.exists(bg_source):
        with Image.open(bg_source) as img:
            img.save(target_bg, "WEBP", quality=90)
            print(f"Background converted: {bg_source} -> {target_bg}")
    else:
        print(f"Source not found: {bg_source}")
except Exception as e:
    print(f"Error processing background: {e}")

# 2. Process Logo
# User said "logo_no_text.png" exists.
logo_source = os.path.join(base_dir, "logo_no_text.png")
logo_target = os.path.join(base_dir, "logo_no_text.webp")

try:
    if os.path.exists(logo_source):
        with Image.open(logo_source) as img:
            # Resize if too huge (optional, but good for web)
            # Max width 500px is plenty for a 20rem or 80px display
            if img.width > 800:
                img.thumbnail((800, 800))
            
            img.save(logo_target, "WEBP", quality=95)
            print(f"Logo converted and saved to {logo_target}")
    else:
        print(f"Error: {logo_source} not found!")

except Exception as e:
    print(f"Error processing logo: {e}")
