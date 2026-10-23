# PRD

## 1.1 Visão
Plataforma web em Python, com análise por streaming de dados, que ajuda **profissionais de arquitetura de cidades e planeamento de estruturas urbanas** a avaliar uma construção proposta numa área concreta. Combina:

- **Contexto geográfico/regional** (concelho, freguesia, polígono desenhado)
- **Cálculos físicos** (estrutural, térmico) com motores de engenharia validados
- **Análise de materiais** (aço, betão, madeira, compósitos)
- **Contexto ecológico** (biodiversidade, regime florestal)
- **Morfologia urbana existente** (pegadas, alturas, densidade)
- **Modelos de ML** (pré-treinados + *geographic fine-tuning*) como camada de previsão e *surrogate*, nunca como substituto único de cálculo normativo

**Decisão de formato:** aplicação web (Streamlit) com resultados progressivos (streaming de progresso e de dados) sobre backend FastAPI. Justificação: ecossistema Python/ML nativo, prototipagem rápida.

## 1.2 Público-alvo
- **Primário:** arquitetos urbanistas, planeadores municipais (câmaras, CCDR), engenheiros civis/estruturais, consultoras de ordenamento do território.
- **Secundário:** investigadores em urbanismo computacional, estudantes.

**Personas**
- *Ana, arquiteta municipal* — valida viabilidade de licenciamento em zona com regime florestal.
- *Rui, engenheiro estrutural* — pré-dimensiona vigas de aço para um edifício em Lisboa.
- *Marta, planeadora regional* — avalia impacto de uma urbanização na biodiversidade local.

## 1.3 Objetivos e métricas

| ID | Objetivo | Métrica |
|----|----------|---------|
| O1 | Reduzir a análise preliminar de um lote de dias para minutos | Tempo médio < 15 min (área ≤ 1 km²) |
| O2 | Contexto ecológico automático | 100% dos relatórios incluem camada GBIF + florestal |
| O3 | Pré-dimensionamento estrutural fiável | Desvio < 5% face a casos analíticos e ao *benchmark* sintético TimoDS (concordância com outro software FEM, não com ensaios reais) |
| O4 | Cobertura geográfica | Portugal no MVP; UE em v2.0 |
| O5 | *Fine-tuning* regional | ≥ 3 regiões configuráveis (v1.1, condicionado a haver dados regionais reais; ver F6) |

## 1.4 Funcionalidades

| ID | Feature | Descrição | Fase |
|----|---------|-----------|------|
| F1 | Seleção geográfica | Mapa interativo; coordenadas, concelho, bounding box, upload GeoJSON; validação de área | MVP |
| F2 | Contexto ecológico | GBIF (ocorrências por polígono, filtradas por licença; a licença de cada registo consta do relatório) + regime florestal (DGT, ArcGIS REST FeatureServer); PROF e corredores ecológicos por localizar | MVP |
| F3 | Morfologia urbana | OpenBuildingMap/OSM, DBSM, UMCC; métricas de densidade, altura média, coeficiente de ocupação | v1.0 |
| F4 | Cálculo físico/estrutural | Vigas de aço (IPE/HEA/HEB) com PyNite/anastruct/sectionproperties, validado com TimoDS (*benchmark* sintético, ver 1.7); simulações térmicas/fluidos: fonte de dados por definir em v1.0 (The Well fora do âmbito, ver `docs/data_sources.md`) | MVP (básico) / v1.0 |
| F5 | Materiais | Catálogo (custo, carbono, durabilidade); extração de quantidades IFC (LivingBIM, IFC-Bench) | v1.0 |
| F6 | *Geographic fine-tuning* | Pré-treino + adaptação regional **apenas com dados regionais reais fornecidos pelo utilizador**; não existe fonte pública definida | v1.1 (condicionada) |
| F7 | Relatórios | PDF; exportação GeoJSON/CSV/IFC; API REST | MVP (PDF) / v1.1 (API) |
| F8 | Streaming de dados | Leitura em streaming (Hugging Face), cache LRU, barra de progresso | v1.0 |

## 1.5 Fontes de dados: seleção justificada
Nem todas as fontes são obrigatórias. Escolhidas por fase:

