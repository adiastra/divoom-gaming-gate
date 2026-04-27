from PIL import Image, ImageDraw, ImageFont
import os

def compose_character_image(background, portrait, name, stats):
    if background and os.path.exists(background):
        bg = Image.open(background).convert("RGB").resize((128, 128))
    else:
        bg = Image.new("RGB", (128, 128), (0, 0, 0))

    draw = ImageDraw.Draw(bg, "RGBA")
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    name_box_height = 22
    draw.rectangle([0, 0, 128, name_box_height], fill=(40, 40, 40, 180))
    try:
        bbox = draw.textbbox((0, 0), name, font=font)
        text_w = bbox[2] - bbox[0]
    except AttributeError:
        text_w, _ = font.getsize(name)
    draw.text(((128 - text_w) // 2, 4), name, fill=(255, 255, 255), font=font)

    stat_keys = list(stats.keys())
    midpoint = (len(stat_keys) + 1) // 2
    left_stats = stat_keys[:midpoint]
    right_stats = stat_keys[midpoint:]

    stat_box_top = name_box_height + 2
    stat_box_height = max(len(left_stats), len(right_stats)) * 16 + 4
    draw.rectangle([0, stat_box_top, 128, stat_box_top + stat_box_height], fill=(40, 40, 40, 180))

    for col, stat_list in enumerate([left_stats, right_stats]):
        for i, key in enumerate(stat_list):
            y = stat_box_top + 2 + i * 16
            x = 6 if col == 0 else 68
            stat_value = stats[key] if isinstance(stats[key], dict) else {"base": stats[key]}
            base = str(stat_value.get("base", ""))
            current = str(stat_value.get("current", ""))
            modifier = str(stat_value.get("modifier", ""))

            draw.text((x, y), f"{key}: ", fill=(200, 200, 200), font=font)
            x_offset = x + draw.textlength(f"{key}: ", font=font)
            draw.text((x_offset, y), base, fill=(255, 255, 255), font=font)
            x_offset += draw.textlength(base, font=font)

            if current:
                draw.text((x_offset, y), f" / {current}", fill=(200, 200, 200), font=font)
                x_offset += draw.textlength(f" / {current}", font=font)
            if modifier:
                color = (200, 200, 200)
                if modifier.startswith("+"):
                    color = (0, 200, 0)
                elif modifier.startswith("-"):
                    color = (220, 0, 0)
                draw.text((x_offset, y), f" ({modifier})", fill=color, font=font)
    return bg