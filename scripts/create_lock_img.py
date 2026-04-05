from PIL import Image, ImageDraw, ImageFont

def create_locked_image():
    # Create a dark grey image
    img = Image.new('RGB', (400, 300), color = (50, 50, 50))
    d = ImageDraw.Draw(img)
    
    # Draw a lock symbol (simple rectangle and loop)
    # Body
    d.rectangle([150, 120, 250, 220], fill=(200, 200, 200))
    # Shackle
    d.arc([165, 80, 235, 160], start=180, end=0, fill=(200, 200, 200), width=10)
    
    # Text
    text = "VIP LOCKED"
    # Basic centering attempt
    d.text((140, 240), text, fill=(255, 215, 0)) # Gold color
    
    img.save('locked.png')
    print("Created locked.png")

if __name__ == "__main__":
    create_locked_image()
