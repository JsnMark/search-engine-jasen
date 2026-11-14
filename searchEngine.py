"""
searchEngine.py

AND queries over the inverted index: a document matches only if it contains
every query token. Matches are ranked by score() (ties broken by docid) and
the top TOP_K urls are returned.

Usage:
    python3 searchEngine.py                 # interactive prompt
    python3 searchEngine.py --test          # run TEST_QUERIES
    python3 searchEngine.py machine learning
"""

import heapq
import sys
import time

from indexReader import IndexReader
from tokenizer import tokenize

TOP_K = 5
TEST_QUERIES = ["cristina lopes", "machine learning", "ACM", "master of software engineering"]


class SearchEngine:
    def __init__(self, out_path: str = "out", out_filename: str = "myInvIndex"):
        self.reader = IndexReader(out_path, out_filename)

    def search(self, query: str):
        """Returns up to TOP_K (url, score) pairs for docs containing every query token."""
        tokens = list(dict.fromkeys(tokenize(query)))  # normalize, drop duplicates, keep order
        if not tokens:
            return []

        matches = self.intersect([self.reader.get_postings(t) for t in tokens])
        top = heapq.nsmallest(TOP_K, matches.items(),
                              key=lambda item: (-self.score(item[1]), item[0]))
        return [(self.reader.get_doc(did)[0], self.score(postings)) for did, postings in top]

    def intersect(self, posting_lists):
        """
        AND of the posting lists. Returns {docid: [that doc's posting for each token]}.
        Starts from the rarest token so the candidate set is as small as possible.
        """
        posting_lists = sorted(posting_lists, key=len)
        if not posting_lists or not posting_lists[0]:
            return {}
        matches = {p.did: [p] for p in posting_lists[0]}
        for postings in posting_lists[1:]:
            matches = {p.did: matches[p.did] + [p] for p in postings if p.did in matches}
            if not matches:
                break
        return matches

    def score(self, postings) -> float:
        """
        Score of one matching doc, given its posting for each query token.
        For now every match scores the same (no tf, no positions), so results
        come out in docid order. Change this to rank by tf, tf-idf, positions,
        title_tf / important_tf, etc.
        """
        return 0.0

    def close(self):
        self.reader.close()


def run(engine, query):
    start = time.perf_counter()
    results = engine.search(query)
    ms = (time.perf_counter() - start) * 1000
    print(f"\n{query!r}: {len(results)} results in {ms:.1f} ms")
    for rank, (url, score) in enumerate(results, 1):
        print(f"  {rank}. {url}")


if __name__ == "__main__":
    engine = SearchEngine()
    try:
        if sys.argv[1:] == ["--test"]:
            for q in TEST_QUERIES:
                run(engine, q)
        elif sys.argv[1:]:
            run(engine, " ".join(sys.argv[1:]))
        else:
            while (q := input("\nquery> ").strip()):
                run(engine, q)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        engine.close()
