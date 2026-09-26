#!/usr/bin/env python3
"""Legenda palavra por palavra (estilo aprovado no reel 06, referência do Pinterest do William).
Grafia vem do roteiro (a transcrição erra: "novo ano" em vez de "ângulo"); o TEMPO vem da transcrição
ilha por ilha. Grava em 4-edicao/montagem.json:
  palavras: [{t, ini, fim, trecho}]  tempo de saída em segundos, uma por vez, corte seco
  enfases:  [{linhas, ini, fim}]      2-3 palavras empilhadas e maiores (lista em edicao.json -> "enfases")
Regras: cada palavra fica até a próxima começar; se a próxima demora mais de 0,35 s, some 0,15 s depois
do fim dela. Nada no gancho (3 s) nem nas cenas de tela (lá a legenda é em bloco embaixo).
Uso: palavras.py "<pasta do reel>" """
import json, os, re, sys, difflib, unicodedata

MANTEM = {'ia': 'IA', 'marilia': 'Marilia', '9barra7': '9barra7'}

def norm(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in t if unicodedata.category(c) != 'Mn'))

def exibe(w):
    limpo = re.sub(r'[.,;:!?"“”]', '', w)
    return MANTEM.get(norm(limpo), limpo.lower())

def main(pasta):
    ed = os.path.join(pasta, '4-edicao')
    e = json.load(open(os.path.join(ed, 'edicao.json'), encoding='utf-8'))
    m = json.load(open(os.path.join(ed, 'montagem.json'), encoding='utf-8'))
    ilhas = json.load(open(os.path.join(ed, 'ilhas.json'), encoding='utf-8'))['ilhas']
    ws = [w for il in ilhas for w in il['palavras']]
    fps = m.get('fps', 30); gancho = e.get('gancho', {}).get('dur_s', 0) if e.get('gancho') else 0
    todas = []
    for t in m['trechos']:
        if t['plano'] == '—': continue
        rot = t['texto'].split()
        pw = [w for w in ws if t['fonte_ini'] - 0.05 <= w['ini'] <= t['fonte_fim'] + 0.1]
        sm = difflib.SequenceMatcher(None, [norm(x) for x in rot], [norm(w['w']) for w in pw], autojunk=False)
        tempo = {}
        for a, b, n in sm.get_matching_blocks():
            for k in range(n): tempo[a + k] = (pw[b + k]['ini'], pw[b + k]['fim'])
        # palavra do roteiro sem par na transcrição: tempo interpolado entre as vizinhas
        conh = sorted(tempo)
        for i in range(len(rot)):
            if i in tempo: continue
            ant = max([j for j in conh if j < i], default=None); pro = min([j for j in conh if j > i], default=None)
            a0 = tempo[ant][1] if ant is not None else t['fonte_ini']; b0 = tempo[pro][0] if pro is not None else t['fonte_fim']
            passo = (b0 - a0) / ((pro if pro is not None else len(rot)) - (ant if ant is not None else -1))
            k = i - (ant if ant is not None else -1); tempo[i] = (a0 + passo * (k - 1) + 0.02, a0 + passo * k)
        base = t['out_f0'] / fps - t['src_t0']; fim_trecho = (t['out_f0'] + t['n']) / fps
        for i, w in enumerate(rot):
            txt = exibe(w)
            if not txt: continue
            todas.append(dict(t=txt, ini=round(tempo[i][0] + base, 3), fim=round(min(tempo[i][1] + base, fim_trecho), 3), trecho=t['num'], norm=norm(w)))
    todas.sort(key=lambda x: x['ini'])
    for i, p in enumerate(todas):
        prox = todas[i + 1]['ini'] if i + 1 < len(todas) else None
        p['fim'] = prox if prox is not None and prox - p['fim'] <= 0.35 else round(p['fim'] + 0.15, 3)
    cortada = [p['ini'] < gancho for p in todas]
    for p in todas: p['ini'] = max(p['ini'], gancho)
    # só a palavra que o gancho cobriu quase inteira sai; palavra real de duração ~0 junta com a seguinte, abaixo
    todas = [p for p, c in zip(todas, cortada) if not (c and p['fim'] - p['ini'] < 0.1)]
    # palavra com menos de 0,15 s na tela pisca: junta com a seguinte na mesma linha ("a primeira", "eu envio")
    juntas, i = [], 0
    while i < len(todas):
        p = dict(todas[i])
        while p['fim'] - p['ini'] < 0.15 and i + 1 < len(todas) and todas[i + 1]['trecho'] == p['trecho'] and not p['t'].endswith(' '):
            q = todas[i + 1]; p = dict(p, t=p['t'] + ' ' + q['t'], fim=q['fim'], norm=p['norm'] + ' ' + q['norm']); i += 1
        juntas.append(p); i += 1
    todas = juntas
    # ênfases: sequência de palavras do edicao.json dentro do trecho indicado
    enf = []
    for x in e.get('enfases', []):
        alvo = [norm(w) for w in x['texto'].split()]
        cand = [p for p in todas if p['trecho'] == x['trecho']]
        achou = None
        for a0 in range(len(cand)):              # grupos podem ter palavras juntas: casa pela sequência de palavras
            for a1 in range(a0 + 1, len(cand) + 1):
                junto = ' '.join(c['norm'] for c in cand[a0:a1]).split()
                if junto == alvo: achou = cand[a0:a1]; break
                if len(junto) >= len(alvo): break
            if achou: break
        if achou:
            enf.append(dict(linhas=' '.join(g['t'] for g in achou).split(), ini=achou[0]['ini'], fim=achou[-1]['fim']))
            for g in achou: g['na_enfase'] = True
        else: print('  AVISO: ênfase não encontrada:', x)
    m['palavras'] = [{k: v for k, v in p.items() if k != 'norm'} for p in todas if not p.get('na_enfase')]
    m['enfases'] = enf
    json.dump(m, open(os.path.join(ed, 'montagem.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    dur = sorted(p['fim'] - p['ini'] for p in todas)
    print(f"{len(todas)} palavras ({len(enf)} ênfases) | tempo na tela: mediana {dur[len(dur) // 2]:.2f}s, menor {dur[0]:.2f}s")
    curtas = [p['t'] for p in todas if p['fim'] - p['ini'] < 0.12]
    if curtas: print('  palavras com menos de 4 quadros na tela:', curtas)

if __name__ == '__main__':
    main(sys.argv[1])
