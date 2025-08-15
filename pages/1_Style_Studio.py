# pages/1_Style_Studio.py
from __future__ import annotations

import io, math, random
from typing import Dict, Tuple
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageChops

#App setup
st.set_page_config(page_title="Style Studio", page_icon="👗", layout="wide")
CANVAS_W, CANVAS_H = 900, 1200

#tiny utils
def blank(size: Tuple[int,int]=(CANVAS_W, CANVAS_H), color=(0,0,0,0)) -> Image.Image:
    return Image.new("RGBA", size, color)

def try_font(size: int):
    for cand in ("arial.ttf", "DejaVuSans.ttf"):
        try: return ImageFont.truetype(cand, size)
        except Exception: pass
    return ImageFont.load_default()

def hex_to_rgb(h: str):
    s = h.strip().lstrip("#")
    if len(s)==3: s="".join(c*2 for c in s)
    return int(s[0:2],16), int(s[2:4],16), int(s[4:6],16)

def contrast_text(h: str) -> str:
    r,g,b = hex_to_rgb(h)
    return "#000000" if (0.2126*r+0.7152*g+0.0722*b) > 165 else "#ffffff"

def rr(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int=1):
    try: draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception: draw.rectangle(box, fill=fill, outline=outline, width=width)

def soft_bg(color="#f6eff6"):
    layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), hex_to_rgb(color)+(255,))
    d = ImageDraw.Draw(layer, "RGBA")
    rr(d, (16,16,CANVAS_W-16,CANVAS_H-16), 30, outline=(255,255,255,180), width=2)
    # subtle vignette
    mask = Image.new("L", (CANVAS_W, CANVAS_H), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse((40,40,CANVAS_W-40,CANVAS_H-60), fill=90)
    mask = mask.filter(ImageFilter.GaussianBlur(110))
    haze = Image.merge("RGBA", (mask,mask,mask,mask))
    return Image.alpha_composite(layer, haze)

# fabrics
def fabric(size: Tuple[int,int], mode: str, primary: str, secondary: str, angle: int, scale: int, glitter: float):
    w,h = size
    base = Image.new("RGBA", size, secondary)
    d = ImageDraw.Draw(base, "RGBA")
    if mode == "Solid":
        pass
    elif mode == "Stripes":
        step = max(8, scale)
        ang = math.radians(angle % 180)
        L = int((w*w+h*h)**0.5)+200
        cx,cy = w//2,h//2
        ux,uy = math.cos(ang), math.sin(ang)
        vx,vy = -uy, ux
        for i in range(-L,L,step):
            x0 = cx+vx*i-ux*L; y0 = cy+vy*i-uy*L
            x1 = cx+vx*i+ux*L; y1 = cy+vy*i+uy*L
            d.line([(x0,y0),(x1,y1)], fill=primary, width=max(6,step//2))
    elif mode == "Polka":
        step = max(18, scale*2); r = max(5, scale//2)
        for y in range(0,h+step,step):
            for x in range(0,w+step,step):
                xo = x + (step//2 if (y//step)%2==0 else 0)
                d.ellipse((xo-r,y-r,xo+r,y+r), fill=primary)
    elif mode == "Check":
        step = max(14, scale)
        for y in range(0,h,step):
            for x in range(0,w,step):
                if ((x//step)+(y//step))%2==0:
                    d.rectangle((x,y,x+step,y+step), fill=primary)
    elif mode == "Gradient":
        r1,g1,b1 = hex_to_rgb(secondary); r2,g2,b2 = hex_to_rgb(primary)
        for yy in range(h):
            t = yy/(h-1)
            r = int(r1*(1-t)+r2*t); g=int(g1*(1-t)+g2*t); b=int(b1*(1-t)+b2*t)
            d.line([(0,yy),(w,yy)], fill=(r,g,b,255))
    # glitter
    if glitter>0:
        rng = random.Random(5)
        dots = Image.new("RGBA", size, (0,0,0,0))
        dd = ImageDraw.Draw(dots, "RGBA")
        n = int((w*h)/1200 * glitter)
        for _ in range(n):
            x=rng.randint(0,w-1); y=rng.randint(0,h-1)
            a=rng.randint(120,220); rad=rng.randint(1,2)
            dd.ellipse((x-rad,y-rad,x+rad,y+rad), fill=(255,255,255,a))
        base = Image.alpha_composite(base, dots)
    return base

def glossy(img: Image.Image, amount: float=0.16):
    if amount<=0: return img
    w,h = img.size
    g = Image.new("L",(1,h))
    for y in range(h):
        t = max(0, 1 - (y/h)*1.6)
        g.putpixel((0,y), int(255*t*amount))
    g = g.resize((w,h))
    return Image.alpha_composite(img, Image.merge("RGBA",(Image.new("L",(w,h),255),)*3+(g,)))

# BODY (proportionate head + jawline)
def draw_body(skin_hex: str, head_scale: float):
    """
    Returns (body_layer, geo) with:
      - head_top / head_bottom / head_h
      - body_mask for clothing fit
    """
    SS=4
    W,H = CANVAS_W*SS, CANVAS_H*SS
    cx = W//2
    skin = hex_to_rgb(skin_hex)

    body_hi = Image.new("RGBA",(W,H),(0,0,0,0))
    mask_hi = Image.new("L",(W,H),0)
    dm = ImageDraw.Draw(mask_hi,"L")

    torso_top = int(H*0.27)
    # head scaled
    head_h = int(H*0.115*head_scale); head_w=int(W*0.125*head_scale)
    neck_w=int(W*0.055); neck_h=int(H*0.055)
    torso_w=int(W*0.29); torso_h=int(H*0.33)
    waist_w=int(torso_w*0.68); hip_w=int(torso_w*1.04)

    # skull + jawline (heart-ish)
    skull = (cx-head_w//2, torso_top-head_h-int(H*0.03),
             cx+head_w//2, torso_top-int(H*0.03))
    dm.ellipse(skull, fill=255)
    jaw_y = torso_top-int(H*0.03); chin_y = jaw_y+int(head_h*0.38)
    dm.polygon([(cx-int(head_w*0.50),jaw_y),
                (cx-int(head_w*0.30),jaw_y+int(head_h*0.17)),
                (cx,chin_y),
                (cx+int(head_w*0.30),jaw_y+int(head_h*0.17)),
                (cx+int(head_w*0.50),jaw_y)], fill=255)

    # neck trapezoid
    dm.polygon([(cx-neck_w//2, jaw_y),
                (cx+neck_w//2, jaw_y),
                (cx+int(neck_w*0.62), jaw_y+neck_h),
                (cx-int(neck_w*0.62), jaw_y+neck_h)], fill=255)

    # torso hourglass
    underarm_y = torso_top+int(torso_h*0.16)
    waist_y = torso_top+int(torso_h*0.58); bottom_y = torso_top+torso_h
    dm.polygon([(cx-torso_w//2,torso_top),
                (cx-int(W*0.13),underarm_y),
                (cx-waist_w//2,waist_y),
                (cx-hip_w//2,bottom_y),
                (cx+hip_w//2,bottom_y),
                (cx+waist_w//2,waist_y),
                (cx+int(W*0.13),underarm_y),
                (cx+torso_w//2,torso_top)], fill=255)

    # arms
    arm_w=int(W*0.05); arm_l=int(H*0.22)
    axL = cx-torso_w//2-int(W*0.015); axR = cx+torso_w//2+int(W*0.015)
    dm.rounded_rectangle((axL-arm_w//2, underarm_y-10, axL+arm_w//2, underarm_y-10+arm_l), 30, fill=255)
    dm.rounded_rectangle((axR-arm_w//2, underarm_y-10, axR+arm_w//2, underarm_y-10+arm_l), 30, fill=255)

    # legs
    leg_w=int(W*0.07); leg_h=int(H*0.30)
    leg_y0 = bottom_y+int(H*0.02); gap=int(W*0.02)
    for sgn in (-1,1):
        x = cx+sgn*(gap+leg_w//2)
        dm.rounded_rectangle((x-leg_w//2, leg_y0, x+leg_w//2, leg_y0+leg_h), 40, fill=255)

    # fill color by mask
    fill = Image.new("RGBA",(W,H), skin+(255,))
    body_hi = Image.composite(fill, body_hi, mask_hi)

    # subtle clavicle
    db = ImageDraw.Draw(body_hi,"RGBA")
    db.arc((cx-int(W*0.04), jaw_y+neck_h-int(H*0.01), cx+int(W*0.04), jaw_y+neck_h+int(H*0.03)),
           20, 160, fill=(0,0,0,22), width=max(1,SS))

    body = body_hi.resize((CANVAS_W,CANVAS_H), Image.LANCZOS)
    mask = mask_hi.resize((CANVAS_W,CANVAS_H), Image.LANCZOS)

    head_bottom = torso_top//SS
    head_top = head_bottom - (head_h//SS) - int(CANVAS_H*0.03)

    geo = {
        "cx": CANVAS_W//2, "torso_top": torso_top//SS, "torso_h": torso_h//SS,
        "torso_w": torso_w//SS, "waist_w": waist_w//SS, "hip_w": hip_w//SS,
        "leg_y0": leg_y0//SS, "leg_h": leg_h//SS,
        "head_top": head_top, "head_bottom": head_bottom, "head_h": head_h//SS,
        "underarm_y": underarm_y//SS, "neck_y": (jaw_y+neck_h)//SS, "body_mask": mask
    }
    return body, geo

# face (anchored to head box)
def draw_face(eye_hex:str, brow_hex:str, lip_hex:str, geo:Dict, brow_thick:int, eye_size:int, blush:bool):
    layer = blank()
    d = ImageDraw.Draw(layer,"RGBA")
    cx = geo["cx"]; head_top = geo["head_top"]

    er,eg,eb = hex_to_rgb(eye_hex)
    br, bg, bb = hex_to_rgb(brow_hex)
    lr,lg,lb = hex_to_rgb(lip_hex)

    # proportions inside head box (stable across styles)
    brow_y = head_top + int(geo["head_h"]*0.28)
    eye_y  = head_top + int(geo["head_h"]*0.38)
    lip_y  = head_top + int(geo["head_h"]*0.60)

    # brows
    t = max(4, brow_thick)
    rr(d, (cx-46, brow_y, cx-8, brow_y+t), 6, fill=(br,bg,bb,230))
    rr(d, (cx+8,  brow_y, cx+46, brow_y+t), 6, fill=(br,bg,bb,230))
    # eyes
    esw = max(10, eye_size)
    d.ellipse((cx-36, eye_y, cx-36+esw, eye_y+esw//2), fill=(er,eg,eb,230))
    d.ellipse((cx+16, eye_y, cx+16+esw, eye_y+esw//2), fill=(er,eg,eb,230))
    # nose bridge
    rr(d, (cx-2, eye_y+6, cx+2, eye_y+20), 2, fill=(0,0,0,28))
    # lips
    rr(d, (cx-14, lip_y, cx+14, lip_y+8), 8, fill=(lr,lg,lb,235))


    # blush
    if blush:
        overlay = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay, "RGBA")

        dx = int(geo["head_h"] * 0.30)   # horizontal offset from center
        drop = int(geo["head_h"] * 0.20) # LOWER than before so it sits mid-cheek
        rx = int(geo["head_h"] * 0.12)   # horizontal radius
        ry = int(geo["head_h"] * 0.08)   # vertical radius

        bcol = (255, 105, 180, 64)

        L = (cx - dx - rx, eye_y + drop - ry,
             cx - dx + rx, eye_y + drop + ry)
        R = (cx + dx - rx, eye_y + drop - ry,
             cx + dx + rx, eye_y + drop + ry)

        od.ellipse(L, fill=bcol)
        od.ellipse(R, fill=bcol)
        layer = Image.alpha_composite(layer, overlay)




    return layer


# hair (safe hairline + proportional volume)
def hair_layers(hair_hex: str, highlight_hex: str, style: str, geo: Dict, hairline: int, volume: int):
    back = blank(); front = blank()
    dB = ImageDraw.Draw(back, "RGBA")
    col = hex_to_rgb(hair_hex)

    cx        = geo["cx"]
    head_top  = geo["head_top"]
    head_h    = geo["head_h"]
    head_bot  = geo["head_bottom"]
    head_w    = int(head_h * 0.86)

    hairline  = int(max(6, min(hairline, head_h // 2)))
    volume    = int(max(0, min(volume, 100)))

    scalp_curve_h = int(head_h * 0.35)  # curve depth over forehead

    # Base scalp fill based on hairline + volume
    expand_x = 1.0 + (volume * 0.002)  # widen with volume
    expand_y = 1.0 + (volume * 0.001)  # height with volume

    scalp_top = head_top + hairline  # lowers hair if hairline slider is high
    scalp_w = int(head_w * expand_x)
    scalp_h = int((head_bot - scalp_top) * expand_y)
    dB.ellipse(
        (cx - scalp_w // 2, scalp_top,
         cx + scalp_w // 2, scalp_top + scalp_h),
        fill=col + (255,)
    )
    # FRONT/TOP SCALP FILL
    scalp_top = head_top + hairline
    scalp_w = int(head_w * (1.1 + volume * 0.002))  # widen slightly with volume
    scalp_h = int((head_bot - scalp_top) * (1.0 + volume * 0.001))  # taller with volume

    # Elliptical fill covering the top and blending into back hair
    dB.pieslice(
        (cx - scalp_w // 2, scalp_top - scalp_h // 3,
         cx + scalp_w // 2, scalp_top + scalp_h),
        start=180, end=360, fill=col + (255,)
    )

    #  STYLE LAYERS
    if style == "Bob":
        dB.pieslice(
            (cx - head_w//2 - 6, head_top,
             cx + head_w//2 + 6, head_bot),
            start=180, end=360, fill=col + (255,)
        )

    elif style == "Straight":
        dB.rectangle(
            (cx - head_w//2 - 4, head_top + scalp_curve_h,
             cx + head_w//2 + 4, head_bot + 20),
            fill=col + (255,)
        )

    elif style == "Waves":
        step = int(head_w * 0.25)
        for i in range(-head_w//2, head_w//2, step):
            dB.pieslice(
                (cx + i, head_bot - 10,
                 cx + i + step, head_bot + 10),
                start=0, end=180, fill=col + (255,)
            )

    elif style == "High Pony":
        # Ponytail above head
        dB.ellipse(
            (cx - 12, head_top - 28,
             cx + 12, head_top + 20),
            fill=col + (255,)
        )
        dB.rectangle(
            (cx - 6, head_top + 20,
             cx + 6, head_bot + 50),
            fill=col + (255,)
        )

    return back, front

# bodice + skirt masks
def bodice_mask(w:int,h:int, neckline:str, waist:int, sleeve:str):
    SS=4; W,H = w*SS, h*SS; cx=W//2
    m = Image.new("L",(W,H),0); d=ImageDraw.Draw(m,"L")
    shoulder=int(H*0.06); under=int(H*0.20); waist_y=int(H*0.60)
    torso_w=int(W*0.78); waist_w=max(SS, waist*SS)

    d.polygon([(cx-torso_w//2,shoulder),
               (cx-int(W*0.32),under),
               (cx-waist_w//2,waist_y),
               (cx+waist_w//2,waist_y),
               (cx+int(W*0.32),under),
               (cx+torso_w//2,shoulder)], fill=255)

    if neckline=="V-neck":
        depth=int(H*0.30)
        d.polygon([(cx, shoulder+depth),
                   (cx-int(W*0.20), shoulder),
                   (cx+int(W*0.20), shoulder)], fill=0)
    elif neckline=="Sweetheart":
        r=int(W*0.22); top=shoulder-int(H*0.02)
        d.pieslice((cx-r,top,cx,top+int(H*0.32)),0,180,fill=0)
        d.pieslice((cx,top,cx+r,top+int(H*0.32)),0,180,fill=0)
        d.polygon([(cx-int(W*0.06), top+int(H*0.16)),
                   (cx+int(W*0.06), top+int(H*0.16)),
                   (cx, top+int(H*0.22))], fill=0)
    elif neckline=="Off-Shoulder":
        band=int(H*0.12)
        d.rectangle((cx-int(W*0.50), shoulder-band, cx+int(W*0.50), shoulder+int(H*0.02)), fill=0)
        d.pieslice((cx-int(W*0.50), shoulder-band, cx+int(W*0.50), shoulder+band), 0, 180, fill=0)
    else: # Scoop
        r=int(W*0.28)
        d.pieslice((cx-r, shoulder-int(H*0.04), cx+r, shoulder+int(H*0.26)), 0, 180, fill=0)

    # sleeves
    if sleeve!="Sleeveless":
        if sleeve=="Cap":
            d.ellipse((cx-int(W*0.56), shoulder-int(H*0.02), cx-int(W*0.26), under+int(H*0.10)), fill=255)
            d.ellipse((cx+int(W*0.26), shoulder-int(H*0.02), cx+int(W*0.56), under+int(H*0.10)), fill=255)
        elif sleeve=="Puff":
            d.ellipse((cx-int(W*0.60), shoulder-int(H*0.04), cx-int(W*0.22), under+int(H*0.18)), fill=255)
            d.ellipse((cx+int(W*0.22), shoulder-int(H*0.04), cx+int(W*0.60), under+int(H*0.18)), fill=255)
        else: # Long
            r=int(H*0.08)
            ImageDraw.Draw(m,"L").rounded_rectangle((cx-int(W*0.60), under-r, cx-int(W*0.30), int(H*0.92)), r, fill=255)
            ImageDraw.Draw(m,"L").rounded_rectangle((cx+int(W*0.30), under-r, cx+int(W*0.60), int(H*0.92)), r, fill=255)

    return m.resize((w,h), Image.LANCZOS)

def skirt_mask(w:int,h:int, cut:str, flare:int):
    SS=4; W,H=w*SS, h*SS; cx=W//2
    m = Image.new("L",(W,H),0); d=ImageDraw.Draw(m,"L")
    top=int(H*0.02)
    if cut=="A-Line":
        d.polygon([(cx-int(W*0.22),top),(cx+int(W*0.22),top),
                   (cx+int(W*0.46), H-int(H*0.06)),(cx-int(W*0.46), H-int(H*0.06))], fill=255)
    elif cut=="Ball Gown":
        d.pieslice((cx-int(W*0.70), top, cx+int(W*0.70), H+int(H*0.70)), 200, -20, fill=255)
    elif cut=="Mermaid":
        waist=int(W*0.24); knee=int(H*0.55)
        d.polygon([(cx-waist//2,top),(cx+waist//2,top),
                   (cx+int(W*0.15),knee),(cx+int(W*0.46),H-int(H*0.04)),
                   (cx-int(W*0.46),H-int(H*0.04)),(cx-int(W*0.15),knee)], fill=255)
    else: # Sheath
        rad=int(W*0.05)
        ImageDraw.Draw(m,"L").rounded_rectangle((cx-int(W*0.24), top, cx+int(W*0.24), H), rad, fill=255)

    if flare>0 and cut in ("A-Line","Ball Gown"):
        glow = Image.new("L",(W,H),0); dg=ImageDraw.Draw(glow)
        dg.ellipse((cx-int(W*(0.34+0.01*flare)), H-int(H*0.25),
                    cx+int(W*(0.34+0.01*flare)), H+int(H*0.55)), fill=int(60+flare*3))
        glow = glow.filter(ImageFilter.GaussianBlur(24))
        m = ImageChops.lighter(m, glow)
    return m.resize((w,h), Image.LANCZOS)

# dress (fits to body via body mask)
def draw_dress(geo:Dict, palette:Dict, opts:Dict):
    layer = blank()
    cx = geo["cx"]; torso_top = geo["torso_top"]; torso_h=geo["torso_h"]
    body_mask = geo["body_mask"]
    dilated = body_mask.filter(ImageFilter.MaxFilter(9))

    # bodice
    bw = int(geo["torso_w"]*2.05); bh=int(torso_h*0.96)
    pat = fabric((bw,bh), opts["pattern"], palette["primary"], palette["secondary"], opts["angle"], opts["scale"], opts["glitter"])
    pat = glossy(pat, 0.16 if opts["gloss"] else 0)
    m_b = bodice_mask(bw,bh,opts["neckline"], waist=geo["waist_w"], sleeve=opts["sleeve"])
    left = cx-bw//2; top = torso_top-int(bh*0.10)
    body_crop = dilated.crop((left, top, left+bw, top+bh))
    m_b = ImageChops.multiply(m_b, body_crop)
    bod = Image.composite(pat, Image.new("RGBA",(bw,bh),(0,0,0,0)), m_b)
    tmp=blank(); tmp.paste(bod,(left,top),bod); layer=Image.alpha_composite(layer,tmp)


    # waist belt / monogram
    if opts["belt"]:
        waist_y = torso_top + int(torso_h * 0.57)
        belt_h = max(14, int(torso_h * 0.08))
        belt_w = int(geo["waist_w"] * 1.05)  # fits waist instead of torso width
        x0 = cx - belt_w // 2

        belt_img = Image.new("RGBA", (belt_w, belt_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(belt_img)

        def rrect(dr, box, r, **kw):
            dr.rounded_rectangle(box, radius=r, **kw)

        def darken(color_val, amt=0.15):
            # If it's a hex string, convert to RGBA
            if isinstance(color_val, str):
                r, g, b = hex_to_rgb(color_val)
                a = 255
            else:
                if len(color_val) == 3:
                    r, g, b = color_val
                    a = 255
                else:
                    r, g, b, a = color_val
            return (
                int(r * (1 - amt)),
                int(g * (1 - amt)),
                int(b * (1 - amt)),
                a
            )

        r = belt_h // 2
        rrect(draw, (0, 0, belt_w - 1, belt_h - 1), r,
              fill=palette["accent"],
              outline=darken(palette["accent"]),
              width=2)

        # unique center plate
        plate_w = max(48, int(belt_w * 0.25))
        plate_h = max(20, int(belt_h * 0.75))
        plate = Image.new("RGBA", (plate_w, plate_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        rrect(pd, (0, 0, plate_w - 1, plate_h - 1), plate_h // 2,
              fill=(255, 255, 255, 200))

        txt = (opts["monogram"][:3] or "BB").upper()
        f = try_font(min(18, plate_h - 6))
        tcol = contrast_text("#ffffff")
        tw, th = f.getlength(txt), f.size
        pd.text(((plate_w - tw) / 2, (plate_h - th) / 2 - 1), txt, font=f, fill=tcol)

        tmp = blank()
        tmp.paste(belt_img, (x0, waist_y - belt_h // 2), belt_img)
        px = x0 + (belt_w - plate_w) // 2
        py = waist_y - plate_h // 2
        tmp.paste(plate, (px, py), plate)
        layer = Image.alpha_composite(layer, tmp)


    # skirt
    sk_top = torso_top+int(torso_h*0.64)
    sh = geo["leg_y0"]+int(geo["leg_h"]*0.92)-sk_top
    sw = int(geo["torso_w"]*2.15)
    sp = fabric((sw,sh), opts["pattern"], palette["primary"], palette["secondary"], opts["angle"], opts["scale"], opts["glitter"])
    sp = glossy(sp, 0.14 if opts["gloss"] else 0)
    m_s = skirt_mask(sw,sh,opts["skirt_cut"], flare=opts["flare"])
    waist_crop = dilated.crop((cx-sw//2, sk_top, cx-sw//2+sw, sk_top+sh))
    m_s = ImageChops.lighter(m_s, waist_crop)
    skirt = Image.composite(sp, Image.new("RGBA",(sw,sh),(0,0,0,0)), m_s)
    tmp=blank(); tmp.paste(skirt,(cx-sw//2, sk_top), skirt); layer=Image.alpha_composite(layer,tmp)

    # hem highlight
    d = ImageDraw.Draw(layer,"RGBA")
    d.arc((cx-sw//2+8, sk_top+sh-36, cx+sw//2-8, sk_top+sh+36), 0,180, fill=palette["accent"], width=2)
    return layer

#shoes & jewelry
def draw_shoes(geo:Dict, shoe_hex:str):
    layer=blank(); d=ImageDraw.Draw(layer,"RGBA")
    cx=geo["cx"]; foot_y = geo["leg_y0"]+int(geo["leg_h"]*0.92)
    col = hex_to_rgb(shoe_hex)
    for sgn in (-1,1):
        x = cx+sgn*40
        rr(d,(x-20,foot_y-6,x+20,foot_y+10),8,fill=col+(255,),outline=(20,20,20,120),width=1)
        d.rectangle((x-16,foot_y+10,x+16,foot_y+24), fill=col+(235,))
    return layer

def draw_accessories(geo:Dict, acc_hex:str, glasses:bool, necklace:bool, earrings:bool):
    layer=blank(); d=ImageDraw.Draw(layer,"RGBA")
    cx=geo["cx"]; head_top = geo["head_top"]
    col = hex_to_rgb(acc_hex)
    if glasses:
        y=head_top + int(geo["head_h"]*0.36)
        rr(d,(cx-46,y-6,cx-8,y+6),6,outline=col+(255,),width=3)
        rr(d,(cx+8,y-6,cx+46,y+6),6,outline=col+(255,),width=3)
        d.line([(cx-8,y),(cx+8,y)], fill=col+(255,), width=3)
    if necklace:
        ny=geo["torso_top"]+22
        d.arc((cx-48,ny-12,cx+48,ny+24), 10,170, fill=col+(255,), width=3)
        d.ellipse((cx-3,ny+10,cx+3,ny+16), fill=col+(255,))
    if earrings:
        ear_y = head_top + int(geo["head_h"]*0.34)
        d.ellipse((cx-56, ear_y, cx-50, ear_y+8), fill=col+(255,))
        d.ellipse((cx+50, ear_y, cx+56, ear_y+8), fill=col+(255,))


    return layer


#  UI
with st.sidebar:
    st.header("Palette")
    c1,c2,c3 = st.columns(3)
    with c1: primary = st.color_picker("Primary", "#ff4fb7")
    with c2: secondary = st.color_picker("Secondary", "#ffe6f3")
    with c3: accent = st.color_picker("Accent", "#ffffff")
    palette = {"primary":primary, "secondary":secondary, "accent":accent}

    st.header("Doll")
    d1,d2,d3 = st.columns(3)
    with d1: skin = st.color_picker("Skin", "#f0d5c4")
    with d2: hair = st.color_picker("Hair", "#4a2f2a")
    with d3: eyes = st.color_picker("Eyes", "#1b1b1b")
    lips = st.color_picker("Lips", "#ff6b9a")
    brows = st.color_picker("Brows", "#3b2a26")
    hair_style = st.selectbox("Hair", ["Straight","Waves","High Pony","Bob"], index=1)
    head_scale = st.slider("Head Size", 0.8, 1.2, 0.95, 0.01)
    hairline = st.slider("Hairline (lower → more forehead)", 8, 40, 16, 1)
    volume = st.slider("Hair Volume", 0, 100, 40, 1)
    brow_thick = st.slider("Brow Thickness", 4, 18, 10, 1)
    eye_size = st.slider("Eye Size", 10, 22, 12, 1)
    blush = st.toggle("Blush", False)

    st.header("Dress")
    neckline = st.selectbox("Neckline", ["Scoop","V-neck","Sweetheart","Off-Shoulder"], index=2)
    sleeve = st.selectbox("Sleeves", ["Sleeveless","Cap","Puff","Long"], index=0)
    skirt = st.selectbox("Skirt", ["A-Line","Ball Gown","Mermaid","Sheath"], index=0)
    flare = st.slider("Flare", 0, 20, 6)
    pattern = st.selectbox("Pattern", ["Solid","Stripes","Polka","Check","Gradient"], index=0)
    angle = st.slider("Stripe Angle", 0, 180, 30, 2)
    scale = st.slider("Pattern Scale", 8, 80, 22, 2)
    glitter = st.slider("Glitter", 0.0, 1.0, 0.25, 0.05)
    gloss = st.toggle("Gloss", True)
    belt = st.toggle("Waist Belt", True)
    bow = st.toggle("Bow/Monogram", True)
    mono = st.text_input("Monogram", "BB")
    highlight = st.color_picker("Hair Highlight", "#ffffff")

    st.header("Accessories")
    shoes = st.color_picker("Shoes", "#2b2b2b")
    glasses = st.toggle("Sunglasses", False)
    necklace = st.toggle("Necklace", True)
    earrings = st.toggle("Earrings", True)

    st.header("Export")
    export_scale = st.select_slider("Scale", [1,2,3], value=2)

opts = {"pattern":pattern, "angle":angle, "scale":scale, "glitter":int(glitter*120),
        "gloss":gloss, "neckline":neckline, "sleeve":sleeve, "skirt_cut":skirt,
        "flare":flare, "belt":belt, "bow":bow, "monogram":mono}

#render
bg = soft_bg("#f6eff6")
body, geo = draw_body(skin, head_scale=head_scale)
hair_back, hair_front = hair_layers(hair, highlight, hair_style, geo, hairline=hairline, volume=volume)
face = draw_face(eyes, brows, lips, geo, brow_thick=brow_thick, eye_size=eye_size, blush=blush)
dress = draw_dress(geo, palette, opts)
shoes_layer = draw_shoes(geo, shoes)
acc = draw_accessories(geo, palette["accent"], glasses, necklace, earrings)

stage = Image.alpha_composite(bg, hair_back)
stage = Image.alpha_composite(stage, body)
stage = Image.alpha_composite(stage, dress)
stage = Image.alpha_composite(stage, shoes_layer)
stage = Image.alpha_composite(stage, face)
stage = Image.alpha_composite(stage, acc)
stage = Image.alpha_composite(stage, hair_front)

st.image(stage, caption="Style Studio — proportionate head • correct hairline • fitted dress", use_container_width=True)

# export
out = stage if export_scale==1 else stage.resize((CANVAS_W*export_scale, CANVAS_H*export_scale), Image.LANCZOS)
buf = io.BytesIO(); out.save(buf, format="PNG")
st.download_button("Download PNG", data=buf.getvalue(), file_name="barbie_style.png", mime="image/png", use_container_width=True)
