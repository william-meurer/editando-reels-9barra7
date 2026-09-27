#!/usr/bin/env python3
"""Monta o projeto do reel no Palmier Pro a partir do montagem.json (escreve o pacote .palmier direto).

Faixas, de cima pra baixo (padrao-edicao.md):
  Destaque · Texto (gancho e legendas) · Janela (a Marilia no formato janela) · Telas (ProRes 4444 com transparência, e o fechamento) · Câmera
  Voz (um pedaço por trecho, do take limpo, ligado à câmera) · Cliques (o som que vem dentro das telas) · Efeitos · Cama
- câmera: a imagem de edição (imagem.py) na escala de cada plano (P1 1, P2 1,10, P3 1,18, ÊNFASE 1,30; empurra até +20%);
  embaixo de uma tela, desce pra metade de baixo (tela dividida: centerY 0,695 ou menos, ver dividida_y; escala 1)
- fechamento: último quadro congelado (vídeo parado, não PNG) na escala do último plano + a marca (kit/fechamento), 4 s
- telas: layout do edicao.json (dividida: câmera desce; cheia: sem câmera; janela: câmera vira janelinha na faixa Janela)
- efeitos: a lista "sfx" do edicao.json (receita da família); sem ela, o padrão do reel 06 (grave no 0:00, whoosh na
  primeira tela, subida na virada, pop no destaque)
- os textos NÃO vão no arquivo (o Palmier calcula a caixa de cada texto): saem prontos em 4-edicao/palmier-textos.json,
  pra aplicar com add_texts depois de abrir o projeto (ver SKILL.md)
Uso: palmier.py "<pasta do reel>" [--nome "Reel 06 - ..."]   (grava o editável em 4-edicao/<nome>.palmier)"""
import argparse, json, os, subprocess, uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(AQUI, '..', '..', '..', '..', 'Produção', 'kit'))
FPS = 30
ESCALA = {'P1': 1.0, 'P2': 2160 / 982 / 2, 'P3': 2160 / 915 / 2, 'ÊNFASE': 2160 / 830 / 2}
EMPURRA = 1.2
DIVIDIDA_Y = 0.695
QUEIXO_MAX = 1330   # na tela dividida, o queixo fica acima disso pra legenda (centro em y 1435) cair no peito


def dividida_y(ed):
    """centerY da câmera embaixo de uma tela: 0,695 (reel 06) ou menos, se ela estiver mais perto da câmera
    e o queixo descer até a legenda (reels 02-05 do lote 1). Queixo = cy + 0,6 w do rosto.json, no recorte do imagem.py."""
    import numpy as np
    ns = {}; exec(open(os.path.join(AQUI, 'imagem.py')).read().split("if __name__")[0], ns)   # recorte() do imagem.py
    r = json.load(open(os.path.join(ed, 'rosto.json')))
    _, y0 = ns['recorte'](r)
    queixo = float(np.median([a['cy'] for a in r]) + 0.6 * np.median([a['w'] for a in r])) - y0
    return round(min(DIVIDIDA_Y, (QUEIXO_MAX - queixo + 960) / 1920), 3)
# efeito: arquivo do kit, volume em dB, e quantos quadros antes do evento ele começa (o ataque cai no evento)
SFX = {
    'impacto': ('sfx/impacto-gancho (grave + estalo).wav', -9.0, 0),
    'whoosh': ('sfx/whoosh (universfield, Pixabay) hp100.wav', -1.5, 17),
    'subida': ('sfx/riser-hit (audiopapkin, Pixabay).mp3', -9.5, 51),
    'pop': ('sfx/pop (DRAGON-STUDIO, Pixabay).mp3', -16.0, 5),
    'clique': ('sfx/mouse click (universfield, Pixabay).mp3', -14.0, 1),
}
# Marilia na janela (formato janela do cardápio): 280 px de largura, 3:4, cantos de 36 px, no alto à direita
# logo abaixo da faixa da interface do Instagram (y 208): longe da legenda, dos botões e do centro da tela
JANELA_W, JANELA_R, JANELA_POS = 280, 36, (1080 - 36 - 280, 236)
ESTILO_DESTAQUE = dict(fontName='DMSans-Bold', bold=True, fontSize=72, color='#FFFFFF', alignment='center', tracking=-5, lineSpacing=-22, shadow=dict(enabled=False))
ESTILO_LEGENDA = dict(fontName='DMSans-Medium', bold=False, fontSize=30.37, color='#FFFFFF', alignment='center', lineSpacing=0,
                      shadow=dict(enabled=True, color='#000000', opacity=0.6, blur=2.2, offset=dict(x=0, y=1.1)))
