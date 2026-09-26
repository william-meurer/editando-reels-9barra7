#!/usr/bin/env python3
"""Cama sonora do reel (padrão aprovado no reel 06): uma só pra todos os reels, "Technology" (prettyjohn1, Pixabay).
- entra no 0:00 abafada (passa-baixa em 1,5 kHz) e abre inteira na virada (edicao.json -> "virada")
- loop de 12 s (blocos de 4 s da própria faixa), emenda de 30 ms
- -3 dB em 1-3,5 kHz, onde a voz se apoia
- abaixa sozinha quando a Marilia fala (~16 a 18 dB abaixo da voz), sobe nas pausas e no fechamento, some em 1,5 s no fim
Lê 4-edicao/audio/montagem-limpa.wav (ou montagem.wav) e 4-edicao/montagem.json. Grava 4-edicao/audio/cama.wav.
Uso: cama.py "<pasta do reel>" """
import json, os, sys, subprocess, wave
import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import uniform_filter1d

AQUI = os.path.dirname(os.path.abspath(__file__))
CAMA = os.path.join(AQUI, '..', '..', '..', '..', '..', 'Produção', 'kit', 'trilha', 'cama - technology (prettyjohn1, Pixabay).mp3')
SR, LOOP = 48000, 12.0


def ler(f, ch):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, ch).astype(np.float64)


def cama(voz, virada_s, fechamento_s):
    s = lambda x: int(round(x * SR)); db = lambda x: 10 ** (x / 20)
    N = len(voz); t = np.arange(N) / SR
    T = ler(CAMA, 2); mono = T.mean(1)
    i0 = int(np.argmax(np.abs(mono) > np.abs(mono).max() * 0.05)); seg = T[i0:i0 + s(LOOP)]
    xf = s(0.03); B = seg.copy()
    while len(B) < N + xf:
        r = np.linspace(0, 1, xf)[:, None]; B = np.concatenate([B[:-xf], B[-xf:] * (1 - r) + seg[:xf] * r, seg[xf:]])
    c = B[:N]
    lp = sosfiltfilt(butter(2, 1500, 'low', fs=SR, output='sos'), c, axis=0)
    m = np.clip((virada_s - t) / 0.5, 0, 1)[:, None]; c = lp * m * db(-2) + c * (1 - m)
    banda = sosfiltfilt(butter(2, [1000, 3500], 'bandpass', fs=SR, output='sos'), c, axis=0); c = c - (1 - db(-3)) * banda
    c = c / np.sqrt((c ** 2).mean()) * 0.1
    env = np.sqrt(np.maximum(uniform_filter1d(voz ** 2, s(0.05)), 0))
    ativo = uniform_filter1d((20 * np.log10(env + 1e-9) > -40).astype(float), s(0.35)) > 0.02
    alvo = np.where(ativo, -12.0, -6.0); alvo[t >= fechamento_s] = -4
    g = np.empty(N); cur = alvo[0]; a = np.exp(-1 / (0.15 * SR)); rl = np.exp(-1 / (0.5 * SR))
    for k in range(0, N, 48):
        tg = alvo[k]; cc = a if tg < cur else rl; cur = tg + (cur - tg) * cc ** 48; g[k:k + 48] = cur
    c = c * db(g)[:, None]
    f = s(1.5); c[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5; fi = s(0.1); c[:fi] *= np.linspace(0, 1, fi)[:, None]
    return c


if __name__ == '__main__':
    ed = os.path.join(sys.argv[1], '4-edicao')
    m = json.load(open(os.path.join(ed, 'montagem.json')))
    fonte = os.path.join(ed, 'audio', 'montagem-limpa.wav')
    if not os.path.exists(fonte): fonte = os.path.join(ed, 'audio', 'montagem.wav')
    voz = ler(fonte, 1)[:, 0]
    virada = (m['virada'] if m.get('virada') is not None else 0) / m['fps']
    c = cama(voz, virada, (m['quadros'] - m['fechamento']) / m['fps'])
    w = wave.open(os.path.join(ed, 'audio', 'cama.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(c, -1, 1) * 32767).astype('<i2').tobytes()); w.close()
    print(f'cama: {len(c) / SR:.2f}s, abre na virada em {virada:.2f}s')
