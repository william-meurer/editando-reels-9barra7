#!/usr/bin/env python3
"""Monta a linha do tempo do reel a partir do roteiro de edição aprovado (4-edicao/edicao.json).
Grava:
- 4-edicao/audio/montagem.wav: a voz na grade de quadros, 30 ms de fade amostra por amostra em toda emenda
  (o corte cai depois do fim da voz e antes do começo dela, medido em 80-1000 Hz), 4 s de silêncio no fechamento
- 4-edicao/montagem.json: trechos (onde cada um cai no reel e de onde vem no take), legendas, palavras com tempo
  de saída, gancho, destaque, virada e telas. É o que o palmier.py e o cama.py leem.

Legenda (padrao-edicao.md): frase em blocos de até 2 linhas, cada linha com até 720 px em DM Sans Medium 54 px
(centralizada, não entra embaixo dos botões do Instagram); nunca termina linha em palavra fraca; corta primeiro
na pontuação e, se não couber, no tempo da fala. Nada nos 3 s do gancho nem enquanto o destaque está na tela.

Uso: montar.py "<pasta do reel>" [--audio audio/D-limpo.wav]   (padrão: D-limpo, ou D-eq9 se ainda não houver)"""
import argparse, json, os, re, sys, difflib, unicodedata
import numpy as np, soundfile as sf
from PIL import ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(AQUI, '..', '..', '..', '..', 'Produção', 'kit')
FPS, SR, FADE, FECHAMENTO = 30, 48000, 0.030, 4.0
LARGURA_MAX = 720
FONTE_LEGENDA = ImageFont.truetype(os.path.join(KIT, 'fonte', 'DMSans-Medium.ttf'), 54)
INICIOS_FORTES = set('que mas porque quando onde'.split())   # a linha nova começa melhor nelas


def norm(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in t if unicodedata.category(c) != 'Mn'))


# o texto vem com acento ("só"), a comparação é sem
INICIOS_BONS = set(norm(w) for w in 'que e com pra para em na no nas nos de do da mas porque sem até junto mantendo quando onde se ou está esta é foi foram vai fica'.split())
FINAIS_PROIBIDOS = set(norm(w) for w in 'e de do da que a o os as um uma pra com em no na se só teu tua meu minha esse essa isso'.split())


# ---------------- linha do tempo e áudio ----------------
def bordas_da_voz(x, sr):
    """Acham onde a VOZ de fato começa/termina perto de um tempo. Mede só 80-1000 Hz:
    a vogal final fraca tem grave; a respiração depois é só chiado agudo."""
    from scipy import signal
    v = signal.sosfiltfilt(signal.butter(4, [80, 1000], 'bandpass', fs=sr, output='sos'), x)
    def db(t): a = v[max(int(t * sr), 0):int((t + 0.01) * sr)]; return 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12)
    h = signal.sosfiltfilt(signal.butter(4, 3000, 'highpass', fs=sr, output='sos'), x)
    def dbh(t): a = h[max(int(t * sr), 0):int((t + 0.01) * sr)]; return 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12)
    def cauda(k, lim=-46, folga=0.12, ate=0.2):
        # o fim da palavra às vezes só tem agudo: soltura do "m", "-gem", "s" final (reel 01, 0:07, "imagem" cortado).
        # Um estouro acima de 3 kHz colado no fim da voz (começa em até 120 ms) é da palavra; respiração vem depois e mais fraca
        j = next((k + i * 0.01 for i in range(int(folga / 0.01)) if dbh(k + i * 0.01) > lim), None)
        if j is None: return k
        while j < k + ate and max(dbh(j), dbh(j + 0.01), dbh(j + 0.02)) > lim - 9: j += 0.01
        return j
    def fim(t, lim=-56, segura=0.05, ate=0.5):
        k = t
        while k < t + ate and not all(db(k + i * 0.01) < lim for i in range(int(segura / 0.01))): k += 0.01
        return cauda(k) if k < t + ate else None
    def ini(t, lim=-56, segura=0.05, ate=0.3):
        k = t
        while k > t - ate and not all(db(k - (i + 1) * 0.01) < lim for i in range(int(segura / 0.01))): k -= 0.01
        return k if k > t - ate else None
    return ini, fim