Y_LEGENDA = 0.7474


def uid(): return str(uuid.uuid4()).upper()
def lin(db): return round(10 ** (db / 20), 5)
def suave(s): return s * s * (3 - 2 * s)


def sonda(f):
    r = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate:format=duration', '-of', 'json', f],
                                  capture_output=True, text=True).stdout)
    v = next((s for s in r['streams'] if s['codec_type'] == 'video'), None)
    return dict(dur=float(r['format'].get('duration', 5)), audio=any(s['codec_type'] == 'audio' for s in r['streams']),
                w=v and v['width'], h=v and v['height'], fps=v and eval(v['r_frame_rate']))


class Projeto:
    def __init__(self):
        self.midia = []; self.faixas = []

    def media(self, caminho, tipo):
        s = sonda(caminho); e = dict(id=uid(), name=os.path.splitext(os.path.basename(caminho))[0], type=tipo, hasAudio=s['audio'] if tipo == 'video' else False,
                                     duration=5 if tipo == 'image' else s['dur'], source=dict(external=dict(absolutePath=os.path.abspath(caminho))))
        if tipo in ('video', 'image'): e.update(sourceWidth=s['w'], sourceHeight=s['h'])
        if tipo == 'video': e['sourceFPS'] = round(s['fps'])
        self.midia.append(e); return e

    def faixa(self, nome, tipo):
        f = dict(id=uid(), name=nome, type=tipo, syncLocked=True, muted=False, hidden=False, displayHeight=44, clips=[]); self.faixas.append(f); return f

    def clipe(self, faixa, m, ini, dur, trim=0, escala=1.0, cy=0.5, vol_db=0.0, kf=None, tipo=None, link=None):
        tipo = tipo or m['type']
        total = int(round(m['duration'] * FPS))
        c = dict(id=uid(), mediaRef=m['id'], mediaType=tipo, sourceClipType=m['type'], startFrame=int(ini), durationFrames=int(dur),
                 trimStartFrame=int(trim), trimEndFrame=max(0, total - int(trim) - int(dur)) if m['type'] != 'image' else 0,
                 transform=dict(centerX=0.5, centerY=cy, width=escala, height=escala, rotation=0, rotationX=0, rotationY=0, flipHorizontal=False, flipVertical=False),
                 opacity=1, volume=lin(vol_db), fadeInFrames=0, fadeOutFrames=0, fadeInInterpolation='linear', fadeOutInterpolation='linear',
                 edgeSoftness=0, edgeRounding=0, crop=dict(top=0, right=0, bottom=0, left=0))
        if link: c['linkGroupId'] = link
        if kf: c.update(kf)
        faixa['clips'].append(c); return c

    def gravar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        for d in ('media', 'masks', 'chat'): os.makedirs(os.path.join(pasta, d), exist_ok=True)
        tl = dict(id=uid(), name='Reel', width=1080, height=1920, fps=FPS, markers=[], settingsConfigured=True, tracks=self.faixas)
        json.dump(dict(timelines=[tl], viewStates={}, activeTimelineId=tl['id'], openTimelineIds=[tl['id']]), open(os.path.join(pasta, 'project.json'), 'w'), ensure_ascii=False)
        json.dump(dict(version=2, folders=[], entries=self.midia), open(os.path.join(pasta, 'media.json'), 'w'), ensure_ascii=False)


