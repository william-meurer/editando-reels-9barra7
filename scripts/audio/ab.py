#!/usr/bin/env python3
"""Vídeo A/B de áudio: o mesmo trecho em várias versões, uma depois da outra, com o nome escrito na tela
e o volume igualado (a mais alta sempre parece a melhor). Áudio em PCM até a emenda, AAC só no final.
Uso: ab.py video_fonte.mov saida.mp4 inicio_s duracao_s "arq.wav|TÍTULO|subtítulo" ..."""
import os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

F = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def lufs(p):
    s = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', s[s.rindex('Summary'):]).group(1))

fonte, saida, t0, dur = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
tmp = tempfile.mkdtemp(); partes = []
for i, v in enumerate(sys.argv[5:]):
    arq, tit, sub = v.split('|')
    im = Image.new('RGBA', (720, 1280), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 60, 720, 230], fill=(0, 0, 0, 190))
    d.text((360, 120), tit, font=ImageFont.truetype(F, 50), fill='white', anchor='mm')
    d.text((360, 185), sub, font=ImageFont.truetype(F, 28), fill=(200, 200, 200), anchor='mm')
    rot, cw, pv = f'{tmp}/r{i}.png', f'{tmp}/c{i}.wav', f'{tmp}/p{i}.mov'
    im.save(rot)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t0), '-t', str(dur), '-i', arq, '-c:a', 'pcm_f32le', cw], check=True)
    g = -15.0 - lufs(cw)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t0), '-t', str(dur), '-i', fonte, '-i', cw, '-i', rot, '-filter_complex',
                    '[0:v]scale=720:1280,fps=30[v];[v][2:v]overlay=0:0[o];[1:a]volume=%.2fdB,afade=t=in:d=0.05,afade=t=out:st=%.2f:d=0.1[a]' % (g, dur - 0.1),
                    '-map', '[o]', '-map', '[a]', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s24le', pv], check=True)
    partes.append(f"file '{pv}'")
open(f'{tmp}/l.txt', 'w').write('\n'.join(partes))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/l.txt', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', saida], check=True)
print('ok:', saida)
