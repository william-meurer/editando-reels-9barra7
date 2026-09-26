#!/usr/bin/env python3
"""Cor do reel: opção E, aprovada no reel 06 (26/09/2026) contra a referência da Human.
Diagnóstico que levou a ela: o bruto não estoura (pico 85 IRE); o 'lavado' é preto levantado (6-8 IRE)
e fundo (janela, 77 IRE) mais claro que a pele (54). Nas referências o fundo fica ABAIXO da pele e a pele
é menos saturada (sat 58-112 contra 133 do bruto).
E = curva na luminância (preto no chão, pele ~57 IRE, altas suaves) + pele menos saturada +
    escurecer só as áreas claras em volta dela (a janela) + grão fino.
Trabalha no quadro JÁ recortado (1080x1920), RGB float 0-1."""
import numpy as np, cv2
from scipy.interpolate import PchipInterpolator

LUM = np.array([0.2126, 0.7152, 0.0722])
CURVA_E = PchipInterpolator(*zip(*[(0, 0), (0.06, 0.0), (0.25, 0.19), (0.54, 0.57), (0.77, 0.66), (0.9, 0.74), (1, 0.84)]))
SAT_E, CALOR_E, RELUZ_E, GRAO_E = 0.86, 0.004, 0.30, 0.022

def _mascara_entorno(h, w, raio=0.42):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx / w - 0.5) / 0.62) ** 2 + ((yy / h - 0.42) / 0.62) ** 2)
    m = np.clip((d - raio) / 0.35, 0, 1); return (m * m * (3 - 2 * m)).astype(np.float32)
_MASC = {}

_TAB = CURVA_E(np.linspace(0, 1, 4096)).astype(np.float32)   # curva tabelada: rápida no quadro inteiro

def aplica_e(c, seed=0):
    Y = c @ LUM; f = _TAB[(np.clip(Y, 0, 1) * 4095).astype(np.int32)]; o = c * (f / np.maximum(Y, 1e-4))[..., None]
    Yo = o @ LUM; o = Yo[..., None] + (o - Yo[..., None]) * SAT_E
    meio = np.clip(1 - abs(Yo - 0.5) * 2, 0, 1)[..., None]; o = o + meio * np.array([CALOR_E, CALOR_E * 0.3, -CALOR_E])
    h, w = o.shape[:2]
    if (h, w) not in _MASC: _MASC[(h, w)] = _mascara_entorno(h, w)
    alto = np.clip((o @ LUM - 0.45) / 0.35, 0, 1)                      # só o que é claro (janela), não o blazer
    o = o * (1 - RELUZ_E * _MASC[(h, w)] * alto)[..., None]
    # grão: mais nos meios-tons. Campo borrado (σ 0,9, grão de filme tem tamanho) e SEGURADO 2 quadros:
    # ruído novo a cada quadro é incompressível (motion-vox: 120 Mbps contra 4) e o Instagram vira borrão
    rng = np.random.default_rng(seed // 2)
    n = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.9)
    Y2 = o @ LUM; m = (0.4 + 0.6 * (1 - np.abs(Y2 - 0.45) * 1.6)).clip(0.2, 1)
    return np.clip(o + (n * GRAO_E * m)[..., None], 0, 1)
