#!/usr/bin/env python3
"""Estalos que o declick.py não pega: tique de 0,5 a 3 ms dentro de vogal forte.
A voz da Marilia quase não tem energia acima de 9 kHz (microfone escuro), então qualquer
descontinuidade (buraco do mic sem fio, emenda) espirra ali. Detecta pela faixa 9-20 kHz
contra a mediana de 40 ms e repara por LSAR só acima de 1,5 kHz (o corpo da voz passa intacto).
Uso: estalos_hf.py entrada.wav saida.wav [--limiar 8]"""
import argparse, json
import numpy as np, soundfile as sf
from scipy import signal, ndimage
import declick

def detectar(x, sr, limiar=8.0):
    h = signal.sosfiltfilt(signal.butter(6, [9000, 20000], 'bandpass', fs=sr, output='sos'), x)
    blk = sr // 2000; n = len(h) // blk
    env = np.sqrt((h[:n * blk].reshape(n, blk) ** 2).mean(1) + 1e-16)
    med = ndimage.median_filter(env, size=81, mode='nearest')
    hit = (env / np.maximum(med, 1e-8) >= limiar) & (env > 1e-4)
    lab, _ = ndimage.label(hit); ev = []
    for s in ndimage.find_objects(lab):
        a, z = s[0].start, s[0].stop
        if z - a <= 6:
            ev.append((max(0, a * blk - int(0.0008 * sr)), min(len(x), z * blk + int(0.0008 * sr))))
    return ev

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('ent'); ap.add_argument('sai'); ap.add_argument('--limiar', type=float, default=8.0)
    a = ap.parse_args()
    x, sr = sf.read(a.ent); ev = detectar(x, sr, a.limiar)
    # dentro de vogal clipada o agudo é distorção periódica, não estalo: fica para o aspereza.py
    clip = ndimage.binary_dilation(np.abs(x) >= 0.465, iterations=int(0.001 * sr))
    ev = [(i0, i1) for i0, i1 in ev if not clip[i0:i1].any()]
    sos = signal.butter(4, 1500, 'lowpass', fs=sr, output='sos')
    grave = signal.sosfiltfilt(sos, x); agudo = x - grave; novo = agudo.copy()
    for i0, i1 in ev: novo[i0:i1] = declick.lsar(agudo, i0, i1, sr)
    sf.write(a.sai, grave + novo, sr, subtype='FLOAT')
    print(f'estalos_hf: {len(ev)} ({len(ev) / (len(x) / sr / 60):.0f}/min)')