def linha_do_tempo(ed, x, sr, fps_src):
    """fps_src: taxa real do take (29,996 no iPhone); o áudio sai na posição exata do take"""
    tr = ed['trechos']; P_ = ed['pausas']; out = []; f_out = 0
    ini_voz, fim_voz = bordas_da_voz(x, sr)
    for i, t in enumerate(tr):
        antes = P_[t['pausa_antes']] if t['pausa_antes'] else 0.10
        depois = P_[tr[i + 1]['pausa_antes']] if i + 1 < len(tr) else 0.35
        ini = t['fonte_ini'] - 0.4 * antes; fim = t['fonte_fim'] + 0.6 * depois
        iv = None if t.get('ini_fixo') else ini_voz(t['fonte_ini'])
        fv = None if t.get('fim_fixo') else fim_voz(t['fonte_fim'])
        if iv is not None: ini = min(ini, iv - 0.03 - FADE)
        elif not t.get('ini_fixo'): print(f"  AVISO: trecho {t['n']} começa no meio da fala — conferir a borda")
        if fv is not None: fim = max(fim, fv + 0.06 + FADE)
        elif not t.get('fim_fixo'): print(f"  AVISO: trecho {t['n']} termina no meio da fala — conferir a borda")
        f0 = int(round(ini * fps_src)); n = int(round((fim - ini) * FPS))
        out.append(dict(t, src_f0=f0, n=n, num=t['n'], src_t0=f0 / fps_src, out_f0=f_out))
        f_out += n
    return out, f_out


def audio_montado(tl, x, sr):
    partes = []; nf = int(FADE * sr); rampa = np.sin(np.linspace(0, np.pi / 2, nf)) ** 2
    for t in tl:
        i0 = int(round(t['src_t0'] * sr)); n = int(round(t['n'] / FPS * sr))
        s = x[i0:i0 + n].copy(); s[:nf] *= rampa; s[-nf:] *= rampa[::-1]; partes.append(s)
    partes.append(np.zeros(int(FECHAMENTO * sr)))
    return np.concatenate(partes)


# ---------------- legendas ----------------
def largura(t): return FONTE_LEGENDA.getlength(t)


def quebrar(txt):
    """Até 2 linhas de até 720 px, sem linha terminando em palavra fraca. None se não couber."""
    ws = txt.split()
    if largura(txt) <= LARGURA_MAX: return [txt]
    melhor = None
    for i in range(1, len(ws)):
        a, b = ' '.join(ws[:i]), ' '.join(ws[i:])
        if max(largura(a), largura(b)) > LARGURA_MAX or norm(ws[i - 1]) in FINAIS_PROIBIDOS: continue
        custo = abs(largura(a) - largura(b)) / 20 + (0 if ws[i - 1].endswith(',') or norm(ws[i]) in INICIOS_BONS else 20) \
            - (10 if norm(ws[i]) in INICIOS_FORTES else 0)
        if melhor is None or custo < melhor[0]: melhor = (custo, [a, b])
    return melhor and melhor[1]


