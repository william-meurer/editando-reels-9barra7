#!/usr/bin/env python3
"""Pacote do reel pro Premiere (FCP7 XML), seguindo as blindagens da skill de aulas da Marilia:
- sequência na resolução do bruto (2160x3840): 100% = quadro exato; o importador só respeita ESCALA
- a imagem tratada já vem com o look e o quadro deslocado, pra zoom centrado cair certo em todo plano
- cada trecho = vídeo + áudio (wav tratado) LINKADOS, masterclipid compartilhado (sobra de apara)
- legendas, gancho e telas provisórias = PNG na resolução da sequência (still: folga infinita pra aparar)
- fechamento = still do último quadro na mesma escala + camada animada (QuickTime Animation, alfa)
- empurra: keyframes vão no XML, mas o importador ignora; entram depois no .prproj
Gera também legendas.srt e preview-premiere.mp4 montado a partir do mesmo plano do XML.
Uso: premiere_xml.py "<pasta do reel>" """
import json, os, subprocess, sys, urllib.parse
import numpy as np, cv2
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import montar as M

FPS, SW, SH = 30, 2160, 3840
K = SW / M.W                      # 2x: desenho em 1080 -> sequência 4K
ESCALA = {p: 100 * SW / lw for p, (lw, _) in M.PLANOS.items()}   # P1 200%, P2 220%, P3 236%, ÊNFASE 260%

def url(p): return 'file://localhost' + urllib.parse.quote(os.path.abspath(p))

def plano_escala(pl):
    base = ESCALA[pl.split()[0]]
    return (base, base * M.EMPURRA) if 'empurra' in pl else (base, base)

# ---------- camadas em 4K ----------
def png_legenda(linhas, p):
    im = Image.new('RGBA', (SW, SH)); d = ImageDraw.Draw(im); f = M.fonte('DMSans-latin.woff2', int(46 * K), 500)
    y = K * (1482 - (len(linhas) - 1) * 29)
    for l in linhas:
        for dx, dy in ((0, 6), (0, 4), (2, 4), (-2, 4)): d.text((SW / 2 + dx, y + dy), l, font=f, fill=M.SOMBRA, anchor='mm')
        d.text((SW / 2, y), l, font=f, fill=(255, 255, 255, 255), anchor='mm'); y += 58 * K
    im.save(p)

def png_escala(camada_1080, p):
    camada_1080.resize((SW, SH), Image.LANCZOS).save(p)

def main(pasta):
    ed = os.path.join(pasta, '4-edicao'); out = os.path.join(ed, 'premiere'); os.makedirs(out, exist_ok=True)
    m = json.load(open(os.path.join(ed, 'montagem.json'), encoding='utf-8'))
    rot = json.load(open(os.path.join(pasta, '1-roteiro', 'roteiro.json'), encoding='utf-8'))
    cenas = {c['n']: c for c in rot['cenas']}
    vid = os.path.join(out, 'IMG_4827 - imagem tratada.mp4'); aud = os.path.join(out, 'IMG_4827 - audio tratado.wav')
    n_src = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', vid], capture_output=True, text=True).stdout)
    tl = m['trechos']; fala = sum(t['n'] for t in tl); FECH = int(M.FECHAMENTO * FPS); total = fala + FECH

    # ---------- PNGs ----------
    leg = m['legendas']; arq_leg = []
    tmp = os.path.join(ed, '_camadas-preview'); os.makedirs(tmp, exist_ok=True)   # PNGs só pro preview, fora do pacote
    for i, b in enumerate(leg):
        p = os.path.join(tmp, f'legenda {i + 1:02d}.png'); png_legenda(b['linhas'], p); arq_leg.append(p)
    gancho = None
    if cenas.get(1, {}).get('texto_na_tela'):
        gancho = os.path.join(tmp, 'gancho.png'); png_escala(M.camada_gancho(cenas[1]['texto_na_tela']), gancho)
    telas = {}
    for t in tl:
        if t['plano'] == '—' and t['cena'] not in telas:
            c = cenas.get(t['cena'], {}); p = os.path.join(out, f"tela cena {t['cena']} (provisória).png")
            png_escala(M.camada_tela(t['cena'], c.get('visual', ''), c.get('texto_na_tela')), p); telas[t['cena']] = p
    # fechamento: último quadro usado, parado, e a camada animada por cima (alfa)
    ult = tl[-1]; f_ult = ult['src_f0'] + ult['n'] - 1
    still = os.path.join(out, 'fechamento - quadro parado.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', vid, '-vf', f'select=eq(n\\,{f_ult})', '-frames:v', '1', still], check=True)
    anim = os.path.join(out, 'fechamento - marca.mov')
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{SW}x{SH}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'qtrle', '-pix_fmt', 'argb', anim], stdin=subprocess.PIPE)
    for k in range(FECH):
        enc.stdin.write(np.asarray(M.camada_fechamento(k / FPS, arroba=False).resize((SW, SH), Image.LANCZOS)).tobytes())   # @9barra7 vai como texto
    enc.stdin.close(); enc.wait()

    # ---------- XML ----------
    ids = {}
    def arq(p, dur, w, h, audio=False, still=False):
        if p in ids: return f'<file id="{ids[p]}"/>'
        fid = f'f{len(ids) + 1}'; ids[p] = fid; nome = os.path.basename(p)
        if w == 0:
            return (f'<file id="{fid}"><name>{nome}</name><pathurl>{url(p)}</pathurl><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>'
                    f'<duration>{dur}</duration><media><audio><samplecharacteristics><depth>24</depth><samplerate>48000</samplerate>'
                    f'</samplecharacteristics><channelcount>1</channelcount></audio></media></file>')
        st = f'<stillframe>TRUE</stillframe>' if still else ''
        return (f'<file id="{fid}"><name>{nome}</name><pathurl>{url(p)}</pathurl><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>'
                f'<duration>{dur}</duration>{st}<timecode><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate><string>00:00:00:00</string>'
                f'<frame>0</frame><displayformat>NDF</displayformat></timecode><media><video><samplecharacteristics><rate><timebase>{FPS}</timebase>'
                f'<ntsc>FALSE</ntsc></rate><width>{w}</width><height>{h}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video></media></file>')
    def motion(e0, e1, dur):
        esc = (f'<value>{e0:.2f}</value>' if abs(e0 - e1) < 0.01 else
               f'<keyframe><when>0</when><value>{e0:.2f}</value></keyframe><keyframe><when>{max(1, dur - 1)}</when><value>{e1:.2f}</value></keyframe>')
        return ('<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype>'
                '<mediatype>video</mediatype><parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name>'
                f'<valuemin>0</valuemin><valuemax>1000</valuemax>{esc}</parameter><parameter authoringApp="PremierePro"><parameterid>center</parameterid>'
                '<name>Center</name><value><horiz>0</horiz><vert>0</vert></value></parameter></effect></filter>')
    def clip(cid, p, mid, dur_arq, pos, ini, fim, extra='', nome=None, **kw):
        return (f'<clipitem id="{cid}"><masterclipid>{mid}</masterclipid><name>{nome or os.path.basename(p)}</name><enabled>TRUE</enabled>'
                f'<duration>{dur_arq}</duration><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate><start>{pos}</start><end>{pos + fim - ini}</end>'
                f'<in>{ini}</in><out>{fim}</out>{arq(p, dur_arq, **kw)}{extra}</clipitem>')

    v1, a1, v2, v3 = [], [], [], []
    plano_log = []
    for i, t in enumerate(tl):
        e0, e1 = plano_escala(t['plano']) if t['plano'] != '—' else (ESCALA['P1'], ESCALA['P1'])
        ini, fim, pos = t['src_f0'], t['src_f0'] + t['n'], t['out_f0']
        lk = (f'<link><linkclipref>v{i}</linkclipref><mediatype>video</mediatype><trackindex>1</trackindex><clipindex>{i + 1}</clipindex></link>'
              f'<link><linkclipref>a{i}</linkclipref><mediatype>audio</mediatype><trackindex>1</trackindex><clipindex>{i + 1}</clipindex><groupindex>1</groupindex></link>')
        nome = f"{t['num']:02d} · {t['plano']}"
        v1.append(clip(f'v{i}', vid, 'mc-video', n_src, pos, ini, fim, motion(e0, e1, fim - ini) + lk, nome=nome, w=SW, h=SH))
        a1.append(clip(f'a{i}', aud, 'mc-audio', n_src, pos, ini, fim,
                       '<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>' + lk, nome=nome, w=0, h=0))
        plano_log.append((t['num'], t['plano'], e0, e1))
    # fechamento no V1: quadro parado na escala do último trecho
    eu = plano_escala(tl[-1]['plano'])[1]
    v1.append(clip('vfech', still, 'mc-fech', FECH * 10, fala, 0, FECH, motion(eu, eu, FECH), nome='fechamento', w=SW, h=SH, still=True))
    # V2: telas provisórias, juntando trechos seguidos da mesma cena
    grupos = []
    for t in tl:
        if t['plano'] != '—': continue
        if grupos and grupos[-1][0] == t['cena'] and grupos[-1][2] == t['out_f0']: grupos[-1][2] = t['out_f0'] + t['n']
        else: grupos.append([t['cena'], t['out_f0'], t['out_f0'] + t['n']])
    for j, (c, a, b) in enumerate(grupos):
        v2.append(clip(f't{j}', telas[c], f'mc-tela{c}', 3600, a, 0, b - a, nome=f'tela cena {c} (provisória)', w=SW, h=SH, still=True))
    # V3: gancho, legendas e marca do fechamento
    # legenda, gancho e @9barra7 NÃO entram como imagem: vão nos .srt, viram texto editável no Premiere
    v3.append(clip('m0', anim, 'mc-marca', FECH, fala, 0, FECH, nome='fechamento - marca', w=SW, h=SH))

    faixa = lambda cs: f'<track><enabled>TRUE</enabled><locked>FALSE</locked>{"".join(cs)}</track>'
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="5"><sequence id="reel">'
           f'<uuid>9b700000-0000-4000-8000-{abs(hash(pasta)) % 10**12:012d}</uuid><name>{m.get("reel", os.path.basename(pasta))} - montagem</name>'
           f'<duration>{total}</duration><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>'
           f'<timecode><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate><string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
           f'<media><video><format><samplecharacteristics><rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate><width>{SW}</width><height>{SH}</height>'
           '<pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance><colordepth>24</colordepth></samplecharacteristics></format>'
           f'{faixa(v1)}{faixa(v2)}{faixa(v3)}</video><audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>24</depth>'
           f'<samplerate>48000</samplerate></samplecharacteristics></format>{faixa(a1)}</audio></media></sequence></xmeml>\n')
    nome_xml = os.path.join(out, f'{os.path.basename(pasta)} - montagem.xml')
    open(nome_xml, 'w', encoding='utf-8').write(xml)
    import xml.dom.minidom; xml.dom.minidom.parseString(open(nome_xml, encoding='utf-8').read().encode())   # bem formado?

    # ---------- SRT ----------
    def tc(s): h, r = divmod(s, 3600); mi, r = divmod(r, 60); return f'{int(h):02d}:{int(mi):02d}:{int(r):02d},{int(round((r % 1) * 1000)):03d}'
    srt = []
    for i, b in enumerate(leg):
        a = max(b['ini'], 3.0 if gancho else 0)
        if b['fim'] - a >= 0.6: srt.append(f"{len(srt) + 1}\n{tc(a)} --> {tc(b['fim'])}\n" + '\n'.join(b['linhas']) + '\n')
    open(os.path.join(out, 'legendas.srt'), 'w', encoding='utf-8').write('\n'.join(srt))
    # 2ª trilha de legenda: título do início e @9barra7 do fechamento (estilo próprio, centralizado)
    g = []
    if gancho:   # quebra definida aqui, medida na Rules Compressed a 400 px em 75% da largura (o Premiere não requebra)
        from PIL import ImageFont
        fr = ImageFont.truetype(os.path.join(M.KIT, 'fonte', 'RulesCompressed-Black.otf'), 400); ls, cur = [], ''
        for p_ in cenas[1]['texto_na_tela'].upper().split():
            if cur and fr.getlength(cur + ' ' + p_) > 0.75 * SW: ls.append(cur); cur = p_
            else: cur = (cur + ' ' + p_).strip()
        ls.append(cur); g.append(f"1\n{tc(0)} --> {tc(3.0)}\n" + '\n'.join(ls) + "\n")
    g.append(f"{len(g) + 1}\n{tc(fala / FPS + 0.85)} --> {tc(total / FPS)}\n@9barra7\n")
    open(os.path.join(out, 'gancho e fechamento.srt'), 'w', encoding='utf-8').write('\n'.join(g))

    # ---------- preview a partir do mesmo plano (zoom centrado sobre a imagem tratada) ----------
    prev = os.path.join(ed, 'preview-premiere.mp4')
    wav = os.path.join(out, '_prev.wav')
    import soundfile as sf
    x, sr = sf.read(aud); partes = []
    for t in tl: partes.append(x[int(round(t['src_f0'] / FPS * sr)):int(round((t['src_f0'] + t['n']) / FPS * sr))])
    partes.append(np.zeros(FECH * sr // FPS)); sf.write(wav, np.concatenate(partes), sr, subtype='PCM_24')
    camadas = {}
    def lay(p):
        if p not in camadas: camadas[p] = Image.open(p).convert('RGBA').resize((M.W, M.H), Image.LANCZOS)
        return camadas[p]
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{M.W}x{M.H}', '-r', str(FPS), '-i', '-', '-i', wav,
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '320k', '-shortest', prev], stdin=subprocess.PIPE)
    def centro(img, esc):
        lw = SW * 100 / esc; lh = lw * SH / SW; x0 = (SW - lw) / 2; y0 = (SH - lh) / 2; s = M.W / lw
        return cv2.warpAffine(img, np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]]), (M.W, M.H), flags=cv2.INTER_AREA)
    leg_f = [(max(int(round(b['ini'] * FPS)), 90 if gancho else 0), int(round(b['fim'] * FPS)), arq_leg[i]) for i, b in enumerate(leg)]
    leg_f = [x for x in leg_f if x[1] - x[0] >= 18]
    ultimo = None; fb = SW * SH * 3
    for t in tl:
        e0, e1 = plano_escala(t['plano']) if t['plano'] != '—' else (ESCALA['P1'],) * 2
        dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f"{t['src_f0'] / FPS:.5f}", '-i', vid, '-frames:v', str(t['n']), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
        for k in range(t['n']):
            fo = t['out_f0'] + k; b = dec.stdout.read(fb)
            img = np.frombuffer(b, np.uint8).reshape(SH, SW, 3)
            fr = centro(img, e0 + (e1 - e0) * k / max(t['n'] - 1, 1)); ultimo = fr
            cs = []
            if t['plano'] == '—': cs.append(lay(telas[t['cena']]))
            if gancho and fo < 90: cs.append(lay(gancho))
            for a, z, p in leg_f:
                if a <= fo < z: cs.append(lay(p))
            enc.stdin.write(M.compor(fr, cs).tobytes())
        dec.stdout.close(); dec.wait()
    for k in range(FECH): enc.stdin.write(M.compor(ultimo, [M.camada_fechamento(k / FPS)]).tobytes())
    enc.stdin.close(); enc.wait(); os.remove(wav)
    import shutil; shutil.rmtree(tmp)

    print(f'ok: {nome_xml}\n    {len(v1)} clipes em V1, {len(v2)} telas em V2, {len(v3)} camadas em V3, áudio linkado em A1')
    print('escalas:', ', '.join(f'{n}:{p} {a:.0f}%' + (f'>{b:.0f}%' if b != a else '') for n, p, a, b in plano_log))
    print('preview:', prev)

if __name__ == '__main__':
    main(sys.argv[1])
