#!/usr/bin/env python3
"""Prepara um reel decupado pra montagem no Remotion: junta os cortes num só vídeo com a fala acelerada,
e grava 4-edicao/montagem.json com a linha do tempo, os blocos de legenda e as cenas.
Uso: preparar.py "<pasta do reel>"   (depois de decupar.py)"""
import json, os, re, subprocess, sys, difflib, unicodedata

VEL = 1.12            # aceleração da voz (padrão de edição)
FPS = 30
# recorte do take 4K vertical (2160x3840) que vira o proxy: sobra margem pro enquadramento fechado
PROXY = dict(x=270, y=300, w=1620, h=2880)
FINAIS_PROIBIDOS = set('e de do da que a o os as um uma pra com em no na se só teu tua meu minha esse essa isso'.split())
MAX_LINHA = 34
INICIOS_BONS = set('que e com pra para em na no nas nos de do da mas porque sem até junto mantendo quando onde se ou está esta é foi foram vai fica'.split())
SIL_MIN, SIL_RESTO = 0.35, 0.08
PEDACO_MIN = 0.35
MODELO = 'mlx-community/whisper-large-v3-turbo'   # pausa maior que 0,35 s dentro do corte vira 0,16 s (0,08 de cada lado)

def norm(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '', t)

def quebrar_linhas(txt):
    """Até 2 linhas de até 34 caracteres, sem linha terminando em palavra proibida. None se não couber."""
    ws = txt.split()
    if len(txt) <= MAX_LINHA: return [txt]
    melhor = None
    for i in range(1, len(ws)):
        a, b = ' '.join(ws[:i]), ' '.join(ws[i:])
        if len(a) > MAX_LINHA or len(b) > MAX_LINHA: continue
        if norm(ws[i-1]) in FINAIS_PROIBIDOS: continue
        custo = abs(len(a) - len(b)) + (0 if ws[i-1].endswith(',') or norm(ws[i]) in INICIOS_BONS else 20)
        if melhor is None or custo < melhor[0]: melhor = (custo, [a, b])
    return melhor and melhor[1]

def partir(b):
    """Parte sem pontuação que não cabe: corta no melhor ponto e repete até caber."""
    if quebrar_linhas(b): return [b]
    ws = b.split(); melhor = None
    for k in range(1, len(ws)):
        if norm(ws[k-1]) in FINAIS_PROIBIDOS: continue
        a, c = ' '.join(ws[:k]), ' '.join(ws[k:])
        custo = abs(len(a) - len(c)) + (0 if norm(ws[k]) in INICIOS_BONS else 15) + (0 if quebrar_linhas(a) and quebrar_linhas(c) else 40)
        if melhor is None or custo < melhor[0]: melhor = (custo, k)
    if not melhor: return [b]
    k = melhor[1]
    return partir(' '.join(ws[:k])) + partir(' '.join(ws[k:]))

def silencios(video, cache):
    """Silêncios do take inteiro, em segundos do original."""
    if os.path.exists(cache): return json.load(open(cache))
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', video, '-vn', '-af', f'silencedetect=noise=-35dB:d={SIL_MIN}', '-f', 'null', '-'], capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', r)]
    fim = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', r)]
    out = list(zip(ini, fim)); json.dump(out, open(cache, 'w')); return out

def trechos(ini, fim, sil):
    """Pedaços do corte que ficam, tirando o miolo das pausas longas do meio.
    Silêncio encostado na borda do corte não conta, e nenhum pedaço fica com menos de 0,35 s (vira piscada)."""
    junto = []   # estalo curto entre dois silêncios não quebra a pausa
    for s0, s1 in sorted(sil):
        if junto and s0 - junto[-1][1] < 0.3: junto[-1][1] = max(junto[-1][1], s1)
        else: junto.append([s0, s1])
    out, a = [], ini
    for s0, s1 in junto:
        if s0 < ini + 0.1 or s1 > fim - 0.1 or s1 - s0 < SIL_MIN: continue
        c0, c1 = s0 + SIL_RESTO, s1 - SIL_RESTO
        if c0 - a < PEDACO_MIN: continue
        out.append((a, c0)); a = c1
    if out and fim - a < PEDACO_MIN: a = out.pop()[0]   # sobra curta no fim: devolve a pausa
    out.append((a, fim)); return out

