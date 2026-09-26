# -*- coding: utf-8 -*-
"""Padrao de audio 9barra7: mede o bruto e diz o que precisa de tratamento.

Uso: python 02_analisa_audio.py bruto.wav [ini_s] [dur_s]
     (wav mono; qualquer taxa; escolher um trecho de fala continua)

Mede: RT60 (eco), espectro 1/3 de oitava referenciado em 1 kHz,
vale anti-anasalado em 500-2000 Hz, ressonancia de sala.

Alvos: RT60 <= 0.5s (senao dereverb.py com forca 0.5, piso -9 --
"eco leve e melhor que abafamento"); vale 500-2000 > -8 dB (senao so
bells suaves <= 2.5 kHz, nunca cortar agudos); ressonancia >= +10 dB
em banda grave-media -> bell de -3 a -5 dB. Loudness final da aula:
-20 LUFS, so na exportacao. Comparar sempre com as outras aulas.
"""
import sys
import wave

import numpy as np

ARQ = sys.argv[1]
INI = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0

w = wave.open(ARQ, "rb")
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
x = x.astype(np.float64) / 32768.0
w.close()
seg = x[int(INI * sr):int((INI + DUR) * sr)]


def rt60(y, sr):
    n = int(0.02 * sr)
    env = np.sqrt(np.convolve(y ** 2, np.ones(n) / n, mode="same")) + 1e-12
    db = 20 * np.log10(env)
    passo, jan = int(0.01 * sr), int(0.30 * sr)
    taxas = []
    for i in range(jan, len(y) - jan, passo):
        if db[i] > db[max(0, i - passo)] and db[i] > -25:
            s = db[i:i + jan:passo]
            t = np.arange(len(s)) * 0.01
            if len(s) > 8 and s[-1] < s[0] - 6:
                A = np.vstack([t, np.ones(len(t))]).T
                m, b = np.linalg.lstsq(A, s, rcond=None)[0]
                r2 = 1 - np.sum((s - (m * t + b)) ** 2) / max(
                    1e-9, np.sum((s - s.mean()) ** 2))
                if m < -3 and r2 > 0.8:
                    taxas.append(-60.0 / m)
    return float(np.median(taxas)) if taxas else float("nan")


rt = rt60(seg, sr)
print("RT60: %.2fs  [alvo <= 0.50s%s]"
      % (rt, "; PRECISA de dereverb leve" if rt > 0.5 else " -- ok"))

N = 4096
freqs = np.fft.rfftfreq(N, 1.0 / sr)
P = np.zeros(len(freqs))
hann = np.hanning(N)
cont = 0
for i in range(0, len(seg) - N, N // 2):
    j = seg[i:i + N]
    if np.sqrt((j ** 2).mean()) < 0.01:
        continue
    P += np.abs(np.fft.rfft(j * hann)) ** 2
    cont += 1
P /= max(cont, 1)
CENTROS = [250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500,
           3150, 4000, 5000, 6300]
b = []
for c in CENTROS:
    lo, hi = c / 2 ** (1 / 6.0), c * 2 ** (1 / 6.0)
    m = (freqs >= lo) & (freqs < hi)
    b.append(10 * np.log10(P[m].mean() + 1e-20))
b = np.array(b)
b -= b[CENTROS.index(1000)]          # referencia SEMPRE em 1 kHz
for c, v in zip(CENTROS, b):
    print("  %5d Hz  %+6.1f dB" % (c, v))
vale = min(b[CENTROS.index(500):CENTROS.index(2000) + 1])
pico = max(b[CENTROS.index(250):CENTROS.index(800) + 1])
print("vale 500-2000 Hz: %+.1f dB  [anasalado se < -8]" % vale)
print("pico 250-800 Hz: %+.1f dB  [ressonancia de sala se >= +10]" % pico)
