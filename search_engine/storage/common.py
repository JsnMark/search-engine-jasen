"""
common.py
"""

import struct
from typing import BinaryIO

U32 = struct.Struct("<I")
U64 = struct.Struct("<Q")

def pack_str(s: str):
    """
    Takes a string and returns bytes in format
    [uint32][string  ]
    [strlen][strbytes]
    """
    b = s.encode("utf-8")
    result_bytes = bytearray()
    result_bytes += U32.pack(len(b))
    result_bytes += b
    return result_bytes

class _Owned:
    """
    Context-manager boilerplate: close the files only if we opened them.
    """
    _files: tuple[BinaryIO, ...] = ()
    _owns = False

    def close(self):
        if self._owns:
            for f in self._files:
                f.close()

    def __enter__(self): 
        return self
    
    def __exit__(self, *exc): 
        self.close()
        return False