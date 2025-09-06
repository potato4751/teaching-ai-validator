# train.py - Process all PDFs in data folder and save knowledge base
import os
import json
import pickle
from pathlib import Path
from typing import List, Dict

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from PyPDF2 import PdfReader

# --- Configuration ---
DATA_DIR = Path("data")
PROCESSED_DIR = Path("processed")
PROCESSED_DIR.mkdir(exist_ok=True)

CHUNK_SIZE = 400  # words per chunk
CHUNK_OVERLAP = 80  # overlapping words

# --- Helper functions ---
def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"Warning: failed to extract page {i} in {pdf_path.name}: {e}")
            text = ""
        pages.append(text)
    return "\n\n".join(pages)

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    i = 0
    cid = 0
    while i < len(words):
        start = i
        end = min(i + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "id": cid,
            "text": chunk_text,
            "start_word": start,
            "end_word": end,
        })
        cid += 1
        if end == len(words):
            break
        i = end - overlap
    return chunks

# --- Main processing ---
def main():
    # Find all PDFs
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {DATA_DIR.resolve()}")

    all_chunks = []
    current_chunk_id = 0

    for pdf_file in pdf_files:
        pdf_path = DATA_DIR / pdf_file
        print(f"Processing {pdf_file}...")
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text)
        # Add source PDF info
        for c in chunks:
            c["source_pdf"] = pdf_file
            c["id"] = current_chunk_id
            current_chunk_id += 1
        all_chunks.extend(chunks)

    print(f"Total chunks created: {len(all_chunks)}")

    # Save chunks as JSON
    chunks_path = PROCESSED_DIR / "chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    # Build TF-IDF matrix
    texts = [c["text"] for c in all_chunks]
    vect = TfidfVectorizer(max_features=20000, ngram_range=(1,2), stop_words="english")
    X = vect.fit_transform(texts)
    print("TF-IDF matrix shape:", X.shape)

    # Save vectorizer and matrix
    vect_path = PROCESSED_DIR / "tfidf_vectorizer.pkl"
    with open(vect_path, "wb") as f:
        pickle.dump(vect, f)

    matrix_path = PROCESSED_DIR / "tfidf_matrix.npz"
    sparse.save_npz(str(matrix_path), X)

    print("Saved:")
    print(" -", chunks_path)
    print(" -", vect_path)
    print(" -", matrix_path)

if __name__ == "__main__":
    main()
