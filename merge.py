"""
merge.py

Merges the sorted binary partial index files into the final index:
.postings, .postingsIdx and .postingsIdxIdx (formats in indexFiles.py).

This is a streaming k-way merge: one record per partial is held in a heap,
so memory use is about one token's postings, not the whole index.

Partials must be passed in the order they were written. Every docid in
partial N+1 is greater than every docid in partial N, so a token's final
posting list is just its lists from each partial joined in partial order.
The postings are never decoded, only copied.
"""

import heapq
from pathlib import Path

from posting import read_partial_record, write_partial_record_raw
from indexFiles import write_idx_entry, write_idx_idx_entry

U32_LIMIT = 2**32  # offsets are stored as u32


def merge_stream(paths):
    """
    Yields (token, posting_count, chunks) in sorted token order, where chunks
    is the token's raw postings bytes from each partial, in partial order.
    """
    files = [open(p, "rb") for p in paths]
    try:
        # heap entries: (token, partial index, posting_count, postings bytes).
        # Ties on token break on partial index, so a token's chunks come out
        # in partial (= docid) order.
        heap = []
        for i, f in enumerate(files):
            record = read_partial_record(f)
            if record is not None:
                heap.append((record[0], i, record[1], record[2]))
        heapq.heapify(heap)

        while heap:
            token = heap[0][0]
            posting_count = 0
            chunks = []
            while heap and heap[0][0] == token:
                _, i, count, raw = heapq.heappop(heap)
                posting_count += count
                chunks.append(raw)
                record = read_partial_record(files[i])
                if record is not None:
                    if record[0] <= token:
                        raise ValueError(f"{paths[i]} is not sorted: {record[0]!r} after {token!r}")
                    heapq.heappush(heap, (record[0], i, record[1], record[2]))
            yield token, posting_count, chunks
    finally:
        for f in files:
            f.close()


def merge_to_partial(paths, out_path):
    """Merges partials into one bigger partial (same format)."""
    with open(out_path, "wb") as out:
        for token, posting_count, chunks in merge_stream(paths):
            write_partial_record_raw(out, token, posting_count, chunks)


def merge_to_index(paths, postings_path, idx_path, idx_idx_path, interval: int) -> int:
    """
    Merges partials into the final three index files.
    Every `interval`-th token (starting with the first) also gets a
    .postingsIdxIdx entry. Returns the number of unique tokens.
    """
    postings_offset = 0
    idx_offset = 0
    num_tokens = 0
    with open(postings_path, "wb") as postings_file, \
         open(idx_path, "wb") as idx_file, \
         open(idx_idx_path, "wb") as idx_idx_file:
        for token, posting_count, chunks in merge_stream(paths):
            byte_len = sum(len(c) for c in chunks)
            if postings_offset + byte_len > U32_LIMIT:
                raise OverflowError(".postings is over 4 GB; offsets no longer fit in a u32")
            for c in chunks:
                postings_file.write(c)

            if num_tokens % interval == 0:
                write_idx_idx_entry(idx_idx_file, token, idx_offset)
            idx_offset += write_idx_entry(idx_file, token, postings_offset, byte_len, posting_count)
            if idx_offset > U32_LIMIT:
                raise OverflowError(".postingsIdx is over 4 GB; offsets no longer fit in a u32")

            postings_offset += byte_len
            num_tokens += 1
    return num_tokens


def merge_partials(paths, postings_path, idx_path, idx_idx_path,
                   interval: int = 64, max_open: int = 100,
                   tmp_dir=".", tmp_prefix: str = "merge") -> int:
    """
    Merges the partials (in the order written) into the final index files.

    If there are more than max_open partials, consecutive groups of max_open
    are first merged into intermediate partials (keeping docid order), and
    this repeats until few enough remain to merge in one pass. Intermediate
    files are written to tmp_dir and deleted when no longer needed; the
    original partials are left alone.

    Returns the number of unique tokens.
    """
    if max_open < 2:
        raise ValueError("max_open must be at least 2")
    paths = [Path(p) for p in paths]
    temps = set()
    round_num = 0
    while len(paths) > max_open:
        next_paths = []
        for g in range(0, len(paths), max_open):
            group = paths[g:g + max_open]
            if len(group) == 1:
                next_paths.append(group[0])
                continue
            out = Path(tmp_dir) / f"{tmp_prefix}_merge_r{round_num}_{g // max_open}.pii"
            merge_to_partial(group, out)
            temps.add(out)
            next_paths.append(out)
            for p in group:  # intermediate inputs are no longer needed
                if p in temps:
                    p.unlink()
                    temps.discard(p)
        paths = next_paths
        round_num += 1

    try:
        return merge_to_index(paths, postings_path, idx_path, idx_idx_path, interval)
    finally:
        for p in temps:
            p.unlink(missing_ok=True)
