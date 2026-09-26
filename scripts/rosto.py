#!/usr/bin/env python3
"""Mede o rosto da Marilia no take de câmera (4K vertical) e grava 4-edicao/rosto.json.
Um quadro a cada 1,5 s, detector de rosto frontal do OpenCV. O detector acha também mãos e cantos de janela:
fica com o grupo de detecções que mais se repete no take (o rosto quase não sai do lugar) e, em cada quadro, com a mais perto dele.
Cada medida: t, cx, cy, w (largura do rosto) e topo (topo da cabeça = cy - 0,95 w, calibrado no reel 06).
O montar.py usa a mediana, então medidas soltas erradas não pesam.
Uso: rosto.py "<pasta do reel>" """
import json, os, sys, subprocess
import numpy as np, cv2

PASSO = 1.5


def take_de_camera(pasta):
    tk = os.path.join(pasta, '3-takes')
    return os.path.join(tk, [f for f in sorted(os.listdir(tk)) if f.startswith('camera__') and f.lower().endswith(('.mov', '.mp4'))][0])


def medir(video):
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video], capture_output=True, text=True).stdout)
    # o iPhone grava com rotação nos metadados: mede no quadro já girado pelo ffmpeg (2160x3840)
    w, h = 2160, 3840
    esc = 0.25  # detecta em 1/4 da resolução, mede de volta no 4K
    cas = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt2.xml'))
    cand = []
    for t in np.arange(PASSO, dur - 0.5, PASSO):
        r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-vf', f'scale={int(w * esc)}:{int(h * esc)}',
                            '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
        if len(r) < int(w * esc) * int(h * esc): continue
        g = np.frombuffer(r, np.uint8).reshape(int(h * esc), int(w * esc))
        for x, y, fw, fh in cas.detectMultiScale(g, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)):
            x, y, fw = x / esc, y / esc, fw / esc
            cand.append((float(t), x + fw / 2, y + fw / 2, fw))
    if not cand: return []
    # o grupo mais frequente (grade de 150 px) é o rosto
    c = np.array(cand)
    chave = [(int(a // 150), int(b // 150)) for a, b in c[:, 1:3]]
    alvo = max(set(chave), key=chave.count)
    centro = c[[k == alvo for k in chave]][:, 1:3].mean(0)
    out = []
    for t in sorted(set(c[:, 0])):
        do_t = c[c[:, 0] == t]
        d = np.hypot(do_t[:, 1] - centro[0], do_t[:, 2] - centro[1])
        if d.min() > 300: continue
        _, cx, cy, fw = do_t[d.argmin()]
        out.append(dict(t=round(t, 2), cx=round(cx, 1), cy=round(cy, 1), w=round(fw, 1), topo=round(cy - 0.95 * fw, 1)))
    return out


if __name__ == '__main__':
    pasta = sys.argv[1]
    m = medir(take_de_camera(pasta))
    json.dump(m, open(os.path.join(pasta, '4-edicao', 'rosto.json'), 'w'), indent=1)
    print(f'rosto: {len(m)} medidas | mediana cx {np.median([r["cx"] for r in m]):.0f} topo {np.median([r["topo"] for r in m]):.0f}')
