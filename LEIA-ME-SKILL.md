# Skill de edição de reels do 9barra7

Leva o take bruto da Marilia até o reel pronto no Palmier Pro. O padrão é o do reel 06 (29.09 Bastidor de projeto real).

## O que tem aqui

- `.claude/skills/editando-reels-9barra7/`: a skill (instruções, `padrao-edicao.md` e scripts)
- `Produção/kit/`: fonte, logo, efeitos sonoros, cama sonora e fechamento da marca
- `Produção/_montagem/`: modelos de tela do Remotion (as que se repetem)
- `Produção/_telas/`: telas feitas uma vez só, no HyperFrames (as do reel 06 servem de modelo)

## Instalar (pedir ao Claude Code, dentro da pasta do 9barra7)

> Instala a skill do repositório github.com/william-meurer/editando-reels-9barra7 nesta pasta seguindo o LEIA-ME-SKILL.md

O que o Claude Code faz:
1. clona o repositório numa pasta temporária e copia `.claude/skills/editando-reels-9barra7/` e `Produção/kit`, `Produção/_montagem`, `Produção/_telas` pras mesmas pastas aqui, sem apagar nada do que já existe
2. confere o que precisa estar instalado no Mac (Apple Silicon):
   - `brew install ffmpeg node`
   - `pip3 install numpy scipy soundfile opencv-python pillow mlx-whisper`
   - `npm install` dentro de `Produção/_montagem`
3. confere se o `.mcp.json` da pasta tem o servidor `palmier-pro` (Palmier Pro instalado e aberto)

Depois é só pedir, por exemplo: "edita o reel 07".

## Atualizar

Quando a skill melhorar, pedir ao Claude Code: "atualiza a skill de reels pelo GitHub". Ele baixa a versão nova e copia por cima só as pastas acima.
