#!/usr/bin/env python3
"""Monta o projeto do reel no Palmier Pro a partir do montagem.json (escreve o pacote .palmier direto).

Faixas, de cima pra baixo (padrao-edicao.md):
  Destaque · Texto (gancho e legendas) · Telas (ProRes 4444 com transparência, e o fechamento) · Câmera
  Voz · Cliques (o som que vem dentro das telas) · Efeitos · Cama
- câmera: a imagem de edição (imagem.py) na escala de cada plano (P1 1, P2 1,10, P3 1,18, ÊNFASE 1,30; empurra até +20%);
  embaixo de uma tela, desce pra metade de baixo (tela dividida: centerY 0,695, escala 1)
- fechamento: último quadro congelado (vídeo parado, não PNG) na escala do último plano + a marca (kit/fechamento), 4 s
- efeitos: grave no 0:00, whoosh na entrada da primeira tela, subida que resolve no corte da virada, pop no destaque
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
# efeito: arquivo do kit, volume em dB, e quantos quadros antes do evento ele começa (o ataque cai no evento)
SFX = {
    'impacto': ('sfx/impacto-gancho (grave + estalo).wav', -9.0, 0),
    'whoosh': ('sfx/whoosh (universfield, Pixabay) hp100.wav', -1.5, 17),
    'subida': ('sfx/riser-hit (audiopapkin, Pixabay).mp3', -9.5, 51),
    'pop': ('sfx/pop (DRAGON-STUDIO, Pixabay).mp3', -16.0, 5),
}
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


def empurra_kf(base, p0, p1, dur):
    a, b = base * (1 + (EMPURRA - 1) * suave(p0)), base * (1 + (EMPURRA - 1) * suave(p1))
    k = lambda f, v: dict(frame=f, value=dict(a=v, b=v), interpolationOut='smooth')
    kp = lambda f, v: dict(frame=f, value=dict(a=(1 - v) / 2, b=(1 - v) / 2), interpolationOut='smooth')
    return dict(scaleTrack=dict(keyframes=[k(0, a), k(dur - 1, b)]), positionTrack=dict(keyframes=[kp(0, a), kp(dur - 1, b)]))


def textos(m):
    """Entradas prontas pro add_texts do Palmier (uma lista por faixa)."""
    t_destaque, t_texto = [], []
    g = m.get('gancho')
    if g:
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
    f_dest, f_texto, f_telas, f_cam = P.faixa('Destaque', 'video'), P.faixa('Texto', 'video'), P.faixa('Telas', 'video'), P.faixa('Câmera', 'video')
    f_voz, f_cliques, f_efeitos, f_cama = P.faixa('Voz', 'audio'), P.faixa('Cliques', 'audio'), P.faixa('Efeitos', 'audio'), P.faixa('Cama', 'audio')
    fala = m['quadros'] - m['fechamento']

    # telas por cima da câmera (o som delas, os cliques, vai ligado na faixa Cliques)
    cobre = []
    for t in m['telas']:
        mt = P.media(os.path.join(ed, t['arquivo']), 'video'); dur = int(round(mt['duration'] * FPS)); link = uid()
        P.clipe(f_telas, mt, t['quadro'], dur, link=link)
        if mt['hasAudio']: P.clipe(f_cliques, mt, t['quadro'], dur, tipo='audio', link=link)
        cobre.append((t['quadro'], t['quadro'] + dur))
    sob_tela = lambda f: any(a_ <= f < b_ for a_, b_ in cobre)

    # câmera: um clipe por trecho, partido onde uma tela começa ou termina
    cam = P.media(os.path.join(ed, 'imagem', 'camera-edicao.mp4'), 'video')
    for t in m['trechos']:
        o, n = t['out_f0'], t['n']; base = ESCALA.get(t['plano'].split()[0], 1.0)
        cortes = sorted({o, o + n} | {x for ab in cobre for x in ab if o < x < o + n})
        for s0, s1 in zip(cortes, cortes[1:]):
            trim = int(round(t['src_t0'] * FPS)) + (s0 - o)
            if sob_tela(s0):
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, cy=DIVIDIDA_Y)
            elif 'empurra' in t['plano']:
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, kf=empurra_kf(base, (s0 - o) / max(n - 1, 1), (s1 - 1 - o) / max(n - 1, 1), s1 - s0))
            else:
                P.clipe(f_cam, cam, s0, s1 - s0, trim=trim, escala=base)

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
    P.clipe(f_voz, P.media(os.path.join(ed, 'audio', 'montagem-limpa.wav'), 'audio'), 0, m['quadros'])
    P.clipe(f_cama, P.media(os.path.join(ed, 'audio', 'cama.wav'), 'audio'), 0, m['quadros'])

    # efeitos
    eventos = [('impacto', 0)]
    if m['telas']: eventos.append(('whoosh', m['telas'][0]['quadro']))
    if m.get('virada') is not None: eventos.append(('subida', m['virada']))
    if m.get('destaque'): eventos.append(('pop', int(round(m['destaque']['ini'] * FPS))))
    for nome_sfx, quadro in eventos:
        arq, vol, antes = SFX[nome_sfx]; ms = P.media(os.path.join(KIT, arq), 'audio')
        P.clipe(f_efeitos, ms, max(0, quadro - antes), int(round(ms['duration'] * FPS)), vol_db=vol)

    destino = os.path.join(ed, nome + '.palmier')
    P.gravar(destino)
    json.dump(textos(m), open(os.path.join(ed, 'palmier-textos.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'palmier: {destino}\n  textos pra aplicar: {os.path.join(ed, "palmier-textos.json")}')


if __name__ == '__main__':
    main()
