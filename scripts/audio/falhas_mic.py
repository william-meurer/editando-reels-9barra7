#!/usr/bin/env python3
"""Última passada na voz já montada (montagem.wav): repara as falhas do microfone sem fio que sobraram.
1) buracos (o sinal congela ~1-2 ms e pula de volta): LSAR em banda cheia só nas amostras da falha
2) estalo curto que sobrou (limiar 5 na faixa 9-20 kHz): LSAR só acima de 1,5 kHz
Não mexe a menos de 20 ms das emendas entre trechos (lá o fade é proposital).
No reel 06 (26/09): 138 buracos e 78 estalos reparados; estalos detectáveis de 45 para 7.
Uso: falhas_mic.py "<pasta do reel>"   (lê 4-edicao/audio/montagem.wav, grava montagem-limpa.wav)"""
import json, sys, importlib.util as u
from pathlib import Path
import numpy as np, soundfile as sf
from scipy import signal

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import estalos_hf, declick  # noqa: E402
_s = u.spec_from_file_location('buracos', AQUI / 'buracos.py'); buracos = u.module_from_spec(_s); _s.loader.exec_module(buracos)


def limpar(x, sr, bordas):
    perto = lambda a, z: any(abs(a / sr - c) < 0.02 or abs(z / sr - c) < 0.02 for c in bordas)
    y = x.copy()
    evb = [(e[0], e[1]) for e in buracos.detectar(y, sr) if not perto(e[0], e[1])]
    for a, z in evb:
        y[a:z] = declick.lsar(y, a, z, sr)
    ev = [(a, z) for a, z in estalos_hf.detectar(y, sr, 5.0) if not perto(a, z)]
    grave = signal.sosfiltfilt(signal.butter(4, 1500, 'lowpass', fs=sr, output='sos'), y)
    agudo = y - grave; novo = agudo.copy()
    for a, z in ev:
        novo[a:z] = declick.lsar(agudo, a, z, sr)
    return grave + novo, len(evb), len(ev)


if __name__ == '__main__':
    ed = Path(sys.argv[1]) / '4-edicao'
    ent = ed / 'audio' / 'montagem.wav'
    x, sr = sf.read(ent)
    m = json.load(open(ed / 'montagem.json'))
    bordas = [t['out_f0'] / m['fps'] for t in m['trechos']] + [sum(t['n'] for t in m['trechos']) / m['fps']]
    y, nb, ne = limpar(x, sr, bordas)
    sf.write(ed / 'audio' / 'montagem-limpa.wav', y, sr, subtype=sf.info(ent).subtype)
    print(f'falhas_mic: {nb} buracos e {ne} estalos reparados; estalos que sobram: '
          f'{len(estalos_hf.detectar(y, sr, 6))} (antes {len(estalos_hf.detectar(x, sr, 6))})')
