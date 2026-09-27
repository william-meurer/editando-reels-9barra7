# Padrão de edição

Duas camadas (27/09): o que está em **Definido** vale igual pra todos os reels (a identidade). O que varia está na **Receita por família**: cada família de roteiro tem o seu jeito de abrir, os seus formatos de tela, a sua trilha e os seus efeitos, fixos dentro da família. Assim o feed não fica todo igual e o teste compara família com família.
Modelo da família Bastidor: reel 06 (29.09), aprovado em 26/09. Final em `Produção/Lote 1 - 22.09 a 05.10/06 - 29.09 Bastidor de projeto real/5-final/`.

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
| Texto do gancho | 3 primeiros segundos, em todos. DM Sans Bold ~128 px (72 no Palmier), branca, sem sombra, CAIXA ALTA, 2 linhas no centro exato do vídeo, letras bem juntas (-5) e entrelinha apertada (-22), o texto já no lugar final e cada palavra entra com fade, desfoque e uma subida curta (5 quadros entre palavras, termina em ~0,7 s), com o som de uma tecla por palavra (`kit/sfx/teclado`) e o grave no 0:00. Sai do Remotion (composição `Gancho`, estilo `palavras`), porque o pop-in do Palmier exporta o bloco inteiro e o typewriter dele alinha à esquerda. O estilo `digitado` (letra por letra com cursor) existe, mas não é o padrão (reel 01). Texto = a primeira frase falada, enxuta (edicao.json). Se uma frase de mais adiante prender mais (promessa, pergunta, número, o resultado), ela pode ser antecipada pro 0:00, desde que o reel entregue o que ela promete e ela não se repita no lugar de origem. Isso aparece como opção no roteiro de edição, e a primeira frase segue sendo o padrão. Sem legenda nesses 3 s |
| Palavra-chave (destaque) | no máximo uma por reel, nunca no gancho, e só se houver uma ideia que valha (pode não ter). Entra onde a ideia cai, não numa posição fixa: no meio do reel também serve. Mesmo estilo do gancho, em minúscula, no centro exato do vídeo, com pop-in. O som "pop" vem da receita da família. Fica até o fim do trecho. A legenda some enquanto ela está na tela |
| Tela (imagem, render, software) | sem fundo preto. Formato escolhido no cardápio abaixo, conforme a receita da família e o que o roteiro pede na cena. **Cada reel usa pelo menos dois formatos.** Sai em corte seco |
| Quando cobrir com tela | sempre que a fala aponta pra algo visível (material, luz, número, ferramenta). Trecho longo de rosto falando de coisa concreta é sinal de cobertura faltando. A indicação visual do roteiro (tela cheia, wipe, abrir no resultado, insert, zoom lento) é o ponto de partida: não se achata tudo num formato só |
| Marcação | contorno branco em volta do que a fala aponta, nunca preenchido, sombra escura fina, desenhado em 8 quadros, preso na palavra (±3 quadros). Um clique por marcação |
| Número na tela | DM Sans Bold ~128 px, branca, sem sombra, letras juntas, no centro da área visível, com pop |
| Selo | pílula DM Sans bold, caixa alta, ~36 px, texto preto, perto do que aponta. Roxo `#A4A1F3` pro errado/antes ("O TOM MUDOU"), verde `#B3FF9F` pro certo/depois |
| Tela de software | gravação real da ferramenta (tela do Mac, 2880 px), em recortes aproximados que seguem a fala. Texto longo não se lê no celular: marcar os trechos importantes em verde `#B3FF9F` (marca-texto) e depois mostrá-los ampliados. O que fica de fora ou deve ser ignorado vai em vermelho `#FF9F9F` (reel 01) |
| Planta | linha branca sobre preto (inverter a planta original), pra marcação branca aparecer |
| Tipografia | DM Sans em tudo |
| Cores | base preto e branco. Verde, vermelho e roxo só em marca-texto e selo |
| Material da Marilia | entra como veio: nunca inverter a cor, recolorir nem cobrir parte da imagem sem pedido. Planta, print e imagem gerada entram como cartão (margem, cantos de 26 px, sombra), e o contorno é sempre branco (o padrão, também sobre planta clara). Quando a fala cita a planta e a imagem juntas, as duas aparecem juntas (painel `grupo`) |
| Transições | corte seco. Na tela dividida, a imagem seguinte entra empurrando (8 quadros) |
| Efeitos sonoros | só os do `kit/sfx/`, com o volume do `palmier.py`. Cada efeito nasce de algo que acontece na tela (troca grande de imagem, marcação, número, corte da virada), nunca de uma posição fixa. A lista de cada reel fica no `edicao.json` ("sfx"), dentro do que a receita da família permite. Nunca dois a menos de 3 s, nada por cima de palavra que precisa ser entendida |
| Cama sonora | uma trilha do banco (`kit/trilha/`, abaixo), tratada igual em todas: abaixa sozinha na fala (~16-18 dB abaixo da voz), sobe nas pausas e no fechamento, -3 dB em 1-3,5 kHz (`cama.py`). Como ela marca a virada vem da receita da família: abre (abafada até a virada), silêncio (some 0,6 s antes e volta cheia) ou plana |
| Virada | o ponto em que o reel sai do problema e entra na solução (no reel 06, o "Por isso"). Marcada no edicao.json. O que acontece nela (cama, subida ou nada) vem da receita da família |
| Fechamento | depois da fala fixa, último quadro congelado, escurece de leve em 0,5 s e entra o logo 9barra7 Academy em branco no centro (`kit/fechamento/`). Sem @9barra7. 4 s |
| Fala fixa do fim | "Eu sou a Marilia, do 9barra7, e te ensino a renderizar com IA respeitando e valorizando o teu projeto. Me acompanha aqui pra ver mais conteúdos assim." |
| Zona livre | as do Checklist de gravação (em 1080×1920): nada importante até y 208 nem a partir de y 1509; nada à direita de x 904 abaixo de y 876 (botões). Vale pra legenda, gancho, destaque, marcação e tela |

