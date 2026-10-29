#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRAN Org - DataGramaZero Extractor & Metadata Parser (v2.0 - Higienizado & Auditado)
Resgata metadados estruturados dos 96 fascículos históricos da DataGramaZero (1999-2015)
a partir dos arquivos HTML do acervo original doado ao CEDAP/UFRGS e reconcilia lacunas
físicas históricas a partir da Base ABCDM (Faculdade de Ciência da Informação - FCI/UnB).
"""

import os
import sys
import re
import json
import hashlib
from html import unescape
from pathlib import Path
from bs4 import BeautifulSoup

# Garante suporte UTF-8 no Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "dgz"
OUTPUT_JSON = BASE_DIR / "data" / "datagramazero_articles.json"
CURATED_FALLBACK = BASE_DIR / "scripts" / "curated_fallback.json"

MONTH_MAP = {
    "fev": ("fevereiro", 1),
    "abr": ("abril", 2),
    "jun": ("junho", 3),
    "ago": ("agosto", 4),
    "out": ("outubro", 5),
    "dez": ("dezembro", 6),
}

def clean_html_text(text: str) -> str:
    """Remove quebras de linha, tags HTML, espaços múltiplos e entidades HTML."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_header_metadata(folder_name: str) -> dict:
    """
    Infere volume, número, mês e ano a partir do nome canônico da pasta do fascículo.
    Ex: 'abr15' -> ano=2015, volume=16, número=2, mês=abril
    """
    m_folder = re.match(r'([a-z]{3})(\d{2})', folder_name.lower())
    if m_folder:
        m_code, y_code = m_folder.groups()
        y_int = int(y_code)
        f_year = 1900 + y_int if y_int >= 90 else 2000 + y_int
        vol = max(0, f_year - 1999)
        f_month_str, num = MONTH_MAP.get(m_code, ("janeiro", 1))

        # Caso especial histórico da edição piloto: dez99 é v.0 n.0
        if folder_name.lower() == "dez99":
            vol = 0
            num = 0

        return {
            "year": f_year,
            "volume": vol,
            "number": num,
            "month": f_month_str,
            "issue_label": f"v.{vol}, n.{num} ({f_month_str}/{f_year})"
        }

    return {
        "year": 2000,
        "volume": 1,
        "number": 1,
        "month": "janeiro",
        "issue_label": "v.1, n.1 (janeiro/2000)"
    }

def split_authors(author_str: str) -> list:
    """Normaliza e divide múltiplos autores separados por vírgula, 'e', ';', '&'."""
    if not author_str:
        return []
    cleaned = clean_html_text(author_str)
    # Remove prefixos comuns de autoria
    cleaned = re.sub(r'^(?:por|by)\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(\*?\)\s*', '', cleaned)
    cleaned = re.sub(r'\s*\[[\*\d]+\]\s*', '', cleaned)
    parts = re.split(r'\s*(?:;|\be\b|\band\b|&)\s*', cleaned)
    authors = []
    for p in parts:
        p = clean_html_text(p)
        p = re.sub(r'^(?:por|by)\s+', '', p, flags=re.IGNORECASE).strip()
        if len(p) > 2 and not p.lower().startswith(('resumo', 'resumen', 'abstract', 'autor')):
            authors.append(p)
    return authors

def clean_title(title_raw: str) -> str:
    """Higieniza título removendo vazamentos de resumos e marcadores."""
    if not title_raw:
        return ""
    t = clean_html_text(title_raw)
    # Remove marcadores de rodapé [*] ou [1]
    t = re.sub(r'\s*\[[\*\d]+\]\s*$', '', t)
    # Remove vazamento de Resumo / Resumen
    t = re.sub(r'\s+Resum(?:o|en):?.*$', '', t, flags=re.IGNORECASE)
    # Remove vazamento de 'por [Autor]' no final do título
    t = re.sub(r'\s+(?:por|by)\s+[A-ZÀ-Ú].*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\*\[\]]+$', '', t).strip()
    return t

