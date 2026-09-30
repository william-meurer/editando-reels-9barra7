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
// no flutua (fundo transparente) os cartões vão sem sombra: pedido do William, ela bugava e ele prefere limpo
const SemSombra = React.createContext(false);

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
const Contorno: React.FC<{m: Marca; w: number; h: number; s: number; cor?: string}> = ({m, w, h, s, cor = '#fff'}) => {
	const k = useCurrentFrame();
	const p = interpolate(k, [0, 8], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const perim = Math.PI * (3 * (m.rx + m.ry) - Math.sqrt((3 * m.rx + m.ry) * (m.rx + 3 * m.ry)));
	return (
		<svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
			<ellipse cx={m.cx} cy={m.cy} rx={m.rx} ry={m.ry} fill="none" stroke={cor} strokeWidth={8.5 / s}
				strokeDasharray={perim} strokeDashoffset={perim * (1 - p)} strokeLinecap="round"
				style={{filter: cor === '#fff' ? `drop-shadow(0 ${1.2 / s}px ${2.4 / s}px rgba(0,0,0,.55))` : 'none'}} />
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

// Tela com imagens reais, em qualquer formato do cardápio (padrao-edicao.md): metade de cima (dividida) ou tela inteira
// (cheia, janela, cortina, zoom). Cada painel é uma imagem: cobre a área (com foco) ou cabe na área segura (planta);
// zoom lento em direção ao foco; contornos e áreas escurecidas presos no quadro da palavra. Coordenadas em pixels da imagem.
export type MarcaImg = {quadro: number; cx: number; cy: number; rx: number; ry: number};
export type Escurece = {quadro: number; x: number; y: number; w: number; h: number};
export type PainelImg = {src: string; w: number; h: number; quadro: number; entrada?: 'empurra' | 'cortina' | 'corte';
	ajuste?: 'cobre' | 'contem'; foco?: [number, number]; zoom?: [number, number]; marcas?: MarcaImg[]; escurece?: Escurece[]; rotulos?: Rotulo[];
	cartao?: boolean;      // a imagem como um cartão: margem, cantos arredondados e sombra (planta, print), em vez de encostar nas bordas
	contorno?: string;     // cor do contorno: branco (padrão, sobre imagem escura) ou preto sobre planta clara
	desenha?: Desenho;
	numeros?: Numero[]};  // texto grande na tela (tela de número), em coordenadas da tela, não da imagem
// número grande sobre a imagem (reel 03: "3 LINHAS · 3 PÁGINAS"): DM Sans bold branco, entra como a palavra do gancho (sem som: o pop da fala vem do sfx)
export type Numero = {quadro: number; texto: string; y: number; tamanho?: number};
// traço da própria Marilia se desenhando sobre a versão limpa da imagem (reel 02: a seta na planta). src = PNG do mesmo
// tamanho com transparência fora do traço; ele aparece de y "de" até y "ate" (px da imagem) em "dur" quadros, com um clique
export type Desenho = {src: string; quadro: number; dur: number; de: number; ate: number};
// acende: o trecho fica apagado até esse quadro (blocos que surgem um a um, na palavra da fala)
export type TrechoPrompt = {texto: string; rotulo?: string; marca?: number; cor?: string; acende?: number};   // marca: quadro em que o marca-texto passa (verde, ou cor: vermelho pro que fica de fora)
// corrido: todos os trechos num parágrafo só (prompt em texto corrido, reel 03); rola: [quadro, deslocamento px] do texto subindo;
// fonte: tamanho em px (36 por padrão)
export type PainelPrompt = {tipo: 'promptador'; quadro: number; entrada?: 'empurra' | 'cortina' | 'corte'; titulo?: string; trechos: TrechoPrompt[];
	corrido?: boolean; rola?: [number, number][]; fonte?: number;
	encolhe?: [number, number, number]};   // [quadro, quadro final, escala]: o texto inteiro encolhe numa coluna ilegível que mostra o tamanho (o prompt não se revela)
// várias imagens juntas na mesma tela (ex.: a planta em cima e a imagem gerada embaixo), cada uma na sua caixa [x, y, w, h];
// entra: quadro em que a imagem sobe pra caixa (sem ele, já está lá quando o painel entra)
export type ItemGrupo = PainelImg & {caixa: [number, number, number, number]; entra?: number};
export type PainelGrupo = {tipo: 'grupo'; quadro: number; entrada?: 'empurra' | 'cortina' | 'corte'; itens: ItemGrupo[]};
// fundo: transparente (padrão: os cartões flutuam sobre a câmera desfocada, formato flutua; o William não quer fundo preto em tela nenhuma) ou preto
export type TelaImg = {duracao: number; area?: 'metade' | 'cheia'; fundo?: 'preto' | 'transparente'; paineis: (PainelImg | PainelPrompt | PainelGrupo)[]};

// resposta do promptador (IA Studio, promptadores.9barra7.com): mesmo fundo, fonte e cor do site, ampliada pra ser lida no celular
const PainelPromptador: React.FC<{p: PainelPrompt; H: number; cartao?: boolean}> = ({p, H, cartao}) => {
	const k = useCurrentFrame();
	const fonte = p.fonte ?? 36;
	const cl = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
	const rolar = (q: number) => p.rola && p.rola.length > 1 ? interpolate(q, p.rola.map((r) => r[0]), p.rola.map((r) => r[1]), {...cl, easing: Easing.inOut(Easing.quad)}) : 0;
	const e = p.encolhe ? interpolate(k, [p.encolhe[0], p.encolhe[1]], [0, 1], {...cl, easing: Easing.inOut(Easing.cubic)}) : 0;
	const escala = p.encolhe ? 1 + (p.encolhe[2] - 1) * e : 1;
	const y = rolar(k) * (1 - e);
	// desfoque de movimento: rolando rápido ou encolhendo, não dá pra ler
	const borrao = Math.max(Math.min(6, Math.abs(rolar(k) - rolar(k - 1)) / 6), p.rola && p.encolhe && k < p.encolhe[1] ? 3 : 0);
	const trecho = (t: TrechoPrompt, j: number) => {
		const a = t.marca === undefined ? 0 : interpolate(k, [t.marca, t.marca + 10], [0, 100], {...cl, easing: Easing.out(Easing.cubic)});
		const luz = t.acende === undefined ? 1 : interpolate(k, [t.acende, t.acende + 6], [0.22, 1], cl);
		return (
			<span key={j} style={{backgroundImage: `linear-gradient(${t.cor ?? '#B3FF9F'}, ${t.cor ?? '#B3FF9F'})`, backgroundRepeat: 'no-repeat', backgroundSize: `${a}% 100%`,
				boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone', padding: '0 4px', opacity: luz}}>
				{t.rotulo && <span style={{fontWeight: 700}}>{t.rotulo} </span>}{t.texto}
			</span>
		);
	};
	return (
		// sobre fundo transparente, o promptador é um cartão claro flutuando (cantos arredondados, sem sombra), não um bloco na metade inteira
		<div style={cartao
			? {position: 'absolute', left: 40, right: 40, top: 222, bottom: H === 1920 ? 400 : 28, background: '#f6f6f4', fontFamily: 'DM Sans', color: '#111',
				borderRadius: 26, outline: '1px solid rgba(255,255,255,.10)', overflow: 'hidden'}
			: {position: 'absolute', inset: 0, background: '#f6f6f4', fontFamily: 'DM Sans', color: '#111'}}>
			<div style={{position: 'absolute', left: cartao ? 40 : 56, right: cartao ? 40 : 56, top: cartao ? 30 : 236, bottom: cartao ? 24 : H === 1920 ? 420 : 24, display: 'flex', flexDirection: 'column', gap: 22, overflow: 'hidden'}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0}}>
					<span style={{fontWeight: 700, fontSize: 24, letterSpacing: '0.1em', color: '#8a8a86'}}>PROMPTADOR</span>
					<span style={{fontWeight: 500, fontSize: 22, color: '#6b6b67', border: '1.5px solid #d9d9d4', borderRadius: 999, padding: '4px 16px'}}>Copiar</span>
				</div>
				{p.titulo && <div style={{fontWeight: 700, fontSize: 40, flexShrink: 0}}>{p.titulo}</div>}
				<div style={{position: 'relative', flex: 1, overflow: 'hidden', WebkitMaskImage: p.rola && e < 1 ? 'linear-gradient(to bottom, #000 85%, transparent)' : undefined}}>
					<div style={{transform: `translateY(${-y}px) scale(${escala})`, transformOrigin: 'top center', filter: borrao > 0.3 ? `blur(${borrao}px)` : undefined,
						display: 'flex', flexDirection: 'column', gap: 22}}>
						{p.corrido
							? <div style={{fontWeight: 500, fontSize: fonte, lineHeight: 1.42}}>{p.trechos.map(trecho)}</div>
							: p.trechos.map((t, j) => <div key={j} style={{fontWeight: 500, fontSize: fonte, lineHeight: 1.42}}>{trecho(t, j)}</div>)}
					</div>
				</div>
			</div>
		</div>
	);
};

const ImagemPainel: React.FC<{p: PainelImg; W: number; H: number; fim: number; livre?: boolean}> = ({p, W, H, fim, livre}) => {
	const k = useCurrentFrame();
	const semSombra = React.useContext(SemSombra);
	// área segura: nada importante acima de y 208 (e abaixo de 1509 na cheia); numa caixa de grupo, a caixa já é a área
	const topo = livre ? 0 : 208, baseSeg = livre ? H : H === 1920 ? 1509 : H;
	let s0: number, ox: number, oy: number;
	if (p.ajuste === 'contem') {
		const mg = p.cartao ? 48 : 0;
		s0 = Math.min((W - 2 * mg) / p.w, (baseSeg - topo - 2 * mg) / p.h); ox = (W - p.w * s0) / 2; oy = topo + (baseSeg - topo - p.h * s0) / 2;
	} else {
		s0 = Math.max(W / p.w, H / p.h);
		const [fx, fy] = p.foco ?? [p.w / 2, p.h / 2];
		ox = Math.min(0, Math.max(W - p.w * s0, W / 2 - fx * s0)); oy = Math.min(0, Math.max(H - p.h * s0, H / 2 - fy * s0));
	}
	const [z0, z1] = p.zoom ?? [1, 1];
	const z = interpolate(k, [p.quadro, fim], [z0, z1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
	const [fx, fy] = p.foco ?? [p.w / 2, p.h / 2];
	const sx = ox + fx * s0, sy = oy + fy * s0;                  // o foco fica parado na tela durante o zoom
	const s = s0 * z; const tx = sx - fx * s, ty = sy - fy * s;
	return (<>
		<div style={{position: 'absolute', left: 0, top: 0, width: p.w, height: p.h, transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${s})`}}>
			<Img src={staticFile(p.src)} style={{width: p.w, height: p.h, display: 'block', ...(p.cartao ? {borderRadius: 26 / s, ...(semSombra ? {} : {boxShadow: `0 ${18 / s}px ${48 / s}px rgba(0,0,0,.55)`}), outline: `${1 / s}px solid rgba(255,255,255,.10)`} : {})}} />
			{p.desenha && k >= p.desenha.quadro && (() => {
				const d = p.desenha!;
				const y = interpolate(k, [d.quadro, d.quadro + d.dur], [d.de, d.ate], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
				const a = d.de > d.ate ? 'to bottom' : 'to top';
				const borda = d.de > d.ate ? y : p.h - y;
				const mask = `linear-gradient(${a}, transparent ${borda - 3}px, #000 ${borda + 3}px)`;
				return <>
					<Img src={staticFile(d.src)} style={{position: 'absolute', left: 0, top: 0, width: p.w, height: p.h, WebkitMaskImage: mask, maskImage: mask, ...(p.cartao ? {borderRadius: 26 / s} : {})}} />
					<Sequence from={d.quadro} layout="none"><Audio src={staticFile('kit/sfx/clique.wav')} volume={0.5} /></Sequence>
				</>;
			})()}
			{(p.escurece ?? []).map((e, j) => (
				<div key={`e${j}`} style={{position: 'absolute', left: e.x, top: e.y, width: e.w, height: e.h, background: '#000',
					opacity: interpolate(k, [e.quadro, e.quadro + 8], [0, 0.72], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />
			))}
			{(p.marcas ?? []).map((m, j) => (
				<Sequence key={j} from={m.quadro} layout="none">
					<Contorno m={{quadro: 0, img: 0, cx: m.cx, cy: m.cy, rx: m.rx, ry: m.ry}} w={p.w} h={p.h} s={s} cor={p.contorno} />
					<Audio src={staticFile('kit/sfx/clique.wav')} volume={0.5} />
				</Sequence>
			))}
			{(p.rotulos ?? []).map((r, j) => (
				<Sequence key={`r${j}`} from={r.quadro} layout="none"><Selo r={r} s={s} /></Sequence>
			))}
		</div>
		{(p.numeros ?? []).map((n, j) => { const a = entra(k, n.quadro, 7);
			return <div key={`n${j}`} style={{...FONTE_G, fontSize: n.tamanho ?? 128, color: '#fff', position: 'absolute', left: 0, right: 0, top: n.y, textAlign: 'center', whiteSpace: 'pre',
				opacity: a, filter: `blur(${(1 - a) * 10}px)`, transform: `translateY(${(1 - a) * 22}px)`, textShadow: '0 2px 18px rgba(0,0,0,.35)'}}>{n.texto}</div>; })}
	</>);
};

const Grupo: React.FC<{p: PainelGrupo; fim: number}> = ({p, fim}) => {
	const k = useCurrentFrame();
	const semSombra = React.useContext(SemSombra);
	return <>{p.itens.map((it, j) => {
		const [x, y, w, h] = it.caixa;
		const a = it.entra === undefined ? 1 : interpolate(k, [it.entra, it.entra + 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
		const cartaoCaixa = it.cartao && it.ajuste !== 'contem';   // imagem que cobre a caixa: o cartão é a própria caixa
		return <div key={j} style={{position: 'absolute', left: x, top: y, width: w, height: h, overflow: 'hidden', opacity: a, transform: `translateY(${(1 - a) * 60}px)`,
			...(cartaoCaixa ? {borderRadius: 26, ...(semSombra ? {} : {boxShadow: '0 18px 48px rgba(0,0,0,.55)'}), outline: '1px solid rgba(255,255,255,.10)'} : {})}}>
			<ImagemPainel p={cartaoCaixa ? {...it, cartao: false} : it} W={w} H={h} fim={fim} livre />
		</div>;
	})}</>;
};

export const TelaImagens: React.FC<TelaImg> = ({paineis, area = 'metade', duracao, fundo = 'transparente'}) => {
	const k = useCurrentFrame();
	const W = 1080, H = area === 'cheia' ? 1920 : 960;
	const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
	const dur = (p?: PainelImg | PainelPrompt | PainelGrupo) => (!p ? 0 : p.entrada === 'cortina' ? 20 : p.entrada === 'corte' ? 0 : 8);
	// sem fundo preto, a sombra dos cartões passa da metade de cima: o recorte desce 140 px pra ela não sair cortada em linha reta
	const sobra = fundo !== 'preto' && H < 1920 ? 140 : 0;
	return (
		<SemSombra.Provider value={fundo !== 'preto'}>
		<AbsoluteFill>
			<div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, clipPath: `inset(0 0 -${sobra}px 0)`, background: fundo === 'preto' ? '#000' : 'transparent'}}>
				{paineis.map((p, i) => {
					const prox = paineis[i + 1];
					if (k < p.quadro || (prox && k >= prox.quadro + dur(prox))) return null;
					const e = p.entrada ?? 'empurra';
					const estilo: React.CSSProperties = {position: 'absolute', inset: 0, clipPath: `inset(0 0 -${sobra}px 0)`};
					if (i > 0 && e === 'empurra') estilo.transform = `translateX(${(1 - interpolate(k, [p.quadro, p.quadro + 8], [0, 1], ease)) * W}px)`;
					if (i > 0 && e === 'cortina') estilo.clipPath = `inset(0 ${100 - interpolate(k, [p.quadro, p.quadro + 20], [0, 100], ease)}% -${sobra}px 0)`;
					if (prox && (prox.entrada ?? 'empurra') === 'empurra' && k >= prox.quadro)
						estilo.transform = `translateX(${-interpolate(k, [prox.quadro, prox.quadro + 8], [0, 1], ease) * W}px)`;
					return <React.Fragment key={i}>
						<div style={{...estilo, zIndex: i}}>{'tipo' in p ? (p.tipo === 'grupo' ? <Grupo p={p} fim={prox ? prox.quadro + dur(prox) : duracao} /> : <PainelPromptador p={p} H={H} cartao={fundo !== 'preto'} />) : <ImagemPainel p={p} W={W} H={H} fim={prox ? prox.quadro + dur(prox) : duracao} />}</div>
						{/* num grupo (cartões do flutua), a linha da cortina fica presa dentro do cartão: começa e termina nas bordas dele, com os mesmos cantos */}
						{i > 0 && e === 'cortina' && k < p.quadro + 20 && ('tipo' in p && p.tipo === 'grupo' ? (() => {
							const x0 = Math.min(...p.itens.map((it) => it.caixa[0])), y0 = Math.min(...p.itens.map((it) => it.caixa[1]));
							const x1 = Math.max(...p.itens.map((it) => it.caixa[0] + it.caixa[2])), y1 = Math.max(...p.itens.map((it) => it.caixa[1] + it.caixa[3]));
							return <div style={{position: 'absolute', left: x0, top: y0, width: x1 - x0, height: y1 - y0, borderRadius: 26, overflow: 'hidden', zIndex: 99}}>
								<div style={{position: 'absolute', top: 0, bottom: 0, width: 6, marginLeft: -3, background: '#fff', left: interpolate(k, [p.quadro, p.quadro + 20], [0, W], ease) - x0}} />
							</div>;
						})() : <div style={{position: 'absolute', top: 0, bottom: 0, width: 6, marginLeft: -3, background: '#fff', zIndex: 99,
							left: `${interpolate(k, [p.quadro, p.quadro + 20], [0, 100], ease)}%`}} />)}
					</React.Fragment>;
				})}
			</div>
		</AbsoluteFill>
		</SemSombra.Provider>
	);
};

// Gancho (padrao-edicao.md, "Texto do gancho"), em dois estilos (padrão: palavras, escolhido no reel 01):
// - digitado: letra por letra num ritmo constante; cada letra entra com fade, desfoque e uma subida curta, e a linha
//   continua centralizada enquanto cresce (a largura desliza, não pula); cursor arredondado que pulsa no fim.
//   Cada letra com o som de uma tecla (kit/sfx/teclado)
// - palavras: o texto já no lugar, cada palavra entra com fade, desfoque e subida, e uma tecla por palavra
// O pop-in e o typewriter do Palmier não servem: o primeiro sai como bloco na exportação, o segundo alinha à esquerda.
// veu: escurece o que está embaixo enquanto o gancho está na tela (0-1), e some nos últimos 8 quadros. Pra gancho sobre imagem clara (reel 02)
export type Gancho = {duracao: number; linhas: string[]; estilo?: 'digitado' | 'palavras'; inicio?: number; ritmo?: number; veu?: number};
const TECLAS = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => `kit/sfx/teclado/tecla-0${i}.wav`);
const FONTE_G = {fontFamily: 'DM Sans', fontWeight: 700, fontSize: 128, letterSpacing: -8.9} as const;
const PASSO = 129;   // entre linhas, igual ao gancho do Palmier (72 pt, entrelinha -22)
let ctxMedida: CanvasRenderingContext2D | null = null;
const largura = (t: string) => {
	if (!ctxMedida) ctxMedida = document.createElement('canvas').getContext('2d');
	ctxMedida!.font = "700 128px 'DM Sans'";
	return t ? ctxMedida!.measureText(t).width + FONTE_G.letterSpacing * t.length : 0;
};
const entra = (k: number, q: number, dur: number) => interpolate(k, [q, q + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

export const TelaGancho: React.FC<Gancho> = ({linhas, estilo = 'palavras', inicio = 2, ritmo = 2, veu = 0, duracao}) => {
	const k = useCurrentFrame();
	const fundo = veu > 0 && <AbsoluteFill style={{background: '#000', opacity: veu * interpolate(k, [duracao - 8, duracao], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />;
	const y0 = 960 - ((linhas.length - 1) * PASSO) / 2;          // centro de cada linha
	if (estilo === 'palavras') {
		const palavras = linhas.map((l) => l.split(' '));
		let w = 0; const tq: number[][] = palavras.map((ps) => ps.map(() => inicio + 5 * w++));
		return (
			<AbsoluteFill>
				{fundo}
				{palavras.map((ps, li) => (
					<div key={li} style={{...FONTE_G, color: '#fff', position: 'absolute', left: 0, right: 0, top: y0 + li * PASSO - 80, height: 160, lineHeight: '160px', textAlign: 'center', whiteSpace: 'pre'}}>
						{ps.map((p, pi) => { const a = entra(k, tq[li][pi], 7);
							return <span key={pi} style={{display: 'inline-block', opacity: a, filter: `blur(${(1 - a) * 10}px)`, transform: `translateY(${(1 - a) * 22}px) scale(${0.97 + 0.03 * a})`}}>{p}{pi < ps.length - 1 ? ' ' : ''}</span>; })}
					</div>
				))}
				{tq.flat().map((q, j) => <Sequence key={j} from={q} layout="none"><Audio src={staticFile(TECLAS[j % TECLAS.length])} volume={0.5} /></Sequence>)}
			</AbsoluteFill>
		);
	}
	// digitado: quadro de cada letra, contínuo entre as linhas
	const t: number[][] = []; let q = inicio;
	for (const l of linhas) { t.push([...l].map(() => { const v = q; q += ritmo; return v; })); }
	const fim = q - ritmo;
	const cursorLinha = (() => { let r = 0; t.forEach((ts, li) => { if (ts[0] <= k) r = li; }); return r; })();
	const pulso = k <= fim + 6 ? 1 : 0.5 + 0.5 * Math.cos(((k - fim - 6) / 30) * 2 * Math.PI);
	let j = 0;
	return (
		<AbsoluteFill>
			{linhas.map((l, li) => {
				const ch = [...l]; const ts = t[li];
				const n = ts.filter((v) => v <= k).length;
				if (n === 0) return null;
				// largura visível deslizando: da largura com n-1 letras pra com n, nos 3 quadros depois da letra
				const a = entra(k, ts[n - 1], 3);
				const wv = largura(ch.slice(0, n - 1).join('')) * (1 - a) + largura(ch.slice(0, n).join('')) * a;
				return (
					<div key={li} style={{...FONTE_G, color: '#fff', position: 'absolute', top: y0 + li * PASSO - 80, height: 160, lineHeight: '160px', left: (1080 - wv) / 2, whiteSpace: 'pre'}}>
						{ch.map((c, ci) => {
							const b = ci < n ? entra(k, ts[ci], 4) : 0; j++;
							return <span key={ci} style={{display: 'inline-block', position: 'relative', opacity: b, filter: `blur(${(1 - b) * 6}px)`, transform: `translateY(${(1 - b) * 10}px)`}}>{c === ' ' ? '\u00a0' : c}
								{ci === n - 1 && li === cursorLinha && <span style={{position: 'absolute', right: -18, top: 34, width: 7, height: 96, borderRadius: 4, background: '#fff', opacity: pulso / Math.max(b, 0.01) * b}} />}
							</span>;
						})}
					</div>
				);
			})}
			{t.flat().map((v, i) => (
				<Sequence key={i} from={v} layout="none">
					<Audio src={staticFile(linhas.join('')[i] === ' ' ? 'kit/sfx/teclado/espaco.wav' : TECLAS[i % TECLAS.length])} volume={0.5} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};
