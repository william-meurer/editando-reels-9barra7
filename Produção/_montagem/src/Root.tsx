import {Composition} from 'remotion';
import {TelaComparacao, cena3Reel06, materiaisReel06} from './Telas';

export const Root: React.FC = () => (
	<>
	<Composition id="Tela3" component={TelaComparacao as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={cena3Reel06.duracao} defaultProps={cena3Reel06 as unknown as Record<string, unknown>} />
	<Composition id="Tela4Materiais" component={TelaComparacao as unknown as React.FC<Record<string, unknown>>} width={1080} height={1920} fps={30}
		durationInFrames={materiaisReel06.duracao} defaultProps={materiaisReel06 as unknown as Record<string, unknown>} />

	</>
);
