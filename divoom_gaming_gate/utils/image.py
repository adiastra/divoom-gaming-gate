from PIL import Image, ImageDraw, ImageFont

def compose_character_image(background, portrait, name, stats):
    img = Image.new('RGB',(128,128),'black')
    draw = ImageDraw.Draw(img)
    total_lines = len(stats) + 3
    line_h = 12; pad = 5; box_h = total_lines*line_h + pad*2
    overlay = Image.new('RGBA',(128,128),(0,0,0,0))
    do = ImageDraw.Draw(overlay)
    do.rectangle([(0,128-box_h),(128,128)],fill=(50,50,50,200))
    img = Image.alpha_composite(img.convert('RGBA'),overlay).convert('RGB')
    draw = ImageDraw.Draw(img); font=ImageFont.load_default()
    bbox=draw.textbbox((0,0),name,font=font); w=bbox[2]-bbox[0]
    draw.text(((128-w)/2,pad),name,font=font,fill=(255,255,255,255))
    y=128-box_h+pad
    for stat,val in stats.items(): draw.text((5,y),f"{stat}: {val}",font=font,fill=(255,255,255,255)); y+=line_h
    draw.text((5,y),f"Wound: {stats.get('Brawn',0)+10}",font=font,fill=(255,200,0,255)); y+=line_h
    draw.text((5,y),f"Strain: {stats.get('Willpower',0)+10}",font=font,fill=(255,200,0,255))
    return img