# Auditoria de fontes de dados (T0.5)

**Data:** 2026-10-06 | **Âmbito:** fontes do MVP (GBIF, serviço florestal, TimoDS, The Well)
**Método:** consulta a documentação oficial e a registos públicos. Os endpoints **não** foram
testados a partir do ambiente de desenvolvimento (sem acesso de rede a esses domínios): os testes
ao vivo estão na secção 6 e devem ser corridos na máquina do utilizador.
**Legenda:** ✅ confirmado em fonte oficial · ⚠️ confirmado só em fonte de terceiros · ❓ não confirmado

## 1. Resumo

| Fonte | Acesso | Licença | Estado para o MVP |
|-------|--------|---------|-------------------|
| GBIF occurrence API | REST, sem autenticação (pesquisa) | Por registo (CC0, CC BY, CC BY-NC) | ✅ Pronta |
| Regime florestal (DGT) | ArcGIS REST FeatureServer | ❓ não confirmada | ⚠️ Pronta tecnicamente; licença e PROF por confirmar |
| TimoDS | Download Zenodo (2 CSV) | CC BY 4.0 | ✅ Pronta, com ressalvas de uso (secção 4) |
| The Well | Streaming Hugging Face (`the_well`) | CC BY 4.0 num dataset verificado; os restantes ❓ | ❌ **Fora do MVP** (P2 aprovada; secção 5) |

## 2. GBIF

- **Base:** `https://api.gbif.org/v1/` ✅. Pesquisa de ocorrências: `/occurrence/search` ✅.
- **Filtro espacial:** parâmetro `geometry` em WKT (POINT, LINESTRING, POLYGON, MULTIPOLYGON) ⚠️.
  Enviar sempre polígonos com anel **anti-horário** (`shapely.geometry.polygon.orient(p, 1.0)`):
  a documentação do cliente rgbif, a propósito dos *downloads*, refere que WKT em sentido horário pode devolver zero resultados.
- **Paginação:** `limit` máximo **300** por pedido; `offset` máximo **100 000** (acima devolve HTTP 400) ⚠️.
  Para áreas ≤ 1 km² é improvável atingir o teto; se acontecer, dividir por ano ou dataset.
- **Autenticação:** a pesquisa não exige; os *downloads* exigem conta GBIF (HTTP Basic) ✅.
- **Limites de taxa:** não há valor fixo. A GBIF avisa que pedidos rápidos podem receber **HTTP 429** e que
  o limite varia com a carga ✅. Recomenda definir `User-Agent` com URL ou email e usar o *download*
  se um script demorar mais de 15 min ✅.
  > Correção: o valor "100 pedidos/minuto" que circulou no rascunho inicial é do iNaturalist, não do GBIF.
- **Licença:** definida **por registo/dataset**; existe o endpoint `/enumeration/license` ✅ e o
  filtro `license` (ex.: `license=CC0_1_0`) ⚠️. Uso comercial ou em relatórios entregues a clientes:
  filtrar por `CC0_1_0` e `CC_BY_4_0` e **excluir `CC_BY_NC_4_0`**; citar sempre o dataset. Termos: gbif.org/terms ⚠️.
- **Consulta base recomendada:**
  `occurrence/search?geometry=<WKT>&hasCoordinate=true&hasGeospatialIssue=false&license=CC0_1_0&license=CC_BY_4_0&limit=300`

## 3. Regime florestal (substitui "OGC API InterGeoPT" no PRD)

**Achado:** o serviço OGC API Features da DGT encontrado
(`infogeo.dgterritorio.gov.pt/arcgis/rest/services/ptp_oigp/OGCFeatureServer`) ✅ expõe **uma única
coleção (id `0`)** de conteúdo desconhecido ❓, sem indício de ser o regime florestal.

O regime florestal existe noutro serviço, **ArcGIS REST FeatureServer** (não OGC API):

- **Serviço:** `https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/Regime_florestal/FeatureServer` ✅
- **Camada:** "Regime florestal", polígonos; a listagem mostra o id **1562** ❓ (confirmar; camadas alojadas costumam ter id 0).
- **Campos vistos:** `codigo` (campo de apresentação) e `regime` (texto, 254) ✅. Lista completa ❓.
- **Capacidades:** formatos JSON/GeoJSON/PBF, paginação, consultas avançadas, **`MaxRecordCount` 2000** ✅.
- **Sistema de coordenadas nativo:** 3857 ✅. Pedir `inSR=4326&outSR=4326` (Rules R1).
- **Licença:** o campo *Copyright Text* está vazio ❓. **Confirmar nos metadados** (dados.gov.pt / SNIG) antes de redistribuir.
- **PROF e corredores ecológicos** (previstos na F2 do PRD): **não localizei** serviço equivalente ❓. Os serviços do ICNF
  (`sigservices.icnf.pt/server/rest/services/...`) existem ✅, mas não verifiquei que camadas expõem.
- **Consulta base:** `.../FeatureServer/<id>/query?where=1=1&geometry=<polígono>&geometryType=esriGeometryPolygon&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=codigo,regime&outSR=4326&f=geojson`

## 4. TimoDS

