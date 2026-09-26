#!/usr/bin/env python3
"""Decupa um reel: acha cada frase do roteiro no take longo e fica com a ÚLTIMA versão de cada uma
(regra da gravação: errou, pausa e repete a frase inteira). Grava 4-edicao/cortes.json.
Uso: decupar.py "<pasta do reel>" """
import json, os, re, sys, glob, difflib, unicodedata

def norm(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', t).split()

def frases(t):
    return [f.strip() for f in re.split(r'(?<=[.?!:])\s+', t or '') if f.strip()]

def palavras(tr):
    ws = []
    for s in tr['segments']:
        for w in s.get('words', []):
            for n in norm(w['word']): ws.append(dict(w=n, ini=w['start'], fim=w['end']))
    return ws

def achar(alvo, ws, de, ate, minimo=0.72):
    """Todas as ocorrências de 'alvo' entre os índices de e ate, com score."""
    n = len(alvo); achados = []
    for i in range(de, max(de, ate - n + 1) + 1):
        for k in (n - 1, n, n + 1):
            j = i + k
            if k < 1 or j > ate: continue
            sc = difflib.SequenceMatcher(None, alvo, [x['w'] for x in ws[i:j]]).ratio()
            if sc >= minimo: achados.append((i, j, sc))
    # remove sobreposições, fica com o melhor de cada grupo
    achados.sort(key=lambda a: (-a[2], a[0])); fim = []
    for a in achados:
        if all(a[1] <= b[0] or a[0] >= b[1] for b in fim): fim.append(a)
    return sorted(fim)

def main(pasta):
    rot = json.load(open(os.path.join(pasta, '1-roteiro', 'roteiro.json'), encoding='utf-8'))
    trs = sorted(glob.glob(os.path.join(pasta, '3-takes', 'camera__*.transcricao.json')))
    if not trs: sys.exit('Sem take de câmera em 3-takes/. Rode organizar.py no lote antes.')
    arq_tr = trs[-1]; tr = json.load(open(arq_tr, encoding='utf-8'))
    video = os.path.basename(arq_tr).replace('.transcricao.json', '')
    video = next((os.path.basename(v) for v in glob.glob(os.path.join(pasta, '3-takes', video + '.*')) if not v.endswith('.json')), video)
    ws = palavras(tr)
    itens = [(c, f) for c in rot['cenas'] for f in frases(c['fala'])]
    cursor, cortes, faltando = 0, [], []
    for idx, (c, f) in enumerate(itens):
        alvo = norm(f)
        prox = norm(itens[idx + 1][1]) if idx + 1 < len(itens) else None
        limite = len(ws)
        if prox:
            p = achar(prox, ws, cursor, len(ws))
            if p: limite = p[0][0]
        occ = achar(alvo, ws, cursor, limite)
        if not occ: faltando.append(dict(cena=c['n'], frase=f)); continue
        i, j, sc = occ[-1]
        cortes.append(dict(cena=c['n'], tipo=c['tipo'], voz=c['voz'], frase=f, arquivo=video,
                           inicio_s=round(max(ws[i]['ini'] - 0.08, 0), 2), fim_s=round(ws[j-1]['fim'] + 0.12, 2),
                           score=round(sc, 2), versoes_encontradas=len(occ)))
        cursor = j
    for a, b in zip(cortes, cortes[1:]):  # sem sobreposição entre cortes vizinhos
        if b['inicio_s'] < a['fim_s']:
            meio = round((a['fim_s'] + b['inicio_s']) / 2, 2); a['fim_s'] = meio; b['inicio_s'] = meio
    out = dict(reel=os.path.basename(pasta), take=video, cortes=cortes, frases_nao_encontradas=faltando)
    os.makedirs(os.path.join(pasta, '4-edicao'), exist_ok=True)
    json.dump(out, open(os.path.join(pasta, '4-edicao', 'cortes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for k in cortes:
        rep = f"  ({k['versoes_encontradas']} versões, ficou a última)" if k['versoes_encontradas'] > 1 else ''
        print(f"cena {k['cena']:>2} {k['inicio_s']:7.2f}–{k['fim_s']:7.2f}  {k['frase'][:60]}{rep}")
    for m in faltando: print(f"FALTOU cena {m['cena']}: {m['frase']}")

if __name__ == '__main__':
    main(sys.argv[1])
