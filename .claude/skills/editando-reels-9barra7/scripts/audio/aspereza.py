#!/usr/bin/env python3
"""Tira a aspereza que a clipagem deixa nas vogais fortes.
Onde o bruto encostou no teto (|x| >= 0,465), a faixa de 5 a 12 kHz é quase toda distorção:
a voz dela é escura e não tem energia real ali. Baixa essa faixa só nesses trechos, com
máscara suave (10 ms de entrada e saída), sem criar degrau.
Uso: aspereza.py bruto.wav entrada.wav saida.wav [--db -10]"""
import argparse
import numpy as np, soundfile as sf
from scipy import signal, ndimage

ap = argparse.ArgumentParser(); ap.add_argument('bruto'); ap.add_argument('ent'); ap.add_argument('sai'); ap.add_argument('--db', type=float, default=-10)
a = ap.parse_args()
b, sr = sf.read(a.bruto); x, _ = sf.read(a.ent)
m = ndimage.binary_dilation(np.abs(b) >= 0.465, iterations=int(0.012 * sr)).astype(float)
k = np.hanning(int(0.02 * sr)); m = np.convolve(m, k / k.sum(), 'same')
banda = signal.sosfiltfilt(signal.butter(4, [5000, 12000], 'bandpass', fs=sr, output='sos'), x)
g = 10 ** (a.db / 20)
sf.write(a.sai, x - m * (1 - g) * banda, sr, subtype='FLOAT')
print(f'aspereza: {100 * (m > 0.5).mean():.1f}% do áudio tratado, faixa 5-12 kHz a {a.db} dB')
