"""Generate custom premium BusReserve 2.0 favicons in ICO, PNG and SVG formats.

Outputs:
- frontend/public/favicon.svg
- frontend/public/favicon-16x16.png
- frontend/public/favicon-32x32.png
- frontend/public/favicon-48x48.png
- frontend/public/apple-touch-icon.png (180x180)
- frontend/public/favicon.ico (multi-resolution ICO 16x16, 32x32, 48x48)
"""

import math
import os
import struct
import zlib

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B1E36" />
      <stop offset="50%" stop-color="#06101E" />
      <stop offset="100%" stop-color="#020710" />
    </linearGradient>
    <linearGradient id="busGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="50%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="brassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FCD34D" />
      <stop offset="100%" stop-color="#D97706" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.4" />
    </filter>
  </defs>

  <!-- Dark Navy Rounded Base Container -->
  <rect width="512" height="512" rx="112" fill="url(#bgGrad)" />

  <!-- Outer Emerald Glow Border -->
  <rect x="16" y="16" width="480" height="480" rx="98" fill="none" stroke="#10B981" stroke-width="6" stroke-opacity="0.25" />

  <!-- Bus Silhouette (Emerald Gradient) -->
  <g filter="url(#shadow)">
    <!-- Main Bus Coach Body -->
    <rect x="120" y="104" width="272" height="296" rx="44" fill="url(#busGrad)" />

    <!-- Upper Destination Display / Roof Sign -->
    <rect x="192" y="122" width="128" height="18" rx="9" fill="#06101E" opacity="0.6" />

    <!-- Windshield (Large Front Window) -->
    <path d="M 148 152 Q 148 144 158 144 L 354 144 Q 364 144 364 152 L 364 232 Q 364 240 354 240 L 158 240 Q 148 240 148 232 Z" fill="#06101E" />
    <!-- Windshield Driver Divider -->
    <line x1="256" y1="144" x2="256" y2="240" stroke="#10B981" stroke-width="4" stroke-opacity="0.4" />

    <!-- Lower Grill & Bumper -->
    <rect x="156" y="272" width="200" height="48" rx="14" fill="#06101E" opacity="0.85" />
    <!-- Grill Slats -->
    <line x1="184" y1="288" x2="328" y2="288" stroke="#34D399" stroke-width="4" stroke-linecap="round" stroke-opacity="0.8" />
    <line x1="200" y1="304" x2="312" y2="304" stroke="#34D399" stroke-width="4" stroke-linecap="round" stroke-opacity="0.8" />

    <!-- Headlights (Left & Right) -->
    <circle cx="160" cy="344" r="14" fill="#FEF08A" />
    <circle cx="160" cy="344" r="8" fill="#FACC15" />
    <circle cx="352" cy="344" r="14" fill="#FEF08A" />
    <circle cx="352" cy="344" r="8" fill="#FACC15" />

    <!-- Wheels (Bottom Left & Right) -->
    <rect x="136" y="388" width="44" height="28" rx="8" fill="#020710" />
    <rect x="332" y="388" width="44" height="28" rx="8" fill="#020710" />

    <!-- Side Mirrors -->
    <rect x="94" y="180" width="18" height="42" rx="7" fill="url(#busGrad)" />
    <rect x="400" y="180" width="18" height="42" rx="7" fill="url(#busGrad)" />
  </g>

  <!-- Brass Accent Status Dot (matching BusReserve 2.0 brand) -->
  <circle cx="396" cy="116" r="28" fill="#06101E" />
  <circle cx="396" cy="116" r="22" fill="url(#brassGrad)" />
  <circle cx="396" cy="116" r="14" fill="#FDE68A" opacity="0.6" />
