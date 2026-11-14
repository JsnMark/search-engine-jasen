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

from posting import Posting, write_partial_record
from docTable import DocTableWriter
from merge import merge_partials
from tokenizer import tokenize
from parser import extract


"""
---------PSEUDO CODE---------
// dont worry about not fitting a single file into mem

partialInvertedIndex = dict()
counter = 0

for each file:
    create a docid
    write (url offset, url length, token count) to .docs and the url to .urls
    data = read(file)
    tokens = tokenize(data)
    for each token:
        add/update posting of the file in that token's entry in the index
    if partialInvertedIndex.size > max size:
        write to a file
    counter++

mergePartialInvIndexes()
"""



class IndexConstructor:
    PARTIAL_FILE_SUFFIX   = "_pii_"
    PARTIAL_FILE_FEXT     = ".pii"
    POSTINGS_FEXT         = ".postings"
    POSTINGS_IDX_FEXT     = ".postingsIdx"
    POSTINGS_IDX_IDX_FEXT = ".postingsIdxIdx"
    DOCS_FEXT             = ".docs"
    URLS_FEXT             = ".urls"


    MAX_POSTINGS_COUNT    = 500_000
    IDX_IDX_INTERVAL      = 64     # every X-th .postingsIdx entry goes in .postingsIdxIdx
    MAX_OPEN_PARTIALS     = 100    # most partial files the merge opens at once
    KEEP_PARTIAL_FILES    = False  # keep the .pii files after merging (for debugging)

    def __init__(self):
        # map<string, list<posting>> 
        self.partialInvIndex = dict() # maps tokens to lists of postings
        self.partialIndexCount = 0
        self.out_path = ""
        self.out_filename = ""

        self.numPostings = 0

    def create(self, path: str, out_path: str, out_filename: str):
        """
        Searches recursively in the path for json files
        to construct an inverted index. 

        @param path: path leading to json files
        @param out_path: path to destination file
        @param out_filename: filename of the inverted index file (without file extension)
        """
        self.partialInvIndex = dict() # map<str, list<posting>>
        self.partialIndexCount = 0
        self.out_path = out_path
        self.out_filename = out_filename

        paths = self._get_all_paths(path, out_path, out_filename)
        if not paths or len(paths) != 5:
            return
        # path to data, path to output file, (.postings, .postingsIdx, .postingsIdxIdx) filepaths, .docs filepath, .urls filepath
        data_path, output_path, index_paths, docs_path, urls_path = paths
        self._remove_partialInvIndex_files(out_path)
        print(data_path, output_path, *index_paths, docs_path, urls_path)
    
        with docs_path.open(mode="wb") as docsFile, urls_path.open(mode="wb") as urlsFile:
            docTable = DocTableWriter(docsFile, urlsFile)
            abc = 0 # TODO REMOVE ME
            for file in self._yield_all_files(data_path):
                # format of data = {"url": [], "content": [], "encoding: [] }
                json_data = self._read_json(file)
                if not isinstance(json_data, dict) or "url" not in json_data or "content" not in json_data:
                    print("invalid json data")
                    continue
                url_string = json_data["url"]
                
                if not isinstance(url_string, str) or url_string == "":
                    print("invalid json data")
                    continue
                fields = extract(json_data["content"]) # title, important, body
                json_data = None # free up mem by removing a ref to json_data

                # TODO revist this part
                tokens = tokenize(fields["title"]) + tokenize(fields["important"]) + tokenize(fields["body"])

                # docid is only assigned once the doc is valid, so docids stay dense (0, 1, 2, ...)
                # and docid i is the i-th record in .docs
                did = docTable.add(url_string, len(tokens))
                position = 0
                for token in tokens:
                    # TODO fix this, only works for milestone 1 probably 
                    self.addPostingToIndex(did, token, position)
                    position += 1

                # Only flush between documents, never in the middle of one. This keeps
                # each document's postings in a single partial, so every docid in
                # partial N+1 is greater than every docid in partial N (the merge
                # relies on this). The index may go over MAX_POSTINGS_COUNT by up to
                # one document's worth of postings before it is flushed.
                if self.numPostings > self.MAX_POSTINGS_COUNT:
                    self.savePartialInvIndex()

                abc += 1
                # if abc >= 10:
                #     print("REMOVE ME")
                #     break

            if self.partialInvIndex:
                self.savePartialInvIndex()

        self.mergePartialInvIndexes(index_paths)

    def mergePartialInvIndexes(self, index_paths):
        """
        Merges every partial written so far into .postings, .postingsIdx and
        .postingsIdxIdx, then deletes the partials (unless KEEP_PARTIAL_FILES).
        """
        postings_path, idx_path, idx_idx_path = index_paths
        partial_paths = [self._partial_path(i) for i in range(self.partialIndexCount)]
        num_tokens = merge_partials(partial_paths, postings_path, idx_path, idx_idx_path,
                                    interval=self.IDX_IDX_INTERVAL,
                                    max_open=self.MAX_OPEN_PARTIALS,
                                    tmp_dir=self.out_path, tmp_prefix=self.out_filename)
        print("merged", len(partial_paths), "partials into", num_tokens, "unique tokens")
        if not self.KEEP_PARTIAL_FILES:
            for path in partial_paths:
                path.unlink(missing_ok=True)


    def addPostingToIndex(self, did: int, token: str, position: int):
        """
        adds a posting to the inverted index
        """
        postings = self.partialInvIndex.setdefault(token, [])
        if postings and postings[-1].did == did:
            postings[-1].positions.append(position)
        else:
            posting = Posting(did)
            posting.positions.append(position)
            postings.append(posting)

        self.numPostings+=1


    def savePartialInvIndex(self):
        dest = self._partial_path(self.partialIndexCount)
        self.partialIndexCount+=1

        # Binary partial: records sorted by token, each one
        # [token_len u32][token][posting_count u32][byte_len u32][postings...]
        # (see posting.py). Sorting lets the merge stream all partials in token
        # order. Tokens are ASCII, so str order matches byte order. Postings in
        # each list are already in increasing docid order because docs are
        # processed in docid order.
        with open(dest, "wb") as file:
            for token in sorted(self.partialInvIndex):
                write_partial_record(file, token, self.partialInvIndex[token])
        self.numPostings = 0
        self.partialInvIndex = dict()
                



                 

        



    # ------------------ HELPERS ------------------------

    def _partial_path(self, i: int) -> Path:
        """Path of the i-th partial index file (partials are merged in this order)."""
        filename = self.out_filename + self.PARTIAL_FILE_SUFFIX + str(i) + self.PARTIAL_FILE_FEXT
        return Path(self.out_path) / filename

    def _yield_all_files(self, path: Path):
        for item in path.rglob("*.json"):
            if item.is_file():
                yield item

    def _read_json(self, file):
        # Load it into json
        with file.open(mode="r", encoding="utf-8") as json_file:
            # format of data = {"url": [], "content": [], "encoding: [] }
            json_data = json.load(json_file)
        return json_data

    def _err_handle_path(self, data_path: Path, output_path: Path):
        if not data_path.exists():
            err_msg = "data path: " + str(data_path) + " does not exist"
            print(err_msg)
            return False
        if not output_path.exists():
            err_msg = "output path: " + str(output_path) + " does not exist"
            print(err_msg)
            return False
        if not data_path.is_dir():
            err_msg = "data path: " + str(data_path) + " is not directory"
            print(err_msg)
            return False
        if not output_path.is_dir():
            err_msg = "data path: " + str(output_path) + " is not directory"
            print(err_msg)
            return False
        return True

    def _get_all_paths(self, path, out_path, out_filename):
        """Returns data_path, output_path, (postings, postingsIdx, postingsIdxIdx paths), docs_path, urls_path"""
        data_path = Path(path)
        output_path = Path(out_path)
        if not self._err_handle_path(data_path, output_path): return ()

        index_paths = tuple(output_path / (out_filename + fext) for fext in
                            (self.POSTINGS_FEXT, self.POSTINGS_IDX_FEXT, self.POSTINGS_IDX_IDX_FEXT))
        for index_path in index_paths:
            if index_path.exists():
                print("err output file exists:", index_path)
                return ()

        docs_path = output_path / (out_filename + self.DOCS_FEXT)
        urls_path = output_path / (out_filename + self.URLS_FEXT)
        docs_path.unlink(missing_ok=True) # remove if exists
        urls_path.unlink(missing_ok=True)
        return data_path, output_path, index_paths, docs_path, urls_path

    def _remove_partialInvIndex_files(self, out: str):
        outpath = Path(out)
        for file_path in outpath.glob(f"*{self.PARTIAL_FILE_FEXT}"):
            try:
                file_path.unlink()
            except Exception as e:
                pass