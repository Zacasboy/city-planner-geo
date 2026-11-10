# Auditoria de fontes de dados (T0.5)

**Data:** 2026-10-06 | **Âmbito:** fontes do MVP (GBIF, serviço florestal, TimoDS, The Well)
**Método:** consulta a documentação oficial e a registos públicos. Os endpoints **não** foram
testados a partir do ambiente de desenvolvimento (sem acesso de rede a esses domínios): os testes
ao vivo estão na secção 6 e devem ser corridos na máquina do utilizador.
**Legenda:** ✅ confirmado em fonte oficial · ⚠️ confirmado só em fonte de terceiros · ❓ não confirmado

## 1. Resumo

| Fonte | Acesso | Licença | Estado para o MVP |
|-------|--------|---------|-------------------|
| GBIF occurrence API | REST, sem autenticação (pesquisa) | Por registo (CC0, CC BY, CC BY-NC ou sem licença); só CC0 e CC BY aceites | ✅ Pronta |
| Regime florestal (DGT) | ArcGIS REST FeatureServer | ❓ não confirmada | ⚠️ Pronta tecnicamente (camada 1562, 209 polígonos); licença e PROF por confirmar |
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
  aceitar só `CC0_1_0` e `CC_BY_4_0` (lista de permitidos, ver abaixo); citar sempre o dataset. Termos: gbif.org/terms ⚠️.
- **Consulta base recomendada:**
  `occurrence/search?geometry=<WKT>&hasCoordinate=true&hasGeospatialIssue=false&license=CC0_1_0&license=CC_BY_4_0&limit=300`

### Testes ao vivo (2026-10-06)

- Polígono de cerca de 3,8 km² em Lisboa: **19 965** ocorrências com coordenadas; **17 146** com licença CC0 ou CC BY (86%);
  **2 819** (14%) ficam de fora com o filtro. O filtro `license=CC0_1_0&license=CC_BY_4_0` funciona ✅.
- `/enumeration/license` devolve **5 valores**: CC0, CC BY 4.0, CC BY-NC 4.0, `UNSPECIFIED` e `UNSUPPORTED` ✅.
  Excluir só o CC BY-NC deixaria passar registos sem licença clara, por isso a regra é uma **lista de permitidos** (CC0 e CC BY 4.0).
- **Facetas:** `facet=speciesKey&facetLimit=3&limit=0` devolve as espécies mais registadas **num só pedido** ✅ (neste teste, sem filtro de
  licença: 1442, 1409 e 1142 ocorrências). Os nomes vêm como chaves numéricas; a resolução em nomes científicos (`/species/{key}`) não foi testada ❓.
- Paginar 19 965 registos seriam cerca de 67 pedidos de 300. Para o relatório ecológico usar **facetas** (lista de espécies com contagens)
  e paginar só se for preciso mostrar registos individuais.
- As contagens são de **ocorrências registadas**: refletem esforço de observação (o primeiro registo devolvido é de ciência cidadã), não abundância.
  Os relatórios não devem apresentá-las como população.

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

### Testes ao vivo (2026-10-06)

- **Camada confirmada:** id **1562** ✅, 14 campos: `fid`, `codigo`, `id_maper`, `id_rf`, `nome`, `tipologia`, `regime`, `proprieda`, `ent_ges`, `reg_flo`,
  `ges_icnf`, `area_ha`, `SHAPE__Length`, `SHAPE__Area` ✅. Exportação em geojson, shapefile, csv, filegdb e sqlite ✅.
- **Tamanho:** apenas **209 polígonos** no total ✅ (extent compatível com Portugal continental). Uma caixa de teste no Pinhal de Leiria
  (-8,98 a -8,90; 39,70 a 39,80) interseta **2** ✅. Se os 209 são a cobertura completa do regime florestal ❓ (comparar com o ICNF).
- **Licença:** `copyrightText` e `description` vazios na camada e no serviço ✅; a pesquisa em dados.gov.pt não encontrou a ficha desta camada.
  **Continua por confirmar** ❓: perguntar ao ICNF/DGT ou localizar o item no portal da DGT (id do item `455721f00bdc4253afe02f572d8d14e2`).
- **Recomendação (a decidir na T1.5):** como são 209 polígonos (abaixo do limite de 2000 por pedido), descarregar a camada inteira num pedido e
  guardá-la em PostGIS com atualização periódica, em vez de consultar o serviço da DGT em cada análise. Reduz a dependência externa (R1) e a latência.
- **Coleção `0` da OGC API da DGT:** é o conjunto `PTP_AIGP`, área de intervenção das 62 OIGP aprovadas (ligações a plantas e a candidaturas do
  Fundo Ambiental) ✅. Não é regime florestal: **confirma P1**. A resposta não expande a sigla OIGP.

## 4. TimoDS

- **Registo:** Zenodo, DOI `10.5281/zenodo.19324945`, versão 1.0 (30-03-2026), **CC BY 4.0** ✅ (via repositório da Universidade de Granada).
- **Conteúdo:** 60 000 vigas de aço Timoshenko, perfis europeus IPE/HEA/HEB, comprimento e **12 rigidezes de apoio elástico**; 6 casos de carga unitários por viga ✅.
- **Saídas:** 21 posições ao longo da viga, **253 grandezas** por instância ✅. Ficheiros: `input_data_TimoDS.csv` e `beam_results_TimoDS.csv` ✅.
- **Geração:** Latin Hypercube com semente fixa, Grasshopper + **Karamba3D** ✅.
- **Ressalvas para o projeto:**
  1. É um conjunto **sintético**: valida o nosso motor contra *outro software de elementos finitos*, não contra ensaios reais.
  2. Só tem cargas **unitárias**: cargas reais exigem sobreposição; o objetivo O3 (< 5%) mede concordância com este *benchmark*.
  3. Apoios elásticos gerais: apoios simples ou encastrados do PyNite têm de ser mapeados para rigidezes (livre ↔ quase encastrado).
  4. A descrição do registo ainda mostra um marcador (`yourusername`), mas os metadados apontam para um repositório real, https://github.com/YDERRAZI/TimoDS_pipeline ✅ (não consultado a partir do ambiente de desenvolvimento).
  5. Convenções deduzidas dos dados (unidades kN e m; `Lcase` 1 a 6 = Fx, Fy, Fz, Mx, My, Mz unitários em `a·L`; molas `k_*`/`c_*` nos extremos A e B; vigas de Timoshenko): ver `backend/app/services/timods_benchmark.py`.
  6. Não substitui a verificação normativa (Eurocódigos).

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

## 5b. OpenBuildingMap (T2.1)

**Estado:** ✅ testado ao vivo em 2026-11-02 (`scripts/check_obm.py`): quarteirão de Lisboa (~1 km²), tile `033110` encontrado, **2065 edifícios em 11,8 s**, sem tiles em falta; só **19 %** com altura (muito abaixo dos 75 % globais). O esquema e a projeção das secções abaixo vêm da documentação do autor e de terceiros.

- **O que é:** 2,69 mil milhões de pegadas (OSM de 2024-07-01, Google Open Buildings, Microsoft ML Footprints) com altura, ocupação e área útil; artigo em Scientific Data (DOI 10.1038/s41597-025-06132-z); dados em GFZ (DOI 10.5880/GFZ.LKUT.2025.002) ✅.
- **Licença:** ODbL v1.0 ✅ (descrição dos dados do GFZ). Obriga a citar a fonte e a partilhar bases derivadas nas mesmas condições; os relatórios citam "OpenBuildingMap (Oostwegel et al., 2025), ODbL v1.0".
- **Acesso:** não há API. Ficheiros `building.<quadkey>.parquet` por tile de nível 6, em `s3://us-west-2.opendata.source.coop/tge-labs/openbuildingmap/` (acesso anónimo), ordenados por curva de Hilbert; ~194 GB no total ⚠️ (blogue de terceiros). A leitura filtra pela coluna `bbox` e só lê os row groups necessários (testado com Parquet sintético).
- **Tiles de Portugal continental:** `031332` e `033110` (Lisboa em `033110`).
- **Esquema:** `id`, `geometry` (WKB), `bbox{xmin,ymin,xmax,ymax}`, `height` (texto), `occupancy`, `source`, `floorspace`, `quadkey`, ... ⚠️. A projeção do Parquet não está confirmada (o GPKG original é EPSG:3857): o código deteta-a pelas estatísticas da `bbox` e aceita as duas.
- **Alturas:** ~25 % dos edifícios não têm. Formatos `H:n` (pisos), `HAPP:n`, `HBET:a,b` (intervalo), `HHT:m` (metros), combináveis com `+`. Pisos a 3 m. As métricas de altura usam só edifícios com altura; o `floor_area_ratio` é um **limite inferior** (sem altura conta 1 piso).
- **Ocupação:** ~60 % `UNK`; só `RES`, `COM` e `IND` entram nas percentagens por tipo.
- **Limites:** áreas até 5 km² (400 acima), cache de 24 h, timeout de 30 s (504); falha de leitura → 503.

## 5c. GlobalBuildingAtlas — alturas estimadas (T2.1)

**Estado:** ✅ testado ao vivo em 2026-11-09 (`scripts/check_gba.py`): quarteirão de Lisboa, tile `w010_n40_w005_n35` encontrado, **1080 de 2065 edifícios (52 %) ganharam altura estimada** (OBM tinha 19 %; ficam 587, 28 %, sem altura), em **14,4 s** (OBM + GBA em paralelo). O esquema real confirma `geometry` (binário), `height`, `bbox`, `id`, `var`, `region`, `source`.

- **O que é:** 2,75 mil milhões de pegadas com altura LoD1 (Zhu et al., TUM, 2025; ESSD 17, 6647). Alturas **estimadas por deep learning** a partir de imagens de satélite (completude > 97 %, RMSE global ≈ 5,5 m); não são medições.
- **Licença:** **CC BY-NC 4.0 — uso não comercial** (README do repositório original). O projeto é não comercial (decisão do utilizador, 2026-11-09), por isso a fonte é usada; se isso mudar, desligar esta fonte. A conversão em Parquet diz CC BY 4.0 (walkthru.earth), mas não substitui a licença dos dados originais. Os resultados com alturas GBA citam a fonte e a licença.
- **Acesso:** `s3://us-west-2.opendata.source.coop/tge-labs/globalbuildingatlas-lod1/<oeste>_<norte>_<este>_<sul>.parquet`, tiles de 5°×5° (Lisboa: `w010_n40_w005_n35`; Portugal continental: esse e `w010_n45_w005_n40`), ~0,2 GB cada, ordenados por curva de Hilbert, row groups de 15 000 linhas; a leitura filtra pela `bbox`.
- **Esquema:** `geometry`, `height` (metros; -999 = sem dados), `bbox{xmin,ymin,xmax,ymax}`, `id`, `region`, `source`, `var` (incerteza) ✅. WGS84 (o código recusa tiles em metros).
- **Como entra:** só nos edifícios do OpenBuildingMap **sem altura**: recebem a altura do polígono GBA que contém o seu centroide; pisos = altura / 3 m (mínimo 1). As alturas do OBM nunca são substituídas. Cada edifício leva `height_source` (`obm` ou `gba_estimate`) e a resposta indica `buildings_with_estimated_height`, a licença e a atribuição.
- **Falhas:** se o GBA não puder ser lido, a análise continua só com o OBM e `gba_tiles_missing` indica `gba:unavailable`.
- **Limite:** timeout total de 60 s (OBM e GBA lidos em paralelo).

## 5d. Tipologia morfológica por regras (T2.2)

Heurística própria, **não** uma classificação científica validada (o UMCC e o Urban Taxonomy não servem, ver D35). Usa as métricas já calculadas; a primeira regra que se cumprir decide o tipo, e a resposta inclui o motivo e o aviso.

| Ordem | Tipo | Regra |
|---|---|---|
| 1 | Large-footprint / industrial | ocupação ≥ 3 % e (pegada média ≥ 600 m² ou ≥ 30 % industriais) |
| 2 | High-rise blocks | média ≥ 7 pisos (só com alturas) |
| 3 | Compact urban fabric | ocupação ≥ 35 % |
| 4 | Medium-density mid-rise | ocupação ≥ 15 % e média ≥ 4 pisos (só com alturas) |
| 5 | Medium-density low-rise | ocupação ≥ 15 % |
| 6 | Low-density / suburban | ocupação ≥ 3 % |
| 7 | Sparse / rural | restante; "No buildings" se não houver edifícios |

- **Ocupação** = índice de implantação (área de pegadas / área desenhada), por isso parques, ruas e terreno vazio dentro do polígono baixam-na.
- **Alturas:** as regras de pisos só contam se ≥ 50 % dos edifícios tiverem altura (reais ou estimadas); senão são ignoradas e a resposta diz-o.
- **Limiares:** escolhidos à mão para áreas urbanas portuguesas, **por calibrar** com exemplos reais (Lisboa, periferia, zona rural).

## 5e. ÖKOBAUDAT — pegada de carbono dos materiais (T2.3)

**Estado:** ✅ catálogo gerado a partir do CSV oficial (versão 2024-II, descarregado pelo utilizador em 2026-11-10; 44 973 linhas). Rota `GET /materials/suggest` testada com testes automáticos; ainda não verificada em produção.

- **O que é:** base oficial alemã (BBSR/BMWSB) de ACV e EPD de produtos de construção, norma EN 15804+A2.
- **Licença:** a página de pesquisa diz *"The BMWSB provides the ÖKOBAUDAT data free of charge and without any restrictions"*. A página "Data Policy" a que as descargas ligam **não foi lida**: confirmar antes de qualquer uso comercial.
- **Descarga:** https://www.oekobaudat.de/en/service/downloads.html → CSV com ponto decimal (separador `;`, codificação cp1252). O site não é acessível a partir do ambiente do assistente; o ficheiro tem de ser descarregado à mão.
- **Como entra:** `scripts/build_materials_catalog.py <csv>` escolhe 24 datasets por UUID (aço de perfis, galvanizado e de armadura; betões C20/25 a C50/60 e com agregado reciclado; madeira lamelada e maciça; tijolos e blocos; 6 isolamentos; vidro duplo e triplo), lê só o módulo **A1-A3** e grava `backend/app/data/materials_oekobaudat.json`. Falha se um dataset não existir ou for ambíguo. Para atualizar: descarregar o novo CSV e voltar a correr o script.
- **Valores:** GWP-total, fóssil, biogénico e LULUC (A2) por unidade de referência (kg, m³ ou m²); o serviço converte para por kg/m³/m² com a massa volúmica do dataset. Única exceção: o aço usa 7850 kg/m³ (EN 1993-1-1, 3.2.6), porque os datasets de aço não a trazem.
- **Datasets:** genéricos alemães (DE) e médias de associações (bauforumstahl WEU, Baustahlgewebe DE); o `Gueltig bis` de cada um vai na resposta (vários genéricos acabam em 2026).
- **Cuidados:** (1) só produção (A1-A3), sem transporte, uso nem fim de vida; (2) dados alemães/europeus, a produção portuguesa pode diferir; (3) **madeira e outros materiais biogénicos têm GWP-total fortemente negativo** (carbono armazenado), por isso a ordenação usa por omissão o GWP **fóssil** e `carbon_metric=total` inclui o biogénico; (4) kg, m³ e m² não são unidades funcionais equivalentes, só comparar materiais com a mesma função.
- **Custos:** não existe fonte aberta de preços unitários em Portugal (INE e IMPIC só publicam índices). O catálogo não traz custos; o utilizador pode indicá-los (`cost=id:valor`) e ordenar por eles.
- **Durabilidade:** sem fonte, **não incluída**. As notas de exposição (`exposure=humid|coastal`) apenas remetem para as normas EN ISO 12944, EN 206 e EN 335.
- **Fontes avaliadas e rejeitadas:** ICE v5 (desde 30/06/2026 só uso educativo, sem integração em ferramentas/APIs); EC3 (API gratuita sem cache nem uso em produção); ECO Portal (API gratuita só com aprovação prévia).

## 5f. Quantidades IFC — IfcOpenShell (T2.4)

**Estado:** ✅ `POST /bim/quantities` (corpo = ficheiro `.ifc` STEP, máx. 25 MB; 413 se exceder, 422 se não for IFC legível). Testado só com modelos gerados em código; falta experimentar com um IFC real.

- **Biblioteca:** IfcOpenShell (`ifcopenshell` no PyPI), LGPL-3.0-or-later, wheels para Python 3.11/3.12. A LGPL permite usá-la como dependência sem tornar o resto do código copyleft; a imagem Docker (`python:3.12-slim`, glibc ≥ 2.31) serve para a wheel `manylinux_2_31`.
- **Método:** (1) lê as quantidades declaradas (`IfcElementQuantity`: `NetVolume`/`GrossVolume`, `NetArea`/`GrossArea`/`NetSideArea`/`GrossSideArea`, `Length`), convertidas com as unidades do modelo; (2) se o elemento não declara volume, calcula-o pela geometria (máx. 1500 elementos por pedido); (3) soma por classe IFC e por material. Cada classe indica quantos volumes são declarados, calculados ou ausentes.
- **Cuidados:** a qualidade depende de como o modelo foi feito; área e comprimento só aparecem se declarados; elementos com vários materiais ficam sob um rótulo combinado, sem dividir o volume. Modelos grandes devem passar para o Celery (regra R9); por agora o limite de 25 MB e de 1500 geometrias protege o pedido.
- **IFC-Bench (HF):** dataset em CC BY 4.0, mas os modelos IFC mantêm a licença de origem e alguns são GPLv3 (sinalizados). É um benchmark de perguntas e respostas, não serve como fonte de dados do produto; só como ficheiros de teste com licença permissiva.
- **LivingBIM (Zenodo):** um único edifício académico, ficheiros de 0,9 a 3,6 GB; licença **não confirmada**. Não usado.

## 6. Testes ao vivo

Executados em 2026-10-06; resultados nas secções 2 e 3. Para repetir (compatível com zsh, sem comentários `#` na colagem;
trocar o email):

```bash
EMAIL="o-seu-email@exemplo.com"
POLY="POLYGON((-9.16%2038.70,-9.14%2038.70,-9.14%2038.72,-9.16%2038.72,-9.16%2038.70))"
BASE="https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/Regime_florestal/FeatureServer"

echo "--- GBIF: contagem com licencas permitidas ---"
curl -s -A "city-planner-geo (contacto: $EMAIL)" "https://api.gbif.org/v1/occurrence/search?geometry=$POLY&hasCoordinate=true&license=CC0_1_0&license=CC_BY_4_0&limit=0" | head -c 300; echo

echo "--- GBIF: especies mais registadas (facetas) ---"
curl -s -A "city-planner-geo (contacto: $EMAIL)" "https://api.gbif.org/v1/occurrence/search?geometry=$POLY&hasCoordinate=true&facet=speciesKey&facetLimit=3&limit=0" | head -c 600; echo

echo "--- Regime florestal: total de poligonos ---"
curl -s "$BASE/1562/query?where=1%3D1&returnCountOnly=true&f=json"; echo
```

## 7. Decisões (P1–P5 aprovadas em 2026-10-06 e aplicadas a PRD, arquitetura, Rules e Tasks)

| # | Proposta | Documentos afetados |
|---|----------|---------------------|
| P1 | Serviço florestal passa a usar o **ArcGIS REST FeatureServer** da DGT em vez de "OGC API InterGeoPT" | PRD (F2, 1.5), System_Architecture, Tasks (T1.5), Rules (R2) |
| P2 | **Retirar o The Well do MVP.** O estrutural usa só PyNite/anastruct validado com TimoDS; avaliar em v1.0 se existe dataset realmente urbano/térmico | PRD (F4, F6, 1.5), System_Architecture, Tasks (T2.5, T3.1), memory (D5) |
| P3 | F6 (*fine-tuning* geográfico) fica **sem fonte de dados definida** até haver dados regionais reais (ex.: do utilizador) | PRD (F6), Tasks (T3.1) |
| P4 | Filtrar GBIF por **lista de permitidos** (só CC0 e CC BY 4.0; exclui CC BY-NC, `UNSPECIFIED` e `UNSUPPORTED`; refinada após o teste ao vivo) e registar a licença de cada registo no relatório | PRD, Rules (R2) |
| P5 | Tratar o O3 (< 5%) como concordância com um *benchmark* sintético e dizê-lo nos relatórios | PRD (1.3, 1.7) |

## 8. Pontos em aberto

- [ ] Licença da camada "Regime florestal" (sem informação no serviço; perguntar ao ICNF/DGT). **Bloqueia a redistribuição na T1.5**
- [ ] Existência e acesso a PROF e corredores ecológicos (não localizados)
- [ ] Confirmar se os 209 polígonos são a cobertura completa do regime florestal no continente
- [ ] Resolução das chaves de espécie do GBIF em nomes científicos (`/species/{key}`)
- [x] Id e campos da camada florestal; conteúdo da coleção `0` da DGT
- [x] Testes ao vivo (GBIF e regime florestal)
- [x] Licença dos 15 datasets restantes do The Well: dispensada (P2 aprovada)