def partir(ws):
    """Lista de palavras -> blocos que cabem; corta na pontuação e, se não der, no melhor ponto."""
    txt = ' '.join(ws)
    if quebrar(txt): return [ws]
    melhor = None
    for k in range(1, len(ws)):
        if norm(ws[k - 1]) in FINAIS_PROIBIDOS: continue
        a, c = ' '.join(ws[:k]), ' '.join(ws[k:])
        custo = (0 if re.search(r'[,.;:?!]$', ws[k - 1]) else 30) + (0 if norm(ws[k]) in INICIOS_BONS else 15) \
            - (10 if norm(ws[k]) in INICIOS_FORTES else 0) + abs(len(a) - len(c)) / 4 + (0 if quebrar(a) and quebrar(c) else 60) \
            + (50 if min(k, len(ws) - k) < 3 else 0)   # bloco de 1 ou 2 palavras pisca na tela
        if melhor is None or custo < melhor[0]: melhor = (custo, k)
    if not melhor: return [ws]
    return partir(ws[:melhor[1]]) + partir(ws[melhor[1]:])


def palavras_do_trecho(t, ilhas):
    """Palavras do roteiro (grafia do texto) com o tempo da transcrição, já no tempo de saída do reel."""
    ws = [w for il in ilhas for w in il['palavras'] if w['ini'] >= t['fonte_ini'] - 0.05 and w['fim'] <= t['fonte_fim'] + 0.05]
    rn = t['texto'].split()
    sm = difflib.SequenceMatcher(None, [norm(x) for x in rn], [norm(w['w']) for w in ws], autojunk=False)
    mapa = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): mapa[a + k] = ws[b + k]
    ini_tr = t['out_f0'] / FPS; fim_tr = (t['out_f0'] + t['n']) / FPS
    out = []
    for j, w in enumerate(rn):
        m = mapa.get(j)
        ini = min(max(ini_tr + (m['ini'] - t['src_t0']), ini_tr), fim_tr) if m else None
        out.append(dict(t=w, ini=ini, trecho=t['num']))
    for j, w in enumerate(out):  # palavra sem tempo: herda da anterior
        if w['ini'] is None: w['ini'] = out[j - 1]['ini'] + 0.2 if j else ini_tr
    return out


def legendas(tl, ilhas, gancho_s, destaque):
    blocos = []; palavras = []
    for t in tl:
        pw = palavras_do_trecho(t, ilhas); palavras += pw
        fim_tr = (t['out_f0'] + t['n']) / FPS
        # frase: corta nos sinais de pontuação e junta os pedaços enquanto couberem em 2 linhas
        grupos = []
        pedacos, cur = [], []
        for w in pw:
            cur.append(w)
            if re.search(r'[,.;:?!]$', w['t']): pedacos.append(cur); cur = []
        if cur: pedacos.append(cur)
        juntos, acc = [], []
        for p in pedacos:
            tent = acc + p
            if quebrar(' '.join(x['t'] for x in tent)) or (acc and len(acc) < 3): acc = tent; continue
            if acc: juntos.append(acc)
            acc = p
        if acc: juntos.append(acc)
        for jb in juntos:
            idx = partir([x['t'] for x in jb]); k = 0
            for b in idx:
                grupos.append(jb[k:k + len(b)]); k += len(b)
        for j, g in enumerate(grupos):
            ini = t['out_f0'] / FPS if j == 0 else g[0]['ini']
            fim = grupos[j + 1][0]['ini'] if j + 1 < len(grupos) else fim_tr
            blocos.append(dict(palavras=[x['t'] for x in g], ini=ini, fim=fim, trecho=t['num']))
    # destaque: o bloco que o contém fica só com o que vem antes dele e sai quando ele entra
    if destaque:
        di, df = destaque['ini'], destaque['fim']
        novos = []
        for b in blocos:
            if b['fim'] <= di + 0.01 or b['ini'] >= df - 0.01: novos.append(b); continue   # df vem arredondado: o bloco que começa colado no fim não é do destaque
            antes = [w for w in palavras if b['ini'] <= w['ini'] < di - 0.01 and w['t'] in b['palavras']]
            if b['ini'] < di and antes:
                novos.append(dict(b, palavras=b['palavras'][:len(antes)], fim=di))
        blocos = novos
    out = []
    for b in blocos:
        if gancho_s and b['trecho'] == tl[0]['num']: continue   # a frase do gancho já está na tela: o resto dela piscaria depois dos 3 s
        ini = max(b['ini'], gancho_s)
        if b['fim'] - ini < 0.6: continue
        out.append(dict(linhas=quebrar(' '.join(b['palavras'])) or [' '.join(b['palavras'])], ini=round(ini, 3), fim=round(b['fim'], 3)))
    return out, palavras