- **Registo:** Zenodo, DOI `10.5281/zenodo.19324945`, versão 1.0 (30-03-2026), **CC BY 4.0** ✅ (via repositório da Universidade de Granada).
- **Conteúdo:** 60 000 vigas de aço Timoshenko, perfis europeus IPE/HEA/HEB, comprimento e **12 rigidezes de apoio elástico**; 6 casos de carga unitários por viga ✅.
- **Saídas:** 21 posições ao longo da viga, **253 grandezas** por instância ✅. Ficheiros: `input_data_TimoDS.csv` e `beam_results_TimoDS.csv` ✅.
- **Geração:** Latin Hypercube com semente fixa, Grasshopper + **Karamba3D** ✅.
- **Ressalvas para o projeto:**
  1. É um conjunto **sintético**: valida o nosso motor contra *outro software de elementos finitos*, não contra ensaios reais.
  2. Só tem cargas **unitárias**: cargas reais exigem sobreposição; o objetivo O3 (< 5%) mede concordância com este *benchmark*.
  3. Apoios elásticos gerais: apoios simples ou encastrados do PyNite têm de ser mapeados para rigidezes (livre ↔ quase encastrado).
  4. O repositório do pipeline indicado no registo parece ser um marcador de posição (`yourusername`) ❓: não contar com ele.
  5. Não substitui a verificação normativa (Eurocódigos).

## 5. The Well

- **Conteúdo:** 15 TB, **16 datasets**, de 6,9 GB a 5,1 TB cada ⚠️. Domínios: sistemas biológicos, dinâmica de fluidos, dispersão acústica,
  magnetohidrodinâmica astrofísica ⚠️. A listagem inclui, por exemplo, `active_matter`, `shear_flow`, `rayleigh_benard`, `acoustic_scattering_*`.
- **Acesso:** pacote PyPI `the_well` (Python ≥ 3.10), `hf://datasets/polymathic-ai/`, CLI `the-well-download`; checkpoints (ex.: `polymathic-ai/FNO-active_matter`) ⚠️.
- **Licença:** `cc-by-4.0` no dataset `MHD_64` ✅; os outros 15 ❓ (verificar um a um).
- **Achado principal:** pelo resumo do artigo e pela lista de datasets, nenhum é de **física de edifícios, microclima urbano ou geografia**:
  são *benchmarks* genéricos de PDE (o mais próximo de térmica é `rayleigh_benard`, convecção genérica sem relação com edifícios).
  Consequências:
  1. A F4 ("simulações térmicas/fluidos" por The Well) **não tem dados de entrada relevantes** para uma construção num local.
  2. A F6 ("*fine-tuning* geográfico a partir do The Well") **não tem base geográfica**: não há dimensão regional nos dados.
  3. O valor real é **metodológico**: arquiteturas (FNO, U-Net) e *checkpoints* pré-treinados para *surrogates* de PDE.
- **Custo/risco:** *download* completo inviável; *streaming* tem latência e depende da Hugging Face; exige PyTorch (dependência pesada).

## 6. Testes ao vivo (correr na máquina do utilizador)

```bash
# GBIF: polígono pequeno em Lisboa (anti-horário), deve devolver count e results
curl -s -A "city-planner-geo (contacto: <o-seu-email>)" \
 "https://api.gbif.org/v1/occurrence/search?geometry=POLYGON((-9.16%2038.70,-9.14%2038.70,-9.14%2038.72,-9.16%2038.72,-9.16%2038.70))&hasCoordinate=true&limit=1" | head -c 400; echo

# Licenças suportadas pelo GBIF
curl -s https://api.gbif.org/v1/enumeration/license | head -c 400; echo

# Regime florestal: metadados da camada (confirmar id, campos, licença)
curl -s "https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/Regime_florestal/FeatureServer?f=json" | head -c 800; echo
curl -s "https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/Regime_florestal/FeatureServer/layers?f=json" | head -c 1500; echo

# OGC API da DGT: o que é a coleção 0?
curl -s "https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/ptp_oigp/OGCFeatureServer/collections?f=json" | head -c 800; echo
```

## 7. Decisões (P1–P5 aprovadas em 2026-10-06 e aplicadas a PRD, arquitetura, Rules e Tasks)

| # | Proposta | Documentos afetados |
|---|----------|---------------------|
| P1 | Serviço florestal passa a usar o **ArcGIS REST FeatureServer** da DGT em vez de "OGC API InterGeoPT" | PRD (F2, 1.5), System_Architecture, Tasks (T1.5), Rules (R2) |
| P2 | **Retirar o The Well do MVP.** O estrutural usa só PyNite/anastruct validado com TimoDS; avaliar em v1.0 se existe dataset realmente urbano/térmico | PRD (F4, F6, 1.5), System_Architecture, Tasks (T2.5, T3.1), memory (D5) |
| P3 | F6 (*fine-tuning* geográfico) fica **sem fonte de dados definida** até haver dados regionais reais (ex.: do utilizador) | PRD (F6), Tasks (T3.1) |
| P4 | Filtrar GBIF por licença (excluir CC BY-NC) e registar a licença de cada registo no relatório | PRD, Rules (R2) |
| P5 | Tratar o O3 (< 5%) como concordância com um *benchmark* sintético e dizê-lo nos relatórios | PRD (1.3, 1.7) |

## 8. Pontos em aberto

- [ ] Licença da camada "Regime florestal" (metadados DGT/SNIG)
- [ ] Id e campos completos da camada; o que é a coleção `0` do OGC API da DGT
- [ ] Existência e acesso a PROF e corredores ecológicos
- [x] Licença dos 15 datasets restantes do The Well: dispensada (P2 aprovada)
- [ ] Resultado dos testes da secção 6
