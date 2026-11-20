# Rotina diária — Notícias do mercado (CW Trader)

Runbook para a tarefa agendada que roda todo dia às 7h (America/Bahia): pesquisa as notícias de **alta relevância** do mercado financeiro, produz **1 Reel + 1 post (simples ou carrossel)** e entrega para o Caio **aprovar antes de publicar**.

## Contexto da marca
- Dono: Caio — marca **CW Trader**, perfil **@cwdaytrade** (Instagram e TikTok). O @cwtrader antigo está bloqueado: assinar sempre @cwdaytrade.
- Objetivo: autoridade, seguidores e venda da mentoria/Grupo VIP (link na bio). Mais de 10 anos de mercado.
- Sempre escrever em **português do Brasil**.
- **Privacidade:** nada de nome completo, localização ou metadados pessoais no conteúdo.
- **Compliance (obrigatório):** sem promessa de lucro, sem recomendação de compra ou venda, sem mostrar telas de opções binárias, e com aviso de risco no fim: "Conteúdo educativo e informativo. Não é recomendação de compra ou venda de ativos. Renda variável envolve risco."
- **Não publicar sem aprovação.** O Caio responde "posta" na conversa da execução, e só então se publica.

## 1. Preparar o ambiente
```bash
# repositório: djkhayo-eng/cwdaytrade-midia (se não estiver no container, usar add_repo com access=push e clonar)
cd cwdaytrade-midia/pipeline
pip install --break-system-packages -q -r requirements.txt
apt-get update -q && apt-get install -y -q espeak-ng ffmpeg
mkdir -p /home/claude/work/$(TZ=America/Bahia date +%F) && cd /home/claude/work/$(TZ=America/Bahia date +%F)
```

## 2. Pesquisar (critério de relevância)
- Janela: **últimas 12–24h**, com prioridade para o que saiu durante a noite e no pré-mercado ("em primeira mão").
- Fazer buscas separadas, em modo `extended` para notícias recentes:
  - **Brasil:** Ibovespa, dólar, Copom/Selic, IPCA, fiscal, Petrobras, Vale, bancos, CVM/BC
  - **EUA:** Fed, CPI, payroll, S&P/Nasdaq, balanços de big techs, grandes IPOs e fusões
  - **Cripto:** BTC/ETH
  - **Global:** petróleo, China, guerras ou tarifas com efeito no mercado
- **Só entra se for de alta relevância:**
  - movimento forte: índice ±2%, dólar ±1%, ação gigante ±5%, BTC ±5%
  - decisão de banco central
  - dado macro que mudou expectativa
  - IPO ou fusão histórica
  - regulação que afeta o investidor
  - evento que todo mundo vai comentar hoje
- **Verificar** cada número em ≥2 fontes confiáveis (preferência por fonte primária: B3, BC, Fed, RI da empresa, Reuters, Bloomberg, CNBC, Valor, InfoMoney). Anotar horário e fonte de cada número.
- **Não repetir tema** já coberto: conferir o log (`claude/rotina-noticias-log.md` no Projeto "CW TRADER", se a ferramenta Projects existir) e a pasta `noticias/` deste repo.
- Se **nenhuma notícia** passar no critério: não produzir nada. Mandar só "Hoje não teve notícia com relevância suficiente" e citar as 2–3 candidatas descartadas.

## 3. Roteiro
**Reel (35–55s, narrado):**
- **Gancho ≤3s:** contraste de número ("Maior IPO da história… e quem comprou perdeu").
- **Desenvolvimento:** contexto → números → o que aconteceu.
- **Lição de trader:** contexto, risco, plano, não operar no hype.
- **CTA:** "Salva e segue… link na bio".
- Números escritos **por extenso** no texto da narração ("oitenta e três dólares"); nas legendas aparecem em algarismos (merges.json).

**Post:**
- Carrossel de 5–7 slides (capa → dado → lista de números → lição → CTA com fontes). Se a notícia for simples, basta 1 post.
- Legenda com palavras-chave, **sem hashtags**: gancho, números em tópicos, lição, CTA, aviso de risco.

## 4. Narração (ElevenLabs pelo Chrome do Mac)
- Usar o Claude in Chrome no Mac do Caio: https://elevenlabs.io/app/speech-synthesis/text-to-speech
  - voz "Michael Bill - Confident, Expressive"
  - modelo Eleven v4
- Limpar o texto (cmd+a, Delete), digitar o roteiro e clicar em "Gerar fala". Depois baixar pelo ícone de download no player de baixo.
- O arquivo vai para `/Users/caiowendel/Downloads/ElevenLabs_*.mp3`. Puxar com `device_stage_files` e copiar como `voz_raw.mp3`.
- **Créditos:** o plano grátis tem 10 mil caracteres/mês, e cada Reel gasta ~900. **Se os créditos acabarem:** fazer o Reel **sem narração** (texto na tela + trilha) e avisar o Caio.
- **Se o Mac ou o Chrome estiverem offline:** fazer o Reel sem narração e avisar.
- **Nunca** digitar senhas nem chaves de API.

