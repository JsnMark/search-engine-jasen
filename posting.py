"""
posting.py



[uint32_t ] [uint32_t ] [uint32_t     ] [uint32_t ] [uint32_t ]
[docid    ] [title_tf ] [important_tf ] [n_pos    ] [pos      ] * n_pos
"""

import struct

U32 = struct.Struct("<I")
POSTING_HEADER = struct.Struct("<IIII") # docid, titletf, importanttf, npos


class Posting():
    def __init__(self, did: int, positions = None, tile_tf = 0, important_tf = 0):
        self.did = did # document id
        self.positions = positions if positions is not None else []
        self.title_tf = tile_tf
        self.important_tf = important_tf

    @property
    def tf(self):
        return len(self.positions)

    @property
    def nbytes(self):
        """"Size of postings in bytes after serialization"""
        return POSTING_HEADER.size + U32.size * len(self.positions)

    def serialize(self):
        n = len(self.positions)
        header = POSTING_HEADER.pack(self.did, self.title_tf, self.important_tf, n)
        return header + struct.pack(f"<{n}I", *self.positions)

    @classmethod
    def deserialize(cls, buf, offset: int = 0):
        """
        Decodes one posting starting at buf[offset].
        Returns (posting, offset just past this posting).
        """
        did, title_tf, important_tf, n = POSTING_HEADER.unpack_from(buf, offset)
        offset += POSTING_HEADER.size
        positions = list(struct.unpack_from(f"<{n}I", buf, offset))
        offset += U32.size * n
        return cls(did, positions, title_tf, important_tf), offset

    def __eq__(self, other):
        return (isinstance(other, Posting)
                and self.did == other.did
                and self.positions == other.positions
                and self.title_tf == other.title_tf
                and self.important_tf == other.important_tf)

    def __repr__(self):
        return (f"Posting(did={self.did}, positions={self.positions}, "
                f"title_tf={self.title_tf}, important_tf={self.important_tf})")