## Cardápio de formatos de tela

| Formato | Como fica | Quando |
|---|---|---|
| dividida | material na metade de cima (1080×960, o que importa abaixo de y 208), Marilia na metade de baixo. A câmera desce o quanto der até centerY 0,695 com o queixo acima de y 1330 (o `palmier.py` calcula pelo rosto) | explicar algo olhando pro material, com ela reagindo |
| cheia | o material ocupa a tela inteira (o que importa entre y 208 e 1509), voz dela em off, legenda por cima | mostrar o resultado, abrir no resultado, imagem que precisa de tamanho |
| janela | material em tela cheia, Marilia numa janelinha retangular de cantos arredondados (3:4, 280 px, como a câmera dupla do iPhone), flutuando no alto à direita logo abaixo de y 208, com sombra leve | gravação de tela e conversa com a IA: a tela manda, ela acompanha |
| cortina | uma imagem varre a outra (antes → depois), dentro da cheia ou da dividida | antes/depois do mesmo ângulo |
| zoom | aproximação lenta até o detalhe, com contorno no fim | erro pequeno que precisa ser visto (puxador, luminária) |
| apoio | vídeo de apoio em tela cheia (insert) | analogia, coisa fora do render |
| número | número ou palavra grande em tela cheia, fundo da própria imagem escurecido | dado que fecha o argumento |

Dentro de uma tela, a imagem seguinte entra empurrando (8 quadros), em cortina ou em corte seco.

## Receita por família

| Família | Abre em | Formatos | Virada | Efeitos | Destaque |
|---|---|---|---|---|---|
| Resultado antes da explicação | o resultado em tela cheia, gancho sobre a imagem, voz em off | cheia, cortina, dividida | silêncio | impacto no 0:00, whoosh na primeira troca grande de imagem | sim, onde a ideia cai |
| Erro custoso | a Marilia (P1 empurra), gancho | zoom, cheia, dividida | abre | impacto, clique nas marcações, subida com o hit na entrada do destaque (na virada soou solta, reel 01) | a palavra do erro, pode ser no meio |
| Contradição de mercado | a Marilia, gancho | dividida, número | plana, marcada pelo corte pra ÊNFASE | impacto, pop no número | a tese, com pop |
| Gravação de tela | a Marilia com o gancho, e logo a tela | janela, cheia | plana | impacto, clique nas marcações, sem whoosh | não (usa selo) |
| Peça livre (analogia) | a Marilia, gancho | apoio, cheia | silêncio | impacto, whoosh na entrada do apoio | a frase de fechamento |
| Bastidor de projeto real | a Marilia (reel 06) | dividida, número | abre + subida | impacto, whoosh, subida, pop | como o 06 |
| Comparação com critério | a comparação em tela cheia, gancho-pergunta sobre ela | cheia, cortina, dividida | abre | impacto, whoosh em cada troca da prancha | sim |

### Trilhas

Banco aprovado em 27/09, em `kit/trilha/` (arquivos `cama - …`): 4 de piano (Inspiring Minimal Piano, Inspiring Piano, Piano Music, Piano inspiring), 4 de lofi (Chill Lamp Light, Chill Lofi, Lofi Chill, Lofi Chill Vlog Beats), 4 de house (as duas Deep House e as duas Minimal House) e a "Technology" do reel 06. Distribuição: dois reels seguidos nunca têm a mesma trilha nem o mesmo estilo, e no mesmo lote uma trilha não se repete. A escolha fica no `edicao.json` ("cama").

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
