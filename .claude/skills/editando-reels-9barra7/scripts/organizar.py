#!/usr/bin/env python3
"""Organiza os brutos de um lote: transcreve, identifica o reel de cada arquivo e liga em 3-takes/.
Uso: organizar.py "<pasta do lote>"   (ex: Produção/Lote 1 - 22.09 a 05.10)"""
import json, os, re, subprocess, sys, glob, unicodedata, difflib

MIDIA = ('.mov', '.mp4', '.m4v', '.mts', '.wav', '.mp3', '.m4a', '.aac')
MODELO = 'mlx-community/whisper-large-v3-turbo'
NUM = {'um':1,'uma':1,'primeiro':1,'dois':2,'duas':2,'tres':3,'quatro':4,'cinco':5,'seis':6,'sete':7,'oito':8,'nove':9,'dez':10,
       'onze':11,'doze':12,'treze':13,'quatorze':14,'catorze':14,'quinze':15,'dezesseis':16,'dezessete':17,'dezoito':18,
       'dezenove':19,'vinte':20,'trinta':30}
MES = {'setembro':9,'outubro':10,'novembro':11,'dezembro':12,'janeiro':1,'fevereiro':2,'marco':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8}

def norm(t):
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9/ ]+', ' ', t)

def numeros(texto):
    """Extrai a sequência de números falados ou escritos: 'vinte e nove do nove' -> [29, 9]."""
    out, acc = [], None
    for w in norm(texto).replace('/', ' ').split():
        if w.isdigit(): out.append(int(w)); acc = None; continue
        if w in MES: out.append(MES[w]); acc = None; continue
        if w in NUM:
            v = NUM[w]
            if acc is not None and acc >= 20 and v < 10: out[-1] = acc + v; acc = None
            else: out.append(v); acc = v if v >= 20 else None
        elif w != 'e': acc = None
    return out

def probe(f):
    r = json.loads(subprocess.run(['ffprobe','-v','quiet','-print_format','json','-show_streams','-show_format',f],capture_output=True,text=True).stdout or '{}')
    v = [s for s in r.get('streams',[]) if s.get('codec_type')=='video']
    a = [s for s in r.get('streams',[]) if s.get('codec_type')=='audio']
    dur = float(r.get('format',{}).get('duration',0))
    if not v: return 'audio', dur, bool(a)
    w, h = int(v[0]['width']), int(v[0]['height'])
    rot = abs(int((v[0].get('tags') or {}).get('rotate', 0) or 0))
    for sd in v[0].get('side_data_list', []):
        if 'rotation' in sd: rot = abs(int(sd['rotation']))
    if rot in (90, 270): w, h = h, w
    return ('camera' if h > w else 'tela'), dur, bool(a)

def transcrever(f, cache):
    os.makedirs(cache, exist_ok=True)
    base = os.path.splitext(os.path.basename(f))[0]
    out = os.path.join(cache, base + '.json')
    if os.path.exists(out): return json.load(open(out, encoding='utf-8'))
    wav = os.path.join(cache, base + '.wav')
    subprocess.run(['ffmpeg','-y','-v','error','-i',f,'-vn','-ac','1','-ar','16000',wav], check=True)
    subprocess.run(['mlx_whisper', wav, '--model', MODELO, '--language', 'pt', '--word-timestamps', 'True',
                    '--output-format', 'json', '--output-dir', cache, '--output-name', base], check=True, capture_output=True)
    os.remove(wav)
    return json.load(open(out, encoding='utf-8'))

def reels_do_lote(lote):
    rs = []
    for d in sorted(glob.glob(os.path.join(lote, '[0-9][0-9] - *'))):
        m = re.match(r'\d\d - (\d\d)\.(\d\d) ', os.path.basename(d))
        rj = os.path.join(d, '1-roteiro', 'roteiro.json')
        if m and os.path.exists(rj):
            r = json.load(open(rj, encoding='utf-8'))
            rs.append(dict(pasta=d, dia=int(m.group(1)), mes=int(m.group(2)),
                           fala=norm(' '.join(c['fala'] or '' for c in r['cenas']))))
    return rs

def identificar(tr, reels):
    inicio = ' '.join(s['text'] for s in tr['segments'] if s['start'] < 8)
    ns = numeros(inicio)
    for i in range(len(ns) - 1):
        hit = [r for r in reels if r['dia'] == ns[i] and r['mes'] == ns[i+1]]
        if hit: return hit[0], 'claquete', 1.0
    texto = norm(tr['text'])
    melhor = max(reels, key=lambda r: difflib.SequenceMatcher(None, texto, r['fala']).ratio())
    return melhor, 'conteudo', round(difflib.SequenceMatcher(None, texto, melhor['fala']).ratio(), 2)

def main(lote):
    brutos = os.path.join(lote, '_brutos'); cache = os.path.join(brutos, '_transcricoes')
    reels = reels_do_lote(lote); mapa = []
    for f in sorted(glob.glob(os.path.join(brutos, '*'))):
        if not f.lower().endswith(MIDIA): continue
        tipo, dur, tem_audio = probe(f)
        if not tem_audio:
            mapa.append(dict(arquivo=os.path.basename(f), tipo=tipo, reel=None, metodo='sem audio')); continue
        tr = transcrever(f, cache)
        r, metodo, conf = identificar(tr, reels)
        ok = metodo == 'claquete' or conf >= 0.35
        item = dict(arquivo=os.path.basename(f), tipo=tipo, duracao_s=round(dur,1), reel=os.path.basename(r['pasta']) if ok else None, metodo=metodo, confianca=conf)
        mapa.append(item)
        if ok:
            dest = os.path.join(r['pasta'], '3-takes')
            os.makedirs(dest, exist_ok=True)
            link = os.path.join(dest, f"{tipo}__{os.path.basename(f)}")
            if not os.path.lexists(link): os.symlink(os.path.relpath(f, dest), link)
            json.dump(tr, open(os.path.join(dest, f"{tipo}__{os.path.splitext(os.path.basename(f))[0]}.transcricao.json"),'w',encoding='utf-8'), ensure_ascii=False)
    json.dump(mapa, open(os.path.join(brutos, '_mapa.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    for m in mapa: print(f"{m['arquivo']:32} {m['tipo']:7} -> {m['reel'] or 'NÃO IDENTIFICADO'}  ({m['metodo']}{', '+str(m.get('confianca')) if m.get('confianca') else ''})")
    semtake = [os.path.basename(r['pasta']) for r in reels if not any(m['reel']==os.path.basename(r['pasta']) and m['tipo']=='camera' for m in mapa)]
    if semtake: print('\nSEM TAKE DE CÂMERA:', ', '.join(semtake))

if __name__ == '__main__':
    main(sys.argv[1])