| Fonte | Uso | Fase | Notas |
|-------|-----|------|-------|
| GBIF API | Biodiversidade | MVP | Excluir licenças CC BY-NC; `User-Agent` identificado; tratar HTTP 429; `limit` máx. 300 e `offset` máx. 100 000 |
| Regime florestal (DGT, ArcGIS REST FeatureServer) | Regime florestal PT | MVP | **[VERIFICAR]** licença e id da camada; PROF e corredores ecológicos não localizados |
| TimoDS (Zenodo, DOI 10.5281/zenodo.19324945) | Validação de vigas de aço | MVP | CC BY 4.0; conjunto sintético com cargas unitárias |
| The Well (`polymathic-ai/the_well`, Hugging Face) | Referência metodológica (arquiteturas e *checkpoints* de PDE) | **Fora do âmbito** | Sem dados de edifícios, microclima ou geografia; ver `docs/data_sources.md` |
| OpenBuildingMap, DBSM | Pegadas de edifícios | v1.0 | **[VERIFICAR]** |
| UMCC (Zenodo) | Classes de morfologia urbana | v1.0 | **[VERIFICAR]** |
| CITYLID, Glasgow 3D City Model, SUM4Re LiDAR | Nuvens de pontos / 3D urbano | v1.0 | Cobertura não é Portugal: usar para treino/validação de métodos |
| LivingBIM, IFC-Bench | Quantidades BIM/IFC | v1.0 | **[VERIFICAR]** |
| STEEL-3dPointClouds, Bridge Datasets | Fadiga e inspeção estrutural | v1.1+ | Opcional |
| EarthworkSat-7K, LUPAN, BuildingWorld | Segmentação de terreno/uso do solo/edifícios | v1.1+ | Opcional |
| Copernicus CLMS | Cobertura do solo | v1.0 | Requer chave **[VERIFICAR]** |

## 1.6 Requisitos não-funcionais

| Categoria | Requisito |
|-----------|-----------|
| Performance | Análise completa < 15 min (≤ 1 km²); tarefas > 30 s assíncronas |
| Escalabilidade | 50 utilizadores simultâneos |
| Disponibilidade | 99,5% |
| Segurança | JWT (Supabase Auth), RLS por utilizador |
| Privacidade/Conformidade | RGPD; dados do utilizador isolados |
| Acessibilidade | WCAG 2.1 AA (dentro dos limites do Streamlit) |
| i18n | PT-PT e EN |

## 1.7 Aviso de responsabilidade (obrigatório nos relatórios)
Os resultados são **pré-dimensionamento e apoio à decisão**. Não substituem projeto de especialidade, verificação normativa (Eurocódigos) nem parecer de entidades competentes. Cada relatório inclui este aviso, as fontes, as licenças e as versões dos dados/modelos. Os resultados estruturais são comparados com um *benchmark* sintético (TimoDS, gerado com Karamba3D) e com casos analíticos: a concordância medida (objetivo O3) não equivale a validação experimental, e os relatórios devem indicá-lo.

## 1.8 Fora de âmbito (v1)
Modelação 3D em tempo real, geração automática de plantas, plug-ins de BIM authoring (Revit/ArchiCAD), regiões fora de Portugal.

## 1.9 Critérios de aceitação do MVP
- [ ] Utilizador seleciona área e obtém contexto ecológico em < 2 min
- [ ] Pré-dimensionamento de viga de aço com desvio < 5% nos casos analíticos e no *benchmark* TimoDS
- [ ] Relatório PDF com contexto ecológico, florestal e cálculo estrutural
- [ ] Autenticação e isolamento de dados por utilizador
- [ ] Deploy em staging via CI/CD

## 1.10 Roadmap

| Fase | Duração | Entrega |
|------|---------|---------|
| MVP | 6 semanas | F1, F2, F4 básico, F7 (PDF) |
| v1.0 | +4 semanas | F3, F5, F8 |
| v1.1 | +3 semanas | F6 (se houver dados regionais), API REST |
| v2.0 | +8 semanas | Expansão UE |

## 1.11 Alterações aprovadas

| Data | Alteração | Referência |
|------|-----------|------------|
| 2026-10-06 | P1: regime florestal via ArcGIS REST da DGT, em vez de "OGC API InterGeoPT" | `docs/data_sources.md` §3 |
| 2026-10-06 | P2: The Well retirado do MVP (sem dados de edifícios, microclima ou geografia) | `docs/data_sources.md` §5 |
| 2026-10-06 | P3: F6 sem fonte pública; depende de dados regionais reais do utilizador | `docs/data_sources.md` §5 |
| 2026-10-06 | P4: GBIF filtrado por licença; licença de cada registo no relatório | `docs/data_sources.md` §2 |
| 2026-10-06 | P5: O3 mede concordância com *benchmark* sintético; dito nos relatórios | `docs/data_sources.md` §4 |
