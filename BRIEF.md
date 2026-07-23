# Desafio prático - AI Automation Builder

Parabéns por passares à fase seguinte. Este é um desafio prático, para fazeres ao
teu ritmo. Aponta a **cerca de 4 horas** de trabalho - não é para ficar perfeito,
é para vermos como pensas e constróis. Avaliamos a entrega tal como a envias, por
isso o teu texto explicativo conta muito.

## O contexto

Uma empresa recolhe feedback de clientes (elogios e reclamações) e quer
transformar isso, de forma automática, em **ideias de anúncios** que atraiam
novos clientes - resolvendo as dores mais reportadas e amplificando o que já
encanta. Queremos ver-te construir o **ciclo completo**:

```
recolha de feedback → análise → geração de criativos → medição → conclusões
```

## As ferramentas (e porquê)

- **PostHog** é a camada de dados - captura o feedback da LP e guarda os
  resultados da campanha. É onde os teus agentes vão *ler* e *escrever* eventos.
- **GitHub Actions** é a camada de automação - o pipeline dos agentes corre lá e
  faz commit dos resultados no próprio repo. Nada corre "só na tua máquina".
- **GitHub Pages** (ou Vercel/Netlify) hospeda a LP.
- **O LLM à tua escolha** (Gemini, Claude, …) faz a inteligência: classificar,
  agrupar, gerar criativos e tirar conclusões.

Não tens de usar exatamente isto, mas é o caminho que preparámos. Se trocares
alguma peça, explica porquê.

## O que te damos, já pronto

- **Dados semeados** ([data/seed_events.ndjson](./data/seed_events.ndjson)):
  ~150 `feedback_submitted` (elogios/reclamações em texto) + ~2000
  `creative_view`/`cta_click` de uma **campanha de anúncios anterior** com 6
  criativos. Dicionário completo em [DATA.md](./DATA.md).
- Um **loader** ([scripts/load_data.py](./scripts/load_data.py)) que injeta esses
  dados no teu PostHog.
- Uma **LP de arranque** ([starter/](./starter/)) com o PostHog já ligado.
- Um **esqueleto de pipeline** ([scripts/pipeline.py](./scripts/pipeline.py)) com
  a leitura do PostHog já feita - a inteligência é tua.
- **Workflows** de deploy da LP e de geração de criativos.

## Setup (checklist)

O fork copia os ficheiros, mas o GitHub, por segurança, não transporta várias
coisas para forks. Trata destes passos antes de começar (uma vez só):

1. **Fork** deste repo, para a tua conta.
2. **Ativa os Actions** no fork: separador *Actions* → "I understand my workflows,
   go ahead and enable them". Em forks os workflows vêm desativados por defeito.
3. **Workflow permissions:** *Settings → Actions → General → Workflow permissions*
   → **Read and write** (o `generate.yml` faz commit dos resultados).
4. **Pages:** *Settings → Pages → Source: GitHub Actions* (a LP publica por aí).
5. Cria uma **conta PostHog** (grátis) e um projeto. Segue o [DATA.md](./DATA.md)
   para injetar os dados com o loader e obter as chaves.
6. **GitHub Secrets** (ver a tabela mais abaixo) e as **tuas** chaves de LLM.

> Na primeira vez, o deploy do Pages pode precisar de uma segunda execução do
> workflow para o site "assentar". É normal.

## O que queremos que construas

**1. Captura.** A LP envia `feedback_submitted` para o PostHog. Decide tu as
propriedades certas.

**2. Agente de análise (feedback).** Lê os `feedback_submitted`, classifica
(tema, sentimento, urgência) e agrupa as dores/elogios recorrentes. Define tu o
contrato de output. Escreve para `analysis/`.

**3. Agente de criativo.** A partir dos clusters, gera para os 2-3 temas mais
relevantes: um ângulo de anúncio, o copy e o *prompt* de imagem (gerar a imagem
em si é opcional). Cada criativo rastreável por tag/UTM. Escreve para `creatives/`.

**4. Medição + leitura.** Um **dashboard público** no PostHog sobre os eventos da
campanha anterior, e um **agente que escreve as conclusões**: que ângulo funciona
melhor, que dor é prioritária, e o que recomendas a seguir. Escreve para
`analysis/results_report.md`.

> Os eventos de resultado que te damos são de uma campanha *anterior* - é o que o
> agente de leitura (passo 4) analisa. Os criativos *novos* que geras (passo 3)
> são para a próxima ronda. Não precisas de gerar tráfego real.

Os passos 2, 3 e 4 devem correr no **GitHub Actions** (workflow `generate.yml`) e
os resultados ficam commitados no repo.

## Entregáveis - tudo hospedado

Responde ao nosso email com **links**, não anexos:

- 🔗 **Repo público** (o teu fork) com todo o código e os resultados commitados
  em `analysis/` e `creatives/`.
- 🔗 **LP a funcionar** (GitHub Pages/Vercel) - conseguimos abrir e submeter.
- 🔗 **Dashboard público do PostHog** (Share → Enable public link).
- 🔗 A **run do GitHub Actions** que gerou os criativos (link para o workflow).
- 📝 **Texto de ~1 página** (no email ou no repo): que decisões tomaste, que
  ferramentas escolheste e porquê, onde puseste o humano no ciclo, como lidas com
  output do LLM quando vem mau, onde a IA te falhou, e o que farias com mais
  tempo. Se cortaste âmbito, diz o quê e porquê. É a peça mais importante.

## GitHub Secrets a configurar (no teu fork)

Em *Settings → Secrets and variables → Actions*:

| Secret | O que é |
|---|---|
| `POSTHOG_HOST` | `https://eu.i.posthog.com` (ou US) |
| `POSTHOG_PROJECT_ID` | ID do teu projeto PostHog |
| `POSTHOG_PERSONAL_API_KEY` | Personal API Key (leitura de eventos) |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | a(s) chave(s) de LLM que usares |

### Permissões do workflow

O `generate.yml` faz commit dos resultados no repo, por isso precisa de escrita.
Em *Settings → Actions → General → Workflow permissions*, escolhe **Read and
write**. Se a tua conta/org bloquear essa opção, cria um Personal Access Token
com scope `repo`, guarda-o como secret (ex. `GH_PAT`) e usa-o no checkout:
`actions/checkout@v4` com `token: ${{ secrets.GH_PAT }}`.

## Como avaliamos

Não procuramos acabamento visual nem cobertura total. Procuramos:

- **Raciocínio de automação** - o ciclo fecha? o criativo é rastreável até ao
  resultado? corre mesmo no Actions?
- **Rigor com o output do LLM** - validação, contrato de output, o que acontece
  quando vem malformado.
- **Qualidade das conclusões** - o que o teu agente *conclui* dos dados, não só o
  que mostra. Há um padrão real nos dados à espera de ser encontrado.

Preferimos um ciclo **estreito e sólido** a um largo e frágil.

## Stack

**Livre.** Script, n8n, o que preferires - usa a ferramenta certa e diz porquê.
**Podes usar IA à vontade** - é o trabalho; queremos ver *como* a diriges e
validas. Qualquer dúvida sobre o enunciado, pergunta.
