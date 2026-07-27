# Leitura dos resultados — `prev_campaign_q1`

_Gerado automaticamente em 2026-07-27 10:36 UTC pelo pipeline (`scripts/pipeline.py`). Os números são calculados em Python (`scripts/metrics.py`); a interpretação é do modelo `gemini-2.5-flash` e foi revista por um humano antes de qualquer decisão de orçamento._

## Conclusões
*   Existe uma forte correlação (Spearman ρ = 0.943) entre o volume de menções no feedback dos utilizadores e o CVR dos criativos. Isto sugere que os criativos que abordam os temas mais mencionados no feedback tendem a ter melhor desempenho. Dentro dos ângulos `pain_resolution` e `praise_amplification`, a correlação é perfeita (ρ = 1.0).
*   O criativo `cr_A` ("Nunca mais percas uma marcacao"), focado em `pain_resolution` e `agendamento`, teve um CVR de 8.42% (IC 95%: 6.03–11.65%), sendo o melhor da campanha. O ângulo `pain_resolution` demonstrou um lift de +59% no CVR face a `praise_amplification` (p=0.0424), o que é significativo.
*   A diferença de CVR entre mobile (4.17%) e desktop (2.92%) não é estatisticamente significativa (p=0.206). Não se deve agir sobre esta diferença aparente, pois pode ser ruído.
*   Existem dores significativas no feedback dos utilizadores, como "Estabilidade e desempenho" (16 queixas, urgência 3.69/5) e "Faturação e subscrição" (14 queixas, urgência 3.86/5), que não foram abordadas por nenhum criativo nesta campanha.

## O que fazer a seguir
1.  **Amplificar criativos focados em `pain_resolution` e temas de alta urgência:** O ângulo `pain_resolution` teve um lift de +59% no CVR (p=0.0424) e o criativo `cr_A` (tema `agendamento`) obteve o melhor CVR (8.42%). O tema `agendamento` tem 26 queixas e urgência média de 3.46/5. Devemos criar mais criativos que resolvam dores específicas e urgentes dos utilizadores.
2.  **Testar novos criativos para dores não abordadas:** Há 16 queixas sobre "Estabilidade e desempenho" (urgência 3.69/5) e 14 queixas sobre "Faturação e subscrição" (urgência 3.86/5), sem criativos correspondentes. Estes temas representam dores significativas e urgentes para os utilizadores e podem ter um alto potencial de CVR, dada a correlação observada entre feedback e desempenho.
3.  **Cortar criativos de baixo desempenho e temas com pouco feedback negativo:** O criativo `cr_F` ("Integra tudo num so lugar"), com tema `integracoes`, teve o pior CVR (1.67%). O tema `integracoes` também tem o menor volume de queixas (7, urgência 3.29/5). Devemos reduzir ou eliminar o investimento em criativos com baixo desempenho e temas menos relevantes para as dores dos utilizadores.

## Limites desta leitura
*   A correlação observada entre o volume de menções no feedback e o CVR dos criativos tem um `n=6`, o que é um número pequeno de pontos de dados para uma correlação robusta.
*   Não temos dados de custo, o que significa que o CVR não pode ser diretamente traduzido em ROI.
*   Não sabemos se as impressões foram distribuídas de forma equitativa por todos os criativos, o que pode influenciar a fiabilidade das comparações de CVR entre eles.

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
| `cr_A` | agendamento | pain_resolution | 26 | **8.42%** |
| `cr_C` | poupanca_tempo | praise_amplification | 23 | **4.17%** |
| `cr_B` | suporte_lento | pain_resolution | 16 | **3.24%** |
| `cr_D` | facilidade | praise_amplification | 22 | **2.5%** |
| `cr_E` | relatorios | praise_amplification | 11 | **2.0%** |
| `cr_F` | integracoes | pain_resolution | 7 | **1.67%** |

Correlação de postos (Spearman) entre volume de feedback e CVR: **ρ = 0.943** no conjunto dos 6 criativos; ρ = 1.0 dentro de `pain_resolution` e ρ = 1.0 dentro de `praise_amplification`.

### Dores sem criativo

Temas com queixas registadas que a campanha anterior nunca abordou:

| Tema | Queixas | Urgência média | Exemplo |
|---|---|---|---|
| Estabilidade e desempenho | 16 | 3.69 | "Crashou tres vezes esta semana e perdi trabalho." |
| Faturação e subscrição | 14 | 3.86 | "Sinceramente, Fui cobrado duas vezes este mes e ninguem me explica porque." |
