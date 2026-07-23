# analysis/

Saídas dos agentes de **análise**, geradas pelo pipeline no GitHub Actions.
Formato à tua escolha; uma sugestão:

- `feedback_clusters.json` - output do **Agente 1**: feedbacks classificados
  (tema, sentimento, urgência) e agrupados por dor/elogio recorrente.
- `results_report.md` - output do **Agente 3**: leitura dos resultados da campanha
  anterior, com conclusões **acionáveis e priorizadas** (que ângulo/dor priorizar
  a seguir), não só métricas.

Estes ficheiros devem ser **commitados pelo workflow**, não à mão.
