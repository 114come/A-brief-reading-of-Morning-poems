import pytest
from app.services.ai.knowledge_base.chunker import fixed_length_chunk


def test_empty_text():
    assert fixed_length_chunk("") == [""]


def test_short_text_no_chunking():
    text = "Hello world"
    result = fixed_length_chunk(text, chunk_size=100, overlap=0)
    assert result == ["Hello world"]


def test_exact_chunk_size():
    text = "A" * 50
    result = fixed_length_chunk(text, chunk_size=50, overlap=0)
    assert result == ["A" * 50]


def test_two_chunks():
    text = "A" * 60
    result = fixed_length_chunk(text, chunk_size=50, overlap=0)
    assert len(result) == 2
    assert len(result[0]) == 50
    assert len(result[1]) == 10


def test_overlap():
    text = "Hello World. This is a test. " * 20
    result = fixed_length_chunk(text, chunk_size=50, overlap=10)
    assert len(result) >= 2
    # Verify overlap: the start of chunk 2 should be earlier than end of chunk 1
    assert result[1].startswith(result[0][-10:])


def test_break_at_newline():
    text = "Short line\n" + "X" * 100 + "\nEnd"
    result = fixed_length_chunk(text, chunk_size=50, overlap=0)
    # Lines shorter than chunk_size/2 should not force break
    assert len(result) >= 2