</svg>
"""


def create_png_image(size: int) -> bytes:
    """Generate a clean RGBA PNG raster representation of the BusReserve logo."""
    # We will compute pixels procedurally on an RGBA grid
    width = size
    height = size
    pixels = bytearray(width * height * 4)

    # Color definitions
    navy_dark = (6, 16, 30, 255)
    navy_mid = (11, 30, 54, 255)
    emerald_main = (16, 185, 129, 255)
    emerald_light = (52, 211, 153, 255)
    emerald_dark = (5, 150, 105, 255)
    brass_gold = (245, 158, 11, 255)
    brass_bright = (252, 211, 77, 255)
    headlight = (254, 240, 138, 255)
    black = (2, 7, 16, 255)

    corner_radius = size * 0.22

    def is_inside_round_rect(x, y, rx, ry, rw, rh, rad):
        if x < rx or x >= rx + rw or y < ry or y >= ry + rh:
            return False
        # Check 4 corners
        cx = rx + rad if x < rx + rad else (rx + rw - rad if x > rx + rw - rad else x)
        cy = ry + rad if y < ry + rad else (ry + rh - rad if y > ry + rh - rad else y)
        dx = x - cx
        dy = y - cy
        return (dx * dx + dy * dy) <= (rad * rad)

    # Render each pixel
    for y in range(height):
        ny = y / height
        for x in range(width):
            nx = x / width
            idx = (y * width + x) * 4

            # Default transparent
            r, g, b, a = 0, 0, 0, 0

            # 1. Base Navy container with rounded corners
            if is_inside_round_rect(x, y, 0, 0, width, height, corner_radius):
                # Subtle vertical gradient
                blend = ny
                r = int(navy_mid[0] * (1 - blend) + navy_dark[0] * blend)
                g = int(navy_mid[1] * (1 - blend) + navy_dark[1] * blend)
                b = int(navy_mid[2] * (1 - blend) + navy_dark[2] * blend)
                a = 255

                # 2. Main Bus Body (Emerald rounded rectangle)
                bx = width * 0.23
                by = height * 0.20
                bw = width * 0.54
                bh = height * 0.60
                brad = max(2, bw * 0.18)

                if is_inside_round_rect(x, y, bx, by, bw, bh, brad):
                    # Emerald gradient
                    eblend = (nx + ny) * 0.5
                    r = int(emerald_light[0] * (1 - eblend) + emerald_dark[0] * eblend)
                    g = int(emerald_light[1] * (1 - eblend) + emerald_dark[1] * eblend)
                    b = int(emerald_light[2] * (1 - eblend) + emerald_dark[2] * eblend)

                    # 3. Windshield (Navy dark window)
                    wx = width * 0.28
                    wy = height * 0.28
                    ww = width * 0.44
                    wh = height * 0.22
                    wrad = max(1, ww * 0.10)
                    if is_inside_round_rect(x, y, wx, wy, ww, wh, wrad):
                        r, g, b = navy_dark[0], navy_dark[1], navy_dark[2]
                        # Center divider
                        if abs(x - width * 0.5) < max(1, width * 0.015):
                            r, g, b = emerald_main[0], emerald_main[1], emerald_main[2]

                    # 4. Lower Grill
                    gx = width * 0.30
                    gy = height * 0.55
                    gw = width * 0.40
                    gh = height * 0.12
                    grad = max(1, gw * 0.10)
                    if is_inside_round_rect(x, y, gx, gy, gw, gh, grad):
                        r, g, b = black[0], black[1], black[2]
                        # Horizontal grill line
                        if abs(y - (gy + gh * 0.5)) < max(1, height * 0.015):
                            r, g, b = emerald_light[0], emerald_light[1], emerald_light[2]

                    # 5. Headlights
                    hl_y = height * 0.70
                    hl_r = max(1.2, width * 0.035)
                    hl_lx = width * 0.31
                    hl_rx = width * 0.69
                    if ((x - hl_lx) ** 2 + (y - hl_y) ** 2) <= hl_r**2:
                        r, g, b = headlight[0], headlight[1], headlight[2]
                    elif ((x - hl_rx) ** 2 + (y - hl_y) ** 2) <= hl_r**2:
                        r, g, b = headlight[0], headlight[1], headlight[2]

                # 6. Wheels
                wheel_y = height * 0.80
                wheel_h = height * 0.06
                wheel_w = width * 0.10
                if (width * 0.26 <= x <= width * 0.36 or width * 0.64 <= x <= width * 0.74) and (
                    wheel_y <= y <= wheel_y + wheel_h
                ):
                    r, g, b = black[0], black[1], black[2]

                # 7. Brass Accent Dot at Top-Right
                dot_x = width * 0.78
                dot_y = height * 0.22
                dot_r = width * 0.075
                dist_sq = (x - dot_x) ** 2 + (y - dot_y) ** 2
                if dist_sq <= (dot_r + width * 0.015) ** 2:
                    # Border ring
                    r, g, b = navy_dark[0], navy_dark[1], navy_dark[2]
                if dist_sq <= dot_r**2:
                    r, g, b = brass_gold[0], brass_gold[1], brass_gold[2]
                if dist_sq <= (dot_r * 0.5) ** 2:
                    r, g, b = brass_bright[0], brass_bright[1], brass_bright[2]

            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = a

    return encode_png(width, height, bytes(pixels))


def encode_png(width: int, height: int, rgba_data: bytes) -> bytes:
    """Encode raw RGBA bytes into standard PNG format."""
    # Chunk generator
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # Signature
    png_sig = b"\x89PNG\r\n\x1a\n"

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)

    # IDAT (Scanlines with filter byte 0)
    stride = width * 4
    scanlines = bytearray()
    for row in range(height):
        scanlines.append(0)  # Filter type 0 (None)
        scanlines.extend(rgba_data[row * stride : (row + 1) * stride])

    compressed = zlib.compress(bytes(scanlines), level=9)
    idat = chunk(b"IDAT", compressed)

    # IEND
    iend = chunk(b"IEND", b"")

    return png_sig + ihdr + idat + iend


def encode_ico(images_png: list[tuple[int, bytes]]) -> bytes:
    """Pack multiple PNG images into a standard Windows ICO file."""
    # ICO Header: 2 reserved, 2 type (1=icon), 2 count
    count = len(images_png)
    ico_header = struct.pack("<HHH", 0, 1, count)

    entries = []
    data_offset = 6 + count * 16

    for size, png_bytes in images_png:
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entries.append(
            struct.pack(
                "<BBBBHHII",
                w,  # Width
                h,  # Height
                0,  # Color count (0=no palette)
                0,  # Reserved
                1,  # Color planes
                32,  # Bits per pixel
                len(png_bytes),  # Size of image data
                data_offset,  # Offset to image data
            )
        )
        data_offset += len(png_bytes)

    return ico_header + b"".join(entries) + b"".join([img[1] for img in images_png])


def main():
    out_dir = "frontend/public"
    os.makedirs(out_dir, exist_ok=True)

    print("Generating custom BusReserve 2.0 branding assets...")

    # 1. Vector SVG
    svg_path = os.path.join(out_dir, "favicon.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT.strip())
    print(f"Created: {svg_path}")

    # 2. PNG images
    sizes = {
        16: "favicon-16x16.png",
        32: "favicon-32x32.png",
        48: "favicon-48x48.png",
        180: "apple-touch-icon.png",
    }

    png_cache = {}
    for size, filename in sizes.items():
        png_data = create_png_image(size)
        png_cache[size] = png_data
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "wb") as f:
            f.write(png_data)
        print(f"Created: {out_path} ({len(png_data)} bytes)")

    # 3. Multi-resolution ICO (16, 32, 48)
    ico_images = [
        (16, png_cache[16]),
        (32, png_cache[32]),
        (48, png_cache[48]),
    ]
    ico_data = encode_ico(ico_images)
    ico_path = os.path.join(out_dir, "favicon.ico")
    with open(ico_path, "wb") as f:
        f.write(ico_data)
    print(f"Created: {ico_path} ({len(ico_data)} bytes)")

    print("\nAll favicon branding assets generated successfully!")


if __name__ == "__main__":
    main()
