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

from pathlib import Path
import shutil
import logging
from collections import Counter
import time
import heapq
import itertools

from search_engine.posting import Posting
from search_engine.tokenizer import tokenize
from search_engine.parsers.base import DocumentParser, ParsedDocument
from search_engine.storage.docTable import DocTableWriter
from search_engine.tf_idf import term_freq, doc_freq, norm
from search_engine.storage.partial import PiiWriter, PiiReader
from search_engine.storage.inverted import InvIndexWriter



OUT_ROOT_PATH         = "out"
PARTIAL_FILE_FEXT     = ".pii" #pii files are named FileName_piiNum.pii
URLS_FEXT             = ".urls"
DOCS_FEXT             = ".docs"
MAX_POSTING_COUNT     = 350_000


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
            c = 1 # debug limiter count
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
        with PiiWriter.open(pii_filepath) as piiWriter:
            for token in sorted(self.pii):
                piiWriter.write_postings(token, self.pii[token])

        self.pii = {}
        self.posting_count = 0
                

        
    def merge_partial_index(self, K=128, interval=128):
        """
        Performs a k-way merge of all partial indexes. Don't use binary as its too slow.
        Don't merge all files at once as OS may have a limit on how many files can be opened.
        For smaller collections, we may be able to merge in 1 pass, but have code
        ensure it can work for larger collections

        @param K how many files to merge in one pass
        @param interval .lex entry for every interval'th token
        """
        if K < 2:
            self.logger.error("K must be >= 2")
            raise Exception()
        start_time = time.time()
        
        piiFileName = ""
        piiWriter = None
        new_pii_iteration = 1
        new_pii_index = 0
        invIndexWriter = None

        # filename_piiiteration_piiindex.pii, sort on int(pii_index)
        files = sorted([f for f in self.out_path.iterdir() 
                            if (f.is_file() and f.suffix == PARTIAL_FILE_FEXT)],
                        key=lambda n: int(n.stem.rsplit("_", 1)[1]))
        if len(files) == 0:
            self.logger.error("No partial files found")
            raise Exception()
        
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
                reader_batch = [PiiReader(f) for f in batch] # list of PiiReaders for the batch

                if final_pass:
                    invIndexWriter = InvIndexWriter.open(self.out_path, self.out_name, interval)       
                    self.logger.debug(f"Opened {invIndexWriter.posts_file_name or "<stream>"}")
                    self.logger.debug(f"Opened {invIndexWriter.idx_file_name or "<stream>"}")
                    self.logger.debug(f"Opened {invIndexWriter.lex_file_name or "<stream>"}")
                else:
                    piiFileName = self.out_path / f"{self.out_name}_{new_pii_iteration}_{new_pii_index}{PARTIAL_FILE_FEXT}"
                    piiWriter = PiiWriter.open(piiFileName)
                    new_pii_index += 1
                    self.logger.debug(f"Opened {piiWriter.file_name}")

                # Acts as a min heap of all the readers's next token
                # all pii files already sorted by token, merge holds heap of next token per reader
                merged_gen = heapq.merge(*reader_batch, key=lambda e: e.token) # lazy evaluate heap, automatically repopulate heap
                for token, group in itertools.groupby(merged_gen, key=lambda e: e.token): # 
                    group = list(group) # Force the group to populate here
                    group_posting_count = sum(e.count for e in group)
                    merged_pl_bytes = b"".join(e.postings_data for e in group)
                    if final_pass:
                        if invIndexWriter is None:
                            self.logger.error("invIndex writer is none")
                            raise ValueError("invIndex writer is none")
                        # write to .posts, .idx, and to in mem lex
                        invIndexWriter.write(token, group_posting_count, merged_pl_bytes)

                    else:
                        if piiWriter is None:
                            self.logger.error("pii writer is none")
                            raise ValueError("pii writer is none")
                        # write to pii
                        piiWriter.write_raw(token, group_posting_count, merged_pl_bytes)

                if final_pass:
                    if not invIndexWriter:
                        self.logger.error("invIndex writer is none")
                        raise ValueError("invIndex writer is none")
                    invIndexWriter.close()
                else:
                    if not piiWriter:
                        self.logger.error("pii writer dne")
                        raise ValueError("pii writer dne")
                    piiWriter.close()
                    new_files.append(Path(piiFileName))
                for batch_file in batch:
                    batch_file.close()
                    Path(batch_file.name).unlink(missing_ok=True)
                    
            files = new_files
            if final_pass:
                break
            new_pii_iteration += 1
            new_pii_index = 0
        end_time = time.time() - start_time
        self.logger.info(f"Merged partial indexes in {end_time:.4f} seconds")


    def yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item
