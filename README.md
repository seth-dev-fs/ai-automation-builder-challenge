# Feedback de clientes → ideias de anúncios → leitura dos resultados

Resposta ao desafio *AI Automation Builder*. O enunciado original está em
[BRIEF.md](./BRIEF.md); o raciocínio por trás das decisões está em
**[DECISIONS.md](./DECISIONS.md)**, que é a parte que interessa ler.

## Links

| | |
|---|---|
| Página de feedback | https://seth-dev-fs.github.io/ai-automation-builder-challenge/ |
| Dashboard público (PostHog) | https://eu.posthog.com/shared/EkA54izBuK7urXIjgy7yQV1tT16HVg |
| Execuções do pipeline | [Actions → Gerar análise e criativos](../../actions/workflows/generate.yml) |
| Leitura dos resultados | [`analysis/results_report.md`](./analysis/results_report.md) |
| Criativos propostos | [`creatives/`](./creatives/) |

## O ciclo

```
    Landing page  ──feedback_submitted──▶  PostHog
                                             │
                                             ▼
                              ┌──────── GitHub Actions ────────┐
                              │                                │
                              │  1. Agente de análise          │──▶ analysis/feedback_clusters.json
                              │     classifica tema/urgência   │──▶ PostHog: feedback_classified
                              │                                │
                              │  2. Agente de resultados       │──▶ analysis/results_report.md
                              │     lê a campanha anterior     │
                              │                                │
                              │  3. Agente de criativo         │──▶ creatives/*.md  (Pull Request)
                              │     escreve os anúncios novos  │──▶ PostHog: creative_generated
                              └────────────────────────────────┘
                                             │
                                    revisão humana (merge)
                                             │
                                             ▼
                                  PostHog: creative_approved
                                             │
                                             ▼
                                        Dashboard
```

## Estrutura

| Ficheiro | O que faz |
|---|---|
| [`scripts/pipeline.py`](./scripts/pipeline.py) | Orquestrador. Lê, chama os três agentes, escreve. |
| [`scripts/llm.py`](./scripts/llm.py) | Wrapper do LLM: contrato de output, validação, retry com o erro reinjetado, desistência controlada. |
| [`scripts/metrics.py`](./scripts/metrics.py) | CVR, intervalos de Wilson, teste z, Spearman. **Toda a aritmética do relatório.** |
| [`scripts/taxonomy.py`](./scripts/taxonomy.py) | Enum fechado de temas + classificador determinístico de recurso. |
| [`scripts/posthog_io.py`](./scripts/posthog_io.py) | Leitura (HogQL) e escrita (capture) no PostHog. |
| [`scripts/agents/`](./scripts/agents/) | Um módulo por agente. |
| [`scripts/make_dashboard.py`](./scripts/make_dashboard.py) | Cria o dashboard e os seus insights por API, para poder ser recriado. |
| [`scripts/register_approval.py`](./scripts/register_approval.py) | Regista no PostHog o que o humano aprovou. |

## Correr

```bash
# sem rede e sem gastar quota — usa data/seed_events.ndjson
python3 scripts/pipeline.py --offline

# contra o PostHog
export POSTHOG_HOST=https://eu.i.posthog.com
export POSTHOG_PROJECT_ID=...
export POSTHOG_PERSONAL_API_KEY=phx_...
export POSTHOG_PROJECT_KEY=phc_...
export GEMINI_API_KEY=...
python3 scripts/pipeline.py

# recriar o dashboard
python3 scripts/make_dashboard.py
```

Sem dependências — só a biblioteca padrão do Python 3.12. O `requirements.txt`
está vazio de propósito ([porquê](./DECISIONS.md)).

O modelo e o ritmo das chamadas são variáveis de repositório
(`GEMINI_MODEL`, `GEMINI_MIN_INTERVAL`), para se ajustarem aos limites do plano
em uso sem mexer no código.

## O que os dados dizem

A ordem dos temas por volume de feedback reproduz a ordem dos criativos por taxa
de conversão — Spearman ρ = 1,0 dentro dos anúncios que resolvem uma dor.
O detalhe está em [`analysis/results_report.md`](./analysis/results_report.md) e
a discussão em [DECISIONS.md](./DECISIONS.md).
