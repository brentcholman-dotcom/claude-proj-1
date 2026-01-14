#!/usr/bin/env python3
"""
Generate simple placeholder icons for PWA
Requires Pillow: pip install Pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os

    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)

    # Icon sizes needed
    icon_sizes = [16, 32, 152, 167, 180, 192, 512]

    # Background gradient colors
    color_start = (102, 126, 234)  # #667eea
    color_end = (118, 75, 162)     # #764ba2

    for size in icon_sizes:
        # Create image with gradient background
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)

        # Simple gradient effect
        for y in range(size):
            r = int(color_start[0] + (color_end[0] - color_start[0]) * y / size)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * y / size)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * y / size)
            draw.line([(0, y), (size, y)], fill=(r, g, b))

        # Add emoji or text in the center
        try:
            # Try to add text
            font_size = size // 2
            text = "🔒"

            # Draw white circle background for better visibility
            circle_radius = size // 2 - size // 10
            circle_center = (size // 2, size // 2)
            draw.ellipse([
                circle_center[0] - circle_radius,
                circle_center[1] - circle_radius,
                circle_center[0] + circle_radius,
                circle_center[1] + circle_radius
            ], fill='white', outline=None)

            # Add a simple "PC" text for Privacy Chat
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()

            text_content = "PC"
            bbox = draw.textbbox((0, 0), text_content, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_position = ((size - text_width) // 2, (size - text_height) // 2 - font_size // 8)

            draw.text(text_position, text_content, fill=color_start, font=font)

        except Exception as e:
            print(f"Note: Could not add text to icon: {e}")
            pass

        # Save the icon
        filename = f'static/icon-{size}.png'
        img.save(filename, 'PNG')
        print(f"✅ Created {filename}")

    print("\n✅ All icons generated successfully!")
    print("📝 Icons saved in the 'static' directory")

except ImportError:
    print("❌ Pillow library not found")
    print("📦 Install it with: pip install Pillow")
    print("\n📝 Alternative: Create icons manually and place them in 'static' directory:")
    print("   - icon-16.png (16x16)")
    print("   - icon-32.png (32x32)")
    print("   - icon-152.png (152x152)")
    print("   - icon-167.png (167x167)")
    print("   - icon-180.png (180x180)")
    print("   - icon-192.png (192x192)")
    print("   - icon-512.png (512x512)")
    print("\n💡 You can use any icon generator like:")
    print("   - https://realfavicongenerator.net/")
    print("   - https://www.favicon-generator.org/")
except Exception as e:
    print(f"❌ Error generating icons: {e}")
