from PIL import Image
import os

base_dir = "/mnt/data/dev/packages/silvasonic/containers/dashboard/src/static/images"
generated_bg_path = "/home/kyellsen/.gemini/antigravity/brain/def98c5a-ef52-4e98-8477-294b19526e41/login_nature_waves_1769437203387.png"

# 1. Process Background Image
try:
    with Image.open(generated_bg_path) as img:
        # Convert to WebP
        target_bg = os.path.join(base_dir, "login_bg_nature.webp")
        img.save(target_bg, "WEBP", quality=90)
        print(f"Background saved to {target_bg}")
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
