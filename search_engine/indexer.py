'''
invertedIndex.py

Takes HTML files to build an inverted index.
An inverted index is a map with token as the key
and list of corresponding postings. A posting is 
the representation of the token's occurence in a 
document. 

not allowed to use a database

Assume all files are in the same format of json for now
However json[content] seems to have different formats
'''


"""
---------PARTIAL INV INDEX PSEUDO CODE---------
// dont worry about not fitting a single file into mem

partialInvertedIndex<Token, PostingList> {} // pii
postings_count = 0

for each file:
    parsed = parse(file)
    docid = next_docid++

    body_tokens = tokenize(parsed.body)
    write url to .urls
    write (docid, url_offset, url_len, token_count) to .docs

    for each body token, position:
        if token not in pii or docid not in pii[token]
            append new posting to pii[token]
            posting_count++
        append position to position list

    for each important token:
        update tf value for this docid
    for each tilte token:
        update tf value for this docid
    

    if partialInvertedIndex.size > max size:
        write pii to a file sorted by token
        pii = {}
        postings_count = 0
if pii:
    write pii to a file sorted by token
"""

from pathlib import Path
import shutil
import logging
from collections import Counter
import struct
import time

import pprint

from search_engine.posting import Posting
from search_engine.tokenizer import tokenize
from search_engine.parsers.base import DocumentParser, ParsedDocument
from search_engine.docTable import DocTableWriter
from search_engine.tf_idf import term_freq, doc_freq, norm



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
        self.next_pii = 0 # next .pii id
        self.in_path = Path(in_path)
        self.out_name = out_name
        self.out_path = Path(OUT_ROOT_PATH) / out_name
        self.parser = parser
        self.next_docid = 0
        self.posting_count = 0
        self.doc_table_writer = None

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
        Creates the partial index files (.pii)
        """

        urls_path = self.out_path / (self.out_name + URLS_FEXT)
        docs_path = self.out_path / (self.out_name + DOCS_FEXT)
        total_doc_count = 0
        total_postings_count = 0
        self.logger.debug(f"Creating partial indexes")
        start_time = time.time()

        with urls_path.open(mode="wb") as urls_file, docs_path.open(mode="wb") as docs_file:
            self.doc_table_writer = DocTableWriter(docs_file, urls_file) # write to .docs and .urls
            c = 1 # TODO REMOVE THIS
            for file in self.yield_all_files(self.in_path):
                parsedDoc = self.parser.parse(file)
                docid = self.next_docid
                self.next_docid += 1
                num_tokens = self.add_tokens_to_partial_index(tokenize(parsedDoc.body), docid)
                self.doc_table_writer.write(parsedDoc.url, num_tokens)
                self.update_title_count(tokenize(parsedDoc.title), docid)
                self.update_important_count(tokenize(parsedDoc.important), docid)

                # rough approximation for memory
                if self.posting_count >= MAX_POSTINGS_COUNT:
                    total_postings_count += self.posting_count
                    self.save_current_pii()
                total_doc_count += 1

                # # Debug limit by postings
                # c -= 1
                # if c <= 0:
                #     break

            # Save pii after iterating through all files
            if self.pii:
                total_postings_count += self.posting_count
                self.save_current_pii()
                
        end_time = time.time() - start_time
        self.logger.debug(f"Finished creating partial indexes for {total_doc_count} documents with {total_postings_count} postings in {end_time} seconds")
            

    def add_tokens_to_partial_index(self, tokens, did) -> int:
        """
        Adds tokens to pii and returns num tokens. Returns num tokens
        because otherwise we would need to keep tokens in mem or free the mem
        """
        for pos, token in enumerate(tokens):
            if token not in self.pii:
                self.pii[token] = []
            # If posting did not in the posting list, add a new posting for the did
            if not self.pii[token] or self.pii[token][-1].did != did:
                self.pii[token].append(Posting(did))
                self.posting_count += 1
            # add the position in the pos list
            self.pii[token][-1].positions.append(pos)
        return len(tokens)

    def update_title_count(self, title_tokens, docid):
        for token, count in Counter(title_tokens).items():
            posting_list = self.pii.get(token)
            if posting_list and posting_list[-1].did == docid:
                posting_list[-1].title_count = count

    def update_important_count(self, important_tokens, docid):
        for token, count in Counter(important_tokens).items():
            posting_list = self.pii.get(token)
            if posting_list and posting_list[-1].did == docid:
                posting_list[-1].important_count = count

    def save_current_pii(self):
        """
        Saves the current partial index into a .pii

        KV Entry Format
        [uint32_t  ] [str   ] [uint32_t      ] [uint32_t               ] [array<Postings> ]
        [token_len ] [token ] [posting_count ] [posting_list_byte_size ] [postings        ]
        """
        pii_id = self.next_pii
        self.next_pii += 1
        pii_filepath = Path(self.out_path) / (self.out_name + "_" + str(pii_id) + PARTIAL_FILE_FEXT)

        with pii_filepath.open(mode="wb") as pii_file:
            for token in sorted(self.pii):
                token_bytes = token.encode("utf-8")
                token_data = struct.pack("<I",len(token_bytes)) + token_bytes
                # Get postings bytes to make postings metadata
                posting_list = self.pii[token]
                postings_data = b"".join(p.serialize() for p in posting_list)
                postings_metadata = struct.pack("<II", len(posting_list), len(postings_data))
                pii_file.write(
                    token_data + postings_metadata + postings_data
                )

        self.pii = {}
        self.posting_count = 0
                

        
    def merge_partial_index(self):
        pass

    def yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item
