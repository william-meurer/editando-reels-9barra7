#!/usr/bin/env python3
"""Confere o mp4 exportado do Palmier e grava a versão de entrega em 5-final/.
1. volume: a soma de voz, cama e efeitos sai ~3 dB acima no Palmier; mede e ajusta o ganho do áudio pra -14 LUFS
   (só ganho, vídeo copiado; sem limitador nem loudnorm, que estalavam). Avisa se o pico passar de -1 dB
2. duração: áudio e vídeo iguais (tolerância de 1 quadro) e igual à do montagem.json
3. quadro preto: nenhum
4. voz: estalos detectáveis que sobraram na voz limpa (a cama tem percussão aguda e engana o detector no mix)
Grava 4-edicao/conferencia.json e 5-final/<nome do reel>.mp4.
Uso: conferir.py "<pasta do reel>" "<mp4 exportado>" [saída]   (saída padrão: 5-final/<nome do reel>.mp4)"""
import json, os, re, sys, subprocess
import numpy as np, soundfile as sf

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(AQUI, 'audio'))
ALVO = -14.0


def loud(f):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-i', f, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', log)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', log)[-1])


def duracoes(f):
    r = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration', '-of', 'json', f], capture_output=True, text=True).stdout)
    return {s['codec_type']: float(s['duration']) for s in r['streams']}


if __name__ == '__main__':
    pasta, exportado = sys.argv[1], sys.argv[2]; ed = os.path.join(pasta, '4-edicao')
    m = json.load(open(os.path.join(ed, 'montagem.json')))
    nome = os.path.basename(os.path.normpath(pasta))
    os.makedirs(os.path.join(pasta, '5-final'), exist_ok=True)
    final = sys.argv[3] if len(sys.argv) > 3 else os.path.join(pasta, '5-final', nome + '.mp4')
    i0, p0 = loud(exportado); ganho = round(ALVO - i0, 2)
    # o Palmier às vezes exporta o áudio uns quadros mais longo que o vídeo (silêncio no fim): corta no tamanho do vídeo
    dv = duracoes(exportado)['video']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', exportado, '-map', '0:v', '-map', '0:a', '-c:v', 'copy', '-af', f'volume={ganho}dB,atrim=end={dv:.4f}',
                    '-c:a', 'aac', '-b:a', '320k', final], check=True)
    i1, p1 = loud(final); d = duracoes(final)
    pretos = subprocess.run(['ffmpeg', '-hide_banner', '-i', final, '-vf', 'blackdetect=d=0.03:pix_th=0.06', '-an', '-f', 'null', '-'],
                            capture_output=True, text=True).stderr.count('black_start')
    import estalos_hf
    voz = os.path.join(ed, 'audio', 'montagem-limpa.wav')
    if not os.path.exists(voz): voz = os.path.join(ed, 'audio', 'montagem.wav')   # voz nova: já sai limpa do D-limpo
    x, sr = sf.read(voz); estalos = len(estalos_hf.detectar(x if x.ndim == 1 else x.mean(1), sr, 6))
    ok_dur = abs(d['audio'] - d['video']) <= 1 / 30 + 0.01 and abs(d['video'] - m['quadros'] / 30) <= 1 / 30 + 0.01
    r = dict(arquivo=final, lufs_exportado=i0, ganho_db=ganho, lufs=i1, pico_db=p1, duracao=d, duracao_ok=ok_dur, quadros_pretos=pretos, estalos_na_voz=estalos)
    json.dump(r, open(os.path.join(ed, 'conferencia.json'), 'w'), ensure_ascii=False, indent=1)
    avisos = [a for a, c in [(f'pico {p1} dB acima de -1', p1 > -1), ('duração de áudio e vídeo não bate', not ok_dur), (f'{pretos} quadro(s) preto(s)', pretos),
                             (f'{estalos} estalos na voz (o reel 06 ficou com 7)', estalos > 15)] if c]
    print(f"conferir: {final}\n  {i1} LUFS (ganho {ganho:+} dB), pico {p1} dB, {d['video']:.2f}s, pretos {pretos}, estalos na voz {estalos}")
    print('  AVISOS: ' + '; '.join(avisos) if avisos else '  tudo ok')
