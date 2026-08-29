from app.features.rag.chunking import chunk_text


def test_chunk_text_single_chunk_when_short():
    text = "Hello world"
    assert chunk_text(text) == ["Hello world"]


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_splits_with_overlap():
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    # 1200 char / step 450 → chunk 1: 0-500, 2: 450-950, 3: 900-1200.
    assert len(chunks) == 3
    assert len(chunks[0]) == 500
    assert len(chunks[1]) == 500
    assert chunks[0][-50:] == chunks[1][:50]  # overlap 50


def test_chunk_text_no_overlap_when_zero():
    text = "B" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=0)

    assert len(chunks) == 2
    assert len(chunks[0]) == 500
    assert len(chunks[1]) == 500


def test_chunk_text_preserves_content():
    text = " ".join(str(i) for i in range(200))
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    # Semua teks asli tetap ada di gabungan chunk.
    assert "199" in " ".join(chunks)
