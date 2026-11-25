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
posting_count = 0

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
        posting_count = 0
if pii:
    write pii to a file sorted by token
"""

from pathlib import Path
import shutil
import logging
from collections import Counter
import struct
import time
import heapq

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
MAX_POSTING_COUNT    = 350_000

U32 = struct.Struct("<I")

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
        total_posting_count = 0
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
                if self.posting_count >= MAX_POSTING_COUNT:
                    total_posting_count += self.posting_count
                    self.save_current_pii()
                total_doc_count += 1

                # # Debug limit by postings
                # c -= 1
                # if c <= 0:
                #     break

            # Save pii after iterating through all files
            if self.pii:
                total_posting_count += self.posting_count
                self.save_current_pii()
                
        end_time = time.time() - start_time
        self.logger.info(f"Finished creating {self.next_pii} partial indexes for {total_doc_count} documents with {total_posting_count} postings in {end_time:.6f} seconds")
            

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
        filename_piiiteration_piiindex.pii
        piiiteration will always be 0 here since its the first one


        KV Entry Format
        [uint32_t  ] [str   ] [uint32_t      ] [uint32_t               ] [array<Postings> ]
        [token_len ] [token ] [posting_count ] [posting_list_byte_size ] [postings        ]
        """
        pii_id = self.next_pii
        self.next_pii += 1
        pii_filepath = Path(self.out_path) / (self.out_name + "_0_" + str(pii_id) + PARTIAL_FILE_FEXT)

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
                

        
    def merge_partial_index(self, K=128):
        """
        Performs a k-way merge of all partial indexes. Don't use binary as its too slow.
        Don't merge all files at once as OS may have a limit on how many files can be opened.
        For smaller collections, we may be able to merge in 1 pass, but have code
        ensure it can work for larger collections
        """
        """
        Pseudocode for intermediate passes

        files = sorted partial files (by pii id)
        lex = [] # in memory
        while 1:
            final_pass = len(files) <= K
            new_files = []
            while files:
                batch = pop first K from files
                if len(batch) == 1 and not final_pass:
                    new_files.append(batch[0])
                    continue
                if final_pass open .posts and .idx
                else open new .pii

                heap = [(header.token, i, header) for i, f in batch if f has an entry]
                while heap:
                    tok = heap.min.token
                    group = []
                    while heap and heap.min.token == tok:
                        group.append(pop(heap))        # ascending file idx
                    if final_pass:
                        write merged postings to .posts
                        write to .idx
                        lex.append(lex item)
                    else:
                        write merged pii item to .pii

                    for item in group:            
                        if batch[item index] has next header: 
                            push new item to heap
                
                if final_pass:
                    write lex count and lex to .lex
                else:
                    new_files.append(new .pii)
                close files 
                delete batch files
            files = new_files
            if final_pass: break
        """
        
        lex = []
        posts_file = None
        idx_file = None
        new_pii_file = None
        new_pii_iteration = 1
        new_pii_index = 0
        # filename_piiiteration_piiindex.pii, sort on int(pii_index)
        files = sorted([f for f in self.out_path.iterdir() 
                            if (f.is_file() and f.suffix == PARTIAL_FILE_FEXT)],
                        key=lambda n: int(n.stem.rsplit("_", 1)[1]))
        
        while True:
            final_pass = len(files) <= K
            new_files = []
            while files:
                # If only 1 file in the batch in an intermediate pass, 
                #   dont waste time copying it
                batch = files[:K] # temporarily a list of paths
                files = files[K:]
                if len(batch) == 1 and not final_pass:
                    new_name_str =  f"{self.out_name}_{new_pii_iteration}_{new_pii_index}{PARTIAL_FILE_FEXT}"
                    new_files.append(batch[0].rename(batch[0].with_name(new_name_str)))
                    new_pii_index += 1
                    continue
                batch = [f.open(mode="rb") for f in batch] # list of open files

                if final_pass:
                    posts_file = (self.out_path / (self.out_name + POSTING_LIST_FEXT)).open(mode="wb")
                    idx_file = (self.out_path / (self.out_name + INDEX_FEXT)).open(mode="wb")
                    self.logger.debug(f"Opened {posts_file.name}")
                    self.logger.debug(f"Opened {idx_file.name}")
                else:
                    new_pii_file = (self.out_path / f"{self.out_name}_{new_pii_iteration}_{new_pii_index}{PARTIAL_FILE_FEXT}").open(mode="wb")
                    new_pii_index += 1
                    self.logger.debug(f"Opened {new_pii_file.name}")

                # heap<tuple<token, batch_idx, pl_count, pl_byte_len>>
                heap = self.build_token_heap(batch)
                while heap:
                    token = heap[0][0]
                    group = []
                    while heap and heap[0][0] == token:
                        group.append(heapq.heappop(heap))

                    merged_pl_bytes = self.merge_posting_lists(group, batch)
                    if final_pass:
                        # write to posts
                        # write to idx
                        # append to lex
                        pass
                    else:
                        # write to pii
                        pass
                    
                    for _, idx, pl_count, pl_byte_len in group:
                        pass
                    
            files = new_files
            if final_pass:
                break
            new_pii_iteration += 1
            new_pii_index = 0
    def merge_posting_lists(self, group, batch):
        """
        Returns the byte object of the merged
        posting lists from the files

        @param group list<tuple<token, batch_idx, pl_count, pl_byte_len>>
        @param batch list<files>
        """
        byte_result = bytearray()
        for _, index, _, pl_byte_len in group:
            file = batch[index]
            byte_result += file.read(pl_byte_len) # guaranteed to not fail since we made the file
        return byte_result

    def read_token_header(self, file):
        """
        Reads the token header in a partial index file.
        Assumes first byte at cursor is the token byte length
        returns None if token byte length is 0 or EOF
        else returns (token, posting_count, byte_len)
        """
        b = file.read(U32.size)
        if len(b) < U32.size:
            return None
        token_byte_len, = U32.unpack(b)
        if token_byte_len == 0:
            return None
        token = file.read(token_byte_len).decode("utf-8")
        pl_posting_count, pl_byte_len = struct.unpack("<II", file.read(8))
        # file now points at posting bytes, need to read pl_byte_len later
        return token, pl_posting_count, pl_byte_len 

    def build_token_heap(self, batch):
        heap = []
        for idx, file in enumerate(batch):
            rth_tuple = self.read_token_header(file)
            if rth_tuple is None:
                continue
            token, pl_count, pl_byte_len = rth_tuple
            heap.append((token, idx, pl_count, pl_byte_len))
        heapq.heapify(heap) # ordered by (token,idx). No cases where other tuple elements matter
        return heap

    def yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item