def achar_destaque(ed, palavras, tl):
    d = ed.get('destaque')
    if not d: return None
    alvo = [norm(x) for x in d['comeca_em'].split()]
    for i in range(len(palavras)):
        if palavras[i]['trecho'] == d['trecho'] and [norm(w['t']) for w in palavras[i:i + len(alvo)]] == alvo:
            t = next(x for x in tl if x['num'] == d['trecho'])
            return dict(texto=d['texto'], ini=round(palavras[i]['ini'], 3), fim=round((t['out_f0'] + t['n']) / FPS, 3))
    print(f"  AVISO: destaque não achado ('{d['comeca_em']}' no trecho {d['trecho']})"); return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('pasta'); ap.add_argument('--audio')
    a = ap.parse_args(); ed_dir = os.path.join(a.pasta, '4-edicao')
    if not a.audio:   # o take limpo (falhas_mic.py) é a fonte da voz montada e dos pedaços de voz do Palmier
        a.audio = 'audio/D-limpo.wav'
        if not os.path.exists(os.path.join(ed_dir, a.audio)):
            a.audio = 'audio/D-eq9.wav'; print('  AVISO: sem audio/D-limpo.wav, montando do D-eq9 (rodar audio/falhas_mic.py antes)')
    ed = json.load(open(os.path.join(ed_dir, 'edicao.json'), encoding='utf-8'))
    ilhas = json.load(open(os.path.join(ed_dir, 'ilhas.json'), encoding='utf-8'))['ilhas']
    x, sr = sf.read(os.path.join(ed_dir, a.audio)); assert sr == SR
    if x.ndim > 1: x = x.mean(1)
    import subprocess
    tk = os.path.join(a.pasta, '3-takes'); video = os.path.join(tk, [f for f in sorted(os.listdir(tk)) if f.startswith('camera__') and f.lower().endswith(('.mov', '.mp4'))][0])
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=nb_frames,duration', '-of', 'json', video], capture_output=True, text=True).stdout)['streams'][0]
    fps_src = int(pr['nb_frames']) / float(pr['duration'])
    tl, n_fala = linha_do_tempo(ed, x, sr, fps_src)
    sf.write(os.path.join(ed_dir, 'audio', 'montagem.wav'), audio_montado(tl, x, sr), SR, subtype='PCM_24')
    gancho = ed.get('gancho'); gancho_s = gancho['dur_s'] if gancho else 0
    _, palavras = legendas(tl, ilhas, gancho_s, None)
    destaque = achar_destaque(ed, palavras, tl)
    leg, palavras = legendas(tl, ilhas, gancho_s, destaque)
    virada = next((t['out_f0'] for t in tl if t['num'] == ed.get('virada')), None)
    telas = [dict(t, quadro=next(x['out_f0'] for x in tl if x['num'] == t['trecho'])) for t in ed.get('telas', [])]
    json.dump(dict(fps=FPS, voz=a.audio, trechos=tl, legendas=leg, palavras=palavras, gancho=gancho, destaque=destaque, virada=virada, telas=telas,
                   cama=ed.get('cama'), sfx=ed.get('sfx'),
                   quadros=n_fala + int(FECHAMENTO * FPS), fechamento=int(FECHAMENTO * FPS)),
              open(os.path.join(ed_dir, 'montagem.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'montar: {len(tl)} trechos, {n_fala / FPS:.2f}s de fala + {FECHAMENTO:.0f}s de fechamento, {len(leg)} blocos de legenda')


if __name__ == '__main__':
    main()
