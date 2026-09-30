---
name: editando-reels-9barra7
description: Use when there are raw recordings in a Produção/Lote folder of the 9barra7 project to be sorted, cut or edited into reels, or when someone asks to edit a 9barra7 reel ("edita o reel 07"), decupagem, montagem, Palmier Pro, telas animadas or sound design on 9barra7 content.
---

# Editando reels do 9barra7

Leva os brutos de um lote até o reel pronto. A Marilia grava **um take longo por reel**, lendo teleprompter: fala a data do reel e bate uma palma no começo, e quando erra, pausa e repete a frase inteira. Nada é renomeado.

O William não edita: eu monto tudo e ele revisa por escrito. O editor é o **Palmier Pro** (MCP `palmier-pro`), onde ele mexe à mão em detalhe pequeno. Remotion e HyperFrames só fazem as telas animadas.

**Duas paradas pra aprovação, e só duas:** o roteiro de edição (antes de montar) e o reel montado no Palmier (antes de exportar). O resto roda direto.

Todas as regras visuais e sonoras estão em `padrao-edicao.md`: a identidade (igual pra todos) e a receita de cada família de roteiro (abertura, formatos de tela, trilha, virada, efeitos). Nada fora dele. Os reels não saem todos iguais: cada um segue a receita da sua família e usa pelo menos dois formatos de tela.

## Estrutura

```
Produção/Lote N - dd.mm a dd.mm/
  _brutos/                  tudo cru: câmera, tela, lapela
  NN - dd.mm Família/
    1-roteiro/  .docx (vale este) + roteiro.json (gerado dele)
    2-arquivos/ renders, prints, plantas, gravações de tela
    3-takes/    preenchido pelo organizar.py
    4-edicao/   edicao.json, montagem.json, audio/, imagem/, telas/
    5-final/    mp4 entregue
```

Scripts em `.claude/skills/editando-reels-9barra7/scripts/`. Todos recebem `"<pasta do reel>"` (o organizar recebe a do lote).

## Etapas

1. **Organizar o lote**: `organizar.py "<pasta do lote>"`. Transcreve cada bruto, acha o reel pela claquete (ou pela fala), separa câmera de tela e liga em `3-takes/`. Mapa em `_brutos/_mapa.json`
2. **Decupar**: `decupar.py`. Acha cada frase do roteiro no take (última versão). Grava `4-edicao/cortes.json`
3. **Tratar o áudio do take**: cadeia em "Áudio" abaixo. Gera `4-edicao/audio/D-eq9.wav` e, depois do `falhas_mic.py` no take inteiro, `D-limpo.wav` (a fonte da voz em tudo que vem depois)
4. **Medir** (podem rodar juntos):
   - `ilhas.py`: transcrição ilha por ilha → `ilhas.json`
   - `rosto.py`: rosto no 4K → `rosto.json`
   - `imagem.py` (depois do rosto; ~4 min): recorte P1 com look C → `imagem/camera-edicao.mp4`
5. **Roteiro de edição**: escrever `edicao.json` e `roteiro-de-edicao.md` (ver formato abaixo). As bordas do corte se conferem pela energia acima de 3 kHz (s, ç, f parecem silêncio no volume).
   - **Conferir o conteúdo, não só o roteiro.** Fala fluente não quer dizer fala certa. Retranscrever cada trecho escolhido sem contexto (`large-v3`, que não "corrige" a fala pro texto) e comparar com o `.docx`: palavra trocada ("neles" no lugar de "nela"), frase incompleta, informação contraditória ou errada, e a tela que não mostra o que a fala diz ("essa planta pra gerar essa imagem" pede as duas na tela ao mesmo tempo, nem que seja em tela cheia: painel `grupo` do `Imagens`). Marcação em planta: identificar cada elemento pelo símbolo (porta = folha + arco tracejado, armário = cabides em série) e marcar primeiro o que o reel usa depois (no reel 01, a porta, que a IA transformou no arco da imagem errada). O que nenhum take resolve vai pra seção "Pra revisar" do roteiro de edição, com o timecode e uma sugestão. Quando a diferença é só de forma, a legenda segue o que ela falou, não o `.docx` (no reel 01, "Me acompanha **por** aqui"). Deslize que vira erro ("neles") vai pro "Pra revisar"
   - **Gancho**: avaliar se alguma frase de mais adiante prende mais que a primeira (regra em `padrao-edicao.md`). Se sim, entra no roteiro de edição como opção, com o trecho antecipado e como a sequência fica sem repetir a frase. Pra antecipar, o trecho vai primeiro na lista `trechos` e sai do lugar de origem
   **PARADA 1: mandar o roteiro de edição pro William e esperar o ok**
