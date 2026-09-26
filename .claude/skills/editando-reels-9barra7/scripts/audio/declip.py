"""Declipagem do bruto: o microfone ceifa os picos da voz em ±0,50 (-6 dBFS).

Amostra "no teto" = |x| >= LIM (0,465: o platô tem ondulação do AAC em
0,48-0,51), mais 1 amostra de borda. Um pico ceifado (sequência contígua)
por vez:
- modelo AR (ordem 32, covariância) ajustado em ±12 ms, só com janelas sem teto;
- LSAR numa janela de ±3 ms, com TODAS as amostras de teto dessa janela como
  incógnitas e restrição de consistência (bvls): a reconstrução nunca fica
  abaixo do valor ceifado observado, com o mesmo sinal;
- grava só as amostras do pico em questão.
Contagem de amostras idêntica; saída em float (pode passar de 0,5).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage
from scipy.linalg import toeplitz
from scipy.optimize import lsq_linear
from scipy.interpolate import CubicSpline

USAR_SPLINE = True
CORTE_CORRECAO = 5000   # Hz


def ar_cov(seg, ruim, ordem):
    N = len(seg)
    # linhas n onde seg[n-ordem..n] não tem teto
    c = np.convolve(ruim.astype(np.int32), np.ones(ordem + 1, np.int32), "full")[ordem:N]
    linhas = np.flatnonzero(c == 0)
    linhas = linhas[linhas >= ordem]
    if len(linhas) < 3 * ordem:
        return None
    idx = linhas[:, None] - np.arange(1, ordem + 1)[None, :]
    X = seg[idx]; y = seg[linhas]
    coef = np.linalg.solve(X.T @ X + 1e-9 * np.eye(ordem), X.T @ y)
    return np.r_[1.0, -coef]


def declip(x, sr, lim, ordem=32):
    teto = ndimage.binary_dilation(np.abs(x) >= lim, iterations=1)
    lab, n = ndimage.label(teto)
    objs = ndimage.find_objects(lab)
    y = x.copy()
    ctx_ar, ctx = int(0.012 * sr), int(0.003 * sr)
    feitos = 0
    for sl in objs:
        r0, r1 = sl[0].start, sl[0].stop
        if r1 - r0 > int(0.004 * sr):             # platô > 4 ms: não é pico de voz
            continue
        # 1) spline cúbica pelas amostras boas das duas bordas (segue a
        #    inclinação da onda); vale para o caso comum de pico curto
        kb = np.arange(max(0, r0 - 40), r0); ka = np.arange(r1, min(len(x), r1 + 40))
        kb = kb[~teto[kb]][-14:]; ka = ka[~teto[ka]][:14]
        if USAR_SPLINE and len(kb) >= 4 and len(ka) >= 4:
            pts = np.r_[kb, ka]
            cs = CubicSpline(pts, x[pts])
            est = cs(np.arange(r0, r1))
            v = x[r0:r1]
            est = np.where(v > 0, np.maximum(est, v), np.minimum(est, v))
            # teto suave: se passar de 1,6x o nível ceifado, encolhe o arco
            # inteiro (mantém o formato redondo, sem criar platô novo)
            exc = np.abs(est - v).max()
            cap = 0.6 * np.abs(v).max()
            if exc > cap:
                est = v + (est - v) * (cap / exc)
            y[r0:r1] = est
            feitos += 1
            continue
        a = None
        for c_ar, o_ar in ((ctx_ar, ordem), (int(0.040 * sr), 24), (int(0.090 * sr), 16)):
            a0, a1 = max(0, r0 - c_ar), min(len(x), r1 + c_ar)
            a = ar_cov(x[a0:a1], teto[a0:a1], o_ar)
            if a is not None:
                break
        if a is None:
            continue
        ordem_l = len(a) - 1
        w0, w1 = max(0, r0 - ctx), min(len(x), r1 + ctx)
        seg = y[w0:w1].copy(); f = teto[w0:w1]
        N = len(seg)
        if N <= ordem_l + 1:
            continue
        # e = A s ; A[i, i..i+ordem] = a invertido
        A = toeplitz(np.r_[a[-1], np.zeros(N - ordem_l - 1)], np.r_[a[::-1], np.zeros(N - ordem_l - 1)])
        mi = np.flatnonzero(f); kn = np.flatnonzero(~f)
        v = x[w0:w1][mi]
        lo = np.where(v > 0, v, 1.7 * v); hi = np.where(v > 0, 1.7 * v, v)   # pico reconstruído até 1,7x o ceifado
        res = lsq_linear(A[:, mi], -A[:, kn] @ seg[kn], bounds=(lo, hi), method="bvls")
        seg[mi] = res.x
        alvo = (np.arange(w0, w1) >= r0) & (np.arange(w0, w1) < r1)
        y[w0:w1][alvo] = seg[alvo]
        feitos += 1
    # A emenda amostra a amostra cria quina (estalo a cada pico: medido no reel 06, 111 -> 425/min).
    # Só a parte grave da correção entra: o formato do pico volta sem acrescentar agudo.
    from scipy import signal as _sg
    y = x + _sg.sosfiltfilt(_sg.butter(4, CORTE_CORRECAO, "lowpass", fs=sr, output="sos"), y - x)
    return y, int(teto.sum()), n, feitos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--lim", type=float, default=0.465)
    ap.add_argument("--relatorio", type=Path)
    a = ap.parse_args()
    x, sr = sf.read(a.entrada, dtype="float64")
    y, n, picos, feitos = declip(x, sr, a.lim)
    sf.write(a.saida, y, sr, subtype="FLOAT")
    rep = dict(amostras_no_teto=n, pct=round(100 * n / len(x), 3), picos=picos, reconstruidos=feitos,
               pico_saida=round(float(np.abs(y).max()), 3))
    if a.relatorio:
        a.relatorio.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
