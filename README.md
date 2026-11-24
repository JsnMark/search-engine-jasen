# File structure

All integers are little-endian with no padding and no compression. Strings are UTF-8 with no terminator, and their length comes from the prefix field.

## .posts
This file holds the raw bytes of the posting list. It will look like a consecutive sequence of postings. To figure out the posting list a posting belongs to, we need the .idx file.

#### Posting Format
`pos` counts token offsets within body text.

```
[uint32_t ] [uint32_t   ] [uint32_t       ] [uint32_t ] [uint32_t ]
[docid    ] [title_count] [important_count] [n_pos    ] [pos      ] * n_pos
```

## .idx
This file holds data in the format {token: posting list metadata}. The data is sorted by token, which enables the .lex binary search and .idx linear scan. Posting lists in .posts are stored in this same order. Posting list data would be stuff like the start byte offset, the total bytes the list takes up, and the amount of postings in the list. This helps us map which posting belongs to which list.

#### Token KV Pair format

```
[uint32_t ] [str  ] [uint64_t    ] [uint32_t               ] [uint32_t     ]
[token_len] [token] [posts_offset] [posting_list_byte_size ] [posting_count]
```

## .lex
This file acts as an index for the idx file. This file will help speed up searching in idx since we will store a list of [(tokens, .idx offsets)]. We will store every X token, always including the first token, to reduce space used so that we can load this file into memory. We will search through this with a binary search to quickly find the general location of our query token. We will seek to the offset in the idx file and do a quick linear scan of at most X tokens to find the posting list data (thus this last step is constant time).

#### Lexicon List format

```
[uint32_t   ]
[entry_count]

then entry_count times:
[uint32_t ] [str  ] [uint64_t  ]
[token_len] [token] [idx_offset]
```

## .urls
This file holds the consecutive raw url bytes back to back.

#### Urls entry format

```
[str]
[url]
```

## .docs
This file holds the mapping of a docid to doc meta data like the url offset in .urls, the url length, and the document token count. These are all fixed length values, so we can easily get document i by seeking i * record length (16 bytes).

#### Docs entry format

```
[uint64_t  ] [uint32_t] [uint32_t   ]
[url_offset] [url_len ] [token_count]
```

## .pii
This is the partial index files that will need to be merged. They will be kv pairs of tokens to postings. Entries will be guaranteed to be sorted by token.

#### KV Entry Format

```
[uint32_t  ] [str   ] [uint32_t      ] [uint32_t               ] [array<Postings> ]
[token_len ] [token ] [posting_count ] [posting_list_byte_size ] [postings        ]
```

#### Posting Format (same as .posts)

```
[uint32_t ] [uint32_t   ] [uint32_t       ] [uint32_t ] [uint32_t ]
[docid    ] [title_count] [important_count] [n_pos    ] [pos      ] * n_pos
```

# Process of finding a specific posting list
First we binary search .lex in memory to find the last entry whose token is `<=` the query, which gives us the general offset in .idx. If the query sorts before the first token in .lex, it isn't in the index. Then we do a constant time scan in .idx to find the mapping of the token to the posting list meta data. If no term is found here then we know it doesn't exist in our index. Afterwards, we have the offset to seek to the correct posting list in .posts and read the postings from there.

# Process of making the inverted index
We can write to .docs and .urls constantly, so we can keep these files open and write to them for every file we read. However, we will need to build partial index files since we don't know if a token will appear in a later document, so we can't store it all in memory. We need to temporarily save a partial index to a file and then merge at the end. These will be flushed only in between documents and never in the middle. After we build these partial indexes, we will perform a merge to produce .posts, .idx, .lex. A partial file i will store docids less than a partial file i+1. Docids are assigned in increasing order, so the merge doesn't need to re-sort them. They are also contiguous and given only to valid documents, so .docs can seek by `docid * 16`. The merge will be a k-way merge (similar to how records are merged in relational databases for queries like ORDER BY). In the end, postings inside a posting list will be sorted by docid which will help our queries later.
