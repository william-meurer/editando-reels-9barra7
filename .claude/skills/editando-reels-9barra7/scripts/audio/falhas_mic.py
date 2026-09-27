#!/usr/bin/env python3
"""Última passada na voz: repara as falhas do microfone sem fio que sobraram.
1) buracos (o sinal congela ~1-2 ms e pula de volta): LSAR em banda cheia só nas amostras da falha
2) estalo curto que sobrou (limiar 5 na faixa 9-20 kHz): LSAR só acima de 1,5 kHz
Roda no take tratado inteiro (D-eq9.wav -> D-limpo.wav), antes do montar.py: é dele que saem a voz montada e os
pedaços de voz do Palmier, então um corte puxado à mão lá continua limpo. Na voz já montada (--montagem, o jeito
antigo) não mexe a menos de 20 ms das emendas entre trechos (lá o fade é proposital).
No reel 06 (26/09): 138 buracos e 78 estalos reparados; estalos detectáveis de 45 para 7.
Uso: falhas_mic.py "<pasta do reel>"   (lê 4-edicao/audio/D-eq9.wav, grava D-limpo.wav)
     falhas_mic.py "<pasta do reel>" --montagem   (lê montagem.wav, grava montagem-limpa.wav)"""
import json, sys, importlib.util as u
from pathlib import Path
import numpy as np, soundfile as sf
from scipy import signal

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import estalos_hf, declick  # noqa: E402
_s = u.spec_from_file_location('buracos', AQUI / 'buracos.py'); buracos = u.module_from_spec(_s); _s.loader.exec_module(buracos)


FINO = 3.5


def limpar(x, sr, bordas):
    perto = lambda a, z: any(abs(a / sr - c) < 0.02 or abs(z / sr - c) < 0.02 for c in bordas)
    y = x.copy()
    evb = [(e[0], e[1]) for e in buracos.detectar(y, sr) if not perto(e[0], e[1])]
    for a, z in evb:
        y[a:z] = declick.lsar(y, a, z, sr)
    ev = [(a, z) for a, z in estalos_hf.detectar(y, sr, 5.0) if not perto(a, z)]
    # glitch fino do microfone sem fio, espalhado pela fala (reel 01, 27/09: o William ouviu "por todo o áudio" com 5 estalos
    # detectáveis no limiar 6): segunda leva no limiar 3,5, só dentro da fala (80-1000 Hz acima de -35 dB), onde a voz dela
    # não tem nada acima de 9 kHz. Fora da fala, 3,5 pegaria respiração e sibilante
    corpo = signal.sosfiltfilt(signal.butter(4, [80, 1000], 'bandpass', fs=sr, output='sos'), y)
    fala = lambda a, z: 20 * np.log10(np.sqrt((corpo[max(0, a - 480):z + 480] ** 2).mean()) + 1e-12) > -35
    ja = {a for a, _ in ev}
    ev += [(a, z) for a, z in estalos_hf.detectar(y, sr, FINO) if a not in ja and fala(a, z) and not perto(a, z)]
    ev.sort(); junto = []                                     # sobrepostos ou colados viram um só reparo
    for a, z in ev:
        if junto and a <= junto[-1][1] + int(0.001 * sr): junto[-1][1] = max(junto[-1][1], z)
        else: junto.append([a, z])
    ev = [tuple(e) for e in junto]
    grave = signal.sosfiltfilt(signal.butter(4, 1500, 'lowpass', fs=sr, output='sos'), y)
    agudo = y - grave; novo = agudo.copy()
    for a, z in ev:
        novo[a:z] = declick.lsar(agudo, a, z, sr)
    return grave + novo, len(evb), len(ev)


if __name__ == '__main__':
    ed = Path(sys.argv[1]) / '4-edicao'
    if '--montagem' in sys.argv:
        ent, sai = ed / 'audio' / 'montagem.wav', ed / 'audio' / 'montagem-limpa.wav'
        m = json.load(open(ed / 'montagem.json'))
        bordas = [t['out_f0'] / m['fps'] for t in m['trechos']] + [sum(t['n'] for t in m['trechos']) / m['fps']]
    else:
        ent, sai, bordas = ed / 'audio' / 'D-eq9.wav', ed / 'audio' / 'D-limpo.wav', []
    x, sr = sf.read(ent)
    y, nb, ne = limpar(x, sr, bordas)
    sf.write(sai, y, sr, subtype=sf.info(ent).subtype)
    print(f'falhas_mic: {nb} buracos e {ne} estalos reparados; estalos que sobram: '
          f'{len(estalos_hf.detectar(y, sr, 6))} (antes {len(estalos_hf.detectar(x, sr, 6))})')
