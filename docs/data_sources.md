# Auditoria de Fontes de Dados

Documentação da auditoria das fontes de dados para o MVP do City Planner Geo.
Conforme T0.5: confirmar URL, licença, esquema e limites de cada dataset/API do MVP (GBIF, InterGeoPT, TimoDS, The Well).

## Fontes de Dados do MVP

### 1. GBIF (Global Biodiversity Information Facility)

#### URL
- https://www.gbif.org/
- API: https://api.gbif.org/v1/

#### Licença
- Dados publicados sob várias licenças (CC0, CC-BY, etc. conforme o fornecedor)
- API terms of use: https://www.gbif.org/terms

#### Esquema (Schema)
- Occurrence data: https://www.gbif.org/developer/occurrence
- Taxonomy: https://www.gbif.org/developer/species
- Checklist bank: https://www.gbif.org/developer/checklist

#### Limites
- Rate limiting: Varies by endpoint, generally generous for academic use
- Maximum records per request: 300 for occurrence search
- Daily download limits: Varies by dataset
- Terms: https://www.gbif.org/terms

#### Notas para o City Planner Geo
- Útil para análise de biodiversidade e serviços ecossistêmicos
- Requer tratamento de diferentes licenças dos dados
- Bom para análise de impacto ambiental de projetos urbanísticos

### 2. InterGeoPT (Infraestrutura Nacional de Informação Geográfica - Portugal)

#### URL
- https://www.intergeopt.pt/
- API: https://www.intergeopt.pt/api/ (OGC API Features/WFS3)

#### Licença
- Dados públicos da Administração Pública Portuguesa
- Geralmente sob licença equivalente a CC-BY 4.0 ou similar para dados públicos
- Termos de uso: https://www.intergeopt.pt/pt/termos-e-condicoes

#### Esquema (Schema)
- Camadas disponíveis: uso do solo, ocupação do solo, infraestrutura, ambiente, etc.
- Esquemas específicos por camada (ver documentação de cada serviço)
- Exemplos: Carta de Uso e Ocupação do Solo (COS), Carta Geotécnica

#### Limites
- Rate limiting: Não especificado pubblicamente, usar com moderação
- Limites de tamanho de resposta: Configurável nas requisições
- Disponibilidade: Serviço público português, esperado alta disponibilidade

#### Notas para o City Planner Geo
- Fonte primária para dados geoespaciais de Portugal
- Inclui dados detalhados de uso e ocupação do solo essenciais para análise urbana
- Dados oficiais do governo português com boa qualidade e atualização

### 3. TimoDS

#### URL
- Necessita pesquisa adicional - possível referência a conjunto de dados sobre solos ou florestas em Portugal
- Verificar se se refere a "Timóteo de Sousa" ou outro conjunto de dados específico

#### Licença
- A determinar após confirmação da fonte exata

#### Esquema (Schema)
- A determinar após confirmação da fonte exata

#### Limites
- A determinar após confirmação da fonte exata

#### Notas para o City Planner Geo
- Fonte a confirmar - possivelmente relacionada a dados de solo ou florestais
- Necessário verificar se é um conjunto de dados público disponível para uso

### 4. The Well

#### URL
- Necessita pesquisa adicional - possível referência a conjunto de dados sobre aquíferos ou recursos hídricos
- Verificar se se refere a "The Well" como conjunto de dados específico de hidrogeologia

#### Licença
- A determinar após confirmação da fonte exata

#### Esquema (Schema)
- A determinar após confirmação da fonte exata

#### Limites
- A determinar após confirmação da fonte exata

#### Notas para o City Planner Geo
- Fonte a confirmar - possivelmente relacionada a dados de aquíferos ou recursos hídricos
- Relevante para análise de disponibilidade de água e risco de inundação

## Próximos Passos
- Pesquisar e confirmar as fontes exatas para TimoDS e The Well
- Preencher detalhes faltantes de licença, esquema e limites
- Avaliar adequação das fontes para os casos de uso do MVP
- Documentar quaisquer limitações ou restrições de uso