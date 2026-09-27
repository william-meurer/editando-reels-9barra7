import React from 'react';
// Telas animadas do reel, renderizadas à parte em ProRes 4444 (com transparência) e colocadas como camada no Palmier.
// Regras: .claude/skills/editando-reels-9barra7/padrao-edicao.md. Tela dividida (26/09): o material ocupa a metade de cima
// (1080x960, sem fundo preto, o que importa abaixo de y 208 por causa da interface do Instagram) e a Marilia aparece
// na metade de baixo (a câmera é descida no Palmier). Contorno branco com sombra fina, clique a cada marcação, corte seco.
import {AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, Easing} from 'remotion';
import {loadFont} from '@remotion/fonts';

loadFont({family: 'DM Sans', url: staticFile('kit/fonte/DMSans-Bold.ttf'), weight: '700'});
loadFont({family: 'DM Sans', url: staticFile('kit/fonte/DMSans-Medium.ttf'), weight: '500'});

const M = {w: 1080, h: 960}; // metade de cima

// cx/cy/rx/ry em pixels da imagem original
export type Marca = {quadro: number; img: 0 | 1; cx: number; cy: number; rx: number; ry: number};
export type Erro = {cx: number; cy: number; rx: number; ry: number; filtro: string}; // só pro provisório: simula o tom errado
export type Comparacao = {
	imagens: [string, string];
	tamanho: [number, number]; // largura e altura originais das imagens
	entraSegunda: number; // quadro em que a segunda imagem entra, empurrando a primeira
	marcas: Marca[];
	duracao: number;
	erroSegunda?: Erro;
	rotulos?: Rotulo[];
};
// selo curto preso na imagem (padrão do selo ANTES/DEPOIS: DM Sans bold, caixa alta, texto preto sobre roxo ou verde)
export type Rotulo = {quadro: number; img: 0 | 1; x: number; y: number; texto: string; cor: string};

const Selo: React.FC<{r: Rotulo; s: number}> = ({r, s}) => {
	const k = useCurrentFrame();
	const a = interpolate(k, [0, 5], [0.8, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.back(2))});
	return (
		<div style={{position: 'absolute', left: r.x, top: r.y, transform: `translate(-50%, -50%) scale(${a / s})`, background: r.cor, color: '#000',
			fontFamily: 'DM Sans', fontWeight: 700, fontSize: 36, letterSpacing: '0.02em', textTransform: 'uppercase', padding: '10px 22px',
			borderRadius: 999, whiteSpace: 'nowrap', opacity: interpolate(k, [0, 2], [0, 1], {extrapolateRight: 'clamp'})}}>{r.texto}</div>
	);
};

// contorno desenhado em 8 quadros, depois segura
const Contorno: React.FC<{m: Marca; w: number; h: number; s: number}> = ({m, w, h, s}) => {
	const k = useCurrentFrame();
	const p = interpolate(k, [0, 8], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const perim = Math.PI * (3 * (m.rx + m.ry) - Math.sqrt((3 * m.rx + m.ry) * (m.rx + 3 * m.ry)));
	return (
		<svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
			<ellipse cx={m.cx} cy={m.cy} rx={m.rx} ry={m.ry} fill="none" stroke="#fff" strokeWidth={8.5 / s}
				strokeDasharray={perim} strokeDashoffset={perim * (1 - p)} strokeLinecap="round"
				style={{filter: `drop-shadow(0 ${1.2 / s}px ${2.4 / s}px rgba(0,0,0,.55))`}} />
		</svg>
	);
};

// imagem cobrindo a metade de cima (corta as laterais), com as marcas presas nela
const Imagem: React.FC<{src: string; tam: [number, number]; empurra: number; i: 0 | 1; marcas: Marca[]; erro?: Erro; rotulos?: Rotulo[]}> = ({src, tam, empurra, i, marcas, erro, rotulos = []}) => {
	const [w, h] = tam;
	const s = Math.max(M.w / w, M.h / h);
	return (
		<div style={{position: 'absolute', left: (M.w - w) / 2, top: (M.h - h) / 2, width: w, height: h,
			transform: `scale(${s * empurra})`, transformOrigin: `${w / 2}px ${h / 2}px`}}>
			<Img src={staticFile(src)} style={{width: w, height: h, display: 'block'}} />
			{erro && (
				<Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: 0, width: w, height: h, filter: erro.filtro,
					WebkitMaskImage: `radial-gradient(ellipse ${erro.rx}px ${erro.ry}px at ${erro.cx}px ${erro.cy}px, #000 70%, transparent 100%)`}} />
			)}
			{marcas.filter((m) => m.img === i).map((m, j) => (
				<Sequence key={j} from={m.quadro} layout="none">
					<Contorno m={m} w={w} h={h} s={s * empurra} />
					<Audio src={staticFile('kit/sfx/clique.wav')} volume={0.5} />
				</Sequence>
			))}
			{rotulos.filter((r) => r.img === i).map((r, j) => (
				<Sequence key={`r${j}`} from={r.quadro} layout="none"><Selo r={r} s={s * empurra} /></Sequence>
			))}
		</div>
	);
};

