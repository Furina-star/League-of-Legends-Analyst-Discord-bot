"""
This module provides a canvas engine for creating and manipulating images using the Pillow library.
It allows you to create a canvas, draw shapes, add text, and save the resulting image.
The engine is designed to be used in an asynchronous context, making it suitable for applications that require non-blocking operations.
"""
import logging
import os
import io
import asyncio
import aiohttp
import aiofiles
import logging
from PIL import Image, ImageDraw, ImageFont

# Get the logger system
logger = logging.getLogger(__name__)

# Dynamically lock the absolute path regardless of execution point
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up two levels from 'modules/interface' to reach the main bot root
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Configuration & Constants
ASSETS_DIR = os.path.join(ROOT_DIR, "data", "assets")
CACHE_DIR = os.path.join(ASSETS_DIR, "img_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Strict Color Palette
WHITE_TEXT = (255, 255, 255)
GOLD_TEXT = (255, 215, 0)
BLUE_TEXT = (43, 109, 240)
RED_TEXT = (240, 43, 43)
DIM_TEXT = (114, 118, 125)
BG_COLOR = (43, 45, 49, 255)
SHADOW_COLOR = (0, 0, 0, 200)

_ASSET_CACHE = {}

# Get the Data Dragon patch for this file dynamically
async def _get_patch_version(session: aiohttp.ClientSession) -> str:
    if "patch_version" not in _ASSET_CACHE:
        try:
            async with session.get("https://ddragon.leagueoflegends.com/api/versions.json") as resp:
                if resp.status == 200:
                    versions = await resp.json()
                    _ASSET_CACHE["patch_version"] = versions[0]
                else:
                    _ASSET_CACHE["patch_version"] = "14.8.1"
        except aiohttp.ClientError:
            _ASSET_CACHE["patch_version"] = "14.8.1"
    return _ASSET_CACHE["patch_version"]

# Helper to load and cache fonts in memory.
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    cache_key = f"font_{size}"
    if cache_key not in _ASSET_CACHE:
        try:
            _ASSET_CACHE[cache_key] = ImageFont.truetype(f"{ASSETS_DIR}/fonts/BeaufortForLOL-Bold.ttf", size)
        except OSError:
            try:
                _ASSET_CACHE[cache_key] = ImageFont.truetype("arial.ttf", size)
            except OSError:
                _ASSET_CACHE[cache_key] = ImageFont.load_default()
    return _ASSET_CACHE[cache_key]

# Helper to load, composite, and cache the background image.
def _get_background(bg_filename: str = "background.jpg") -> Image.Image:
    cache_key = f"bg_{bg_filename}"
    if cache_key not in _ASSET_CACHE:
        bg_path = os.path.join(ASSETS_DIR, "background", bg_filename)

        if os.path.exists(bg_path):
            background = Image.open(bg_path).convert("RGBA").resize((800, 660))
            overlay = Image.new("RGBA", (800, 660), (0, 0, 0, 40))
            _ASSET_CACHE[cache_key] = Image.alpha_composite(background, overlay)
        else:
            # Print a critical error
            logger.critical(f"Missing background image at {bg_path}! Falling back to solid color.")
            _ASSET_CACHE[cache_key] = Image.new("RGBA", (800, 660), BG_COLOR)

    return _ASSET_CACHE[cache_key].copy()

# Helper to cache the gold selection border.
def _get_select_icon() -> Image.Image | None:
    if "select_icon" not in _ASSET_CACHE:
        try:
            _ASSET_CACHE["select_icon"] = Image.open(f"{ASSETS_DIR}/icon/champion_series_icon.png").convert("RGBA").resize(
                (80, 80))
        except OSError:
            _ASSET_CACHE["select_icon"] = None
    return _ASSET_CACHE["select_icon"]

# Helper to cache the champion icon rounded edge mask.
def _get_rounded_mask() -> Image.Image:
    if "mask" not in _ASSET_CACHE:
        mask = Image.new("L", (80, 80), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 80, 80), radius=12, fill=255)
        _ASSET_CACHE["mask"] = mask
    return _ASSET_CACHE["mask"]

