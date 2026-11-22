'''
invertedIndex.py

Takes HTML files to build an inverted index.
An inverted index is a map with token as the key
and list of corresponding postings. A posting is 
the representation of the token's occurence in a 
document. 

not allowed to use a database
'''

from pathlib import Path
import json

from posting import Posting
from tokenizer import tokenize
from parser import extract


"""
---------PARTIAL INV INDEX PSEUDO CODE---------
// dont worry about not fitting a single file into mem

partialInvertedIndex<Token, PostingList> {} // pii

for each file:
    create a docid
    write url to .urls
    write (docid, offset) to .docs
    data = read(file)
    tokens = tokenize(data)
    for each token:
        if token in pii:
            update posting list with new position
        else:   
            add kv pair to pii

    if partialInvertedIndex.size > max size:
        write pii to a file
"""

OUT_PATH = "out"
PARTIAL_FILE_FEXT     = ".pii" #pii files are named FileName_piiNum.pii
POSTING_LIST_FEXT     = ".posts"
INDEX_FEXT            = ".idx" 
LEXICON_FEXT          = ".lex"
URLS_FEXT             = ".urls"
DOCS_FEXT             = ".docs"
MAX_POSTINGS_COUNT    = 35_000

class Indexer:
    # ------ Public ------
    def __init__(self):
        # map<string, list<posting>> 
        self.pii = dict() # maps tokens to lists of postings

    def create_index(self, in_path: str, out_name: str):
        """
        Searches recursively in the path for json files
        to construct an inverted index. 

        @param in_path: path leading to json files
        @param out_name: prefix name to be used in naming files
            ie - name="robbert" => robbert_1.pii, robbert.lex, ect
        """

        # Create out folder if dne
        Path(OUT_PATH).mkdir(parents=True, exist_ok=True)

        self.remove_index(out_name)
        self.create_partial_index()
        self.merge_partial_index()

    def remove_index(self, index_name: str):
        """
        Removes the index associated with index_name. 
        @param index_name: name used in naming files 
            (same as out_name in create_index)
        """
        out_path = Path(OUT_PATH)
        if not out_path.exists():
           return

        for file in self.yield_all_files(out_path):
            stem = file.stem
            suffix = file.suffix
            if not suffix in [
                PARTIAL_FILE_FEXT, POSTING_LIST_FEXT, INDEX_FEXT,
                LEXICON_FEXT, URLS_FEXT, DOCS_FEXT
            ]:
                continue
            if stem == index_name:
                file.unlink()
                continue
            # if pii file and associated w index_name
            if suffix == PARTIAL_FILE_FEXT:
                parts = stem.rsplit("_", 1)
                if (len(parts) == 2 
                    and parts[0] == index_name 
                    and parts[1].isdigit()
                ):
                    file.unlink()


    # ------ Private ------

    def create_partial_index(self):
        pass

    def merge_partial_index(self):
        pass

    def yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item