6. **Montar**: `montar.py` → `audio/montagem.wav` e `montagem.json` (trechos, legendas, gancho, destaque, virada, telas)
7. **Fazer a cama**: `audio/cama.py` → `cama.wav` (a voz montada já sai limpa, do `D-limpo.wav`)
8. **Telas** (em `4-edicao/telas/`, ProRes 4444 com transparência, material só na metade de cima, 1080×960):
   - tela que se repete (comparação de renders, materiais): template do Remotion em `Produção/_montagem/src/Telas.tsx`, uma `Composition` por tela no `Root.tsx`.
     `npx remotion render <Id> <saída>.mov --codec prores --prores-profile 4444 --pixel-format yuva444p10le --image-format png`
   - tela única (números, gravação de software): HyperFrames, um projeto por tela em `Produção/_telas/<reel>-<cena>/` (modelo: `reel06-cena9`, `reel06-cena6-7`). `npx hyperframes render --format mov`
   - **gravação de tela** vem crua: antes de virar tela, olhar os quadros (um a cada 0,5 s) e decupar o que serve. Tira espera de carregamento, erro de digitação, clique perdido e navegação que não ajuda; o que sobra entra sincronizado com a palavra da fala que descreve a ação. Nunca decidir pelo nome do arquivo. O som da gravação só entra se fizer parte do conteúdo (clique vai na faixa Cliques)
   - gancho: composição `Gancho` do Remotion (linhas do `edicao.json`) → `telas/gancho.mov`, com o som das teclas dentro. O `palmier.py` põe no 0:00 e tira o gancho dos textos
     `npx remotion render Gancho telas/gancho.mov --props='{"duracao": 90, "linhas": ["INFO DEMAIS", "PRA IA"]}' --codec prores --prores-profile 4444 --pixel-format yuva444p10le --image-format png`
   - anotar cada tela em `4-edicao/telas.md` (o que mostra, de onde vem cada imagem)
   - material ainda não chegou em `2-arquivos/`: `telas_provisorias.py` gera cada tela como placeholder (composição `Placeholder`), no tamanho e no tempo da definitiva, dizendo o que falta e o nome do arquivo esperado. Monta-se o reel inteiro assim; quando o material chega, renderiza-se a tela real com o mesmo nome
9. **Projeto no Palmier**: `palmier.py` grava o editável em `4-edicao/<reel>.palmier` (fica com o reel, nunca na pasta do Palmier) e `4-edicao/palmier-textos.json`. Depois, pelo MCP:
   - `manage_project` open no .palmier (o Palmier precisa estar aberto)
   - `add_texts` sem `trackIndex`, primeiro a lista `texto` e depois a `destaque` (cada chamada cria uma faixa nova no topo; o Palmier apaga as faixas vazias na primeira edição, então os índices 0 e 1 não são confiáveis). Depois renomear as duas faixas pra Texto e Destaque com `manage_tracks`
   - conferir com `capture_frame` o gancho, uma legenda sobre câmera, uma sobre tela, o destaque e o fechamento (o `inspect_timeline` ignora o zoom)
   **PARADA 2: avisar o William que o reel está no Palmier e esperar o ok ou os ajustes**
10. **Exportar e conferir**: `export_project` (mp4) só depois do ok. Depois `conferir.py "<pasta>" "<mp4 exportado>"`: acerta -14 LUFS só com ganho (o Palmier exporta ~3 dB alto), confere duração, quadro preto e estalos, e grava `5-final/<reel>.mp4`
11. **Revisor cego**: um agente que não viu nada da edição assiste ao `5-final` (quadros a cada 0,5 s + áudio) com o `padrao-edicao.md` e aponta o que quebra regra. Resultado em `4-edicao/revisor-cego.json`. Corrigir o que for erro de regra; o que for gosto vira pergunta pro William
12. **Higienizar a pasta**: em `4-edicao/` ficam só o editável, os json, `audio/` (D-eq9, D-limpo, montagem, cama), `imagem/camera-edicao.mp4` e as telas finais com nome limpo (`telas/cena3.mov`). Versões, testes e previews vão pra `4-edicao/_arquivo/`. Renomeou arquivo que o editável usa: atualizar o `media.json` dele e conferir que nenhum link quebrou
13. **Thumb**: `capa.py` (regras em "Thumb" no `padrao-edicao.md`). Levar pelo menos 3 quadros dela pra aprovação; a escolhida vai pra `5-final/capa.jpg`
14. **Entrega**: caminho do mp4 e, se houver, o que o revisor levantou que pede decisão. Pacote Premiere só se a Marilia pedir (`export_project` modo xml)

## edicao.json

Formato do reel 06 (`Produção/Lote 1.../06 .../4-edicao/edicao.json`):
- `pausas`: {cont 0.12, frase 0.2, cena 0.3}
- `trechos`: n, ilha, fonte_ini, fonte_fim (s no take), cena, pausa_antes, plano (P1, P2, P3, ÊNFASE, com "empurra" se for o caso), texto
- `fora`: ilhas descartadas e o motivo (recomeço, hesitação, versão antiga)
- `gancho`: texto enxuto da primeira frase, `linhas` (2, CAIXA ALTA), `dur_s` 3
- `virada`: nº do trecho onde o reel sai do problema e entra na solução. É ele que dá a dinâmica da cama, não o roteiro
- `destaque`: texto (2 linhas com `\n`), trecho, `comeca_em` (palavra da fala em que entra). No máximo um, ou `null` quando a receita não pede
- `cama`: `arquivo` (em `kit/trilha/`), `inicio` (s, opcional), `virada` (abre | silencio | plana), da receita da família
- `sfx`: lista de efeitos, cada um com `tipo` (impacto, whoosh, subida, pop, clique), `trecho` e `palavra` opcionais. Sem a lista, vale o pacote do reel 06
- `telas`: arquivo (em `4-edicao/telas/`), `layout` (dividida | cheia | janela), trecho em que entra, `ate_trecho` (último que ela cobre) e `paineis` (uma imagem por vez: trecho, `palavra` em que entra, titulo, arquivo esperado em `2-arquivos/`, obs). Várias imagens seguidas numa tela só, pra seguinte entrar empurrando

