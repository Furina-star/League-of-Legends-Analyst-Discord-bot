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
    # Load and prepare the Background Image
    bg_path = "data/assets/background.jpg"
    if os.path.exists(bg_path):
        # Load the custom background and resize it to canvas dimensions
        background = Image.open(bg_path).convert("RGBA").resize((800, 480))

        # Add a semi-transparent dark overlay so the text pops
        overlay = Image.new("RGBA", (800, 480), (0, 0, 0, 80))
        canvas = Image.alpha_composite(background, overlay)
    else:
        # Fallback to the classic Discord dark gray if the file is missing
        canvas = Image.new("RGBA", (800, 480), (43, 45, 49, 255))

    draw = ImageDraw.Draw(canvas)

    # Load the special "Selected" icon
    try:
        select_icon = Image.open("data/assets/champion_series_icon.png").convert("RGBA").resize((30, 30))
    except:
        select_icon = None

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        font = ImageFont.load_default()

    positions = ['top', 'jungle', 'mid', 'adc', 'support']

    # Download/Load all 10 champion images simultaneously
    async with aiohttp.ClientSession() as session:
        blue_icons = await asyncio.gather(*[fetch_icon(session, blue_dict[p]) for p in positions])
        red_icons = await asyncio.gather(*[fetch_icon(session, red_dict[p]) for p in positions])

    # Define colors for the labels
    BLUE_TEXT = (88, 101, 242)  # Discord Blurple
    RED_TEXT = (237, 66, 69)  # Discord Red
    WHITE_TEXT = (255, 255, 255)  # Discord Secondary Text (Gray)
    GOLD_TEXT = (255, 215, 0)

    # Draw Blue Side
    y = 20
    for i, icon in enumerate(blue_icons):
        canvas.paste(icon, (40, y), icon)
        current_val = blue_dict[positions[i]]
        is_user_slot = (user_team == "Blue" and positions[i] == role)

        if current_val == "Unknown":
            display_text = f"[{positions[i].upper()}]"
            text_color = GOLD_TEXT if is_user_slot else WHITE_TEXT
        else:
            display_text = f"{current_val} (You)" if is_user_slot else current_val
            text_color = BLUE_TEXT

        if is_user_slot and select_icon:
            canvas.paste(select_icon, (140, y - 5), select_icon)
            draw.text((180, y + 25), display_text, fill=text_color, font=font)
        else:
            draw.text((140, y + 25), display_text, fill=text_color, font=font)
        y += 90

    # Draw Red Side
    y = 20
    for i, icon in enumerate(red_icons):
        canvas.paste(icon, (680, y), icon)
        current_val = red_dict[positions[i]]
        is_user_slot = (user_team == "Red" and positions[i] == role)

        if current_val == "Unknown":
            display_text = f"[{positions[i].upper()}]"
            text_color = GOLD_TEXT if is_user_slot else WHITE_TEXT
        else:
            display_text = f"{current_val} (You)" if is_user_slot else current_val
            text_color = RED_TEXT

        text_bbox = draw.textbbox((0, 0), display_text, font=font)
        text_x = 660 - text_bbox[2]

        if is_user_slot and select_icon:
            canvas.paste(select_icon, (text_x - 40, y - 5), select_icon)
            draw.text((text_x, y + 25), display_text, fill=text_color, font=font)
        else:
            draw.text((text_x, y + 25), display_text, fill=text_color, font=font)
        y += 90

    # Save to memory stream
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer