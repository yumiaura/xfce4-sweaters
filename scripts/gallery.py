#!/usr/bin/env python3
"""Render the actual software textures for documentation (no desktop required)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from xfce4_sweaters.textures import Registry,border

# Window colours follow the myAura xfwm4/GTK theme: wm_bg for the title bar,
# theme_bg_color for the body, white title text and white button glyphs on the
# right (minimize, maximize, close), as in the theme's normal button state.
TITLE_BAR='#6a3043'; BODY='#5a2939'; TITLE_TEXT='#ffffff'; BODY_TEXT='#ece7ee'
REPOSITORY='https://github.com/yumiaura/xfce4-sweaters'

registry=Registry()
canvas=Image.new('RGB',(1440,1000),'#1e1b21')
draw=ImageDraw.Draw(canvas)
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try:
    heading=ImageFont.truetype(font_path,42); label=ImageFont.truetype(font_path,21); small=ImageFont.truetype(font_path,15)
except OSError:
    heading=label=small=ImageFont.load_default()
draw.text((60,40),'xfce4-sweaters',fill='#ece7ee',font=heading)
choices=[('zigzag','#648e7b'),('twinkle','#c78461'),('ribbon','#8279ab'),('pastel-patchwork','#b56e84'),('checker','#7297b8'),('seedling','#596f4c')]
for index,(texture,color) in enumerate(choices):
    x=60+(index%3)*450; y=140+(index//3)*385
    frame=border(registry,420,290,{'texture':texture,'color':color,'width':30,'stitch':5})
    left,top,right,bottom=x+30,y+30,x+390,y+260
    draw.rounded_rectangle((left,top,right,bottom),radius=6,fill=BODY)
    draw.rounded_rectangle((left,top,right,top+36),radius=6,fill=TITLE_BAR)
    draw.rectangle((left,top+18,right,top+36),fill=TITLE_BAR)
    draw.text((left+8,top+11),'Terminal' if index%2==0 else 'Notes',font=small,fill=TITLE_TEXT)
    close_x,max_x,min_x=(right-14-slot*22 for slot in range(3)); cy=top+18
    draw.line((min_x-5,cy+4,min_x+5,cy+4),fill=TITLE_TEXT,width=2)
    draw.rectangle((max_x-5,cy-5,max_x+5,cy+5),outline=TITLE_TEXT,width=2)
    draw.line((close_x-5,cy-5,close_x+5,cy+5),fill=TITLE_TEXT,width=2); draw.line((close_x-5,cy+5,close_x+5,cy-5),fill=TITLE_TEXT,width=2)
    draw.text((left+35,top+80),registry.specs[texture]['name'],font=label,fill=BODY_TEXT)
    canvas.paste(frame,(x,y),frame)
    draw.text((x+5,y+306),f'{texture}  /  {color}',font=small,fill='#b9b0bd')
draw.text((60,952),REPOSITORY,fill='#a9a0ad',font=label)
output=Path(sys.argv[1]) if len(sys.argv)>1 else Path('docs/textures.png')
canvas.save(output)
print(output)