export const TelaComparacao: React.FC<Comparacao> = (c) => {
	const k = useCurrentFrame();
	// a segunda entra empurrando a primeira pra esquerda em 8 quadros
	const t = interpolate(k, [c.entraSegunda, c.entraSegunda + 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
	// entra já em movimento: aproximação lenta de 4% na cena toda
	const empurra = interpolate(k, [0, c.duracao], [1, 1.04]);
	return (
		<AbsoluteFill>
			<div style={{position: 'absolute', left: 0, top: 0, width: M.w, height: M.h, overflow: 'hidden'}}>
				<div style={{position: 'absolute', inset: 0, overflow: 'hidden', transform: `translateX(${-t * M.w}px)`}}>
					<Imagem src={c.imagens[0]} tam={c.tamanho} empurra={empurra} i={0} marcas={c.marcas} rotulos={c.rotulos} />
				</div>
				{k >= c.entraSegunda && (
					<div style={{position: 'absolute', inset: 0, overflow: 'hidden', transform: `translateX(${(1 - t) * M.w}px)`}}>
						<Imagem src={c.imagens[1]} tam={c.tamanho} empurra={empurra} i={1} marcas={c.marcas} erro={c.erroSegunda} rotulos={c.rotulos} />
					</div>
				)}
			</div>
		</AbsoluteFill>
	);
};

// reel 06, cena 3 (telas.md): "madeira" 11,9 s · "primeira imagem" 13,5 · "segunda" 15,6 · "percebe" 17,4. Cena começa no quadro 349 (11,63 s).
// Imagens definitivas (2-arquivos): render 1 = "imagem 1.png"; render 2 com o tom errado = "errado.png". Recortadas pra metade de cima em _recortes/.
export const cena3Reel06: Comparacao = {
	imagens: ['arquivos/F5-01/_recortes/render-1.jpg', 'arquivos/F5-01/_recortes/render-2-errado.jpg'],
	tamanho: [2160, 1920],
	entraSegunda: 119,
	marcas: [
		{quadro: 8, img: 0, cx: 700, cy: 610, rx: 520, ry: 150},
		{quadro: 127, img: 1, cx: 1080, cy: 640, rx: 560, ry: 170},
	],
	duracao: 195,
	// o erro fica explícito: selo roxo (cor do ANTES) logo abaixo do círculo
	rotulos: [{quadro: 131, img: 1, x: 1080, y: 880, texto: 'o tom mudou', cor: '#A4A1F3'}],
};

// reel 06, cobertura do trecho 0:21,8 a 0:28,2 (quadros 655 a 847): "os materiais" (687) madeira e concreto · "a iluminação" (715) luz.
// Uma imagem só (render 1): a segunda nunca entra.
export const materiaisReel06: Comparacao = {
	imagens: ['arquivos/F5-01/_recortes/render-1.jpg', 'arquivos/F5-01/_recortes/render-1.jpg'],
	tamanho: [2160, 1920],
	entraSegunda: 100000,
	marcas: [
		{quadro: 32, img: 0, cx: 700, cy: 610, rx: 520, ry: 150},
		{quadro: 44, img: 0, cx: 1660, cy: 700, rx: 210, ry: 210},
		{quadro: 68, img: 0, cx: 520, cy: 1180, rx: 430, ry: 220},
	],
	duracao: 192,
};

// Tela provisória quando o material ainda não chegou (2-arquivos vazio): no tamanho e no tempo da tela definitiva,
// diz o que falta, o nome do arquivo esperado e o formato (padrao-edicao.md, cardápio). Troca-se pelo render real sem mexer na montagem.
// area: metade (tela dividida) ou cheia (cheia, círculo, apoio, número). entrada: empurra | cortina | corte. movimento: zoom.
export type Painel = {quadro: number; titulo: string; arquivo: string; obs?: string; entrada?: 'empurra' | 'cortina' | 'corte'; movimento?: 'zoom'; formato?: string};
export type Placeholder = {duracao: number; paineis: Painel[]; area?: 'metade' | 'cheia'};

const PainelVazio: React.FC<{p: Painel; cheia: boolean; i: number}> = ({p, cheia, i}) => {
	const k = useCurrentFrame();
	const z = p.movimento === 'zoom' ? interpolate(k, [p.quadro, p.quadro + 150], [1, 1.12], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
	return (
		<div style={{position: 'absolute', inset: 0, background: i % 2 ? '#232323' : '#1b1b1b', overflow: 'hidden'}}>
			<div style={{position: 'absolute', left: 28, right: 28, top: 216, bottom: cheia ? 1920 - 1500 : 28, border: '3px dashed rgba(255,255,255,.45)', borderRadius: 18,
				display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 26, padding: '0 64px', textAlign: 'center',
				transform: `scale(${z})`}}>
				<div style={{fontFamily: 'DM Sans', fontWeight: 700, fontSize: 30, letterSpacing: '0.08em', color: '#1b1b1b', background: '#fff',
					padding: '8px 20px', borderRadius: 999}}>FALTA MATERIAL{p.formato ? ` · ${p.formato.toUpperCase()}` : ''}</div>
				<div style={{fontFamily: 'DM Sans', fontWeight: 700, fontSize: 54, lineHeight: 1.12, color: '#fff'}}>{p.titulo}</div>
				{p.obs && <div style={{fontFamily: 'DM Sans', fontWeight: 500, fontSize: 32, lineHeight: 1.3, color: 'rgba(255,255,255,.75)'}}>{p.obs}</div>}
				<div style={{fontFamily: 'DM Sans', fontWeight: 500, fontSize: 28, color: 'rgba(255,255,255,.5)'}}>2-arquivos/{p.arquivo}</div>
			</div>
		</div>
	);
};

export const TelaPlaceholder: React.FC<Placeholder> = ({paineis, area = 'metade'}) => {
	const k = useCurrentFrame();
	const cheia = area === 'cheia';
	const W = M.w, Hh = cheia ? 1920 : M.h;
	const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
	return (
		<AbsoluteFill>
			<div style={{position: 'absolute', left: 0, top: 0, width: W, height: Hh, overflow: 'hidden'}}>
				{paineis.map((p, i) => {
					const prox = paineis[i + 1];
					const fimProx = prox ? prox.quadro + (prox.entrada === 'cortina' ? 20 : prox.entrada === 'corte' ? 0 : 8) : Infinity;
					if (k < p.quadro || k >= fimProx) return null;
					const e = p.entrada ?? 'empurra';
					let estilo: React.CSSProperties = {position: 'absolute', inset: 0};
					if (i > 0 && e === 'empurra') {
						const t = interpolate(k, [p.quadro, p.quadro + 8], [0, 1], ease);
						estilo.transform = `translateX(${(1 - t) * W}px)`;
					} else if (i > 0 && e === 'cortina') {
						const t = interpolate(k, [p.quadro, p.quadro + 20], [0, 100], ease);
						estilo.clipPath = `inset(0 ${100 - t}% 0 0)`;
					}
					if (prox && (prox.entrada ?? 'empurra') === 'empurra' && k >= prox.quadro) {
						const t = interpolate(k, [prox.quadro, prox.quadro + 8], [0, 1], ease);
						estilo.transform = `translateX(${-t * W}px)`;
					}
					return <React.Fragment key={i}><div style={{...estilo, zIndex: i}}><PainelVazio p={p} cheia={cheia} i={i} /></div>
						{i > 0 && e === 'cortina' && k < p.quadro + 20 && <div style={{position: 'absolute', top: 0, bottom: 0, width: 6, marginLeft: -3, background: '#fff', zIndex: 99,
							left: `${interpolate(k, [p.quadro, p.quadro + 20], [0, 100], ease)}%`}} />}</React.Fragment>;
				})}
			</div>
		</AbsoluteFill>
	);
};
