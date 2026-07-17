# GeoCAR Amapá — Complemento QGIS

## Ferramenta de apoio ao Cadastro Ambiental Rural

**Autores:** Luís Lopes e Pedro Américo Jr.
**Versão:** 1.0
**Compatibilidade:** QGIS 3.34 ou superior

---

## 📋 Sobre o GeoCAR Amapá

O **GeoCAR Amapá** é um complemento para QGIS desenvolvido como ferramenta de apoio à consulta e utilização da Base de Referência do Cadastro Ambiental Rural (CAR) no Estado do Amapá.

O complemento auxilia proprietários, possuidores, responsáveis técnicos e demais usuários no processamento de informações ambientais relacionadas ao imóvel rural, permitindo:

* Recorte automático das camadas ambientais de referência pelo polígono do imóvel;
* Verificação da hidrografia na área de influência do imóvel;
* Cálculo das áreas de Floresta, Cerrado e Campo presentes no imóvel;
* Estimativa orientativa da Reserva Legal;
* Geração de relatório técnico em TXT e HTML;
* Criação de camada vetorial para auxiliar na delimitação da Reserva Legal.

O GeoCAR Amapá possui caráter exclusivamente **orientativo e de apoio**. Os resultados e cálculos gerados pelo complemento não constituem análise oficial do Cadastro Ambiental Rural e não substituem a análise realizada pelo órgão ambiental competente.

---

## 📁 Estrutura do Complemento

A estrutura básica do GeoCAR Amapá é composta pelos arquivos do complemento, pela interface de processamento e pelo GeoPackage que contém a Base de Referência utilizada nas operações espaciais.

A Base de Referência deve estar disponível no diretório esperado pelo complemento, mantendo a estrutura e os nomes internos das camadas necessários ao seu funcionamento.

---

## 🚀 Instalação

O GeoCAR Amapá pode ser instalado no QGIS por meio do Gerenciador de Complementos ou, quando disponibilizado como arquivo ZIP, pela opção:

**Complementos → Gerenciar e Instalar Complementos → Instalar a partir de ZIP**

Após a instalação e ativação, o ícone do **GeoCAR Amapá** ficará disponível na interface do QGIS.

---

## 🖥️ Como usar

### Aba 1 — Processar CAR

1. Preencha as informações solicitadas;
2. Selecione o município;
3. Selecione, na lista de camadas disponíveis, o polígono correspondente ao imóvel;
4. Informe as fitofisionomias presentes no imóvel;
5. Selecione a pasta de saída;
6. Inicie o processamento.

O GeoCAR Amapá realizará o cruzamento espacial do imóvel com as informações disponíveis na Base de Referência e produzirá os resultados correspondentes.

Entre os produtos gerados estão:

* Camadas vetoriais resultantes dos recortes;
* Organização das camadas resultantes no projeto QGIS;
* Camada destinada a auxiliar na delimitação da Reserva Legal;
* Relatório com os resultados do processamento.

### Aba 2 — Base de Referência

Permite carregar no projeto QGIS as camadas que compõem a Base de Referência utilizada pelo GeoCAR Amapá, possibilitando sua visualização e consulta.

### Aba 3 — Log de Processamento

Apresenta, em tempo real, as mensagens relacionadas às etapas executadas pelo complemento durante o processamento.

O usuário também pode utilizar a opção **Limpar log** para remover as mensagens exibidas.

---

## 📐 Sistema de Referência

Para a realização dos cálculos e operações espaciais, o complemento utiliza:

**SIRGAS 2000 / UTM Zone 22S — EPSG:31976**

A utilização de um sistema de coordenadas projetado permite a realização dos cálculos de área em metros quadrados e hectares.

---

## 📊 Estimativa da Reserva Legal

O GeoCAR Amapá utiliza as fitofisionomias identificadas no imóvel para auxiliar na estimativa da área de Reserva Legal.

| Fitofisionomia | Percentual de referência |
| -------------- | ------------------------ |
| Floresta       | 80%                      |
| Cerrado        | 35%                      |
| Campo          | 20%                      |

Os resultados apresentados pelo complemento possuem caráter **orientativo** e devem ser interpretados considerando a legislação ambiental aplicável e as particularidades de cada imóvel.

---

## ⚠️ Aviso

O **GeoCAR Amapá** é uma ferramenta de apoio e orientação.

O uso do complemento não substitui os procedimentos oficiais relacionados ao Cadastro Ambiental Rural, nem a análise técnica realizada pelo órgão ambiental competente.

Os usuários são responsáveis pela conferência das informações utilizadas e dos resultados gerados pelo complemento.

---

## 👨‍💻 Autores

**Luís Lopes**
**Pedro Américo Jr.**

GeoCAR Amapá — Ferramenta de apoio ao Cadastro Ambiental Rural.
