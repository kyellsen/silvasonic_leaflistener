from PIL import Image
import os

source_path = "/mnt/data/dev/packages/silvasonic/containers/dashboard/src/static/images/logo.jpg"
dest_path = "/mnt/data/dev/packages/silvasonic/containers/dashboard/src/static/images/logo.webp"

# Target height for header (h-16 is 64px, let's target 60px for padding or slightly larger for high DPI)
# Actually, let's keep it reasonably high res for retina displays but small file size.
# 120px height should be plenty for a 64px container.
TARGET_HEIGHT = 120

try:
    with Image.open(source_path) as img:
        # Calculate width to maintain aspect ratio
        aspect_ratio = img.width / img.height
        new_width = int(TARGET_HEIGHT * aspect_ratio)
        
        print(f"Original size: {img.size}")
        print(f"Resizing to: {new_width}x{TARGET_HEIGHT}")
        
        resized_img = img.resize((new_width, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        
        print(f"Saving to {dest_path}")
        resized_img.save(dest_path, "WEBP", quality=90)
        
    print("Optimization complete.")
    
    # Verify file existence and size
    if os.path.exists(dest_path):
        size = os.path.getsize(dest_path)
        print(f"New file size: {size} bytes")
    else:
        print("Error: Destination file not found.")

except Exception as e:
    print(f"Error processing image: {e}")
