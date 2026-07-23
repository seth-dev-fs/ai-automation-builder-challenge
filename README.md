# Desafio - AI Automation Builder

Faz **fork** deste repositório e trabalha a partir do teu fork.

O enunciado completo está em **[BRIEF.md](./BRIEF.md)** - começa por aí.

## O que vais construir

Um ciclo completo, automatizado, que transforma feedback de clientes em ideias de
anúncios e depois lê os resultados:

```
LP de feedback → PostHog → análise (IA) → criativos (IA) → dashboard → conclusões (IA)
```

## O que há neste repo

| | |
|---|---|
| [BRIEF.md](./BRIEF.md) | O enunciado. Lê primeiro. |
| [DATA.md](./DATA.md) | Os dados semeados, como os injetar e como os consultar. |
| [data/seed_events.ndjson](./data/seed_events.ndjson) | Dados de arranque (feedback + campanha anterior). |
| [scripts/load_data.py](./scripts/load_data.py) | Injeta os dados semeados no **teu** PostHog. |
| [scripts/pipeline.py](./scripts/pipeline.py) | Esqueleto dos 3 agentes (corre no GitHub Actions). |
| [starter/](./starter/) | LP de arranque com o PostHog já ligado. |
| [analysis/](./analysis/) · [creatives/](./creatives/) | Onde o pipeline escreve os resultados. |
| [.github/workflows/](./.github/workflows/) | Deploy da LP (Pages) + geração automática de criativos. |

## Arranque rápido

1. **Fork** deste repo.
2. Cria uma **conta PostHog** (grátis) e um projeto novo. Guarda a *Project API Key*.
3. Injeta os dados semeados:
   ```bash
   export POSTHOG_PROJECT_KEY=phc_a_tua_key
   python3 scripts/load_data.py            # --host https://us.i.posthog.com se fores US
   ```
4. Configura os **GitHub Secrets** do teu fork (ver [BRIEF.md](./BRIEF.md)).
5. Constrói o ciclo. Stack livre. Usa IA à vontade.

Tudo o que entregas deve ficar **hospedado** - links, não zips. Ver os
entregáveis em [BRIEF.md](./BRIEF.md).
