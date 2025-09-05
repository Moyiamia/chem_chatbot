# new_ui/qa_bridge.py
import os, sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_qe = None
_loaded = False

def init_engine(index_dir: Optional[str] = None):
    global _qe, _loaded
    if _loaded:
        return
    import qa_engine as qe
    _qe = qe
    _loaded = True

def reload_engine(index_dir: Optional[str] = None) -> str:
    """调用 qa_engine.reload_index 热加载"""
    if not _loaded:
        init_engine(index_dir)
    if hasattr(_qe, "reload_index"):
        _qe.reload_index(index_dir or "vector_dbs_all")
        return "reloaded"
    return "noop"

def ask(query: str):
    if not _loaded:
        init_engine()
    return _qe.ask_question(query)
