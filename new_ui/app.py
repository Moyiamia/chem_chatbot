import os
import time
import uuid
from pathlib import Path
from typing import List, Dict

import streamlit as st

from qa_bridge import init_engine, ask, reload_engine
from worker import save_pdf, build_index_async, delete_pdf

#  基础配置 
st.set_page_config(page_title="Dissertation QA", layout="wide")
ADMIN_PASS = os.getenv("ADMIN_PASS", "123456")
INDEX_DIR = os.getenv("INDEX_DIR", "vector_dbs_all")
PDF_DIR = os.getenv("PDF_DIR", "pdfs")

# 样式：采用第一版紧凑样式 + 标题样式 
st.markdown("""
<style>
.app-title { white-space: nowrap; font-size: 2rem; font-weight: 700; margin: 0 0 .25rem 0; }
section[data-testid="stHorizontalBlock"] button { padding:4px 10px; height:32px; white-space:nowrap; }
section[data-testid="stHorizontalBlock"] { gap: 0.6rem !important; }
</style>
""", unsafe_allow_html=True)

#  会话状态 
if "messages" not in st.session_state:
    st.session_state.messages = []
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:8]

#  文件与索引辅助 
def _is_url(u: str) -> bool:
    return bool(u) and (u.startswith("http://") or u.startswith("https://") or u.startswith("/"))

@st.cache_data(ttl=5)
def list_pdfs() -> List[Dict]:
    p = Path(PDF_DIR)
    p.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(p.glob("*.pdf")):
        items.append({
            "name": f.name,
            "path": str(f),
            "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
            "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
        })
    return items

@st.cache_data(ttl=5)
def indexed_doc_ids(index_dir: str) -> Dict[str, int]:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        db = FAISS.load_local(index_dir, emb, allow_dangerous_deserialization=True)
    except Exception:
        return {}
    counts = {}
    for _, v in db.docstore._dict.items():
        did = v.metadata.get("doc_id")
        if not did or did == "__init__":
            continue
        counts[did] = counts.get(did, 0) + 1
    return counts

