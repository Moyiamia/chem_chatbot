# qa_engine.py
import os, re
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import google.generativeai as genai

load_dotenv()

# Embedding / Vector store 
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = FAISS.load_local("vector_dbs_all", embedding, allow_dangerous_deserialization=True)

#  Gemini 
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-flash-lite")


def _bold_keywords(text: str, query: str) -> str:
   
    tokens = sorted({t.lower() for t in re.findall(r"[A-Za-z]{3,}", query)}, key=len, reverse=True)
    for t in tokens:
        text = re.sub(rf"(?i)\b({re.escape(t)})\b", r"**\1**", text)
    return text


def _to_list(val):
    """只保留非空且是 http/https 开头的链接"""
    if not val or val == "N/A":
        return []
    if isinstance(val, list):
        return [x for x in val if isinstance(x, str) and x.strip().lower().startswith(("http://", "https://"))]
    if isinstance(val, str) and val.strip().lower().startswith(("http://", "https://")):
        return [val.strip()]
    return []

def _normalize_citation_groups(text: str) -> str:
    """把 [1, 2] / [1 2] / [1;2] 这些拆成 [1][2]；多次迭代直到没有可替换的"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\[(\d+)\s*[,; ]\s*(\d+)\]", r"[\1][\2]", text)
    return text

def _linkify_citations(text: str, ordered_sources: list[str]) -> str:
    """把 [n] 变成 [[n]](url)，只链接有效编号。"""
    max_n = len(ordered_sources)
    def repl(m):
        n = int(m.group(1))
        if 1 <= n <= max_n:
            return f"[[{n}]]({ordered_sources[n-1]})"
        return m.group(0)
    return re.sub(r"\[(\d+)\]", repl, text)

# 
def ask_question(user_query, k=4):
    # 1) 检索
    docs = db.similarity_search(user_query, k=k)

    # 2) 构建来源→编号
    source_to_id, ordered_sources = {}, []
    for d in docs:
        for s in _to_list(d.metadata.get("source")):
            if s not in source_to_id:
                source_to_id[s] = len(source_to_id) + 1
                ordered_sources.append(s)

    # 3) 供模型参考的片段（带允许的标签）
    parts = []
    for d in docs:
        ids = "".join(f"[{source_to_id[s]}]" for s in _to_list(d.metadata.get("source"))) or "[N/A]"
        meta = f"(module={d.metadata.get('module','N/A')}, page={d.metadata.get('page','N/A')})"
        parts.append(f"{ids} {meta}\n{d.page_content}")
    context = "\n\n".join(parts)

    # 4) 生成 —— 合并你的风格 + 稳定引用规则
    prompt = f"""
You are a helpful assistant for chemistry postgraduate students.

Below is a collection of reference content retrieved from university documents. 
Your task is to write a helpful, organized, and detailed answer to the user's question. 

Please:
- Combine and paraphrase the relevant points
- Do not just repeat raw excerpts
- Write in a clear, informative, and friendly tone
- If multiple steps are involved, use bullet points or numbering
- Insert source citations in square brackets like [1], [2] **immediately after** relevant sentences or bullet points
- A single source number can appear multiple times if relevant
- Do NOT limit each source to just one sentence — fully integrate all relevant information into a cohesive answer

Citation rules (strict):
- Use only citation numbers that appear with the snippets below
- Each tag must be standalone like [1]; if multiple apply, write them back-to-back with no commas/spaces: [1][2][4]
- Do NOT output URLs or a sources list; only use the inline tags

Reference Content (each snippet is prefixed with the allowed tag(s)):
{context}

User's Question:
{user_query}

Answer:
""".strip()

    resp = model.generate_content(prompt)
    base = (resp.text or "").strip()

    
    base = _normalize_citation_groups(base)
    answer_md = _linkify_citations(base, ordered_sources)

    
    citations = []
    for idx, url in enumerate(ordered_sources, start=1):
        chosen = None
        for d in docs:
            if url in _to_list(d.metadata.get("source")):
                chosen = d
                break
        module = chosen.metadata.get("module", "N/A") if chosen else "N/A"
        page = chosen.metadata.get("page", "N/A") if chosen else "N/A"
        raw = (chosen.page_content if chosen else "") or ""
        excerpt = raw.strip().replace("\n", " ")
        #if len(excerpt) > 260:
            #excerpt = excerpt[:260].rstrip() + "…"
        excerpt = _bold_keywords(excerpt, user_query)
        if len(excerpt) > 420:                            
            excerpt = excerpt[:420].rstrip() + "…"
        citations.append({
            "n": idx,
            "url": url,
            "module": module,
            "page": page,
            "excerpt": excerpt if excerpt else "(no excerpt)",
        })

    return {"answer_md": answer_md, "citations": citations}

def reload_index(index_dir: str = "vector_dbs_all"):
    """renew FAISS """
    global embedding, db
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.load_local(index_dir, embedding, allow_dangerous_deserialization=True)