# Helper to cache a smaller rounded mask for banned champions
def _get_ban_mask() -> Image.Image:
    if "ban_mask" not in _ASSET_CACHE:
        mask = Image.new("L", (45, 45), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 45, 45), radius=8, fill=255)
        _ASSET_CACHE["ban_mask"] = mask
    return _ASSET_CACHE["ban_mask"]

# Asynchronous Data Fetching
async def fetch_icon(session: aiohttp.ClientSession, champ: str) -> Image.Image:
    if champ == "Unknown" or "(You)" in champ:
        return Image.new("RGBA", (80, 80), BG_COLOR)

    filepath = os.path.join(CACHE_DIR, f"{champ}.png")

    if not os.path.exists(filepath):
        patch_version = await _get_patch_version(session)
        url = f"https://ddragon.leagueoflegends.com/cdn/{patch_version}/img/champion/{champ}.png"

        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                async with aiofiles.open(filepath, "wb") as f:
                    await f.write(data)
            else:
                return Image.new("RGBA", (80, 80), BG_COLOR)

    return Image.open(filepath).convert("RGBA").resize((80, 80))

# Helper to perfectly center and shadow title text.
def _draw_centered_header(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, fill: tuple):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((x - w / 2 + 2, y + 2), text, fill=SHADOW_COLOR, font=font)
    draw.text((x - w / 2, y), text, fill=fill, font=font)

# Helper to determine the display text and color for each slot, reducing complexity in the main drawing loop.
def _resolve_slot_visuals(current_val: str, pos: str, is_user: bool, team_name: str, player_name: str=None) -> tuple[str, tuple]:
    if current_val == "Unknown":
        formatted_pos = "ADC" if pos == "adc" else pos.title()
        return f"[{formatted_pos}]", (GOLD_TEXT if is_user else WHITE_TEXT)

    # Slice the name if it is too long to prevent center overlap
    if player_name and len(player_name) > 11:
        player_name = player_name[:10] + "…"

    display_text = player_name if player_name else current_val
    text = f"{display_text} (You)" if is_user else display_text
    color = BLUE_TEXT if team_name == "Blue" else RED_TEXT
    return text, color

# Helper to draw either the Blue or Red side columns using the exact same logic.
def _draw_team_column(canvas: Image.Image, draw: ImageDraw.ImageDraw, icons: list, team_dict: dict, role: str, user_team: str, team_name: str, x_offset: int, align: str, names_dict: dict=None):
    y = 100
    positions = ['top', 'jungle', 'mid', 'adc', 'support']

    mask = _get_rounded_mask()
    select_icon = _get_select_icon()
    font = _get_font(28)

    for i, icon in enumerate(icons):
        canvas.paste(icon, (x_offset, y), mask)

        is_user_slot = (user_team == team_name and positions[i] == role)
        if is_user_slot and select_icon:
            canvas.paste(select_icon, (x_offset, y), select_icon)

        # Grab the player's name for this role if the dictionary exists
        champ_name = team_dict[positions[i]]
        player_name = names_dict[positions[i]] if names_dict else None

        display_text, text_color = _resolve_slot_visuals(champ_name, positions[i], is_user_slot, team_name, player_name)

        if align == "left":
            text_x = x_offset + 100
        else:
            text_bbox = draw.textbbox((0, 0), display_text, font=font)
            text_x = x_offset - 20 - (text_bbox[2] - text_bbox[0])

        draw.text((text_x + 2, y + 27), display_text, fill=SHADOW_COLOR, font=font)
        draw.text((text_x, y + 25), display_text, fill=text_color, font=font)

        y += 90