O `roteiro-de-edicao.md` é a versão pra ler: trecho a trecho com plano, cobertura, gancho, virada, destaque, o que ficou de fora e **Pra revisar** (fala errada ou incompleta que nenhum take resolve, com timecode; vazia quando não houver).

## Antes de seguir, conferir

| Sinal | O que fazer |
|---|---|
| `NÃO IDENTIFICADO` no organizar | abrir o arquivo, ouvir o começo, e ligar manualmente em `3-takes/` |
| `SEM TAKE DE CÂMERA` | avisar quem gravou, não inventar corte |
| `FALTOU cena N` no decupar | a frase não foi falada ou mudou no refino. Conferir contra o .docx antes de seguir |
| palavra com mais de 0,9 s na ilha, ou fala sem texto no meio dela | o Whisper engoliu um recomeço (no reel 02, "Então, além de todas as informações" duas vezes numa ilha só). Retranscrever só aquele pedaço e cortar na última versão |
| ela regravou só o fim de uma frase | partir o trecho em dois no `edicao.json` (começo da 1ª versão + fim da regravada) |
| arquivo `audio` no mapa (lapela gravada à parte) | a sincronização pela palma ainda não existe. Avisar antes de montar |
| `.docx` mais novo que o `roteiro.json` | o roteiro foi refinado. Atualizar o json a partir do docx antes de decupar |
| mediana do `rosto.json` fora de x 900-1200, y 900-1150 | o detector pegou outra coisa (nos reels 02-05, a luminária do fundo). Abrir um quadro do take antes de rodar o `imagem.py` |
| legenda caindo no rosto na tela dividida | subir a câmera (centerY), nunca a legenda |
| `AVISOS` no conferir | resolver antes de entregar |

## Áudio (em `scripts/audio/`)

Sobre o áudio do take em wav float mono 48 kHz, nesta ordem:
1. `buracos.py`: falhas de ~1 ms do microfone sem fio
2. `estalos_hf.py`: estalo curto dentro de vogal forte (a voz dela quase não tem energia acima de 9 kHz, todo estalo espirra ali)
3. `declip.py`: reconstrução do pico só abaixo de 5 kHz
4. `aspereza.py`: baixa 5-12 kHz só onde o bruto clipou
5. `cadeia_reel.py --bruto <wav do bruto>`: EQ de timbre, compressor leve, -14 LUFS e limitador com antecipação → `D-eq9.wav`. Nada de loudnorm (estalava)

Depois da cadeia: `falhas_mic.py` no take inteiro (`D-eq9` → `D-limpo`). Depois do `montar.py`: `cama.py` (trilha da receita da família). `ab.py` gera vídeo A/B quando uma escolha precisa ser de ouvido.
Conferir com `estalos_hf.detectar(x, sr, 6.0)`: no reel 06, bruto 291, tratado ~47, voz final 7.

## Palmier: o que já se sabe

- o projeto precisa estar aberto na sessão (`manage_project` open) antes de qualquer edição
- a voz entra em pedaços, um por trecho, apontando pro `D-limpo.wav` inteiro e ligada à câmera do trecho (o `palmier.py` já faz). Assim um corte puxado à mão mexe imagem e voz juntas e tem sobra dos dois lados. O `montagem.wav` fica só pra cama e pra conferência
- texto: tamanho em pontos do canvas (px = pt × 1,778); negrito precisa de `bold: true`
- não lê qtrle: tela com transparência sempre em ProRes 4444
- clipe com transparência que começa no meio de outro faz o quadro inteiro sumir na exportação: a janela sai num arquivo só por tela (o `palmier.py` já junta)
- imagem PNG sai mais quente que vídeo: quadro congelado é sempre vídeo parado (o `palmier.py` já faz)
- a soma de áudio exporta ~3 dB alta (o `conferir.py` corrige)
- não gastar crédito de geração do Palmier (música, efeito, imagem) quando há biblioteca grátis

## Referências

Todas as referências do William (reels, legenda, gancho, skills, ferramentas), com o que aproveitamos de cada uma: `Produção/referencias/LEIA-ME.md`. Consultar antes de propor estilo novo.

## Regras

- O `.docx` do reel é a versão que vale. O `roteiro.json` é derivado dele
- Nunca apagar nem renomear nada em `_brutos/`. O que sai de uso vai pra `_aposentados/` ou `_descartados/`
- Mudança de padrão só com ok do William, e vale pra todos os reels seguintes
