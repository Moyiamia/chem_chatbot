# build_vector_all.py
import argparse
import glob
import json
import os
import re
from typing import List

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from module_links import MODULE_LINKS

from urllib.parse import quote

def _is_http_url(u: str) -> bool:
    return isinstance(u, str) and u.strip().lower().startswith(("http://", "https://"))


# 可执行 tesseract 路径（你的环境已设此路径，如不同请自行调整）
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

# 目录常量
ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = "vector_dbs_all"
PDF_DIR = "pdfs"
STATIC_PDF_DIR = os.path.join(ROOT, ".streamlit", "static", "pdfs")
os.makedirs(STATIC_PDF_DIR, exist_ok=True)

# 手动链接映射（老师上传时可写入 links.json）
LINKS_JSON = os.path.join(ROOT, "links.json")
try:
    with open(LINKS_JSON, "r", encoding="utf-8") as f:
        LINK_MAP = json.load(f) or {}
except Exception:
    LINK_MAP = {}


# ----------------- 基础：加载/创建索引 -----------------
def _load_db():
    emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    index_path = os.path.join(INDEX_DIR, "index.faiss")

    if os.path.exists(index_path):
        db = FAISS.load_local(INDEX_DIR, emb, allow_dangerous_deserialization=True)
        return db, emb

    os.makedirs(INDEX_DIR, exist_ok=True)
    db = FAISS.from_texts(["__init__"], embedding=emb, metadatas=[{"doc_id": "__init__"}])
    db.delete(list(db.docstore._dict.keys()))
    db.save_local(INDEX_DIR)
    return db, emb


# ----------------- 抽取+切分：优先文本，失败走 OCR -----------------
def _split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n{2,}|\n\s*\n", text) if len(p.strip()) > 50]


# def _source_for(fname: str, module_link: str) -> str:
#     """
#     来源优先级：
#     1) links.json 的手动链接
#     2) module_links 里的外链（不为 N/A）
#     3) 本地静态文件链接 /static/pdfs/<fname>
#     """
#     manual = LINK_MAP.get(fname)
#     if manual:
#         return manual
#     if module_link and module_link != "N/A":
#         return module_link
#     return f"/static/pdfs/{fname}"


def _source_for(fname: str, module_link: str) -> str:
    """
    New rule:
    - Only use teacher-provided URL from links.json
    - If not provided (or not http/https), return empty string ("")
    - No fallback to MODULE_LINKS or /static
    """
    manual = ""
    try:
        with open(LINKS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        manual = (data.get(fname) or "").strip()
    except Exception:
        manual = ""

    return manual if _is_http_url(manual) else ""


def _extract_chunks_from_pdf(pdf_path: str) -> List[Document]:
    module_name = os.path.splitext(os.path.basename(pdf_path))[0]
    module_link = MODULE_LINKS.get(module_name, "N/A")
    fname = os.path.basename(pdf_path)
    source_url = _source_for(fname, module_link)

    chunks: List[Document] = []

    # 1) 优先用 pypdf 抽文本
    try:
        reader = PdfReader(pdf_path)
        any_text = False
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                any_text = True
                for para in _split_paragraphs(text):
                    chunks.append(
                        Document(
                            page_content=para,
                            metadata={
                                "doc_id": fname,
                                "module": module_name,
                                "source": source_url,
                                "page": page_num,
                            },
                        )
                    )
        if any_text:
            return chunks
    except Exception:
        # 允许回退到 OCR
        pass

    # 2) OCR 兜底
    images = convert_from_path(pdf_path, dpi=300)
    for page_num, image in enumerate(images, start=1):
        text = pytesseract.image_to_string(image)
        for para in _split_paragraphs(text):
            chunks.append(
                Document(
                    page_content=para,
                    metadata={
                        "doc_id": fname,
                        "module": module_name,
                        "source": source_url,
                        "page": page_num,
                    },
                )
            )
    return chunks


# ----------------- 操作：增量添加 / 删除 / 全量重建 -----------------
def add_pdf_to_index(pdf_path: str):
    db, _ = _load_db()
    docs = _extract_chunks_from_pdf(pdf_path)
    if not docs:
        print(f"[warn] no docs extracted from {pdf_path}")
        return
    db.add_documents(docs)
    db.save_local(INDEX_DIR)
    print(f"[ok] added: {os.path.basename(pdf_path)} ({len(docs)} chunks)")


def delete_by_doc_id(doc_id: str):
    db, _ = _load_db()
    keys = [k for k, v in db.docstore._dict.items() if v.metadata.get("doc_id") == doc_id]
    if not keys:
        print(f"[warn] not found: {doc_id}")
        return
    db.delete(keys)
    db.save_local(INDEX_DIR)
    print(f"[ok] deleted: {doc_id} ({len(keys)} vectors)")


def rebuild_all():
    db, _ = _load_db()
    all_keys = list(db.docstore._dict.keys())
    if all_keys:
        db.delete(all_keys)
        db.save_local(INDEX_DIR)

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    if not pdfs:
        print("[warn] no pdf files in 'pdfs/'")
    for p in pdfs:
        add_pdf_to_index(p)
    print("[ok] rebuild done. total pdfs:", len(pdfs))


# ----------------- CLI -----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, help="only index this PDF (incremental)")
    parser.add_argument("--delete", type=str, help="delete by doc_id (filename)")
    parser.add_argument("--rebuild", action="store_true", help="rebuild all")
    args = parser.parse_args()

    if args.delete:
        delete_by_doc_id(args.delete)
    elif args.pdf:
        add_pdf_to_index(args.pdf)
    elif args.rebuild:
        rebuild_all()
    else:
        rebuild_all()
