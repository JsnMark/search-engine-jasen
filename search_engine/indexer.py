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
import shutil
import logging

from search_engine.posting import Posting
from search_engine.tokenizer import tokenize
from search_engine.parsers.base import DocumentParser, ParsedDocument




OUT_ROOT_PATH = "out"
PARTIAL_FILE_FEXT     = ".pii" #pii files are named FileName_piiNum.pii
POSTING_LIST_FEXT     = ".posts"
INDEX_FEXT            = ".idx" 
LEXICON_FEXT          = ".lex"
URLS_FEXT             = ".urls"
DOCS_FEXT             = ".docs"
MAX_POSTINGS_COUNT    = 35_000

class Indexer:
    # ------ Public ------
    def __init__(self, in_path: str, out_name: str, parser: DocumentParser):
        # map<string, list<posting>> 
        self.pii = dict() # maps tokens to lists of postings in the partial inverted index
        self.in_path = Path(in_path)
        self.out_name = out_name
        self.out_path = Path(OUT_ROOT_PATH) / out_name
        self.parser = parser

        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.info("Initialized Indexer")

    def create_index(self):
        """
        Searches recursively in the path for json files
        to construct an inverted index. 
        """

        # Remove the out folder if it exists and make a new one
        self.remove_index()
        self.out_path.mkdir(parents=True, exist_ok=True)

        self.create_partial_index()
        self.merge_partial_index()

    def remove_index(self):
        """
        Removes the index associated with index_name. 
        @param index_name: name used in naming files 
            (same as out_name in create_index)
        """
        if self.out_path.exists() and self.out_path.is_dir():
            shutil.rmtree(self.out_path)
            self.logger.info(f'Removed out path "{str(self.out_path)}"')
        else: 
            self.logger.info(f'Did not remove out path "{str(self.out_path)}", none found')


    # ------ Private ------

    def create_partial_index(self):
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
        self.logger.debug("creating partial indexes")
        for file in self.yield_all_files(self.in_path):

            break
        pass

    def merge_partial_index(self):
        pass

    def yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item