## 5. Alinhar a legenda palavra por palavra
```bash
printf '%s\n' "parágrafo 1" "parágrafo 2" ... > script.txt   # 1 parágrafo por linha = 1 cena
ffmpeg -y -i voz_raw.mp3 -ac 1 -ar 44100 voz_raw.wav
echo '{"IPO":"i pê ó"}' > say.json        # pronúncias de siglas/nomes estrangeiros para o espeak
python3 /caminho/pipeline/align.py        # gera words.json
echo '[[["oitenta","e","três","dólares"],"US$ 83,"]]' > merges.json && python3 /caminho/pipeline/merge_words.py
```

## 6. Montar o Reel
- Copiar `exemplos/reel_ipo_anthropic.py` para o diretório de trabalho (como reel.py; ajuste PIPELINE se o repo não estiver em /home/claude/cwdaytrade-midia) e adaptar as cenas.
  - `NP` = número de parágrafos
  - funções `s_*` = uma por cena
  - `K(p, "palavra")` = tempo da palavra
  - `slam`, `text3d`, `label`, `chart`, `ticker_card`, `confetti`, `draw_tape`
- Formato: 1080x1920, 30fps. Legendas em y≈1340; área segura com topo >180px e fundo <1560px.
- **Mídias do Caio** (puxar com `device_stage_files`, no máximo 400MB por arquivo):
  - `/Users/caiowendel/Documents/CWTrader-Instagram/04-Banco-de-midia/` (fotos: retratos, setup-trader, lifestyle-viagem-praia)
  - `/Users/caiowendel/Documents/CWTrader-Instagram/05-Videos-originais/`, que inclui `RPReplay_Final1692063704.mov`, ele dando aula de blazer azul (enquadrar com zoom 1.35 e cy=0.25 para esconder o texto embutido)
  - `/Users/caiowendel/Documents/CWTrader-Instagram/03-Conteudo/Videos-sem-edicao/`
- **Regras de imagem:**
  - Não repetir o b-roll do dia anterior.
  - Foto com mão ou dedos à mostra: **não usar recorte 2.5D** (fica deformado). Usar a foto inteira com zoom lento.
  - Nunca navegar pela biblioteca do app Fotos inteira, porque tem conteúdo íntimo e privado. Usar só as pastas acima ou um vídeo que o Caio indicar.
  - Não usar foto de pessoa pública nem logo de empresa. Nome em texto pode.
- **Gráficos:** se a trajetória entre pontos reais for ilustrativa, escrever isso no gráfico ("trajetória ilustrativa · preços: fonte").
- **Render:** `python3 reel.py info`, depois 2 processos em paralelo (`render 0 N/2 pa.mp4` e `render N/2 N pb.mp4`), depois concat.
- **Áudio:** `python3 /caminho/pipeline/music_sfx.py` (lê timeline.json, gera music.wav e sfx.wav), depois `bash /caminho/pipeline/mix.sh voz_raw.mp3 $DUR`, depois mux com aac 256k e `-movflags +faststart`.
- **Revisão (QC):** folha de quadros a cada ~3s, conferindo números, acentos, texto cortado, sobreposição com o rosto e legenda dentro da área segura.

## 7. Carrossel
```bash
python3 /caminho/pipeline/carousel.py spec.json slides/   # ver exemplos/carrossel_ipo_spec.json
```
Formato 1080x1350 (4:5). A capa pode usar uma foto do Caio no `bg`.

## 8. Entregar para aprovação
1. Salvar no Mac (`device_commit_files`) em `/Users/caiowendel/Documents/CWTrader-Instagram/03-Conteudo/Noticias/AAAA-MM-DD/`: o reel, a capa, os slides e um `legendas.txt`.
2. Subir as mídias neste repo em `noticias/AAAA-MM-DD/`. Fazer commit e push com:
   `git -c user.name="cwdaytrade" -c user.email="noreply@users.noreply.github.com"`
   - Usar as URLs raw **com o SHA do commit**, por causa do cache: `https://raw.githubusercontent.com/djkhayo-eng/cwdaytrade-midia/<SHA>/noticias/...`
3. Enviar ao Caio (SendUserFile com o reel e os slides, mais uma mensagem curta e push notification):
   - manchete e por que importa (1 linha)
   - as legendas
   - as fontes
   - "Responde **posta** que eu publico no Instagram e no TikTok"
4. Registrar no log do Projeto (`claude/rotina-noticias-log.md`): data, tema, fontes, status "aguardando aprovação".

## 9. Publicar (somente depois do "posta")
**Instagram** (Windsor MCP, conector `instagram`, conta `17841423682481883`):
- Reel: `create_video_post` com `video_url` (raw do SHA), `cover_url`, `share_to_feed: true` e `caption`.
- Carrossel: `create_carousel_post` com `image_urls` (2–10 JPEG ≤8MB, 4:5) e `caption`.
- Post simples: `create_image_post`.

**TikTok** (Metricool MCP `createScheduledPost`, blogId `8160128`, timezone `America/Bahia`):
- Data = agora + 6 min.
- `providers [{network: tiktok}]`, `autoPublish: true`.
- `tiktokData` com `title` (obrigatório) e `isAigc: true`, porque a voz é sintética.
- `videoThumbnailUrl` = capa.
- Para o carrossel no TikTok, mandar as imagens em `media`.

**Depois de publicar:** atualizar o log para "publicado", com o media id e o link do planner.
