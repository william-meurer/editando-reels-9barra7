#!/usr/bin/env python3
"""Cadeia de voz do reel, depois de declip.py e buracos.py (da skill de aulas).
1. EQ de fase zero casando o espectro da fala com o de voz feminina (LTASS), com teto
2. compressor leve + controle de sibilância
3. ganho até -14 LUFS + limitador com antecipação a -1,8 dBFS (loudnorm cortava pico e estalava)
Uso: cadeia_reel.py entrada.wav saida.wav [--teto 6] [--sem-eq] [--sem-comp]"""
import argparse, json, subprocess
import numpy as np, soundfile as sf

SR = 48000
C = np.array([100,125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500])
ALVO = np.array([-6,-2,2,4,5,6,6,6,4,2,0,-2,-3,-5,-6,-8,-9,-11,-12,-13,-15,-18], float)
LUFS, TP = -14.0, -1.0

def bandas(x):
    N = 4096; f = np.fft.rfftfreq(N, 1 / SR); P = np.zeros(len(f)); h = np.hanning(N); c = 0
    for i in range(0, len(x) - N, N // 2):
        j = x[i:i + N]
        if np.sqrt((j ** 2).mean()) < 0.02: continue      # só quadros de fala
        P += np.abs(np.fft.rfft(j * h)) ** 2; c += 1
    P /= c
    b = np.array([10 * np.log10(P[(f >= k / 2 ** (1 / 6)) & (f < k * 2 ** (1 / 6))].mean() + 1e-20) for k in C])
    return b - b[list(C).index(1000)]

def curva(x, teto):
    d = np.clip(ALVO - bandas(x), -teto, teto)
    d[C <= 160] = np.minimum(d[C <= 160], 3.0)            # grave: só um pouco, senão ronca
    d[C > 9000] = np.minimum(d[C > 9000], teto - 3)       # acima de 9 kHz o ganho vira chiado
    return np.convolve(np.pad(d, 1, mode='edge'), [.25, .5, .25], mode='valid')

def eq(x, d):
    n = len(x); fr = np.fft.rfftfreq(n, 1 / SR)
    g = np.interp(np.log10(np.maximum(fr, 1)), np.log10(C), d, left=0, right=d[-1]); g[fr < 72] = 0
    y = np.fft.irfft(np.fft.rfft(x) * 10 ** (g / 20), n)
    return y * np.sqrt((x ** 2).mean() / (y ** 2).mean())

def mede(p):
    import re
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = r[r.rindex('Summary'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))

def limitador(x, teto_db=-1.8, olha=0.005, solta=0.08):
    """Limitador com antecipação, fora de tempo real: o ganho começa a descer ANTES do pico
    (5 ms) e volta devagar (80 ms). Sem atraso e sem quina, diferente do limitador do loudnorm,
    que cortava os picos das vogais fortes e criava estalo (medido no reel 06)."""
    from scipy import ndimage
    teto = 10 ** (teto_db / 20)
    g = np.minimum(1.0, teto / np.maximum(np.abs(x), 1e-9))
    n = int(olha * SR)
    g = ndimage.minimum_filter1d(g, 2 * n + 1)                 # antecipa e segura
    k = np.hanning(2 * n + 1); g = np.convolve(g, k / k.sum(), 'same')   # desce suave
    r = np.exp(-1 / (solta * SR)); out = g.copy()              # volta devagar
    for i in range(1, len(g)):
        out[i] = min(g[i], out[i - 1] * r + (1 - r))
    return x * out

def volume(ent, sai, pre=''):
    """Filtros ffmpeg (compressor), depois ganho até -14 LUFS e o limitador. Sem loudnorm."""
    tmp = sai + '.c.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', ent] + (['-af', pre] if pre else []) + ['-c:a', 'pcm_f32le', tmp], check=True)
    x, _ = sf.read(tmp)
    for _ in range(3):                                          # ganho e limite convergem em 2-3 voltas
        i, _p = mede(tmp)
        x = limitador(x * 10 ** ((LUFS - i) / 20))
        sf.write(tmp, x, SR, subtype='FLOAT')
    sf.write(sai, x, SR, subtype='PCM_24')
    import os; os.remove(tmp)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('ent'); ap.add_argument('sai')
    ap.add_argument('--teto', type=float, default=6); ap.add_argument('--sem-eq', action='store_true'); ap.add_argument('--sem-comp', action='store_true')
    ap.add_argument('--bruto', help='wav do bruto: refaz o aspereza DEPOIS do EQ, descontando o reforço do EQ na faixa 5-12 kHz')
    a = ap.parse_args()
    x, _ = sf.read(a.ent)
    tmp = a.sai + '.eq.wav'
    if not a.sem_eq:
        d = curva(x, a.teto); print('EQ:', ' '.join(f'{k}:{v:+.1f}' for k, v in zip(C, d)))
        x = eq(x, d)
        if a.bruto:   # o EQ devolveria a distorção que o aspereza.py tirou: tira de novo, na medida do reforço
            from scipy import signal, ndimage
            b_, _ = sf.read(a.bruto)
            reforco = float(np.mean(d[(C >= 5000) & (C <= 12500)]))
            m = ndimage.binary_dilation(np.abs(b_) >= 0.465, iterations=int(0.012 * SR)).astype(float)
            k = np.hanning(int(0.02 * SR)); m = np.convolve(m, k / k.sum(), 'same')
            banda = signal.sosfiltfilt(signal.butter(4, [5000, 12000], 'bandpass', fs=SR, output='sos'), x)
            x = x - m * (1 - 10 ** (-reforco / 20)) * banda
            print(f'aspereza depois do EQ: -{reforco:.1f} dB nos trechos clipados')
    sf.write(tmp, x / max(1, np.abs(x).max() / 0.95), SR, subtype='FLOAT')
    pre = '' if a.sem_comp else 'acompressor=threshold=-22dB:ratio=2.5:attack=8:release=140:knee=6,deesser=i=0.35:m=0.5:f=0.5'
    volume(tmp, a.sai, pre)
    import os; os.remove(tmp)
    i, p = mede(a.sai); print(f'medido: {i} LUFS | pico {p} dBFS')
