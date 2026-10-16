#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRAN Org - DataGramaZero Extractor & Metadata Parser
Resgata metadados estruturados dos 97 fascículos históricos da DataGramaZero (1999-2015)
a partir dos arquivos HTML do acervo original doado ao CEDAP/UFRGS.
"""

import os
import sys
import re
import json
import hashlib
from html import unescape
from pathlib import Path

# Garante suporte UTF-8 no Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "dgz"
OUTPUT_JSON = BASE_DIR / "data" / "datagramazero_articles.json"

MONTH_MAP = {
    "fev": ("fevereiro", 2),
    "abr": ("abril", 4),
    "jun": ("junho", 6),
    "ago": ("agosto", 8),
    "out": ("outubro", 10),
    "dez": ("dezembro", 12),
}

def clean_html_text(text: str) -> str:
    """Remove tags HTML, espaços múltiplos e entidades HTML."""
    if not text:
        return ""
    # Substitui quebras de linha e tabs por espaço
    text = re.sub(r'[\r\n\t]+', ' ', text)
    # Remove tags HTML
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities (ex: &eacute; -> é)
    text = unescape(text)
    # Remove espaços duplos
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_header_metadata(html: str, folder_name: str):
    """
    Tenta inferir volume, número, mês e ano a partir do cabeçalho ou do nome da pasta.
    Ex: 'DataGramaZero - Revista de Informação - v.16 n.2 abr/15 ARTIGO 01'
    """
    # Fallback via nome da pasta: ex 'abr15' -> mes=abr, ano=2015
    m_folder = re.match(r'([a-z]{3})(\d{2})', folder_name.lower())
    f_year = 2000
    f_month_str = "abril"
    f_month_num = 4
    if m_folder:
        m_code, y_code = m_folder.groups()
        y_int = int(y_code)
        f_year = 1900 + y_int if y_int >= 90 else 2000 + y_int
        if m_code in MONTH_MAP:
            f_month_str, f_month_num = MONTH_MAP[m_code]

    # Busca no texto: v.16 n.2 abr/15
    vol = None
    num = None
    
    m_vol = re.search(r'v\.?\s*(\d+)', html, re.IGNORECASE)
    if m_vol:
        vol = int(m_vol.group(1))
    else:
        # Inferência se v. for ausente: 1999=v0, 2000=v1, ..., 2015=v16
        vol = max(0, f_year - 1999)

    m_num = re.search(r'n\.?\s*(\d+)', html, re.IGNORECASE)
    if m_num:
        num = int(m_num.group(1))
    else:
        num = f_month_num // 2 if f_month_num else 1

    return {
        "year": f_year,
        "volume": vol,
        "number": num,
        "month": f_month_str,
        "issue_label": f"v.{vol}, n.{num} ({f_month_str}/{f_year})"
    }

def split_authors(author_str: str) -> list:
    """Normaliza e divide múltiplos autores separados por vírgula, 'e', ';', '&'."""
    if not author_str:
        return []
    cleaned = clean_html_text(author_str)
    # Remove prefixo 'por '
    cleaned = re.sub(r'^(por|by)\s+', '', cleaned, flags=re.IGNORECASE)
    # Divide por separadores comuns
    parts = re.split(r'\s*(?:;|\be\b|\band\b|&)\s*', cleaned)
    authors = []
    for p in parts:
        p_clean = p.strip().strip(',').strip()
        if p_clean and len(p_clean) > 2 and not p_clean.lower().startswith(('artigo', 'resumo', 'data')):
            authors.append(p_clean)
    return authors

def parse_article_html(file_path: Path, folder_name: str) -> dict:
    """Extrai metadados estruturados de um arquivo HTML de artigo."""
    try:
        with open(file_path, "r", encoding="iso-8859-1", errors="ignore") as f:
            html = f.read()
    except Exception as e:
        return None

    rel_path = f"dgz/{folder_name}/{file_path.name}"
    sha256 = hashlib.sha256(html.encode("iso-8859-1", errors="ignore")).hexdigest()

    header_meta = parse_header_metadata(html, folder_name)

    # Identificação do ID do artigo a partir do nome do arquivo (ex: Art_01.htm)
    art_match = re.search(r'art[_-]?(\d+)', file_path.name, re.IGNORECASE)
    art_num = int(art_match.group(1)) if art_match else 1
    article_id = f"dgz-v{header_meta['volume']:02d}-n{header_meta['number']:02d}-a{art_num:02d}"

    # 1. Título em Português e Inglês
    # Usualmente dentro de <center><b>...</b> ou após ARTIGO XX
    title = ""
    title_en = ""
    
    # Procura blocos de título após a linha horizontal <hr>
    center_match = re.search(r'<hr>(.*?)(?:<blockquote>|<p><b>Resumo|<b>Resumo)', html, re.IGNORECASE | re.DOTALL)
    center_block = center_match.group(1) if center_match else html[:3000]

    # Tenta achar o título em <b> dentro de center_block
    b_matches = re.findall(r'<b[^>]*>(.*?)</b>', center_block, re.IGNORECASE | re.DOTALL)
    if b_matches:
        for b_cand in b_matches:
            b_text = clean_html_text(b_cand)
            if len(b_text) > 10 and not b_text.lower().startswith(('datagramazero', 'artigo', 'resumo')):
                title = b_text
                break

    # Tenta achar o título em inglês em <i> dentro de center_block
    i_matches = re.findall(r'<i[^>]*>(.*?)</i>', center_block, re.IGNORECASE | re.DOTALL)
    if i_matches:
        for i_cand in i_matches:
            i_text = clean_html_text(i_cand)
            if len(i_text) > 10 and not i_text.lower().startswith(('datagramazero', 'artigo', 'v.')):
                if i_text != title:
                    title_en = i_text
                    break

    # Fallback de título via <title> tag
    if not title:
        m_title = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if m_title:
            t_cand = clean_html_text(m_title.group(1))
            if len(t_cand) > 5 and not t_cand.lower().startswith(('artigo', 'capa', 'dgz')):
                title = t_cand

    # 2. Autores
    authors = []
    # Padrão: por <a href="#Autor">...</a> ou por <font ...>...</font>
    por_match = re.search(r'(?:por|by)\s*(?:<font[^>]*>)?\s*(?:<a[^>]*>)?(.*?)(?:</a>)?(?:</font>)?\s*</center>', center_block, re.IGNORECASE | re.DOTALL)
    if por_match:
        authors = split_authors(por_match.group(1))
    
    # Se ainda vazio, procura no link #Autor
    if not authors:
        autor_link = re.search(r'<a\s+href=[\'"]#autor[\'"][^>]*>(.*?)</a>', center_block, re.IGNORECASE | re.DOTALL)
        if autor_link:
            authors = split_authors(autor_link.group(1))

    # 3. Resumo em Português / Espanhol
    abstract = None
    resumo_pattern = r'<b>\s*Resum(?:o|en)[\*:\s&nbsp;]*</b>\s*(?:&nbsp;)?\s*:?\s*(.*?)(?:<b>\s*Palabras|<b>\s*Palavras[- ]chave|<b>\s*Abstract|<b>\s*Keywords|<p>\s*<b>|$)'
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

    # Se title ainda vazio, usa nome padrão
    if not title:
        title = f"Artigo {art_num:02d} ({header_meta['issue_label']})"

    return {
        "id": article_id,
        "title": title,
        "title_en": title_en if title_en else None,
        "authors": authors if authors else ["Aldo de Albuquerque Barreto"],
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
        "pdf_url": None,
        "url": f"https://github.com/BRAN-Org/datagramazero-open-database/blob/main/data/raw/{rel_path}",
        "source_file": rel_path,
        "provenance": {
            "source": "CEDAP/UFRGS (Coleção Oficial DataGramaZero - Aldo Barreto)",
            "source_url": "http://hdl.handle.net/20.500.11959/1269",
            "raw_file_sha256": sha256,
            "archive_url": "https://cedap.ufrgs.br/xmlui/bitstream/handle/20.500.11959/1269/dgz.zip",
            "notes": "Metadados resgatados e estruturados pela BRAN Org a partir do HTML estático original."
        }
    }

def ensure_raw_archive():
    """Baixa e extrai dgz.zip automaticamente se não estiver presente."""
    RAW_DIR.parent.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR.parent / "dgz.zip"
    
    if not RAW_DIR.exists() or not any(RAW_DIR.iterdir()):
        if not zip_path.exists():
            print("📥 Baixando dgz.zip do repositório oficial CEDAP/UFRGS (~56 MB)...")
            import urllib.request
            url = "https://cedap.ufrgs.br/xmlui/bitstream/handle/20.500.11959/1269/dgz.zip?sequence=1"
            urllib.request.urlretrieve(url, zip_path)
            print(f"✅ Download concluído: {zip_path}")
        
        print("📦 Descompactando acervo histórico em data/raw/dgz...")
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(RAW_DIR.parent)
        print("✅ Acervo descompactado com sucesso.")

def main():
    print("🚀 [BRAN Org] Iniciando parser censitário da DataGramaZero...")
    ensure_raw_archive()
    if not RAW_DIR.exists():
        print(f"❌ Diretório não encontrado: {RAW_DIR}")
        return

    issues = sorted([d for d in os.listdir(RAW_DIR) if (RAW_DIR / d).is_dir()])
    print(f"📦 Total de diretórios de fascículos: {len(issues)}")

    all_articles = []
    seen_ids = set()

    for issue in issues:
        issue_dir = RAW_DIR / issue
        # Artigos são nomeados Art_XX.htm, art_XX.htm, etc.
        art_files = sorted([f for f in os.listdir(issue_dir) if re.match(r'^art[_-]?\d+\.html?$', f, re.IGNORECASE)])
        for art_f in art_files:
            file_path = issue_dir / art_f
            parsed = parse_article_html(file_path, issue)
            if parsed:
                # Evita duplicatas se houver
                if parsed["id"] in seen_ids:
                    parsed["id"] = f"{parsed['id']}-{len(seen_ids)}"
                seen_ids.add(parsed["id"])
                all_articles.append(parsed)

    # Ordena por ano descendente, depois volume e artigo
    all_articles.sort(key=lambda x: (x.get("year", 0), x.get("volume", 0), x.get("number", 0)), reverse=True)

    print(f"\n✅ Total de artigos estruturados com sucesso: {len(all_articles)}")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"📁 Dataset salvo em: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
