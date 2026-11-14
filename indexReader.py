"""
indexReader.py

Looks up tokens in the final index files without loading the whole index.

Lookup of a token:
  1. binary search the in-memory .postingsIdxIdx tokens for the last one <= the token
  2. read that one block of .postingsIdx (at most IDX_IDX_INTERVAL entries) and
     scan it for the token; if it isn't there, the token isn't in the index
  3. seek to the token's offset in .postings and read byte_len bytes

Usage as a debug tool:
    python3 indexReader.py out myInvIndex apple banana
"""

import io
import sys
from bisect import bisect_right
from pathlib import Path

from posting import deserialize_postings
from indexFiles import read_idx_entry, read_idx_idx_entry
from docTable import DocTableReader


class IndexReader:
    POSTINGS_FEXT         = ".postings"
    POSTINGS_IDX_FEXT     = ".postingsIdx"
    POSTINGS_IDX_IDX_FEXT = ".postingsIdxIdx"
    DOCS_FEXT             = ".docs"
    URLS_FEXT             = ".urls"

    def __init__(self, out_path: str, out_filename: str):
        base = Path(out_path) / out_filename
        path = lambda fext: base.with_name(base.name + fext)

        # The only thing held in memory: every X-th token and its .postingsIdx offset.
        self.idx_idx_tokens = []
        self.idx_idx_offsets = []
        with open(path(self.POSTINGS_IDX_IDX_FEXT), "rb") as f:
            while (entry := read_idx_idx_entry(f)) is not None:
                self.idx_idx_tokens.append(entry[0])
                self.idx_idx_offsets.append(entry[1])

        self.postings_file = open(path(self.POSTINGS_FEXT), "rb")
        self.idx_file = open(path(self.POSTINGS_IDX_FEXT), "rb")
        self.idx_size = self.idx_file.seek(0, io.SEEK_END)
        self.docs = DocTableReader(open(path(self.DOCS_FEXT), "rb"), open(path(self.URLS_FEXT), "rb"))

    # ------------------ lookups ------------------------

    def lookup(self, token: str):
        """
        Returns (offset, byte_len, posting_count) of the token's posting list
        in .postings, or None if the token isn't in the index.
        """
        i = bisect_right(self.idx_idx_tokens, token) - 1
        if i < 0:
            return None  # sorts before the first token in the index

        # Read the whole block in one go: from this sparse entry to the next one
        # (or to the end of .postingsIdx for the last block).
        start = self.idx_idx_offsets[i]
        end = self.idx_idx_offsets[i + 1] if i + 1 < len(self.idx_idx_offsets) else self.idx_size
        self.idx_file.seek(start)
        block = io.BytesIO(self.idx_file.read(end - start))

        while (entry := read_idx_entry(block)) is not None:
            entry_token, offset, byte_len, posting_count = entry
            if entry_token == token:
                return offset, byte_len, posting_count
            if entry_token > token:
                break  # passed where it would be, so it isn't in the index
        return None

    def get_postings(self, token: str) -> list:
        """Returns the token's postings (sorted by docid), or [] if not in the index."""
        found = self.lookup(token)
        if found is None:
            return []
        offset, byte_len, posting_count = found
        self.postings_file.seek(offset)
        postings = deserialize_postings(self.postings_file.read(byte_len))
        if len(postings) != posting_count:
            raise ValueError(f"{token!r}: expected {posting_count} postings, decoded {len(postings)}")
        return postings

    def document_frequency(self, token: str) -> int:
        found = self.lookup(token)
        return found[2] if found else 0

    def get_doc(self, did: int):
        """Returns (url, token_count) for a docid."""
        return self.docs.get(did)

    @property
    def num_docs(self) -> int:
        return len(self.docs)

    # ------------------ cleanup ------------------------

    def close(self):
        for f in (self.postings_file, self.idx_file, self.docs.docs_file, self.docs.urls_file):
            f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    out_path, out_filename, *tokens = sys.argv[1:]
    with IndexReader(out_path, out_filename) as reader:
        print(f"{reader.num_docs} docs, {len(reader.idx_idx_tokens)} sparse index entries in memory")
        for token in tokens:
            postings = reader.get_postings(token)
            print(f"\n{token}: df={len(postings)}")
            for p in postings[:5]:
                url, _ = reader.get_doc(p.did)
                print(f"    did={p.did} tf={p.tf} {url}")
            if len(postings) > 5:
                print(f"    ... {len(postings) - 5} more")
