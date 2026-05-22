"""Q&A hook — mirrors src/hooks/useQA.ts."""
from __future__ import annotations

def useQA(question: str = "") -> dict:
    """Q&A interaction."""
    return {"question": question, "answer": None}

use_qa = useQA