def ouvir(a, b, audio):
    """Transcreve um pedaço do take e devolve as palavras com tempo absoluto."""
    import mlx_whisper
    r = mlx_whisper.transcribe(audio[int(a * 16000):int(b * 16000)], path_or_hf_repo=MODELO, language='pt',
                               word_timestamps=True, condition_on_previous_text=False)
    return [dict(word=w['word'], start=w['start'] + a, end=w['end'] + a) for s in r['segments'] for w in s.get('words', [])]

def sem_recomeco(pedacos, audio):
    """Tira o pedaço em que ela começou a frase e parou pra recomeçar: o começo dele se repete num pedaço seguinte.
    Devolve os pedaços que ficam e as palavras deles (a transcrição do take inteiro funde repetições e erra o tempo)."""
    ouvidos = [ouvir(a, b, audio) for a, b in pedacos]
    txt = [[norm(w['word']) for w in o if norm(w['word'])] for o in ouvidos]
    fica, palavras = [], []
    for i, ws in enumerate(txt):
        ini = ws[:4]
        repete = ini and any(difflib.SequenceMatcher(None, ini, o[:len(ini)]).ratio() >= 0.75 for o in txt[i + 1:])
        if repete: print(f"  recomeço descartado ({pedacos[i][0]:.1f}s): {' '.join(ws)}"); continue
        fica.append(pedacos[i]); palavras += ouvidos[i]
    return fica, palavras

def blocos(frase):
    """Divide a frase em blocos que cabem em 2 linhas, cortando primeiro em vírgula ou ponto."""
    partes = [p.strip() for p in re.split(r'(?<=[,.;:?!])\s+', frase) if p.strip()]
    out, acc = [], ''
    for p in partes:
        tent = (acc + ' ' + p).strip()
        if quebrar_linhas(tent): acc = tent; continue
        if acc: out.append(acc)
        acc = p
    if acc: out.append(acc)
    final = []
    for b in out: final += partir(b)
    return final

