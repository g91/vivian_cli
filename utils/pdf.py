"""PDF utilities — mirrors src/utils/pdf.ts"""
from __future__ import annotations
from typing import Optional

def is_pdf_file(path: str) -> bool:
    return path.lower().endswith(".pdf")

def read_pdf_text(path: str) -> Optional[str]:
    try:
        import pypdf
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        return None
    except Exception:
        return None