#  侧边栏 
with st.sidebar:
    st.markdown("### Library Admin")
    st.caption("Need to manage the library? Enter the admin password.")

    if not st.session_state.admin_mode:
        pwd = st.text_input("Admin Password", type="password", placeholder="Admin password")
        if st.button("Enter Maintenance Mode", use_container_width=True):
            if pwd == ADMIN_PASS:
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("Incorrect password")
    else:
        st.success("In Maintenance Mode")
        if st.button("Exit Maintenance Mode", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()

    st.divider()
    if st.button("New Chat  \n(Clear Current History)", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

#  页面头部 
left, right = st.columns([1, 1])
with left:
    st.markdown('<div class="app-title">📚 Chemistry Student Info Chatbot</div>', unsafe_allow_html=True)
with right:
    st.caption(f"Session: {st.session_state.session_id}")

#  管理区（合并逻辑 + 第一版布局）
if st.session_state.admin_mode:
    st.subheader("🛠️ Library Maintenance")

    st.info(
        "Quick guide: 1) Upload PDFs → 2) Click **Save and Update Library** → "
        "3) Click **Refresh Library** → 4) Start asking questions."
    )

    top1, top2, top3, top4, top5 = st.columns([2, 1.1, 1.1, 1.1, 0.7])
    with top1:
        up = st.file_uploader("Upload PDF (Drag & Drop or Select)", type=["pdf"])
        source_url = st.text_input("Source URL (required)", placeholder="https://...")

    with top2:
        if up and st.button("Save & Build (incremental)", use_container_width=True):
            url = (source_url or "").strip()
            if not url:
                st.error("Please enter a Source URL before saving.")
            else:
                path = save_pdf(up, up.name, source_url=url)
                build_index_async(target_pdf_path=path)
                st.success(f"Saved: {os.path.basename(path)}. Incremental build started in background.")
                list_pdfs.clear(); indexed_doc_ids.clear()

    with top3:
        if st.button("Rebuild Entire Library (Slower)", use_container_width=True):
            build_index_async()
            st.info("Full rebuild started in the background")

    with top4:
        if st.button("Refresh Library", use_container_width=True):
            msg = reload_engine(INDEX_DIR)
            st.success(f"Library status: {msg}")
            indexed_doc_ids.clear()

    with top5:
        if st.button("Refresh", use_container_width=True):
            list_pdfs.clear(); indexed_doc_ids.clear()

    st.markdown("### 📄 Document List")
    files = list_pdfs()
    indexed = indexed_doc_ids(INDEX_DIR)

    if not files:
        st.info("The PDFs folder is empty. Please upload some PDFs first.")
    else:
        h1, h2, h3, h4, h5, h6 = st.columns([4.5, 1, 1.6, 1.7, 1.1, 1.4])
        h1.write("File Name"); h2.write("Size (MB)"); h3.write("Last Modified"); h4.write("Searchable Status"); h5.write("Actions"); h6.write("")

        for f in files:
            name = f["name"]
            size = f["size_mb"]
            mtime = f["mtime"]
            path = f["path"]
            nvec = indexed.get(name, 0)

            c1, c2, c3, c4, c5, c6 = st.columns([4.5, 1, 1.6, 1.7, 1.1, 1.4])
            c1.write(name)
            c2.write(size)
            c3.write(mtime)
            # c4.success(f"Indexed {nvec}") if nvec > 0 else c4.warning("Not yet searchable")
            if nvec > 0:
                c4.success(f"Indexed {nvec}")
            else:
                c4.warning("Not yet searchable")


            if c5.button("Delete", key=f"del_{name}", use_container_width=True):
                delete_pdf(name)
                build_index_async(delete_doc_id=name)
                st.warning(f"Submitted deletion: {name}. Click \"Refresh Library\" above to apply.")
                list_pdfs.clear(); indexed_doc_ids.clear()

            try:
                with open(path, "rb") as fh:
                    c6.download_button("Download", data=fh.read(), file_name=name, mime="application/pdf")
            except Exception:
                c6.write("")

        idx_path = os.path.join(INDEX_DIR, "index.faiss")
        if os.path.exists(idx_path):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(idx_path)))
            st.caption(f"Library last updated: {ts}")
        else:
            st.caption("Library not found (please rebuild it once).")

    st.divider()

#  初始化引擎 
try:
    init_engine(index_dir=INDEX_DIR)
except Exception as e:
    st.error(f"RuntimeError: Unable to start the engine. Please check qa_engine.py: {e}")
    st.stop()

#  引用函数 
def _render_citation(c: Dict):
    n = c.get("n", "?")
    module = c.get("module", "N/A")
    page = c.get("page", "N/A")
    url = (c.get("url", "") or "").strip()
    parts = [f"**[{n}]** {module} (p.{page})"]
    if _is_url(url):
        parts.append(f"[{url}]({url})")
    excerpt = c.get("excerpt", "(no excerpt)")
    parts.append(f"> {excerpt}")
    st.markdown("\n\n".join(parts))

#  历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        cits = msg.get("citations") or []
        if cits:
            with st.expander("🔎 References (click to view)", expanded=False):
                for c in cits:
                    _render_citation(c)

#  聊天输入
user_input = st.chat_input("Enter your question (answers are based on the teacher-maintained PDF library)")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        citations = []
        try:
            result = ask(user_input)
            answer_md = (result or {}).get("answer_md", "").strip()
            citations = (result or {}).get("citations", []) or []
            if not answer_md:
                answer_md = "(No answer generated — please check if the library is updated and reloaded)"
            placeholder.markdown(answer_md)
            if citations:
                with st.expander("🔎 References (click to view)", expanded=False):
                    for c in citations:
                        _render_citation(c)
        except Exception as e:
            answer_md = f"Backend error: {e}"
            placeholder.markdown(answer_md)
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer_md,
        "citations": citations,
    })
