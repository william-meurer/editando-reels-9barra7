#!/usr/bin/env python3
"""Aplica os textos do reel no Palmier sem colar nada na conversa: abre o projeto numa sessão MCP própria (HTTP local),
aplica 4-edicao/palmier-textos.json (texto e destaque), nomeia as faixas Texto e Destaque, apaga as faixas de texto vazias
e, se pedir, exporta. Precisa do Palmier aberto.
Uso: palmier_textos.py "<pasta do reel>" [--exportar <saida.mp4>] [--so-exportar <saida.mp4>]"""
import glob, json, os, sys, urllib.request

U = 'http://127.0.0.1:19789/mcp'
SID = None


def rpc(method, params=None, notif=False):
    global SID
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None: body["params"] = params
    if not notif: body["id"] = 1
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if SID: h['Mcp-Session-Id'] = SID
    r = urllib.request.urlopen(urllib.request.Request(U, json.dumps(body).encode(), h), timeout=900)
    SID = SID or r.headers.get('Mcp-Session-Id')
    for l in r.read().decode().splitlines():
        if l.startswith('data: {'): return json.loads(l[6:])


def tool(name, args):
    r = rpc('tools/call', {'name': name, 'arguments': args})
    txt = r['result']['content'][0]['text']
    if r['result'].get('isError'): raise SystemExit(f'{name}: {txt[:500]}')
    return txt


if __name__ == '__main__':
    pasta = sys.argv[1]; ed = os.path.join(pasta, '4-edicao')
    saida = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a in ('--exportar', '--so-exportar')), None)
    proj = glob.glob(os.path.join(ed, '*.palmier'))[0]
    rpc('initialize', {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "palmier_textos", "version": "1"}})
    rpc('notifications/initialized', notif=True)
    tool('manage_project', {'action': 'open', 'path': proj})
    if '--so-exportar' not in sys.argv:
        t = json.load(open(os.path.join(ed, 'palmier-textos.json')))
        tool('add_texts', {'entries': t['texto']})
        if t.get('destaque'): tool('add_texts', {'entries': t['destaque']})
        tl = json.loads(tool('get_timeline', {}))
        vid = [x for x in tl['tracks'] if x.get('type') == 'video']
        nomes = ['Destaque', 'Texto'] if t.get('destaque') else ['Texto']
        tool('manage_tracks', {'set': [{'trackId': v['trackId'], 'name': n} for v, n in zip(vid, nomes)]})
        tl = json.loads(tool('get_timeline', {}))
        vazias = [{'trackId': x['trackId']} for x in tl['tracks'] if x.get('name') in ('Texto', 'Destaque') and not x.get('clips')]
        if vazias: tool('manage_tracks', {'remove': vazias})
        tl = json.loads(tool('get_timeline', {}))
        print('faixas:', [(x.get('name'), len(x.get('clips', []))) for x in tl['tracks']])
    if saida:
        print(tool('export_project', {'mode': 'video', 'outputPath': os.path.abspath(saida)})[:200])
