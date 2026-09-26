#!/usr/bin/env python3
"""Transcreve o take ILHA POR ILHA de fala e grava 4-edicao/ilhas.json (método da skill de aulas da Marilia).
Transcrevendo cada ilha isolada, o Whisper não tem contexto pra "limpar" as frases repetidas: cada tentativa
dela vira texto com tempo absoluto, e o roteiro de edição escolhe a última versão boa.
Silêncio: -30 dB por pelo menos 0,3 s (ffmpeg silencedetect) no áudio tratado (audio/D-eq9.wav) ou no take.
Formato: {silencios: [[ini, fim]...], ilhas: [{ini, fim, texto, palavras: [{w, ini, fim}]}]}, tempos do take.
Uso: ilhas.py "<pasta do reel>" """
import json, os, re, sys, subprocess, tempfile
import numpy as np, soundfile as sf

MODELO = 'mlx-community/whisper-large-v3-turbo'  # o mesmo do organizar.py
PISO_DB, MIN_SIL, MARGEM = -30, 0.3, 0.12


def fonte_de_audio(pasta):
    tratado = os.path.join(pasta, '4-edicao', 'audio', 'D-eq9.wav')
    if os.path.exists(tratado): return tratado
    tk = os.path.join(pasta, '3-takes')
    return os.path.join(tk, [f for f in sorted(os.listdir(tk)) if f.startswith('camera__') and f.lower().endswith(('.mov', '.mp4'))][0])


def silencios(audio):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-i', audio, '-af', f'silencedetect=noise={PISO_DB}dB:d={MIN_SIL}', '-vn', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
    fim = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio], capture_output=True, text=True).stdout)
    if len(fim) < len(ini): fim.append(dur)
    return [[a, b] for a, b in zip(ini, fim)], dur


def transcrever(pasta):
    import mlx_whisper
    audio = fonte_de_audio(pasta)
    sil, dur = silencios(audio)
    # ilhas = o que fica entre os silêncios
    bordas = [0.0] + [x for s in sil for x in s] + [dur]
    pares = [(bordas[i], bordas[i + 1]) for i in range(0, len(bordas) - 1, 2)]
    pares = [(a, b) for a, b in pares if b - a > 0.15]
    x, sr = sf.read(audio, always_2d=True); x = x.mean(1)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for a, b in pares:
            i0, i1 = int(max(0, a - MARGEM) * sr), int(min(dur, b + MARGEM) * sr)
            wav = os.path.join(tmp, 'ilha.wav'); sf.write(wav, x[i0:i1], sr)
            r = mlx_whisper.transcribe(wav, path_or_hf_repo=MODELO, language='pt', word_timestamps=True, condition_on_previous_text=False)
            ws = [dict(w=w['word'].strip(), ini=round(i0 / sr + w['start'], 3), fim=round(i0 / sr + w['end'], 3))
                  for s in r.get('segments', []) for w in s.get('words', []) if w['word'].strip()]
            if not ws: continue
            out.append(dict(ini=round(a, 3), fim=round(b, 3), texto=r.get('text', '').strip(), palavras=ws))
    return dict(silencios=[[round(a, 6), round(b, 6)] for a, b in sil], ilhas=out)


if __name__ == '__main__':
    pasta = sys.argv[1]
    d = transcrever(pasta)
    json.dump(d, open(os.path.join(pasta, '4-edicao', 'ilhas.json'), 'w'), ensure_ascii=False, indent=1)
    print(f"ilhas: {len(d['ilhas'])} ilhas de fala, {sum(len(i['palavras']) for i in d['ilhas'])} palavras")