def parse_article_html(file_path: Path, folder_name: str) -> dict:
    """Extrai metadados estruturados de um arquivo HTML de artigo com DOM parsing."""
    try:
        with open(file_path, "r", encoding="iso-8859-1", errors="ignore") as f:
            html = f.read()
    except Exception:
        return None

    rel_path = f"dgz/{folder_name}/{file_path.name}"
    sha256 = hashlib.sha256(html.encode("iso-8859-1", errors="ignore")).hexdigest()
    header_meta = parse_header_metadata(folder_name)

    # Identificação do número do artigo a partir do nome do arquivo (ex: Art_01.htm)
    art_match = re.search(r'art[_-]?(\d+)', file_path.name, re.IGNORECASE)
    art_num = int(art_match.group(1)) if art_match else 1

    soup = BeautifulSoup(html, "html.parser")

    # 1. Título em Português / Espanhol e Título em Inglês
    title = ""
    title_en = None

    # Tenta localizar blocos centrais onde os títulos ficam
    centers = soup.find_all(["center", "p"], align=re.compile(r'center', re.I))
    if not centers:
        centers = soup.find_all("center")

    for c in centers:
        # Busca <b> para título principal
        b_tags = c.find_all("b")
        for b in b_tags:
            b_text = clean_title(b.get_text())
            if len(b_text) > 8 and not b_text.lower().startswith(('datagramazero', 'artigo', 'v.', 'n.')):
                title = b_text
                break
        if title:
            # Busca <i> para título em inglês
            i_tags = c.find_all("i")
            for i in i_tags:
                i_text = clean_title(i.get_text())
                if len(i_text) > 8 and i_text != title and not i_text.lower().startswith(('datagramazero', 'artigo', 'v.')):
                    title_en = i_text
                    break
            break

    # Fallback se não achou título em tags de centro
    if not title:
        m = re.search(r'<hr[^>]*>(.*?)(?:<b>\s*Resum|<p>\s*<b>\s*Resum)', html, re.I | re.S)
        if m:
            block = BeautifulSoup(m.group(1), "html.parser")
            lines = [clean_title(s) for s in block.stripped_strings if len(clean_title(s)) > 10 and not clean_title(s).lower().startswith(('datagramazero', 'artigo', 'por '))]
            if lines:
                title = lines[0]
                if len(lines) > 1 and not lines[1].lower().startswith(('por ', 'by ')):
                    title_en = lines[1]

    # Fallback final via tag <title>
    if not title or title.lower().startswith(('artigo', 'datagramazero')):
        t_tag = soup.find("title")
        if t_tag:
            t_cand = clean_title(t_tag.get_text())
            if len(t_cand) > 5 and not t_cand.lower().startswith(('artigo', 'capa', 'dgz')):
                title = t_cand

    if not title:
        title = f"Artigo {art_num:02d} ({header_meta['issue_label']})"

    # 2. Autores
    authors = []
    # Procura links diretos para âncora #Autor
    for a_tag in soup.find_all("a", href=re.compile(r'#Autor', re.I)):
        text_a = a_tag.get_text()
        if text_a and len(text_a.strip()) > 2:
            authors.extend(split_authors(text_a))

    # Fallback procurando texto 'por <...>'
    if not authors:
        por_match = re.search(r'(?:por|by)\s+(?:<[^>]+>\s*)*([A-ZÀ-Ú][^<\n\r]+)', html, re.I)
        if por_match:
            authors = split_authors(por_match.group(1))

    if not authors:
        authors = ["Aldo de Albuquerque Barreto"]

    # 3. Resumo em Português / Espanhol
    abstract = None
    resumo_pattern = r'<b>\s*Resum(?:o|en)[\*:\s&nbsp;]*</b>\s*(?:&nbsp;)?\s*:?\s*(.*?)(?:<b>\s*Palabras|<b>\s*Palavras[- ]chave|<b>\s*Abstract|<b>\s*Keywords|<p>\s*<b>|<hr>|$)'
    resumo_match = re.search(resumo_pattern, html, re.IGNORECASE | re.DOTALL)
    if resumo_match:
        abstract = clean_html_text(resumo_match.group(1))

    # 4. Palavras-chave / Palabras clave
    keywords = []
    kw_pattern = r'<b>\s*Palavr?as?[- ]ch?aves?[\*:\s&nbsp;]*</b>\s*(?:&nbsp;)?\s*:?\s*(.*?)(?:<b>\s*Abstract|<b>\s*Keywords|<p>\s*<b>|<hr>|$)'
    kw_match = re.search(kw_pattern, html, re.IGNORECASE | re.DOTALL)
    if kw_match:
        kw_raw = clean_html_text(kw_match.group(1))
        parts = re.split(r'[;,\.]\s*', kw_raw)
        keywords = [p.strip() for p in parts if len(p.strip()) > 2]

    # 5. Abstract em Inglês
    abstract_en = None
    absen_pattern = r'<b>\s*Abstract[\*:\s&nbsp;]*</b>\s*(?:&nbsp;)?\s*:?\s*(.*?)(?:<b>\s*Keywords|<b>\s*Palavras|<p>\s*<b>|<hr>|<p>&nbsp;</p>|$)'
    absen_match = re.search(absen_pattern, html, re.IGNORECASE | re.DOTALL)
    if absen_match:
        abstract_en = clean_html_text(absen_match.group(1))

    # 6. Keywords em Inglês
    keywords_en = []
    kwen_pattern = r'<b>\s*Keywords[\*:\s&nbsp;]*</b>\s*(?:&nbsp;)?\s*:?\s*(.*?)(?:<p>\s*<b>|<hr>|<p>&nbsp;</p>|$)'
    kwen_match = re.search(kwen_pattern, html, re.IGNORECASE | re.DOTALL)
    if kwen_match:
        kwen_raw = clean_html_text(kwen_match.group(1))
        parts = re.split(r'[;,\.]\s*', kwen_raw)
        keywords_en = [p.strip() for p in parts if len(p.strip()) > 2]

    # Mapeamento de PDF companheiro (edições 2012-2015)
    pdf_url = None
    for cand in [f"Artigo {art_num:02d}.pdf", f"Artigo {art_num}.pdf", f"Art_{art_num:02d}.pdf", f"art_{art_num:02d}.pdf"]:
        if (file_path.parent / cand).exists():
            pdf_url = f"https://github.com/BRAN-Org/datagramazero-open-database/raw/main/data/raw/dgz/{folder_name}/{cand}"
            break

    return {
        "title": title,
        "title_en": title_en,
        "authors": authors,
        "year": header_meta["year"],
        "volume": header_meta["volume"],
        "number": header_meta["number"],
        "issue": header_meta["issue_label"],
        "month": header_meta["month"],
        "section": "Artigo",
        "abstract": abstract,
        "abstract_en": abstract_en,
        "keywords": keywords,
        "keywords_en": keywords_en,
        "doi": "N/A",
        "pdf_url": pdf_url,
        "url": f"https://github.com/BRAN-Org/datagramazero-open-database/blob/main/data/raw/{rel_path}",
        "source_file": rel_path,
        "art_order": art_num,
        "provenance": {
            "source": "CEDAP/UFRGS (Coleção Oficial DataGramaZero - Aldo Barreto)",
            "source_url": "http://hdl.handle.net/20.500.11959/1269",
            "raw_file_sha256": sha256,
            "archive_url": "https://cedap.ufrgs.br/xmlui/bitstream/handle/20.500.11959/1269/dgz.zip",
            "notes": "Metadados estruturados e higienizados pela BRAN Org a partir do HTML estático original."
        }
    }

