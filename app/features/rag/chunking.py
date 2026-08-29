def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Potong teks jadi chunk dengan overlap (berbasis karakter, sederhana).

    - `chunk_size`: panjang maksimal tiap chunk (karakter).
    - `overlap`: jumlah karakter yang diulang antar-chunk, supaya konteks di
      batas potongan tidak hilang.

    Contoh: teks 1200 char, chunk_size 500, overlap 50 →
    chunk 1: [0:500], chunk 2: [450:950], chunk 3: [900:1200].
    """
    if not text.strip():
        return []

    text = text.strip()
    chunks: list[str] = []

    if len(text) <= chunk_size:
        return [text]

    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start += step

    return chunks
