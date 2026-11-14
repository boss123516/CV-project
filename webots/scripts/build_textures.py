#!/usr/bin/env python3
"""Deterministic materials and storefront graphics, generated with Pillow."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'textures'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def font(size):
    return ImageFont.truetype(FONT,size)


def noise_texture(name,color,grain,seed=7):
    rng=np.random.default_rng(seed)
    n=rng.normal(0,grain,(512,512,1))
    image=Image.fromarray(np.uint8(np.clip(np.array(color)[None,None,:]+n,0,255)))
    image.save(OUT/name)
    return image


def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    noise_texture('asphalt.png',(66,70,73),7)
    paving=noise_texture('pavers.png',(161,155,141),5)
    d=ImageDraw.Draw(paving)
    for y in range(0,513,64):
        d.line((0,y,512,y),fill=(103,100,93),width=3)
        offset=64 if y%128 else 0
        for x in range(-128+offset,513,128):
            d.line((x,y,x,y+64),fill=(104,101,94),width=3)
            d.line((x+3,y+4,x+124,y+4),fill=(178,172,158),width=1)
    paving.save(OUT/'pavers.png')
    concrete=noise_texture('concrete.png',(182,180,171),4)
    d=ImageDraw.Draw(concrete)
    for xy in [(30,60,105,190),(105,190,90,265),(105,190,157,220),(389,460,423,383)]:
        d.line(xy,fill=(137,135,127),width=1)
    concrete.save(OUT/'concrete.png')
    brick=noise_texture('brick.png',(144,94,75),5)
    d=ImageDraw.Draw(brick)
    for y in range(0,513,64):
        d.line((0,y,512,y),fill=(184,177,160),width=5)
        offset=64 if y%128 else 0
        for x in range(-128+offset,513,128): d.line((x,y,x,y+64),fill=(184,177,160),width=5)
    brick.save(OUT/'brick.png')
    wood=noise_texture('wood.png',(119,79,46),5)
    d=ImageDraw.Draw(wood)
    rng=np.random.default_rng(22)
    for _ in range(130):
        y=int(rng.integers(512)); d.line((0,y,512,y+int(rng.integers(-3,4))),fill=(98,64,39),width=1)
    wood.save(OUT/'wood.png')
    tactile=Image.new('RGB',(256,256),(211,168,46));d=ImageDraw.Draw(tactile)
    for x in [34,80,126,172,218]: d.rounded_rectangle((x,0,x+14,256),radius=6,fill=(239,199,72))
    tactile.save(OUT/'tactile.png')
    blister=Image.new('RGB',(256,256),(211,168,46));d=ImageDraw.Draw(blister)
    for y in range(26,256,51):
        for x in range(26,256,51):
            d.ellipse((x-12,y-12,x+12,y+12),fill=(245,205,84))
    blister.save(OUT/'blister.png')
    # An unbranded, weathered blank panel instead of shop/menu lettering.
    panel=noise_texture('menu.png',(53,62,60),4,seed=31)
    d=ImageDraw.Draw(panel)
    d.rectangle((14,14,498,498),outline=(111,106,91),width=8)
    for y in [102,199,302,411]:d.line((60,y,430,y+3),fill=(66,75,72),width=2)
    panel.save(OUT/'menu.png')
    im=Image.new('RGB',(1024,256),(235,183,43));d=ImageDraw.Draw(im)
    for x in range(-256,1100,128): d.polygon([(x,0),(x+66,0),(x+322,256),(x+256,256)],fill=(42,43,40))
    d.rectangle((267,48,757,208),fill=(241,231,208))
    d.text((512,129),'보도 공사 중',font=font(67),fill=(42,43,40),anchor='mm')
    im.save(OUT/'roadworks.png')
    print(f'Generated {len(list(OUT.glob("*.png")))} local texture assets')


if __name__=='__main__': generate()