def janela(cam_path, rosto, trim, dur, destino):
    """A Marilia numa janelinha retangular de cantos arredondados (como a câmera dupla do iPhone), 3:4, com sombra leve,
    já na posição do quadro (ProRes 4444 com transparência). Recorte de cabeça e ombros: 2 x 2,67 larguras do rosto."""
    import numpy as np
    w = float(np.median([a['w'] for a in rosto]))
    cw, ch = int(round(2.0 * w / 2) * 2), int(round(2.0 * w * 4 / 3 / 2) * 2)
    x0, y0 = 540 - cw // 2, int(max(0, 0.22 * 1920 - 0.3 * w))   # topo da cabeça em 22% no recorte do imagem.py
    W, H, R = JANELA_W, JANELA_W * 4 // 3, JANELA_R; X, Y = JANELA_POS
    m = 30                                                       # margem pra sombra
    # distância até a borda do retângulo arredondado (negativa dentro), com a janela deslocada de (dx, dy) na margem
    dist = lambda dx, dy: (f"(hypot(max(max({R}-(X-{m + dx}),(X-{m + dx})-{W - 1 - R}),0),max(max({R}-(Y-{m + dy}),(Y-{m + dy})-{H - 1 - R}),0))-{R})")
    a_jan = f"255*clip(0.5-{dist(0, 0)},0,1)"
    a_som = f"115*clip(1-{dist(0, 8)}/22,0,1)"                  # sombra leve, 8 px abaixo, some em 22 px
    fc = (f"[0:v]crop={cw}:{ch}:{x0}:{y0},scale={W}:{H},format=yuva444p,pad={W + 2 * m}:{H + 2 * m}:{m}:{m}:color=black,"
          f"geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='max({a_jan},{a_som})',"
          f"pad=1080:1920:{X - m}:{Y - m}:color=black@0")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{trim / FPS:.4f}', '-t', f'{dur / FPS:.4f}', '-i', cam_path, '-vf', fc,
                    '-an', '-r', str(FPS), '-frames:v', str(int(dur)), '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', destino], check=True)


def empurra_kf(base, p0, p1, dur):
    a, b = base * (1 + (EMPURRA - 1) * suave(p0)), base * (1 + (EMPURRA - 1) * suave(p1))
    k = lambda f, v: dict(frame=f, value=dict(a=v, b=v), interpolationOut='smooth')
    kp = lambda f, v: dict(frame=f, value=dict(a=(1 - v) / 2, b=(1 - v) / 2), interpolationOut='smooth')
    return dict(scaleTrack=dict(keyframes=[k(0, a), k(dur - 1, b)]), positionTrack=dict(keyframes=[kp(0, a), kp(dur - 1, b)]))


