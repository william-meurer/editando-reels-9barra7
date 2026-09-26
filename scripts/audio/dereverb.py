# -*- coding: utf-8 -*-
"""Reduz a reverberacao por subtracao espectral da cauda tardia.

A cada instante, parte do que se ouve e o rastro do que foi dito alguns
milissegundos atras, ja atenuado pelo RT60 da sala. Estima-se esse rastro
a partir dos quadros anteriores e subtrai-se do espectro atual, com um
piso para nao abrir buraco no som.

uso: dereverb.py <wav entrada> <wav saida> <rt60> <forca> [piso_dB]
"""
import sys

import numpy as np

ENT, SAI = sys.argv[1], sys.argv[2]
RT60 = float(sys.argv[3])
FORCA = float(sys.argv[4])
PISO_DB = float(sys.argv[5]) if len(sys.argv) > 5 else -12.0

N, HOP = 2048, 512
ATRASO = 4          # quadros: so o que vem depois de ~43 ms e cauda tardia
CAUDA = 45          # quadros considerados


def le_wav(p):
    with open(p, "rb") as f:
        d = f.read()
    i = d.index(b"data")
    sr = int.from_bytes(d[24:28], "little")
    x = np.frombuffer(d[i + 8:], dtype=np.int16).astype(np.float64) / 32768.0
    return x, sr


def grava_wav(p, x, sr):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2").tobytes()
    cab = (b"RIFF" + (36 + len(pcm)).to_bytes(4, "little") + b"WAVEfmt " +
           (16).to_bytes(4, "little") + (1).to_bytes(2, "little") +
           (1).to_bytes(2, "little") + sr.to_bytes(4, "little") +
           (sr * 2).to_bytes(4, "little") + (2).to_bytes(2, "little") +
           (16).to_bytes(2, "little") + b"data" +
           len(pcm).to_bytes(4, "little"))
    open(p, "wb").write(cab + pcm)


x, sr = le_wav(ENT)
jan = np.hanning(N + 1)[:N]
nq = 1 + (len(x) - N) // HOP
X = np.empty((nq, N // 2 + 1), dtype=complex)
for i in range(nq):
    X[i] = np.fft.rfft(x[i * HOP:i * HOP + N] * jan)

P = np.abs(X) ** 2
# quanto a energia cai por quadro, segundo o RT60 medido
queda_db = 60.0 * (HOP / float(sr)) / RT60
g = 10 ** (-queda_db / 10.0)

R = np.zeros_like(P)
for k in range(ATRASO, CAUDA):
    R[k:] += (g ** k) * P[:-k]

piso = 10 ** (PISO_DB / 10.0)
ganho = np.sqrt(np.maximum(P - FORCA * R, piso * P) / np.maximum(P, 1e-20))

# suaviza o ganho ao longo da frequencia: evita o chiado musical sem
# abafar o ataque das palavras
k = np.ones(5) / 5.0
ganho = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, ganho)

# limite suave de subida, so para nao criar degrau audivel entre quadros
for i in range(1, nq):
    ganho[i] = np.minimum(ganho[i], ganho[i - 1] * 3.0 + 0.08)

Y = X * ganho
y = np.zeros(len(x))
peso = np.zeros(len(x))
for i in range(nq):
    y[i * HOP:i * HOP + N] += np.fft.irfft(Y[i], N) * jan
    peso[i * HOP:i * HOP + N] += jan ** 2
y /= np.maximum(peso, 1e-6)

grava_wav(SAI, y, sr)
print("  %s -> %s   RT60=%.2f forca=%.1f piso=%.0fdB" % (ENT, SAI, RT60, FORCA, PISO_DB))
