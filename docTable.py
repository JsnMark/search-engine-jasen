"""
docTable.py

The document table: maps a docid to its url and token count.

.urls:  url bytes (UTF-8) back to back, no separators
.docs:  one fixed 12-byte record per document, docid i at byte i * 12
        [url_off u32][url_len u32][token_count u32]   (little-endian)

Docids must be assigned densely (0, 1, 2, ...) in the order documents are
added, so the record for docid i is the i-th record written.
"""

import struct

DOC_RECORD = struct.Struct("<III")  # url_off, url_len, token_count


class DocTableWriter:
    """Appends documents to open .docs and .urls files (binary mode)."""

    def __init__(self, docs_file, urls_file):
        self.docs_file = docs_file
        self.urls_file = urls_file
        self.url_offset = 0
        self.count = 0

    def add(self, url: str, token_count: int) -> int:
        """Writes one document and returns its docid."""
        url_bytes = url.encode("utf-8")
        self.docs_file.write(DOC_RECORD.pack(self.url_offset, len(url_bytes), token_count))
        self.urls_file.write(url_bytes)
        self.url_offset += len(url_bytes)

        did = self.count
        self.count += 1
        return did


class DocTableReader:
    """Random access into .docs and .urls files (binary mode)."""

    def __init__(self, docs_file, urls_file):
        self.docs_file = docs_file
        self.urls_file = urls_file

    def __len__(self):
        self.docs_file.seek(0, 2)  # seek to end
        return self.docs_file.tell() // DOC_RECORD.size

    def get(self, did: int):
        """Returns (url, token_count) for a docid."""
        self.docs_file.seek(did * DOC_RECORD.size)
        data = self.docs_file.read(DOC_RECORD.size)
        if len(data) != DOC_RECORD.size:
            raise IndexError(f"docid {did} out of range")
        url_off, url_len, token_count = DOC_RECORD.unpack(data)

        self.urls_file.seek(url_off)
        url_bytes = self.urls_file.read(url_len)
        if len(url_bytes) != url_len:
            raise ValueError(f"url for docid {did} is truncated")
        return url_bytes.decode("utf-8"), token_count
