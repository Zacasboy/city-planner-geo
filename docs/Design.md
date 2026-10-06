# Design

Referenciado por `Rules.md`. Define o essencial para consistência da UI.

- **Fluxo principal:** Login → Selecionar área (mapa) → Configurar construção → Executar análise (progresso por etapa) → Resultados por separadores (Ecologia, Floresta, Estrutural, Morfologia, Materiais) → Exportar relatório.
- **Layout:** sidebar com projeto e parâmetros; área central com mapa/resultados; sem JavaScript customizado.
- **Componentes reutilizáveis** (`frontend/components/`): `MapSelector`, `ProgressTracker`, `ResultCard`, `ReportButton`, `DisclaimerBanner`.
- **Estados obrigatórios** em cada vista: *a carregar*, *vazio*, *erro* (mensagem acionável), *resultado parcial*.
- **Comunicação de incerteza:** previsões ML mostram intervalo/confiança e a origem (modelo + versão).
- **Cores/tipografia:** tema escuro/claro nativo do Streamlit; paleta semântica (verde = conforme, amarelo = atenção, vermelho = condicionante). Nunca usar apenas cor para transmitir estado.
- **Unidades:** SI; áreas mostradas em ha/m² conforme escala (API sempre em m²).