def parse_fev13_index(ind_path: Path) -> list:
    """Extrai os 7 artigos de fev/2013 diretamente a partir de Ind_art.htm."""
    with open(ind_path, "r", encoding="latin1", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    sha256 = hashlib.sha256(html.encode("latin1", errors="ignore")).hexdigest()
    header_meta = parse_header_metadata("fev13")

    articles = []
    art_links = soup.find_all("a", href=re.compile(r'^Art_\d+\.htm$', re.I))

    for a in art_links:
        href = a.get("href", "")
        m = re.match(r'^Art_(\d+)\.htm$', href, re.I)
        if not m:
            continue
        art_num = int(m.group(1))
        title = clean_title(" ".join(a.get_text().split()))

        parent = a.find_parent(["td", "blockquote", "p"])
        title_en = None
        authors = []
        abstract = None
        keywords = []

        if parent:
            text = parent.get_text()
            i_tag = parent.find("i")
            if i_tag:
                title_en = clean_title(i_tag.get_text())

            aut_a = parent.find("a", href=re.compile(r'#Autor', re.I))
            if aut_a:
                authors = split_authors(aut_a.get_text())

            m_res = re.search(r'Resumo\s*:\s*(.*?)(?:Palavras-chave|Abstract|$)', text, re.S)
            if m_res:
                abstract = clean_html_text(m_res.group(1))

            m_kw = re.search(r'Palavras-chave\s*:\s*(.*?)(?:Abstract|$)', text, re.S)
            if m_kw:
                parts = re.split(r'[;,\.]\s*', m_kw.group(1))
                keywords = [p.strip() for p in parts if len(p.strip()) > 2]

        if not authors:
            authors = ["Aldo de Albuquerque Barreto"]

        articles.append({
            "title": title,
            "title_en": title_en,
            "authors": authors,
            "year": header_meta["year"],
            "volume": header_meta["volume"],
            "number": header_meta["number"],
            "issue": header_meta["issue_label"],
            "month": header_meta["month"],
            "section": "Artigo",
            "abstract": abstract,
            "abstract_en": None,
            "keywords": keywords,
            "keywords_en": [],
            "doi": "N/A",
            "pdf_url": None,
            "url": "https://github.com/BRAN-Org/datagramazero-open-database/blob/main/data/raw/dgz/fev13/Ind_art.htm",
            "source_file": "dgz/fev13/Ind_art.htm",
            "art_order": art_num,
            "provenance": {
                "source": "CEDAP/UFRGS (Coleção Oficial DataGramaZero - Aldo Barreto)",
                "source_url": "http://hdl.handle.net/20.500.11959/1269",
                "raw_file_sha256": sha256,
                "archive_url": "https://cedap.ufrgs.br/xmlui/bitstream/handle/20.500.11959/1269/dgz.zip",
                "notes": "Artigo recuperado diretamente do sumário Ind_art.htm da edição fev/2013 (arquivos Art_XX.htm desmembrados ausentes no zip original do CEDAP)."
            }
        })

    articles.sort(key=lambda x: x["art_order"])
    return articles

def main():
    print("🚀 [BRAN Org] Iniciando parser censitário e higienizado da DataGramaZero...")
    if not RAW_DIR.exists():
        print(f"❌ Diretório não encontrado: {RAW_DIR}")
        return

    issues = sorted([d for d in os.listdir(RAW_DIR) if (RAW_DIR / d).is_dir() and d != "Atual"])
    print(f"📦 Total de diretórios de fascículos: {len(issues)}")

    raw_articles = []

    for issue in issues:
        issue_dir = RAW_DIR / issue

        # A pasta abr02 no dump do CEDAP contém cópias duplicadas de ago15 (v.16 n.4).
        # Ignoramos esses arquivos duplicados e usamos os registros reconciliados de abr/2002 via curated_fallback.
        if issue.lower() == "abr02":
            continue

        # Caso especial fev13: artigos individuais não vieram desmembrados; estão no Ind_art.htm
        if issue.lower() == "fev13":
            ind_path = issue_dir / "Ind_art.htm"
            if ind_path.exists():
                fev13_arts = parse_fev13_index(ind_path)
                print(f"  ✓ fev13: {len(fev13_arts)} artigos recuperados via Ind_art.htm")
                raw_articles.extend(fev13_arts)
            continue

        # Extração padrão via Art_*.htm
        art_files = sorted([f for f in os.listdir(issue_dir) if re.match(r'^art[_-]?\d+\.html?$', f, re.IGNORECASE)])
        for art_f in art_files:
            file_path = issue_dir / art_f
            parsed = parse_article_html(file_path, issue)
            if parsed:
                raw_articles.append(parsed)

    print(f"📄 Artigos extraídos diretamente do HTML: {len(raw_articles)}")

    # Incorporação do Curated Fallback (reconciliado contra a Base ABCDM / FCI-UnB)
    if CURATED_FALLBACK.exists():
        with open(CURATED_FALLBACK, "r", encoding="utf-8") as f:
            curated_list = json.load(f)
        for c in curated_list:
            c["art_order"] = c.get("number", 1)
        raw_articles.extend(curated_list)
        print(f"📥 Reconciliação ABCDM (FCI/UnB) incorporada: +{len(curated_list)} artigos históricos")

    # Ordenação cronológica estrita por ano, volume, número e ordem do artigo
    raw_articles.sort(key=lambda x: (x.get("year", 0), x.get("volume", 0), x.get("number", 0), x.get("art_order", 0)))

    # Atribuição de IDs determinísticos canônicos
    issue_counters = {}
    final_articles = []
    seen_ids = set()

    for art in raw_articles:
        vol = art["volume"]
        num = art["number"]
        issue_key = f"v{vol:02d}-n{num:02d}"
        issue_counters[issue_key] = issue_counters.get(issue_key, 0) + 1
        art_idx = issue_counters[issue_key]

        art_id = f"dgz-{issue_key}-a{art_idx:02d}"
        if art_id in seen_ids:
            art_id = f"{art_id}-{len(seen_ids)}"
        seen_ids.add(art_id)

        art["id"] = art_id
        if "art_order" in art:
            del art["art_order"]

        final_articles.append(art)

    print(f"\n✅ Total de artigos estruturados e consolidados: {len(final_articles)}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_articles, f, ensure_ascii=False, indent=2)

    print(f"📁 Dataset canônico salvo em: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
