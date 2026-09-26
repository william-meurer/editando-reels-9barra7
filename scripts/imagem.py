#!/usr/bin/env python3
"""Gera a imagem de edição do reel a partir do take bruto: recorte do plano P1 no 4K, look C, pronta pro Palmier.
- recorte 1080x1920 do 4K, sem reescala (nitidez total): centrado no rosto, 22% da altura de folga acima da cabeça (rosto.json)
- look C (aprovado no reel 06): contraste leve, calor leve, nitidez leve
- um quadro-chave por quadro (corta sem engasgar no Palmier), bt709
Os outros planos (P2, P3, ÊNFASE, empurra) são zoom em cima desse recorte, feitos no Palmier.
Conferido no reel 06: mesma origem de recorte da versão feita à mão (x 550, y 690) e diferença média < 2 níveis de cor.
Uso: imagem.py "<pasta do reel>"   (grava 4-edicao/imagem/camera-edicao.mp4)"""
import json, os, sys, subprocess
import numpy as np

LOOK = 'eq=contrast=1.08:saturation=1.05:gamma=0.97,colorbalance=rm=0.03:bm=-0.03,unsharp=5:5:0.3'
W, H, SRC_W, SRC_H, FOLGA = 1080, 1920, 2160, 3840, 0.22


def recorte(rosto):
    cx = float(np.median([r['cx'] for r in rosto])); topo = float(np.median([r['topo'] for r in rosto]))
    x0 = int(round(min(max(cx - W / 2, 0), SRC_W - W))); y0 = int(round(min(max(topo - FOLGA * H, 0), SRC_H - H)))
    return x0, y0


if __name__ == '__main__':
    pasta = sys.argv[1]; ed = os.path.join(pasta, '4-edicao')
    tk = os.path.join(pasta, '3-takes')
    video = os.path.join(tk, [f for f in sorted(os.listdir(tk)) if f.startswith('camera__') and f.lower().endswith(('.mov', '.mp4'))][0])
    x0, y0 = recorte(json.load(open(os.path.join(ed, 'rosto.json'))))
    os.makedirs(os.path.join(ed, 'imagem'), exist_ok=True)
    saida = os.path.join(ed, 'imagem', 'camera-edicao.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-an', '-vf', f'crop={W}:{H}:{x0}:{y0},{LOOK}',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '12', '-g', '1', '-pix_fmt', 'yuv420p',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', saida], check=True)
    print(f'imagem: {saida} (recorte x {x0}, y {y0})')
