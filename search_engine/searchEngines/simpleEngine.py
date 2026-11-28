"""
simpleEngine.py

** does not consider order
** only simple tfidf
** unique tokens only
** ands all query terms
"""

"""
SimpleSearch PseudoCode


terms = unique(tokenize(query))
metas = [idx_lookup(t) for t in terms]
if any meta is None: return []
sort terms by meta.posting_count
candidates = intersect(posting lists, shortest first)   # docid -> postings
N = len(docTable)
for docid, postings in candidates:
    score = sum(1 + log p.tf) * log(N / meta.df)
top = heapq.nlargest(k, ...)
return [docTable.url(d) for d, _ in top]
"""

import logging
from pathlib import Path
import time
import pprint

from search_engine.searchEngines.base import SearchEngine
from search_engine.tokenizer import tokenize
from search_engine.storage.inverted import InvIndexReader


class SimpleEngine(SearchEngine):
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        super().__init__(name)
        self.invIndexReader.load_lex()
        
        


    def search(self, query: str, top_k=5):
        terms = list(set(tokenize(query)))
        self.logger.debug(f"Tokens: {terms}")
        idx_metas = [self.invIndexReader.idx_lookup(m) for m in terms]
        pprint.pprint(idx_metas)



        return ""