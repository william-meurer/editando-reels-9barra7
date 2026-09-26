# Padrão de edição

Vale igual para os 36 reels do teste. Mudar qualquer item no meio do teste invalida a comparação.
Modelo: reel 06 (29.09 Bastidor de projeto real), aprovado em 26/09. Final em `Produção/Lote 1 - 22.09 a 05.10/06 - 29.09 Bastidor de projeto real/5-final/`.

## Definido

| Item | Valor |
|---|---|
| Pegada | editorial: a imagem é protagonista. Cor de marca só em pontos fixos (palavra-chave em trecho de prompt, selo) |
| Formato | 9:16, 1080×1920, 30 quadros, bt709, -14 LUFS |
| Duração | o mais curta possível sem cortar conteúdo. O ajuste de tempo é no roteiro (alvo de 170 palavras), não na edição |
| Ritmo | corte a cada 2 a 3 segundos |
| Fala | corte seco entre frases, na borda da voz (medida em 80-1000 Hz), com 30 ms de fade no áudio. Pausa entre trechos: 0,12 s (continuação), 0,2 s (frase), 0,3 s (cena). Velocidade natural |
| Planos | P1 = recorte de 1080 px do 4K (1:1, nitidez total), centrado no rosto, com 22% de folga acima da cabeça. P2 110%, P3 118%, ÊNFASE 130%, empurra até +20%. Zoom centrado. Todo pulo na câmera alterna o enquadramento, e dois trechos seguidos mudam pelo menos 12% de escala |
| Primeiro plano | recorte digital do take em 4K, nunca movimento de câmera |
| Cor da imagem | look C (contraste leve, calor leve, nitidez leve), aplicado na imagem de edição (`imagem.py`). A cor E foi reprovada |
| Texto do gancho | 3 primeiros segundos, em todos. DM Sans Bold ~128 px (72 no Palmier), branca, sem sombra, CAIXA ALTA, 2 linhas no centro exato do vídeo, letras bem juntas (-5) e entrelinha apertada (-22), entra palavra por palavra (pop-in) junto com o grave. Texto = a primeira frase falada, enxuta (edicao.json). Sem legenda nesses 3 s |
| Palavra-chave (destaque) | a ideia que fecha o reel, no máximo uma por reel, nunca no gancho. Mesmo estilo do gancho, em minúscula, no centro exato do vídeo, com pop-in e o som "pop". Fica até o fim do trecho. A legenda some enquanto ela está na tela |
| Tela (imagem, render, software) | sem fundo preto. Tela dividida na vertical: o material ocupa a metade de cima inteira (1080×960, uma imagem por vez, a seguinte entra empurrando; o que importa abaixo de y 208) e a Marilia fica na metade de baixo (a câmera desce pra centerY 0,695, rosto logo abaixo da emenda, queixo acima de y ~1330). Sai em corte seco |
| Quando cobrir com tela | sempre que a fala aponta pra algo visível (material, luz, número, ferramenta). Trecho longo de rosto falando de coisa concreta é sinal de cobertura faltando |
| Marcação | contorno branco em volta do que a fala aponta, nunca preenchido, sombra escura fina, desenhado em 8 quadros, preso na palavra (±3 quadros). Um clique por marcação |
| Número na tela | DM Sans Bold ~128 px, branca, sem sombra, letras juntas, no centro da área visível, com pop |
| Selo | pílula DM Sans bold, caixa alta, ~36 px, texto preto, perto do que aponta. Roxo `#A4A1F3` pro errado/antes ("O TOM MUDOU"), verde `#B3FF9F` pro certo/depois |
| Tela de software | gravação real da ferramenta (tela do Mac, 2880 px), em recortes aproximados que seguem a fala. Texto longo não se lê no celular: marcar os trechos importantes em verde `#B3FF9F` (marca-texto) e depois mostrá-los ampliados |
| Planta | linha branca sobre preto (inverter a planta original), pra marcação branca aparecer |
| Tipografia | DM Sans em tudo |
| Cores | base preto e branco. Verde e roxo só em marca-texto e selo |
| Transições | corte seco. Na tela dividida, a imagem seguinte entra empurrando (8 quadros) |
| Efeitos sonoros | só estes (`kit/sfx/`), com o volume do `palmier.py`: grave + estalo no 0:00 (gancho), whoosh na entrada da primeira tela, subida que resolve no corte da virada, pop no destaque, clique de mouse (estilo papelão) em cada marcação. Nunca dois a menos de 3 s, nada por cima de palavra que precisa ser entendida |
| Cama sonora | uma só pra todos: "Technology" (prettyjohn1, Pixabay, `kit/trilha/`). Abafada até a virada, abre inteira nela, abaixa sozinha na fala (~16-18 dB abaixo da voz), sobe nas pausas e no fechamento, -3 dB em 1-3,5 kHz (`cama.py`) |
| Virada | o ponto em que o reel sai do problema e entra na solução (no reel 06, o "Por isso"). Marcada no edicao.json: nela a cama abre e a subida resolve |
| Fechamento | depois da fala fixa, último quadro congelado, escurece de leve em 0,5 s e entra o logo 9barra7 Academy em branco no centro (`kit/fechamento/`). Sem @9barra7. 4 s |
| Fala fixa do fim | "Eu sou a Marilia, do 9barra7, e te ensino a renderizar com IA respeitando e valorizando o teu projeto. Me acompanha aqui pra ver mais conteúdos assim." |
| Zona livre | as do Checklist de gravação (em 1080×1920): nada importante até y 208 nem a partir de y 1509; nada à direita de x 904 abaixo de y 876 (botões). Vale pra legenda, gancho, destaque, marcação e tela |

## Legenda da fala

Bloco embaixo em todo o reel (câmera e tela). Nada nos 3 s do gancho nem enquanto o destaque está na tela. O `montar.py` aplica tudo isto.

- frase inteira, até 2 linhas, centralizada no vídeo (x 540), DM Sans Medium 54 px, branca com sombra fina, linhas de 68 px, centro do bloco em y 1435
- a linha mais larga até 720 px (não entra embaixo dos botões do Instagram)
- cada bloco se entende sozinho, sem o áudio
- nenhuma linha termina em: e, de, do, da, que, a, o, os, as, um, uma, pra, com, em, no, na, se, só, teu, tua, meu, minha, esse, essa, isso
- a linha nova começa melhor em "que", "mas", "quando", "onde", "porque"
- frase longa vira dois blocos, cortados primeiro na vírgula ou no ponto e, se não couber, no tempo da fala. Bloco de 1 ou 2 palavras não fica sozinho (pisca)
- na tela dividida, a legenda cai no peito da Marilia: se cair no rosto, sobe o enquadramento da câmera, não a legenda

## Kit

Tudo em `Produção/kit/`: `fonte/` (DM Sans), `logo/`, `sfx/` (os efeitos acima; descartados em `sfx/_descartados/`), `trilha/` (a cama), `fechamento/` (a marca do fim, ProRes 4444 com transparência). Origem da marca: design system em `~/Documents/claude/9barra7-ui`.
