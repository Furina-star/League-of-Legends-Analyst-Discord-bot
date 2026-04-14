"""
This module provides a canvas engine for creating and manipulating images using the Pillow library.
It allows you to create a canvas, draw shapes, add text, and save the resulting image.
The engine is designed to be used in an asynchronous context, making it suitable for applications that require non-blocking operations.
"""

import os
import io
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# Cache folder so we only download Riot's images once
CACHE_DIR = "data/img_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
PATCH_VERSION = "16.7.1"

async def fetch_icon(session: aiohttp.ClientSession, champ: str) -> Image.Image:
    if champ == "Unknown" or "(You)" in champ:
        return Image.new("RGBA", (80, 80), (43, 45, 49, 255))

    if champ == "MonkeyKing": champ = "Wukong"  # Riot API naming edge case

    filepath = os.path.join(CACHE_DIR, f"{champ}.png")

    if not os.path.exists(filepath):
        url = f"http://ddragon.leagueoflegends.com/cdn/{PATCH_VERSION}/img/champion/{champ}.png"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)
            else:
                return Image.new("RGBA", (80, 80), (43, 45, 49, 255))

    return Image.open(filepath).convert("RGBA").resize((80, 80))


async def render_draft_board(blue_dict: dict, red_dict: dict, role: str, user_name: str, user_team: str) -> io.BytesIO:
    # 1. Background (🔥 FIX: Increased height from 480 to 560 for the header)
    bg_path = "data/assets/background.jpg"
    if os.path.exists(bg_path):
        background = Image.open(bg_path).convert("RGBA").resize((800, 560))
        overlay = Image.new("RGBA", (800, 560), (0, 0, 0, 80))
        canvas = Image.alpha_composite(background, overlay)
    else:
        canvas = Image.new("RGBA", (800, 560), (43, 45, 49, 255))

    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("data/assets/BeaufortForLOL-Bold.ttf", 28)
        header_font = ImageFont.truetype("data/assets/BeaufortForLOL-Bold.ttf", 36)
        vs_font = ImageFont.truetype("data/assets/BeaufortForLOL-Bold.ttf", 58)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 28)
            header_font = ImageFont.truetype("arial.ttf", 36)
            vs_font = ImageFont.truetype("arial.ttf", 58)
        except IOError:
            font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            vs_font = ImageFont.load_default()

    # 3. Selected Icon Overlay
    try:
        select_icon = Image.open("data/assets/champion_series_icon.png").convert("RGBA").resize((80, 80))
    except Exception:
        select_icon = None

    # 🎨 Colors
    WHITE_TEXT = (255, 255, 255)
    GOLD_TEXT = (255, 215, 0)
    BLUE_TEXT = (43, 109, 240)  # #2B6DF0
    RED_TEXT = (240, 43, 43)  # #F02B2B

    # 🏆 NEW: Helper function to easily center the beautiful headers
    def draw_centered(text, x, y, f, fill):
        bbox = draw.textbbox((0, 0), text, font=f)
        w = bbox[2] - bbox[0]
        # Shadow
        draw.text((x - w / 2 + 2, y + 2), text, fill=(0, 0, 0, 200), font=f)
        # Main Text
        draw.text((x - w / 2, y), text, fill=fill, font=f)

    draw_centered("BLUE TEAM", 200, 30, header_font, BLUE_TEXT)
    draw_centered("RED TEAM", 600, 30, header_font, RED_TEXT)
    draw_centered("VS", 400, 42, vs_font, GOLD_TEXT)

    positions = ['top', 'jungle', 'mid', 'adc', 'support']

    async with aiohttp.ClientSession() as session:
        blue_icons = await asyncio.gather(*[fetch_icon(session, blue_dict[p]) for p in positions])
        red_icons = await asyncio.gather(*[fetch_icon(session, red_dict[p]) for p in positions])

    # 4. Rounded Corners Mask
    mask = Image.new("L", (80, 80), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, 80, 80), radius=12, fill=255)

    # Draw Blue Side
    y = 100  # 🔥 FIX: Shifted down from 20 to 100 to leave space for the banner!
    for i, icon in enumerate(blue_icons):
        canvas.paste(icon, (40, y), mask)

        is_user_slot = (user_team == "Blue" and positions[i] == role)
        if is_user_slot and select_icon:
            canvas.paste(select_icon, (40, y), select_icon)

        current_val = blue_dict[positions[i]]
        if current_val == "Unknown":
            formatted_pos = "ADC" if positions[i] == "adc" else positions[i].title()
            display_text = f"[{formatted_pos}]"
            text_color = GOLD_TEXT if is_user_slot else WHITE_TEXT
        else:
            display_text = f"{current_val} (You)" if is_user_slot else current_val
            text_color = BLUE_TEXT

        draw.text((142, y + 27), display_text, fill=(0, 0, 0, 200), font=font)
        draw.text((140, y + 25), display_text, fill=text_color, font=font)
        y += 90

    # Draw Red Side
    y = 100  # 🔥 FIX: Shifted down from 20 to 100 to leave space for the banner!
    for i, icon in enumerate(red_icons):
        canvas.paste(icon, (680, y), mask)

        is_user_slot = (user_team == "Red" and positions[i] == role)
        if is_user_slot and select_icon:
            canvas.paste(select_icon, (680, y), select_icon)

        current_val = red_dict[positions[i]]
        if current_val == "Unknown":
            formatted_pos = "ADC" if positions[i] == "adc" else positions[i].title()
            display_text = f"[{formatted_pos}]"
            text_color = GOLD_TEXT if is_user_slot else WHITE_TEXT
        else:
            display_text = f"{current_val} (You)" if is_user_slot else current_val
            text_color = RED_TEXT

        text_bbox = draw.textbbox((0, 0), display_text, font=font)
        text_x = 660 - text_bbox[2]

        draw.text((text_x + 2, y + 27), display_text, fill=(0, 0, 0, 200), font=font)
        draw.text((text_x, y + 25), display_text, fill=text_color, font=font)
        y += 90

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer