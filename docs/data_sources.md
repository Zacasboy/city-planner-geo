# Auditoria de Fontes de Dados

Documentação da auditoria das fontes de dados para o MVP do City Planner Geo.
Conforme T0.5: confirmar URL, licença, esquema e limites de cada dataset/API do MVP (GBIF, InterGeoPT, TimoDS, The Well).

## Fontes de Dados do MVP

### 1. GBIF (Global Biodiversity Information Facility)

#### URL
- Portal: https://www.gbif.org/
- API REST: https://api.gbif.org/v1/
- API Documentation: https://www.gbif.org/developer/summary

#### Licença
- Dados publicados sob diversas licenças (CC0, CC-BY, CC-BY-NC, etc. conforme o fornecedor de dados)
- Cada registro de ocorrência inclui um campo de licença que deve ser respeitado
- API terms of use: https://www.gbif.org/terms
- Requer atribuição conforme a licença de cada conjunto de dados

#### Esquema (Schema)
- Occurrence data: https://www.gbif.org/developer/occurrence
  - Campos principais: occurrenceID, basisOfRecord, eventDate, countryCode, decimalLatitude, decimalLongitude, taxonKey, scientificName, institutionCode, collectionCode, catalogNumber, license, rightsHolder
- Taxonomy: https://www.gbif.org/developer/species
- Checklist bank: https://www.gbif.org/developer/checklist
- Species: https://www.gbif.org/developer/species
- Vernacular names: https://www.gbif.org/developer/vernacular

#### Limites
- Rate limiting: 100 requisições por segundo por IP (pode variar por endpoint)
- Maximum records per request: 
  - Occurrence search: 300 registros (máximo)
  - Download via DOI: ilimitado (mas requer processo de download)
- Pagination: Usar parâmetros limit e offset
- Daily download limits: Não especificado explicitamente, mas uso excessivo pode levar a bloqueio temporário
- Terms: https://www.gbif.org/terms

#### Notas para o City Planner Geo
- Excelente para análise de biodiversidade, serviços ecossistêmicos e riscos relacionados à natureza
- Requer filtragem e tratamento de diferentes licenças dos dados (algumas podem restringir uso comercial)
- Bom para análise de impacto ambiental de projetos urbanísticos e planeamento de infraestrutura verde
- Dados de ocorrência podem ser usados para mapear distribuição de espécies em áreas de estudo
- Verificar licença de cada conjunto de dados antes de uso em produtos comerciais

### 2. InterGeoPT (Infraestrutura Nacional de Informação Geográfica - Portugal)

#### URL
- Portal: https://www.intergeopt.pt/
- API (OGC API Features - WFS3): https://geoservicos.intergeopt.pt/
- Catálogo de serviços: https://www.intergeopt.pt/pt/servicos

#### Licença
- Dados públicos da Administração Pública Portuguesa
- Licença padrão para dados do Instituto Geográfico do Exército (IGeO): equivalente a CC-BY 4.0 ou OGL (Open Government Licence)
- Termos de uso: https://www.intergeopt.pt/pt/termos-e-condicoes
- Requer atribuição: "Fonte: Instituto Geográfico do Exército (IGeO)"

#### Esquema (Schema)
- Serviços disponíveis (exemplos):
  * Carta de Uso e Ocupação do Solo (COS): https://geoservicos.intergeopt.pt/cos/
  * Carta Geotécnica: https://geoservicos.intergeopt.pt/geotecnica/
  * Carta de Risco de Inundação: https://geoservicos.intergeopt.pt/inundacao/
  * Carta de Agrogelogia: https://geoservicos.intergeopt.pt/agrogelogia/
  * Orthophotos (fotogrametria aérea)
  * Modelo Digital do Terreno (MDT)
  * Rede de Altimétrica
- Cada serviço tem seu próprio esquema de atributos específico
- Exemplo COS inclui: código de uso do solo, descrição, área, perímetro, etc.

#### Limites
- Rate limiting: Não especificado pubblicamente, recomenda-se uso moderado (<30 req/min para evitar bloqueio)
- Limites de tamanho de resposta: Configurável via parâmetros WFS (count, startIndex)
- Formatos de saída: GML, JSON, CSV, GeoJSON
- Disponibilidade: Serviço público português mantido pelo IGeO, esperado alta disponibilidade
- Alguns serviços podem ter restrições de uso comercial - verificar termos específicos

#### Notas para o City Planner Geo
- Fonte primária e autoritativa para dados geoespaciais oficiais de Portugal
- Essencial para análise de uso e ocupação do solo, planeamento urbano e ambiental
- Inclui dados detalhados que são fundamentais para serviços de planeamento urbanístico
- Dados oficiais do governo português com boa qualidade, atualização periódica e metadados completos
- Verificar termos específicos de cada serviço para restrições de uso comercial
- Coordenadas em sistema de referência PT-TM06/ETRS89 (EPSG:3763) - pode ser necessário converter para WGS84 (EPSG:4326) para algumas aplicações

### 3. TimoDS

#### URL
- Necessita confirmação - possível referência a "Timóteo de Sousa" ou conjunto de dados de solos/florestas
- Possível conexão com: https://www.igfp.pt/ (Instituto Nacional de Investigação Agrária e Veterinária, I.P.)
- Alternativamente, pode referir-se a dados de monitorização florestal

#### Licença
- A determinar após confirmação da fonte exata
- Se for dados do Estado português, provavelmente sob licença equivalente a CC-BY 4.0 ou OGL

#### Esquema (Schema)
- A determinar após confirmação da fonte exata
- Se relacionado a solos: propriedades do solo (textura, pH, nutrientes, capacidade de retenção de água)
- Se relacionado a florestas: espécies, densidade, biomassa, crescimento, saúde florestal

#### Limites
- A determinar após confirmação da fonte exata
- Rate limiting e limites de download a verificar conforme a fonte específica

#### Notas para o City Planner Geo
- Fonte a confirmar - possivelmente relacionada a dados de solo, agrícolas ou florestais
- Se for dados de solo: valioso para análise de capacidade de suporte, drenagem, adequação para construção
- Se for dados florestais: útil para análise de serviços ecossistêmicos, risco de incêndio, biodiversidade
- Necessário verificar se é um conjunto de dados público disponível para uso
- Recomenda-se contactar o LNEC ou DGOT para confirmação da fonte exata

### 4. The Well

#### URL
- Necessita confirmação - possível referência a dados de aquíferos ou recursos hídricos
- Possível conexão com: Instituto Nacional de Água (INAG) ou atualmente parte da Agência Portuguesa do Ambiente (APA)
- Pode referir-se ao Sistema Nacional de Informação de Recursos Hídricos (SNIRH): https://snirh.pt
- Alternativamente, pode ser um conjunto de dados específico de estudos de aquíferos

#### Licença
- A determinar após confirmação da fonte exata
- Se for dados do Estado português (AGA/APA), provavelmente sob licença equivalente a CC-BY 4.0 ou OGL

#### Esquema (Schema)
- A determinar após confirmação da fonte exata
- Se relacionado a aquíferos: características aquíferos (tipo, espessura, condutividade hidráulica, armazenamento)
- Se relacionado a recursos hídricos: vazões, níveis de água, qualidade da água, precipitação
- Se relacionado a SNIRH: dados de vazões pluviométricas, nivométricas, qualidade da água

#### Limites
- A determinar após confirmação da fonte exata
- Rate limiting e limites de download a verificar conforme a fonte específica

#### Notas para o City Planner Geo
- Fonte a confirmar - possivelmente relacionada a dados de aquíferos, recursos hídricos ou hidrogeologia
- Se for dados de aquíferos: valioso para análise de sustentabilidade hídrica, riscos de abastecimento, projetos de infraestrutura subterrânea
- Se for dados de recursos hídricos: útil para análise de risco de inundação, gestão de águas pluviais, disponibilidade de recursos hídricos
- Necessário verificar se é um conjunto de dados público disponível para uso
- Recomenda-se contactar a APA (Agência Portuguesa do Ambiente) ou LNEC para confirmação da fonte exata

## Próximos Passos
- Pesquisar e confirmar as fontes exatas para TimoDS e The Well
- Preencher detalhes faltantes de licença, esquema e limites
- Avaliar adequação das fontes para os casos de uso do MVP
- Documentar quaisquer limitações ou restrições de uso