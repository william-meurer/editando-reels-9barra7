"""Acha e reconstrói os BURACOS digitais do microfone no bruto.

O defeito: por ~0,5-2 ms o sinal congela num valor quase fixo e depois pula
de volta (degrau nas duas pontas). Soa como um tique sutil dentro da fala.
Detecção: janela de 1 ms com variação < FRAC do pico-a-pico local (±10 ms),
longe do pico (não é clipagem) e com salto nas bordas.
Reparo: LSAR em banda cheia só nas amostras congeladas (+2 de cada lado).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage

import importlib.util as _u

_s = _u.spec_from_file_location("dc", Path(__file__).with_name("declick.py"))
dc = _u.module_from_spec(_s)
_s.loader.exec_module(dc)


def detectar(x: np.ndarray, sr: int, frac: float = 0.07, piso_db: float = -66.0):
    w = max(8, int(0.0006 * sr))                   # 0,6 ms de variação mínima
    mx = ndimage.maximum_filter1d(x, w, origin=0)
    mn = ndimage.minimum_filter1d(x, w, origin=0)
    rng = mx - mn
    L = int(0.010 * sr)
    pp = ndimage.maximum_filter1d(x, 2 * L) - ndimage.minimum_filter1d(x, 2 * L)
    pico = ndimage.maximum_filter1d(np.abs(x), 2 * L)
    plano = (rng < frac * pp) & (pp > 10 ** (piso_db / 20))
    lab, _ = ndimage.label(plano)
    ev = []
    for sl in ndimage.find_objects(lab):
        a, b = sl[0].start - w // 2, sl[0].stop + w // 2
        a, b = max(1, a), min(len(x) - 2, b)
        n = b - a
        if n < int(0.0007 * sr) or n > int(0.0016 * sr):
            continue
        nivel = np.median(x[a:b])
        if abs(nivel) > 0.85 * pico[a]:            # topo clipado, não buraco
            continue
        # degrau em pelo menos uma borda (congelou/voltou de repente)
        d0 = abs(x[a] - x[a - 1]) + abs(x[a + 1] - x[a])
        d1 = abs(x[b] - x[b - 1]) + abs(x[b + 1] - x[b])
        dd = np.abs(np.diff(x[max(0, a - L):b + L]))
        tip = np.percentile(dd, 90) + 1e-9
        if max(d0, d1) < 2.5 * tip:
            continue
        ev.append((a - 2, b + 2, float(max(d0, d1) / tip)))
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--relatorio", type=Path)
    ap.add_argument("--fim", type=float)
    a = ap.parse_args()
    info = sf.info(a.entrada)
    x, sr = sf.read(a.entrada, dtype="float64", always_2d=True, frames=-1 if a.fim is None else int(a.fim * info.samplerate))
    y = x.copy()
    ev = detectar(x[:, 0], sr)
    for ch in range(x.shape[1]):
        for i0, i1, _ in ev:
            y[i0:i1, ch] = dc.lsar(x[:, ch], i0, i1, sr, ordem=40)
    sf.write(a.saida, np.clip(y, -1, 1) if y.shape[1] > 1 else np.clip(y[:, 0], -1, 1), sr, subtype=info.subtype)
    rep = dict(eventos=len(ev), por_minuto=len(ev) / (len(x) / sr / 60),
               lista=[dict(t=round(i0 / sr, 4), ms=round((i1 - i0) / sr * 1000, 2), salto=round(s, 1)) for i0, i1, s in ev])
    if a.relatorio:
        a.relatorio.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("buracos %d | %.1f/min" % (rep["eventos"], rep["por_minuto"]))


if __name__ == "__main__":
    main()
