# Leitura dos resultados — `prev_campaign_q1`

_Gerado automaticamente em 2026-07-27 10:15 UTC pelo pipeline (`scripts/pipeline.py`). Os números são calculados em Python (`scripts/metrics.py`); a interpretação é do modelo `gemini-2.5-flash-lite` e foi revista por um humano antes de qualquer decisão de orçamento._

## Conclusões
* O feedback positivo dos utilizadores está diretamente correlacionado com o desempenho dos anúncios. Criativos que abordam temas com muitos elogios (como "Facilidade de uso" e "Poupança de tempo") tendem a ter um CVR mais elevado, enquanto temas com muitas queixas e poucos elogios (como "Faturação e subscrição" e "Estabilidade e desempenho") apresentam um CVR mais baixo.
* O ângulo "pain_resolution" demonstrou ser significativamente mais eficaz (lift de 59%, p=0.0424) do que "praise_amplification", indicando que resolver dores dos utilizadores é uma estratégia mais rentável para a conversão.
* A diferença de CVR entre dispositivos móveis (4.17%) e desktop (2.92%) não é estatisticamente significativa (p=0.206), pelo que não devemos tomar decisões com base nesta aparente diferença.

## O que fazer a seguir
1. **Amplificar criativos focados em "pain_resolution" e "Facilidade de uso/Poupança de tempo"**: O criativo cr_A, com tema "agendamento" (parte de "pain_resolution"), teve um CVR de 8.42%. Devemos investir mais em criativos que resolvam dores claras e que abordem os temas com mais elogios.
2. **Cortar criativos focados em "integrações"**: O criativo cr_F, com tema "integrações", teve um CVR de 1.67%, um dos mais baixos. Este tema também tem poucas menções positivas no feedback.
3. **Testar novos criativos focados em "Faturação e subscrição" e "Estabilidade e desempenho"**: Estes temas apresentam queixas com alta urgência (3.79/5 e 3.92/5 respetivamente) mas não tiveram criativos dedicados na campanha anterior. Dada a correlação entre feedback e desempenho, abordar estas dores pode gerar um aumento significativo no CVR.

## Limites desta leitura
* Não temos dados sobre a distribuição igualitária de impressões por criativo, o que pode ter influenciado o desempenho individual.
* A métrica CVR não considera o custo por clique ou por conversão, pelo que não podemos inferir o ROI (Retorno sobre o Investimento) desta campanha.
* A correlação observada (Spearman ρ = 0.829) baseia-se num número reduzido de temas (n=6), o que limita a generalização das conclusões.

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
| `cr_A` | agendamento | pain_resolution | 29 | **8.42%** |
| `cr_C` | poupanca_tempo | praise_amplification | 21 | **4.17%** |
| `cr_B` | suporte_lento | pain_resolution | 16 | **3.24%** |
| `cr_D` | facilidade | praise_amplification | 22 | **2.5%** |
| `cr_E` | relatorios | praise_amplification | 13 | **2.0%** |
| `cr_F` | integracoes | pain_resolution | 5 | **1.67%** |

Correlação de postos (Spearman) entre volume de feedback e CVR: **ρ = 0.829** no conjunto dos 6 criativos; ρ = 1.0 dentro de `pain_resolution` e ρ = 0.5 dentro de `praise_amplification`.

### Dores sem criativo

Temas com queixas registadas que a campanha anterior nunca abordou:

| Tema | Queixas | Urgência média | Exemplo |
|---|---|---|---|
| Faturação e subscrição | 14 | 3.79 | "Sinceramente, Fui cobrado duas vezes este mes e ninguem me explica porque." |
| Estabilidade e desempenho | 12 | 3.92 | "Crashou tres vezes esta semana e perdi trabalho." |
