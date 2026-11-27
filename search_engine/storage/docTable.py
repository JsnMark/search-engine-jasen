"""
docTable.py

manages .docs and .urls

doc entry format
[uint64_t  ] [uint32_t] [uint32_t   ]
[url_offset] [url_len ] [token_count]

url entry format
[str]
[url]
"""

import logging
import struct
import os
from pathlib import Path
from typing import BinaryIO, NamedTuple

from search_engine.storage.common import _Owned

DOC_RECORD = struct.Struct("<QII") # url_offset, url_len, token_count
URLS_FEXT  = ".urls"
DOCS_FEXT  = ".docs"


class DocEntry(NamedTuple):
    url: str
    token_count: int


class DocTableWriter(_Owned):
    def __init__(self, docs_file: BinaryIO, urls_file: BinaryIO):
        self.docs_file = docs_file
        self.urls_file = urls_file
        self._files = (docs_file, urls_file)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @property
    def docs_file_name(self):
        return getattr(self.docs_file, "name", None)
    @property
    def urls_file_name(self):
        return getattr(self.urls_file, "name", None)

    @classmethod
    def open(cls, out_dir: Path, name: str) -> DocTableWriter:
        docTableWriter = cls(
            open(out_dir / f"{name}{DOCS_FEXT}", "wb"),
            open(out_dir / f"{name}{URLS_FEXT}", "wb"),
        )
        docTableWriter._owns = True
        return docTableWriter

    def write(self, url: str, token_count: int):
        """
        Writes the url to .urls and its record to .docs.
        Must be called once per docid, in increasing docid order,
        since the record for docid i lives at i * DOC_RECORD.size.
        """
        url_bytes = url.encode("utf-8")
        url_offset = self.urls_file.tell()
        self.urls_file.write(url_bytes)
        self.docs_file.write(DOC_RECORD.pack(url_offset, len(url_bytes), token_count))


class DocTableReader(_Owned):
    def __init__(self, docs_file: BinaryIO, urls_file: BinaryIO):
        self.docs_file = docs_file
        self.urls_file = urls_file
        self._files = (docs_file, urls_file)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # .docs is fixed width, so the doc count comes from its size
        self.docs_file.seek(0, os.SEEK_END)
        size = self.docs_file.tell()
        if size % DOC_RECORD.size != 0:
            raise ValueError(f"{self.docs_file_name or "<stream>"}: truncated .docs ({size} bytes is not a multiple of {DOC_RECORD.size})")
        self._n = size // DOC_RECORD.size

    @property
    def docs_file_name(self):
        return getattr(self.docs_file, "name", None)
    @property
    def urls_file_name(self):
        return getattr(self.urls_file, "name", None)

    @classmethod
    def open(cls, out_dir: Path, name: str) -> DocTableReader:
        docTableReader = cls(
            open(out_dir / f"{name}{DOCS_FEXT}", "rb"),
            open(out_dir / f"{name}{URLS_FEXT}", "rb"),
        )
        docTableReader._owns = True
        return docTableReader

    def url(self, docid: int) -> str:
        url_offset, url_len, _ = self._read_docs_record(docid)
        self.urls_file.seek(url_offset)
        return self._read_exact_len(self.urls_file, url_len).decode("utf-8")

    def token_count(self, docid: int) -> int:
        """
        Body token count of a doc, without touching .urls
        """
        return self._read_docs_record(docid)[2]

    def get(self, docid: int) -> DocEntry:
        url_offset, url_len, token_count = self._read_docs_record(docid)
        self.urls_file.seek(url_offset)
        url = self._read_exact_len(self.urls_file, url_len).decode("utf-8")
        return DocEntry(url, token_count)

    def __len__(self) -> int:
        """
        Number of documents in the table
        """
        return self._n

    def _read_docs_record(self, docid: int) -> tuple[int, int, int]:
        if not 0 <= docid < self._n:
            raise IndexError(f"docid {docid} out of range [0, {self._n})")
        self.docs_file.seek(docid * DOC_RECORD.size)
        return DOC_RECORD.unpack(self._read_exact_len(self.docs_file, DOC_RECORD.size))

    def _read_exact_len(self, f: BinaryIO, n: int) -> bytes:
        data = f.read(n)
        if len(data) != n:
            raise ValueError(f"{getattr(f, "name", "<stream>")}: truncated (wanted {n} bytes, got {len(data)})")
        return data

    def __getitem__(self, docid: int) -> DocEntry:
        return self.get(docid)
