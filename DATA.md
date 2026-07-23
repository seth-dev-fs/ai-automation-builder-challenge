# Dados — o que injetar e como usar

## 1. Cria a conta e o projeto PostHog

1. Regista-te em [posthog.com](https://posthog.com) (o plano grátis chega).
2. Cria um **projeto novo**. Em *Settings → Project* copia a **Project API Key**
   (`phc_...`) — é a chave de *escrita*, usada pela LP e pelo loader.
3. Em *Settings → Personal API Keys* cria uma **Personal API Key** (`phx_...`)
   com scopes de *leitura* (`query:read`, `event:read`, `insight:read`) — é a que
   os teus agentes usam para *ler* eventos.

## 2. Injeta os dados semeados

```bash
export POSTHOG_PROJECT_KEY=phc_a_tua_key
python3 scripts/load_data.py                       # EU cloud por defeito
# US: python3 scripts/load_data.py --host https://us.i.posthog.com
```

Só stdlib, sem `pip install`. Usa `--dry-run` para ver as contagens sem enviar.
Corre **uma vez** — correr de novo duplica os eventos. Podem demorar 1-2 min a
aparecer no PostHog (*Activity*).

## 3. O que fica no PostHog

Todos os eventos estão distribuídos pelos **últimos ~30 dias**.

### `feedback_submitted` (150 eventos)

Feedback de clientes, em texto (PT). Input do teu **Agente de análise**.

| Propriedade | Tipo | Exemplo |
|---|---|---|
| `feedback_type` | `praise` \| `complaint` | `complaint` |
| `text` | string | "Marcar uma sessão é sempre uma confusão..." |
| `channel` | string | `web`, `mobile`, `email_survey` |

> O **tema** de cada feedback **não** vem nas propriedades — é isso que o teu
> agente tem de inferir a partir do `text`.

### `creative_view` (2000) e `cta_click` (77)

Resultados de uma **campanha anterior** (`prev_campaign_q1`) com 6 criativos. Um
`cta_click` é uma conversão sobre o `creative_view` do mesmo criativo. Input do
teu **Agente de leitura de resultados**.

| Propriedade | Tipo | Exemplo |
|---|---|---|
| `creative_id` | string | `cr_A` … `cr_F` |
| `angle_type` | `pain_resolution` \| `praise_amplification` | `pain_resolution` |
| `theme` | string | `agendamento`, `poupanca_tempo`, … |
| `headline` | string | "Nunca mais percas uma marcação" |
| `utm_campaign` | string | `prev_campaign_q1` |
| `utm_source` | string | `facebook`, `instagram`, `google` |
| `utm_content` | string | = `creative_id` |
| `device_type` | string | `mobile`, `desktop` |

## 4. Como ler eventos (para os agentes)

Usa a **Personal API Key** com a Query API (HogQL). Exemplo:

```bash
curl -s "$POSTHOG_HOST/api/projects/$POSTHOG_PROJECT_ID/query/" \
  -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "kind": "HogQLQuery",
      "query": "SELECT properties.creative_id, count() FROM events WHERE event = '\''creative_view'\'' GROUP BY 1 ORDER BY 2 DESC"
    }
  }'
```

O [scripts/pipeline.py](./scripts/pipeline.py) já traz uma função `posthog_query()`
pronta. Também podes explorar tudo na UI (Activity / SQL / Insights) antes de
automatizar. Os eventos que a **tua** LP enviar aparecem no mesmo projeto.
