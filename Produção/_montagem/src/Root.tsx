import {Composition} from 'remotion';
import {TelaComparacao, TelaGancho, TelaImagens, TelaPlaceholder, cena3Reel06, materiaisReel06} from './Telas';

export const Root: React.FC = () => (
	<>
	<Composition id="Tela3" component={TelaComparacao as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={cena3Reel06.duracao} defaultProps={cena3Reel06 as unknown as Record<string, unknown>} />
	<Composition id="Tela4Materiais" component={TelaComparacao as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={materiaisReel06.duracao} defaultProps={materiaisReel06 as unknown as Record<string, unknown>} />
	{/* provisória: props e duração vêm do --props (ver Telas.tsx, Placeholder) */}
	<Composition id="Placeholder" component={TelaPlaceholder as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={90} defaultProps={{duracao: 90, paineis: [{quadro: 0, titulo: 'Render do quarto', arquivo: 'render-1.jpg'}]} as unknown as Record<string, unknown>}
		calculateMetadata={({props}) => ({durationInFrames: (props as {duracao: number}).duracao})} />	{/* telas com imagens reais: props e duração vêm do --props (ver Telas.tsx, TelaImagens) */}
	<Composition id="Imagens" component={TelaImagens as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={90} defaultProps={{duracao: 90, paineis: []} as unknown as Record<string, unknown>}
		calculateMetadata={({props}) => ({durationInFrames: (props as {duracao: number}).duracao})} />
	{/* gancho digitado: linhas e duração vêm do --props (ver Telas.tsx, TelaGancho) */}
	<Composition id="Gancho" component={TelaGancho as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={90} defaultProps={{duracao: 90, linhas: ['INFO DEMAIS', 'PRA IA']} as unknown as Record<string, unknown>}
		calculateMetadata={({props}) => ({durationInFrames: (props as {duracao: number}).duracao})} />
	</>
);
