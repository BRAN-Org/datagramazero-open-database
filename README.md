# DataGramaZero Open Database

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.23593504"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.23593504.svg" alt="Zenodo DOI"></a>
  <a href="#-síntese-do-acervo--governança"><img src="https://img.shields.io/badge/Confiabilidade-Auditado%20e%20Validado-brightgreen" alt="Confiabilidade"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/Licen%C3%A7a-CC_BY--NC--SA_4.0-lightgrey.svg" alt="CC BY-NC-SA 4.0"></a>
  <a href="#-como-usar-os-dados"><img src="https://img.shields.io/badge/Formatos-SQLite_%7C_CSV_%7C_JSON-blue.svg" alt="Formatos"></a>
</p>

Base de dados bibliométrica aberta e acervo histórico completo dos 487 artigos e ensaios publicados na DataGramaZero - Revista de Ciência da Informação (1999–2015), periódico pioneiro de acesso aberto fundado pelo Prof. Aldo de Albuquerque Barreto e disponibilizado pela BRAN Org sob princípios FAIR e BOAI.

---

## 📊 Síntese do Acervo & Governança

> [!NOTE]
> **Status de Confiabilidade:** 🟢 **Auditado e Validado**  
> 📌 **Diagnóstico Metodológico:** Acervo auditado e reconciliado contra a Base ABCDM (FCI/UnB), com recuperação das lacunas físicas de jun/2007 e out/2015, saneamento de metadados multilíngues e 99,6% de cobertura de resumos históricos.

| Métrica / Atributo | Detalhes do Acervo |
| :--- | :--- |
| **Período Histórico** | 1999–2015 (16 Volumes, 96 Edições) |
| **Total de Trabalhos** | **487 artigos científicos catalogados** |
| **Textos Completos (PDF/HTML)** | Acervo histórico integral (487 artigos e ensaios, 1.765 arquivos preservados via CEDAP/UFRGS e reconciliação FCI/UnB) |
| **Integridade Criptográfica** | Hash SHA-256 por arquivo e rastreabilidade estrita (`provenance.json`) |
| **Formatos Disponíveis** | SQLite3 (`.sqlite`), CSV (UTF-8 BOM), JSON, BibTeX (`.bib`), RIS (`.ris`) |
| **Licença dos Dados** | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (Uso acadêmico; vedada ingestão por IA comercial) |

---

## 📥 Download do Pacote Consolidado

O acervo bruto, o banco relacional completo e os arquivos individuais estão arquivados permanentemente no **CERN / Zenodo** sob DOI imutável:

- 🔗 **DOI Permanente:** [https://doi.org/10.5281/zenodo.23593504](https://doi.org/10.5281/zenodo.23593504)
- 📦 **Conteúdo do .zip:** Banco SQLite3 (`datagramazero_articles.sqlite`), planilhas CSV consolidadas (`datagramazero_articles.csv`), metadados estruturados JSON, referências BibTeX/RIS e coleção completa de PDFs/HTMLs históricos.

```bash
# Download direto do pacote completo via terminal
curl -LO "https://zenodo.org/records/23593504/files/datagramazero-open-database-zenodo.zip"
unzip datagramazero-open-database-zenodo.zip
```

---

## ⚡ Como Usar os Dados

### Python (Pandas)
```python
import pandas as pd

df = pd.read_json("data/datagramazero_articles.json")
print(f"Total: {len(df)} artigos | Período: {df['year'].min()} a {df['year'].max()}")
```

### SQLite3 (SQL no terminal)
```bash
sqlite3 data/datagramazero_articles.sqlite "SELECT year, COUNT(*) as total FROM articles GROUP BY year ORDER BY year;"
```

---

## 🌐 API REST Pública

Endpoints públicos e gratuitos (sem necessidade de chave de autenticação):

| Método | Endpoint | Finalidade |
| :--- | :--- | :--- |
| `GET` | `/api/v1/articles` | Busca textual (`?q=`), filtros facetados (`?year=`, `?author=`) e paginação |
| `GET` | `/api/v1/articles/:key` | Consulta individual por ID do artigo |
| `GET` | `/api/v1/articles/stats` | Métricas consolidadas, rankings de autores e palavras-chave |
| `GET` | `/api/v1/articles/export?format=csv` | Download instantâneo dos dados filtrados em CSV (BOM UTF-8) |

> **Executar localmente:** `npm install && npm start` (disponível em `http://localhost:3000`).

---

## 📖 Como Citar Este Dataset

```bibtex
@misc{datagramazero_open_database_2026,
  author       = {BRAN Org},
  title        = {DataGramaZero Open Database},
  year         = {2026},
  howpublished = {Zenodo},
  doi          = {10.5281/zenodo.23593504},
  url          = {https://doi.org/10.5281/zenodo.23593504}
}
```

**ABNT:**
> BRAN ORG. **DataGramaZero Open Database**. Genebra: CERN / Zenodo, 2026. DOI: 10.5281/zenodo.23593504. Disponível em: &lt;https://doi.org/10.5281/zenodo.23593504&gt;.