def textos(m, gancho_tela=False):
    """Entradas prontas pro add_texts do Palmier (uma lista por faixa). Com o gancho digitado (telas/gancho.mov), ele não vai como texto."""
    t_destaque, t_texto = [], []
    g = m.get('gancho')
    if g and not gancho_tela:
        t_texto.append(dict(startFrame=0, endFrame=int(round(g['dur_s'] * FPS)), content='\n'.join(g['linhas']).upper(), animation='popIn',
                            style=dict(ESTILO_DESTAQUE, fontCase='mixed'), transform=dict(x=0.5, y=0.5)))
    for b in m['legendas']:
        t_texto.append(dict(startFrame=int(round(b['ini'] * FPS)), endFrame=int(round(b['fim'] * FPS)), content='\n'.join(b['linhas']),
                            style=ESTILO_LEGENDA, transform=dict(x=0.5, y=Y_LEGENDA)))
    d = m.get('destaque')
    if d:
        t_destaque.append(dict(startFrame=int(round(d['ini'] * FPS)), endFrame=int(round(d['fim'] * FPS)), content=d['texto'], animation='popIn',
                               style=ESTILO_DESTAQUE, transform=dict(x=0.5, y=0.5)))
    return dict(destaque=t_destaque, texto=t_texto)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('pasta'); ap.add_argument('--nome')
    a = ap.parse_args(); ed = os.path.join(a.pasta, '4-edicao')
    m = json.load(open(os.path.join(ed, 'montagem.json'), encoding='utf-8'))
    nome = a.nome or os.path.basename(os.path.normpath(a.pasta))
    P = Projeto()
    f_dest, f_texto, f_jan, f_telas, f_cam = P.faixa('Destaque', 'video'), P.faixa('Texto', 'video'), P.faixa('Janela', 'video'), P.faixa('Telas', 'video'), P.faixa('Câmera', 'video')
    f_voz, f_cliques, f_efeitos, f_cama = P.faixa('Voz', 'audio'), P.faixa('Cliques', 'audio'), P.faixa('Efeitos', 'audio'), P.faixa('Cama', 'audio')
    fala = m['quadros'] - m['fechamento']

    # gancho digitado (Remotion, composição Gancho): tela com transparência no 0:00 e o som das teclas ligado na faixa Cliques
    gancho_mov = os.path.join(ed, 'telas', 'gancho.mov')
    if m.get('gancho') and os.path.exists(gancho_mov):
        mg = P.media(gancho_mov, 'video'); dg = int(round(mg['duration'] * FPS)); lg = uid()
        P.clipe(f_jan, mg, 0, dg, link=lg)   # na faixa Janela (livre no gancho): na faixa Texto o add_texts apagaria
        if mg['hasAudio']: P.clipe(f_cliques, mg, 0, dg, tipo='audio', link=lg, vol_db=-4.0)
    elif m.get('gancho'):
        print('  AVISO: sem telas/gancho.mov, o gancho vai como texto do Palmier (typewriter alinha à esquerda). Renderizar a composição Gancho')

    # telas por cima da câmera (o som delas, os cliques, vai ligado na faixa Cliques)
    cobre = []
    for t in m['telas']:
        mt = P.media(os.path.join(ed, t['arquivo']), 'video'); dur = int(round(mt['duration'] * FPS)); link = uid()
        P.clipe(f_telas, mt, t['quadro'], dur, link=link)
        if mt['hasAudio']: P.clipe(f_cliques, mt, t['quadro'], dur, tipo='audio', link=link)
        cobre.append((t['quadro'], t['quadro'] + dur, t.get('layout', 'dividida')))
    sob_tela = lambda f: next((l for a_, b_, l in cobre if a_ <= f < b_), None)
    div_y = dividida_y(ed)
    rosto = json.load(open(os.path.join(ed, 'rosto.json')))
    for f in os.listdir(os.path.join(ed, 'imagem')):
        if f.startswith(('janela-', 'circulo-')): os.remove(os.path.join(ed, 'imagem', f))

    # câmera: um clipe por trecho, partido onde uma tela começa ou termina
    cam = P.media(os.path.join(ed, 'imagem', 'camera-edicao.mp4'), 'video')
    pedacos_janela = []
    grupo = {}   # trecho -> linkGroupId: câmera e voz do mesmo trecho andam juntas no Palmier
    for t in m['trechos']:
        o, n = t['out_f0'], t['n']; base = ESCALA.get(t['plano'].split()[0], 1.0); g = grupo[t['num']] = uid()
        cortes = sorted({o, o + n} | {x for ab in cobre for x in ab[:2] if o < x < o + n})
        for s0, s1 in zip(cortes, cortes[1:]):
            trim = int(round(t['src_t0'] * FPS)) + (s0 - o)
            layout = sob_tela(s0)
            if layout == 'cheia':
                continue                                  # tela cheia: voz em off, sem câmera
            if layout == 'janela':
                arq = os.path.join(ed, 'imagem', f'janela-{s0}.mov')
                janela(cam['source']['external']['absolutePath'], rosto, trim, s1 - s0, arq)
                pedacos_janela.append((s0, s1, arq))
                continue
            if layout:
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, cy=div_y, link=g)
            elif 'empurra' in t['plano']:
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, kf=empurra_kf(base, (s0 - o) / max(n - 1, 1), (s1 - 1 - o) / max(n - 1, 1), s1 - s0), link=g)
            else:
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, escala=base, link=g)

    # janela: um arquivo só por tela (o Palmier some com o quadro inteiro quando um clipe com transparência começa no meio de outro)
    for a_, b_, l in cobre:
        if l != 'janela': continue
        ps = sorted(p_ for p_ in pedacos_janela if a_ <= p_[0] < b_)
        if not ps: continue
        lista = os.path.join(ed, 'imagem', f'janela-{a_}.txt'); junto = os.path.join(ed, 'imagem', f'janela-tela-{a_}.mov')
        open(lista, 'w').write(''.join(f"file '{p_[2]}'\n" for p_ in ps))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lista, '-c', 'copy', junto], check=True)
        for p_ in ps: os.remove(p_[2])
        os.remove(lista)
        P.clipe(f_jan, P.media(junto, 'video'), ps[0][0], ps[-1][1] - ps[0][0])

    # fechamento: último quadro congelado + a marca
    ult = m['trechos'][-1]
    # vídeo de 4 s do mesmo quadro, codificado igual à câmera: se fosse PNG, o Palmier mostra a cor mais quente e o fechamento pula
    parado = os.path.join(ed, 'imagem', 'quadro-final.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{ult['src_t0'] + (ult['n'] - 1) / FPS:.4f}", '-i', cam['source']['external']['absolutePath'],
                    '-vf', f"trim=end_frame=1,loop=loop={m['fechamento'] - 1}:size=1:start=0,setpts=N/{FPS}/TB", '-r', str(FPS), '-an',
                    '-c:v', 'libx264', '-crf', '12', '-g', '1', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', parado], check=True)
    P.clipe(f_cam, P.media(parado, 'video'), fala, m['fechamento'], escala=ESCALA.get(ult['plano'].split()[0], 1.0))
    marca = P.media(os.path.join(KIT, 'fechamento', 'fechamento-marca.mov'), 'video')
    P.clipe(f_telas, marca, fala, m['fechamento'])

    # voz e cama
    # voz: um pedaço por trecho, apontando pro take limpo inteiro (com sobra antes e depois), ligado à câmera do trecho.
    # Puxar um corte no Palmier mexe imagem e voz juntas. Fade de 1 quadro nas bordas, como os 30 ms do montagem.wav
    voz = P.media(os.path.join(ed, m.get('voz', 'audio/D-eq9.wav')), 'audio')
    if 'limpo' not in voz['name']: print('  AVISO: voz sem a limpeza do falhas_mic.py (rodar audio/falhas_mic.py e o montar.py de novo)')
    for t in m['trechos']:
        c = P.clipe(f_voz, voz, t['out_f0'], t['n'], trim=int(round(t['src_t0'] * FPS)), link=grupo[t['num']])
        c.update(fadeInFrames=1, fadeOutFrames=1)
    P.clipe(f_cama, P.media(os.path.join(ed, 'audio', 'cama.wav'), 'audio'), 0, m['quadros'])

    # efeitos
    if m.get('sfx') is not None:
        # a lista do reel (receita da família): tipo + trecho (+ palavra em que cai); subida sem trecho cai na virada
        def quadro_de(e):
            if e.get('palavra'):
                w = next(x for x in m['palavras'] if x['trecho'] == e['trecho'] and x['t'].strip('.,:;?!…“”').lower() == e['palavra'].lower())
                return int(round(w['ini'] * FPS))
            if e.get('trecho'): return next(t['out_f0'] for t in m['trechos'] if t['num'] == e['trecho'])
            return m['virada'] if e['tipo'] == 'subida' else 0
        eventos = sorted((e['tipo'], quadro_de(e)) for e in m['sfx'])
        eventos.sort(key=lambda e: e[1])
        for (_, q0), (n1, q1) in zip(eventos, eventos[1:]):
            if q1 - q0 < 3 * FPS: print(f'  AVISO: efeito {n1} a menos de 3 s do anterior ({(q1 - q0) / FPS:.1f} s)')
    else:
        eventos = [('impacto', 0)]
        if m['telas']: eventos.append(('whoosh', m['telas'][0]['quadro']))
        if m.get('virada') is not None: eventos.append(('subida', m['virada']))
        if m.get('destaque'): eventos.append(('pop', int(round(m['destaque']['ini'] * FPS))))
    for nome_sfx, quadro in eventos:
        arq, vol, antes = SFX[nome_sfx]; ms = P.media(os.path.join(KIT, arq), 'audio')
        P.clipe(f_efeitos, ms, max(0, quadro - antes), int(round(ms['duration'] * FPS)), vol_db=vol)

    destino = os.path.join(ed, nome + '.palmier')
    P.gravar(destino)
    json.dump(textos(m, os.path.exists(gancho_mov)), open(os.path.join(ed, 'palmier-textos.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'palmier: {destino}\n  textos pra aplicar: {os.path.join(ed, "palmier-textos.json")}')


if __name__ == '__main__':
    main()
