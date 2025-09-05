# new_ui/worker.py
import os
import json
import shutil
import subprocess
import threading
from typing import Optional

# 路径常量
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "pdfs")
BUILD = os.path.join(ROOT, "build_vector_all.py")

# 静态目录（用于前端直接点击预览 /static/pdfs/<file>）
STATIC_PDF_DIR = os.path.join(ROOT, ".streamlit", "static", "pdfs")
os.makedirs(STATIC_PDF_DIR, exist_ok=True)

# 手动链接配置
LINKS_JSON = os.path.join(ROOT, "links.json")


def _update_links_map(filename: str, source_url: Optional[str]):
    """把老师手填的来源 URL 写入 links.json（供索引优先使用）。"""
    if not source_url:
        return
    try:
        data = {}
        if os.path.exists(LINKS_JSON):
            with open(LINKS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        data[filename] = source_url
        with open(LINKS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # 不阻塞主流程
        pass


def _remove_link_from_map(filename: str):
    """从 links.json 删除对应文件名的手动来源链接。"""
    try:
        if not os.path.exists(LINKS_JSON):
            return
        with open(LINKS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if filename in data:
            data.pop(filename, None)
            with open(LINKS_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # 不阻塞主流程
        pass


def save_pdf(file, filename: Optional[str] = None, source_url: Optional[str] = None) -> str:
    """
    保存上传的 PDF 到 pdfs/，复制一份到 .streamlit/static/pdfs/，
    并将可选的来源 URL 记录到 links.json。
    """
    os.makedirs(PDF_DIR, exist_ok=True)
    name = filename or file.name
    path = os.path.join(PDF_DIR, name)
    with open(path, "wb") as f:
        f.write(file.read())

    # 复制静态副本，供 /static/pdfs/<name> 直接点击
    try:
        shutil.copy2(path, os.path.join(STATIC_PDF_DIR, name))
    except Exception:
        pass

    # 记录手动来源链接
    _update_links_map(name, source_url)
    return path


def delete_pdf(filename: str) -> None:
    """从文件系统删除 PDF 本体和静态副本，并移除 links.json 中的手动链接。"""
    for base in (PDF_DIR, STATIC_PDF_DIR):
        try:
            os.remove(os.path.join(base, filename))
        except FileNotFoundError:
            pass
    # 同步清理手动链接
    _remove_link_from_map(filename)


def _run(cmd: list[str]):
    subprocess.run(cmd, check=True)


def build_index_async(target_pdf_path: Optional[str] = None, delete_doc_id: Optional[str] = None):
    """
    后台线程调用 build_vector_all.py：
    - --pdf <path>       增量添加
    - --delete <doc_id>  删除
    - --rebuild          全量重建
    """
    if not os.path.exists(BUILD):
        raise FileNotFoundError("build_vector_all.py not found")

    if delete_doc_id:
        cmd = ["python", BUILD, "--delete", delete_doc_id]
    elif target_pdf_path:
        cmd = ["python", BUILD, "--pdf", target_pdf_path]
    else:
        cmd = ["python", BUILD, "--rebuild"]

    t = threading.Thread(target=_run, args=(cmd,), daemon=True)
    t.start()
    return t
