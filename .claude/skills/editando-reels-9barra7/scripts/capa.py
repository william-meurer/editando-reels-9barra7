"""Thumb do reel (padrao-edicao.md, "Thumb"), aprovada no reel 01: a foto da Marilia escurecida, faixas verticais de
vidro escuro nas laterais, degradê embaixo, logo 9barra7 Academy branco centralizado no alto, pílula e título em duas
linhas (DM Sans Medium pequena + Rules Compressed Black grande, ambas brancas). Tudo dentro do recorte 3:4 da grade (y 240-1680).
A foto é um quadro de imagem/camera-edicao.mp4 (ffmpeg -ss <s> -frames:v 1), com ela sorrindo e olhando pra câmera.
Uso: capa.py <quadro.png> <saida.jpg> "<linha pequena>" "<LINHA GRANDE>" ["<pílula>"]"""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance
import os
KIT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'Produção', 'kit')) + '/'
W, H = 1080, 1920
foto, saida, L1, L2 = sys.argv[1:5]
PILULA = sys.argv[5] if len(sys.argv) > 5 else 'Render com IA'
z = 1.12
cam = Image.open(foto).convert('RGB')
c = cam.resize((int(W * z), int(H * z)), Image.LANCZOS)
oy = int(0.30 * (c.height - H))
img = c.crop(((c.width - W) // 2, oy, (c.width - W) // 2 + W, oy + H))
# clima: menos brilho, um pouco mais de contraste, levemente dessaturado
img = ImageEnhance.Brightness(img).enhance(0.8)
img = ImageEnhance.Contrast(img).enhance(1.12)
img = ImageEnhance.Color(img).enhance(0.9)
base = img.convert('RGBA')
# faixas verticais de vidro escuro (as laterais mais escuras, o centro limpo pro rosto)
faixas = Image.new('RGBA', (W, H), (0, 0, 0, 0)); df = ImageDraw.Draw(faixas)
for x0, x1, a in [(0, 150, 120), (150, 330, 70), (750, 930, 70), (930, 1080, 120)]:
    df.rectangle([x0, 0, x1, H], fill=(0, 0, 0, a))
    df.line([(x1, 0), (x1, H)], fill=(255, 255, 255, 14), width=2)
base.alpha_composite(faixas)
# degradê: escuro no topo (logo) e forte embaixo (título)
g = Image.new('L', (1, H))
for y in range(H):
    t = y / H
    v = 110 * max(0, (0.18 - t) / 0.18) + 245 * max(0, (t - 0.52) / 0.48) ** 1.3
    g.putpixel((0, y), int(min(255, v)))
base.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), 0)] * 3 + [g.resize((W, H))]))
d = ImageDraw.Draw(base)
# logo centralizado no topo (dentro do recorte 3:4 da grade: y >= 240), versão branca
logo = Image.open(KIT + 'logo/9barra7-academy.png').convert('RGBA')
r, gg, b, a = logo.split()
lum = ImageOps.invert(Image.merge('RGB', (r, gg, b)).convert('L'))
logo = Image.merge('RGBA', (lum, lum, lum, a))
LW = 430; logo = logo.resize((LW, int(logo.height * LW / logo.width)), Image.LANCZOS)
base.alpha_composite(logo, ((W - LW) // 2, 300))
# título: linha 1 DM Sans Medium pequena, linha 2 Rules Compressed Black grande, as duas brancas
# as duas linhas com a mesma largura, alinhadas nas duas beiradas (pedido do William, reel 04). A grande fica em 200
# e a pequena muda de corpo pra bater (56 a 120). Pequena curta demais: cresce até 120, abre o espaçamento até +14
# e só então a grande encolhe; pequena longa demais: fica em 56 e a grande cresce
def larg(texto, fonte, track):
    return sum(fonte.getlength(ch) + track for ch in texto) - track
def linha(texto, fonte, y, cor, track):
    x = (W - larg(texto, fonte, track)) / 2
    for ch in texto:
        d.text((x, y), ch, font=fonte, fill=cor, anchor='ls'); x += fonte.getlength(ch) + track
F1, F2 = KIT + 'fonte/DMSans-Medium.ttf', KIT + 'fonte/RulesCompressed-Black.otf'
t1, t2 = L1.upper(), L2.upper()
f2 = ImageFont.truetype(F2, 200); alvo = min(larg(t2, f2, 0), 960)
s1 = 76 * alvo / larg(t1, ImageFont.truetype(F1, 76), -2)
gaps1 = max(len(t1) - 1, 1)
if s1 > 120:
    s1 = 120; w1 = larg(t1, ImageFont.truetype(F1, 120), -2)
    if (alvo - w1) / gaps1 > 14:
        alvo = w1 + 14 * gaps1
        f2 = ImageFont.truetype(F2, round(200 * alvo / larg(t2, f2, 0)))
elif s1 < 56:
    s1 = 56; alvo = min(larg(t1, ImageFont.truetype(F1, 56), -2), 960)
    f2 = ImageFont.truetype(F2, round(200 * alvo / larg(t2, f2, 0)))
f1 = ImageFont.truetype(F1, round(s1))
k1 = -2 + (alvo - larg(t1, f1, -2)) / gaps1
k2 = (alvo - larg(t2, f2, 0)) / max(len(t2) - 1, 1)
# pílula: acima da linha pequena, com a mesma folga qualquer que seja o corpo dela
fp = ImageFont.truetype(KIT + 'fonte/DMSans-Medium.ttf', 36)
pil = PILULA
pw = fp.getlength(pil) + 56; py = round(1400 - 0.72 * s1 - 26 - 62)
d.rounded_rectangle([(W - pw) / 2, py, (W + pw) / 2, py + 62], 31, outline=(255, 255, 255, 235), width=2)
d.text((W / 2, py + 31), pil, font=fp, fill=(255, 255, 255, 255), anchor='mm')
linha(t1, f1, 1400, (255, 255, 255, 255), k1)
linha(t2, f2, 1612, (255, 255, 255, 255), k2)
base.convert('RGB').save(saida, quality=95)