# Main Execution Engine
async def render_draft_board(blue_dict: dict, red_dict: dict, role: str, user_team: str, banned_champs: list | None = None, blue_names: dict | None = None, red_names: dict | None = None, blue_prob: float | None = None, red_prob: float | None = None, bg_filename: str = "background.jpg") -> io.BytesIO:
    canvas = _get_background(bg_filename)
    draw = ImageDraw.Draw(canvas)

    _draw_centered_header(draw, "BLUE TEAM", 200, 30, _get_font(36), BLUE_TEXT)
    _draw_centered_header(draw, "RED TEAM", 600, 30, _get_font(36), RED_TEXT)
    _draw_centered_header(draw, "VS", 400, 42, _get_font(58), GOLD_TEXT)

    positions = ['top', 'jungle', 'mid', 'adc', 'support']
    async with aiohttp.ClientSession() as session:
        blue_icons = await asyncio.gather(*[fetch_icon(session, blue_dict[p]) for p in positions])
        red_icons = await asyncio.gather(*[fetch_icon(session, red_dict[p]) for p in positions])
        if banned_champs is not None:
            ban_icons = await asyncio.gather(*[fetch_icon(session, champ) for champ in banned_champs])

    _draw_team_column(canvas, draw, blue_icons, blue_dict, role, user_team, "Blue", 40, "left", blue_names)
    _draw_team_column(canvas, draw, red_icons, red_dict, role, user_team, "Red", 680, "right", red_names)

    # Tug of War Bar
    if blue_prob is not None and red_prob is not None:
        bar_x, bar_y = 100, 565
        bar_w, bar_h = 600, 24

        draw.rectangle([bar_x - 2, bar_y - 2, bar_x + bar_w + 2, bar_y + bar_h + 2], fill=(20, 20, 20, 220))

        blue_w = int(bar_w * blue_prob)
        draw.rectangle([bar_x, bar_y, bar_x + blue_w, bar_y + bar_h], fill=(43, 109, 240, 230))
        draw.rectangle([bar_x + blue_w, bar_y, bar_x + bar_w, bar_y + bar_h], fill=(240, 43, 43, 230))

        # The text percentage inside the Tug-of-war bar
        prob_font = _get_font(18)
        draw.text(
            (bar_x + 10, bar_y),
            f"{blue_prob * 100:.1f}%",
            fill=WHITE_TEXT,
            font=prob_font,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255)
        )

        red_text = f"{red_prob * 100:.1f}%"
        red_bbox = draw.textbbox((0, 0), red_text, font=prob_font)
        draw.text(
            (bar_x + bar_w - (red_bbox[2] - red_bbox[0]) - 10, bar_y),
            red_text,
            fill=WHITE_TEXT,
            font=prob_font,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255)
        )

    # Draw the Banned Champions Section!
    if banned_champs is not None:
        _draw_centered_header(draw, "BANNED CHAMPIONS", 400, 565, _get_font(24), DIM_TEXT)
        ban_size = 45
        spacing = 15
        total_slots = 10
        total_w = total_slots * ban_size + (total_slots - 1) * spacing
        start_x = int(400 - (total_w / 2))
        ban_mask = _get_ban_mask()

        for i in range(total_slots):
            x = start_x + i * (ban_size + spacing)
            y = 600

            if i < len(banned_champs):
                small_icon = ban_icons[i].resize((ban_size, ban_size), Image.Resampling.LANCZOS)
                grayscale = small_icon.convert("LA").convert("RGBA")
                canvas.paste(grayscale, (x, y), ban_mask)
                draw.line((x + 4, y + ban_size - 4, x + ban_size - 4, y + 4), fill=(240, 43, 43, 230), width=4)
            else:
                draw.rounded_rectangle(
                    (x, y, x + ban_size, y + ban_size),
                    radius=8, fill=(30, 32, 36, 180), outline=(80, 84, 92, 200), width=2
                )
    else:
        if blue_prob is not None:
            canvas = canvas.crop((0, 0, 800, 610))
        else:
            canvas = canvas.crop((0, 0, 800, 560))

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer