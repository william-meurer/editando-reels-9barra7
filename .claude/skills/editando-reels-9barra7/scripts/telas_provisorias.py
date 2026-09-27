#!/usr/bin/env python3
"""Telas provisórias (placeholder) quando o material ainda não chegou em 2-arquivos/.
Cada tela do edicao.json com "ate_trecho" e "paineis" vira um ProRes 4444 no tamanho e no tempo da definitiva
(composição Placeholder do Remotion, _montagem/src/Telas.tsx): metade de cima com o que falta e o nome do arquivo esperado,
o painel seguinte entra empurrando. Tela: layout (dividida | cheia | janela). Painel: trecho, palavra (opcional, entra nela), titulo, arquivo, obs, entrada (empurra | cortina | corte), movimento (zoom), formato (rótulo). Grava também telas.md.
Depois, a tela definitiva é renderizada com o mesmo nome e o editável não muda.
Uso: telas_provisorias.py "<pasta do reel>"   (depois do montar.py)"""
import json,sys,os,subprocess,re,unicodedata
AQUI=os.path.dirname(os.path.abspath(__file__))
REM=os.path.normpath(os.path.join(AQUI,'..','..','..','..','Produção','_montagem'))
def n(t): return re.sub(r'[^a-z0-9]','',''.join(c for c in unicodedata.normalize('NFD',t.lower()) if unicodedata.category(c)!='Mn'))
pasta=os.path.abspath(sys.argv[1]); r=os.path.basename(pasta); ed=pasta+'/4-edicao'
e=json.load(open(ed+'/edicao.json')); m=json.load(open(ed+'/montagem.json'))
T={t['num']:t for t in m['trechos']}
md=[f"# Telas do reel {r}\n","Todas provisórias (placeholder): o material ainda não chegou em `2-arquivos/`. Cada uma já tem o tamanho e o tempo da definitiva; é só renderizar a real com o mesmo nome.\n","| Tela | Trechos | Tempo no reel | Painéis (o que falta) |","|---|---|---|---|"]
os.makedirs(ed+'/telas',exist_ok=True)
for tl in e['telas']:
    a=T[tl['trecho']]['out_f0']; b=T[tl['ate_trecho']]['out_f0']+T[tl['ate_trecho']]['n']
    pain=[]
    for p in tl['paineis']:
        q=T[p['trecho']]['out_f0']-a
        if p.get('palavra'):
            ws=[w for w in m['palavras'] if w['trecho']==p['trecho'] and n(w['t'])==n(p['palavra'])]
            assert ws, (p,r); q=int(round(ws[0]['ini']*30))-a
        pain.append(dict(quadro=max(q,0),titulo=p['titulo'],arquivo=p['arquivo'],**{k:p[k] for k in ('obs','entrada','movimento','formato') if p.get(k)}))
    props=dict(duracao=b-a,paineis=pain,area='metade' if tl.get('layout','dividida')=='dividida' else 'cheia'); pf=os.path.join(ed,".placeholder-props.json")
    json.dump(props,open(pf,'w'),ensure_ascii=False)
    out=ed+'/'+tl['arquivo']
    res=subprocess.run(['npx','remotion','render','Placeholder',out,'--props='+pf,'--codec','prores','--prores-profile','4444','--pixel-format','yuva444p10le','--image-format','png','--log','error'],cwd=REM,capture_output=True,text=True)
    os.remove(pf)
    if res.returncode: print(res.stderr[-800:]); sys.exit(1)
    f=lambda q: f"{q//30//60}:{q/30%60:05.2f}"
    md.append(f"| `{tl['arquivo']}` | {tl['trecho']}-{tl['ate_trecho']} | {f(a)} a {f(b)} ({(b-a)/30:.1f} s) | "+' · '.join(f"{p['titulo']} (`{p['arquivo']}`{', '+p['obs'] if p.get('obs') else ''})" for p in pain)+" |")
    print(r[:2],tl['arquivo'],b-a,'quadros', [p['quadro'] for p in pain])
open(ed+'/telas.md','w').write('\n'.join(md)+'\n')
