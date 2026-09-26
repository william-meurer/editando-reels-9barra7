"""Remove os estalos do microfone (tique curto de banda larga que já vem no
bruto) sem tocar no resto da voz.

Detecção: envelope acima de 5 kHz em blocos de 0,5 ms; estalo = subida
estreita (<= ~4 ms) muito acima da mediana local de 40 ms. Sibilante dura
30 ms ou mais e não passa no teste de estreiteza.
Reparo: interpolação AR por mínimos quadrados (LSAR) só nas amostras do
estalo, com 25 ms de contexto de cada lado. Contagem de amostras idêntica.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import linalg, ndimage, signal


def detectar(x: np.ndarray, sr: int, limiar: float = 8.0, piso_db: float = -80.0):
    sos = signal.butter(6, 5000, "highpass", fs=sr, output="sos")
    h = signal.sosfiltfilt(sos, x)
    blk = sr // 2000                                     # 0,5 ms
    n = len(h) // blk
    env = np.sqrt(np.mean(h[: n * blk].reshape(n, blk) ** 2, axis=1) + 1e-14)
    med = ndimage.median_filter(env, size=81, mode="nearest")      # 40 ms
    razao = env / np.maximum(med, 1e-7)
    piso = 10 ** (piso_db / 20)
    hit = (razao >= limiar) & (env >= piso)
    lab, k = ndimage.label(hit)
    eventos = []
    for sl in ndimage.find_objects(lab):
        a, z = sl[0].start, sl[0].stop
        if z - a > 8:                                    # > 4 ms: não é estalo
            continue
        # estreiteza: energia fora da janela (±6 ms) tem que ser bem menor
        ctx_a, ctx_z = max(0, a - 12), min(n, z + 12)
        viz = np.r_[env[ctx_a:a], env[z:ctx_z]]
        if len(viz) and np.max(viz) > 0.5 * np.max(env[a:z]):
            continue
        i0 = a * blk - int(0.0015 * sr)
        i1 = z * blk + int(0.0015 * sr)
        # serrilhado: estalo é degrau/agulha; voz é periódica e lisa.
        # Resíduo contra mediana de 11 amostras dentro do evento tem que
        # ser bem maior que no contexto de ±25 ms.
        c0, c1 = max(0, i0 - int(0.025 * sr)), min(len(x), i1 + int(0.025 * sr))
        res = np.abs(x[c0:c1] - signal.medfilt(x[c0:c1], 11))
        dentro = res[i0 - c0: i1 - c0]
        fora = np.r_[res[: i0 - c0], res[i1 - c0:]]
        if len(fora) == 0 or np.max(dentro) < 3.0 * np.percentile(fora, 95):
            continue
        eventos.append((max(0, i0), min(len(x), i1), float(np.max(razao[a:z]))))
    # junta vizinhos
    out = []
    for e in sorted(eventos):
        if out and e[0] <= out[-1][1] + int(0.002 * sr):
            out[-1] = (out[-1][0], max(out[-1][1], e[1]), max(out[-1][2], e[2]))
        else:
            out.append(e)
    return out


def lsar(x: np.ndarray, i0: int, i1: int, sr: int, ordem: int = 32) -> np.ndarray:
    ctx = int(0.025 * sr)
    a = max(0, i0 - ctx)
    z = min(len(x), i1 + ctx)
    seg = x[a:z].copy()
    m0, m1 = i0 - a, i1 - a
    bons = np.r_[seg[:m0], seg[m1:]]
    if len(bons) < 4 * ordem:
        return x[i0:i1]
    # AR pelo método da autocorrelação no contexto
    r = np.correlate(bons, bons, "full")[len(bons) - 1: len(bons) + ordem]
    r[0] *= 1.0001
    coef = linalg.solve_toeplitz(r[:ordem], r[1: ordem + 1])
    ar = np.r_[1.0, -coef]
    N = len(seg)
    # matriz de erro de predição e = A s
    L = N - ordem
    A = np.zeros((L, N))
    for i in range(L):
        A[i, i: i + ordem + 1] = ar[::-1]
    miss = np.arange(m0, m1)
    known = np.r_[np.arange(0, m0), np.arange(m1, N)]
    Au, Ak = A[:, miss], A[:, known]
    sol = np.linalg.lstsq(Au, -Ak @ seg[known], rcond=None)[0]
    return sol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--limiar", type=float, default=8.0)
    ap.add_argument("--relatorio", type=Path)
    args = ap.parse_args()
    x, sr = sf.read(args.entrada, dtype="float64", always_2d=True)
    info = sf.info(args.entrada)
    mono = x.mean(axis=1)
    ev = detectar(mono, sr, args.limiar)
    # Só a banda acima de 1,5 kHz é reconstruída no estalo: o corpo da voz
    # (fundamental e 1º formante) passa intacto. Divisão de fase zero com
    # reconstrução perfeita (agudo = sinal - grave).
    sos = signal.butter(4, 1500, "lowpass", fs=sr, output="sos")
    y = x.copy()
    for ch in range(x.shape[1]):
        grave = signal.sosfiltfilt(sos, x[:, ch])
        agudo = x[:, ch] - grave
        novo = agudo.copy()
        for i0, i1, _ in ev:
            novo[i0:i1] = lsar(agudo, i0, i1, sr)
        y[:, ch] = grave + novo
    y = np.clip(y, -1.0, 1.0)
    sf.write(args.saida, y if y.shape[1] > 1 else y[:, 0], sr, subtype=info.subtype)
    assert sf.info(args.saida).frames == info.frames
    rep = dict(eventos=len(ev), por_minuto=len(ev) / (len(mono) / sr / 60),
               amostras_alteradas_pct=100 * sum(b - a for a, b, _ in ev) / len(mono),
               lista=[dict(t=round(a / sr, 4), dur_ms=round((b - a) / sr * 1000, 2), razao=round(r, 1))
                      for a, b, r in ev])
    if args.relatorio:
        args.relatorio.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("eventos %d | %.1f/min | %.3f%% das amostras" % (
        rep["eventos"], rep["por_minuto"], rep["amostras_alteradas_pct"]))


if __name__ == "__main__":
    main()
