# Leitura dos resultados — `prev_campaign_q1`

_Gerado automaticamente em 2026-08-24 07:07 UTC pelo pipeline (`scripts/pipeline.py`). Os números são calculados em Python (`scripts/metrics.py`); a interpretação é do modelo `gemini-2.5-flash` e foi revista por um humano antes de qualquer decisão de orçamento._

## Conclusões
* O feedback dos utilizadores, especialmente as queixas, está fortemente correlacionado com o desempenho dos criativos. A correlação de Spearman de 0.943 (n=6) sugere que os criativos que abordam as dores mais mencionadas tendem a ter um CVR mais elevado. Isto implica que a seleção de criativos deve ser guiada prioritariamente pelas queixas dos utilizadores.
* O criativo "Nunca mais percas uma marcacao" (cr_A), com um CVR de 8.42% (IC 95%: 6.03–11.65%), foi o de melhor desempenho, alinhado com o tema "Agendamento e marcações", que gerou 27 queixas. Este resultado é consistente com a correlação observada.
* O ângulo "pain_resolution" teve um lift de +59% no CVR (4.71% vs 2.96%, p=0.0424) em comparação com "praise_amplification", indicando que focar na resolução de problemas é significativamente mais eficaz.
* A diferença aparente no CVR entre mobile (4.17%) e desktop (2.92%) não é estatisticamente significativa (p=0.206). Não se deve agir sobre esta diferença ainda, pois pode ser ruído.

## O que fazer a seguir
1. Amplificar criativos com o ângulo "pain_resolution" e focados em "Agendamento e marcações". O criativo cr_A teve um CVR de 8.42%, e o ângulo "pain_resolution" demonstrou um lift de +59%. O tema "Agendamento e marcações" é o que tem mais queixas (27).
2. Testar novos criativos que abordem as dores "Estabilidade e desempenho" (16 queixas, urgência 3.62/5) e "Faturação e subscrição" (14 queixas, urgência 3.57/5), usando o ângulo "pain_resolution". Estas dores têm alta urgência e volume de queixas, mas não foram abordadas na campanha anterior.
3. Cortar ou otimizar criativos com o tema "Integrações" e o ângulo "praise_amplification". O criativo cr_F, com o tema "Integrações", teve o pior CVR (1.67%). O ângulo "praise_amplification" teve um desempenho inferior ao "pain_resolution".

## Limites desta leitura
* A correlação observada entre o volume de menções no feedback e o CVR do criativo tem um n=6, o que é um tamanho de amostra pequeno para generalizações amplas.
* Não há dados de custo, portanto o CVR não pode ser diretamente traduzido em ROI.
* Não sabemos se as impressões foram distribuídas de forma equitativa por todos os criativos, o que pode influenciar a fiabilidade das comparações de CVR entre eles.

---

## Os números

Campanha `prev_campaign_q1` — 2000 impressões, 77 cliques, CVR global **3.85%**, 6 criativos.

### Por criativo

| Criativo | Ângulo | Tema | Headline | Vistas | Cliques | CVR | IC 95% |
|---|---|---|---|---|---|---|---|
| `cr_A` | pain_resolution | agendamento | _Nunca mais percas uma marcacao_ | 380 | 32 | **8.42%** | 6.03–11.65% |
| `cr_C` | praise_amplification | poupanca_tempo | _Poupa 5h por semana_ | 360 | 15 | **4.17%** | 2.54–6.76% |
| `cr_B` | pain_resolution | suporte_lento | _Suporte que responde em minutos_ | 340 | 11 | **3.24%** | 1.82–5.7% |
| `cr_D` | praise_amplification | facilidade | _A app que a tua equipa adora_ | 320 | 8 | **2.5%** | 1.27–4.85% |
| `cr_E` | praise_amplification | relatorios | _Relatorios que impressionam a chefia_ | 300 | 6 | **2.0%** | 0.92–4.29% |
| `cr_F` | pain_resolution | integracoes | _Integra tudo num so lugar_ | 300 | 5 | **1.67%** | 0.71–3.84% |

### Por ângulo

| Ângulo | Vistas | Cliques | CVR | IC 95% |
|---|---|---|---|---|
| `pain_resolution` | 1020 | 48 | **4.71%** | 3.57–6.18% |
| `praise_amplification` | 980 | 29 | **2.96%** | 2.07–4.22% |

### Por dispositivo e por origem

| Segmento | Vistas | Cliques | CVR | IC 95% |
|---|---|---|---|---|
| `mobile` | 1487 | 62 | 4.17% | 3.27–5.31% |
| `desktop` | 513 | 15 | 2.92% | 1.78–4.77% |
| `google` | 420 | 21 | 5.0% | 3.29–7.52% |
| `instagram` | 806 | 31 | 3.85% | 2.72–5.41% |
| `facebook` | 774 | 25 | 3.23% | 2.2–4.72% |

### Testes de significância

| Comparação | Lift | z | p | Conclusão |
|---|---|---|---|---|
| `pain_resolution` vs `praise_amplification` | +59% | 2.03 | 0.0424 | **significativo** |
| `cr_A` vs restantes | +203% | 5.146 | 2.66e-07 | **significativo** |
| `mobile` vs `desktop` | +43% | 1.264 | 0.206 | não significativo |

### Sinal do feedback vs. desempenho do criativo

Para cada criativo: quantas vezes o seu tema aparece no feedback, com a carga correspondente ao ângulo (queixas para `pain_resolution`, elogios para `praise_amplification`).

| Criativo | Tema | Ângulo | Menções no feedback | CVR |
|---|---|---|---|---|
| `cr_A` | agendamento | pain_resolution | 27 | **8.42%** |
| `cr_C` | poupanca_tempo | praise_amplification | 23 | **4.17%** |
| `cr_B` | suporte_lento | pain_resolution | 16 | **3.24%** |
| `cr_D` | facilidade | praise_amplification | 22 | **2.5%** |
| `cr_E` | relatorios | praise_amplification | 11 | **2.0%** |
| `cr_F` | integracoes | pain_resolution | 10 | **1.67%** |

Correlação de postos (Spearman) entre volume de feedback e CVR: **ρ = 0.943** no conjunto dos 6 criativos; ρ = 1.0 dentro de `pain_resolution` e ρ = 1.0 dentro de `praise_amplification`.

### Dores sem criativo

Temas com queixas registadas que a campanha anterior nunca abordou:

| Tema | Queixas | Urgência média | Exemplo |
|---|---|---|---|
| Estabilidade e desempenho | 16 | 3.62 | "Crashou tres vezes esta semana e perdi trabalho." |
| Faturação e subscrição | 14 | 3.57 | "Honestamente, Fui cobrado duas vezes este mes e ninguem me explica porque." |