def main(pasta):
    ed = os.path.join(pasta, '4-edicao'); base = os.path.join(ed, 'base'); os.makedirs(base, exist_ok=True)
    cortes = json.load(open(os.path.join(ed, 'cortes.json'), encoding='utf-8'))
    rot = json.load(open(os.path.join(pasta, '1-roteiro', 'roteiro.json'), encoding='utf-8'))
    cenas = {c['n']: c for c in rot['cenas']}
    video = os.path.join(pasta, '3-takes', cortes['take'] if 'take' in cortes and os.path.exists(os.path.join(pasta, '3-takes', str(cortes['take']))) else cortes['cortes'][0]['arquivo'])
    trs = [f for f in os.listdir(os.path.join(pasta, '3-takes')) if f.endswith('.transcricao.json')]
    tr = json.load(open(os.path.join(pasta, '3-takes', trs[0]), encoding='utf-8'))
    ws = [w for s in tr['segments'] for w in s.get('words', [])]

    # 1. um trecho por corte, acelerado, com fade curto no áudio pra não estalar
    lista = os.path.join(base, 'lista.txt'); linhas = []
    tl, t = [], 0.0
    sil = silencios(video, os.path.join(base, 'silencios.json')); nseg = 0
    wav = os.path.join(base, 'take.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
    import numpy as np, wave
    with wave.open(wav) as w: audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    os.remove(wav)
    for i, c in enumerate(cortes['cortes']):
        ini, fim = c['inicio_s'], c['fim_s']; p = PROXY; mapa_t = []; t0 = t
        pedacos, palavras_corte = sem_recomeco(trechos(ini, fim, sil), audio)
        for a, b in pedacos:
            seg = os.path.join(base, f'seg{nseg:03d}.mp4'); nseg += 1; dur = (b - a) / VEL
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', str(b - a), '-i', video,
                '-vf', f"crop={p['w']}:{p['h']}:{p['x']}:{p['y']},setpts=PTS/{VEL},fps={FPS}",
                '-af', f"atempo={VEL},afade=t=in:d=0.015,afade=t=out:st={max(dur-0.015,0):.3f}:d=0.015",
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', seg], check=True)
            real = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', seg], capture_output=True, text=True).stdout)
            linhas.append(f"file '{os.path.basename(seg)}'")
            mapa_t.append((a, b, t, real)); t += real
        def novo(x):
            for a, b, tn, r in mapa_t:
                if x <= b: return tn + max(x - a, 0) / VEL
            return mapa_t[-1][2] + mapa_t[-1][3]
        real = t - t0; t = t0
        pw = [dict(w=norm(w['word']), t=novo(w['start']), f=novo(w['end'])) for w in palavras_corte if norm(w['word'])]
        # blocos de legenda com o texto do roteiro, cronometrados pelas palavras faladas
        bl = []
        rw = c['frase'].split(); rn = [norm(x) for x in rw]
        sm = difflib.SequenceMatcher(None, rn, [x['w'] for x in pw], autojunk=False)
        mapa = {}
        for a, b, n in sm.get_matching_blocks():
            for k in range(n): mapa[a + k] = pw[b + k]
        k0 = 0
        for b in blocos(c['frase']):
            n = len(b.split()); idx = range(k0, k0 + n); k0 += n
            achadas = [mapa[j] for j in idx if j in mapa]
            bl.append(dict(texto=b, linhas=quebrar_linhas(b) or [b],
                           ini=round(achadas[0]['t'] if achadas else t, 3), fim=round(achadas[-1]['f'] if achadas else t + real, 3)))
        # blocos encostam um no outro: cada um fica até o próximo começar
        for j in range(len(bl)):
            bl[j]['ini'] = t if j == 0 else bl[j]['ini']
            bl[j]['fim'] = bl[j+1]['ini'] if j + 1 < len(bl) else t + real
        cena = cenas.get(c['cena'], {})
        tl.append(dict(corte=i, cena=c['cena'], tipo=cena.get('tipo'), voz=cena.get('voz'), camera=cena.get('camera'),
                       visual=cena.get('visual'), texto_na_tela=cena.get('texto_na_tela'),
                       ini=round(t, 3), fim=round(t + real, 3), blocos=bl,
                       trechos=[round(x[2], 3) for x in mapa_t]))  # onde cada pedaço começa: pulo de imagem a esconder
        t += real
    open(lista, 'w').write('\n'.join(linhas) + '\n')
    fala = os.path.join(base, 'fala.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lista, '-c', 'copy', '-movflags', '+faststart', fala], check=True)
    for f in os.listdir(base):
        if f.startswith('seg'): os.remove(os.path.join(base, f))
    os.remove(lista)

    arq = os.path.join(ed, 'montagem.json')
    antigo = json.load(open(arq, encoding='utf-8')) if os.path.exists(arq) else {}
    m = dict(reel=os.path.basename(pasta), codigo=rot.get('codigo'), fps=FPS, velocidade=VEL, proxy=PROXY,
             video='base/fala.mp4', duracao_fala_s=round(t, 3), cortes=tl,
             # escolhas manuais sobrevivem a uma nova preparação
             palavras_chave=antigo.get('palavras_chave', []), enquadramento=antigo.get('enquadramento', {}))
    json.dump(m, open(arq, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"fala: {t:.1f}s  ({len(tl)} cortes, {sum(len(x['blocos']) for x in tl)} blocos de legenda)")
    for x in tl:
        for b in x['blocos']:
            ps = len(b['texto'].split()) / max(b['fim'] - b['ini'], 0.01)
            alerta = '   <- LENTO: conferir se tem frase regravada aqui' if ps < 2 and len(b['texto'].split()) > 3 else ''
            print(f"  cena {x['cena']:>2} {b['ini']:6.2f}  {' / '.join(b['linhas'])}{alerta}")

if __name__ == '__main__':
    main(sys.argv[1])
