# File structure

### .postings
This file holds the raw bytes of the posting list. It will look like a consecutive sequence of postings. To figure out the posting list a posting belongs to, we need the .postingsIdx file

### .postingsIdx
This file holds data in the format {token: posting list metadata}. The data is sorted by token to provide an order for .postingsIdxIdx (needed for binary search and linear scan). Posting list data would be stuff like the start byte offset, the total bytes the list takes up, and the amount of postings in the list. This helps us map which posting belongs to which list

### .postingsIdxIdx
This file acts as an index for the postingsIdx file.We don't acutally need this, but this file will help speed up searching in postingsIdx since we will store 2 lists of [tokens ] and [.postingsIdx offsets]. We will store every X token to reduce space used so that we can load this file into memory. We will search through this with a binary search to quickly find the general location of our query token. We will seek to the offset in .postingsIdx and do a quick linear scan of at most X tokens to find the posting list data (thus this last step is constant time).

### .urls
This file holds the consecutive raw url bytes back to back

### .docs
This file holds the mapping of a docid to doc meta data like the url offset in .urls, the url length, and the document token count. These are all fixed length values, so we can easily get document i by seeking i * record length.

# Process of finding a specific posting list
First we binary search .postingsIdxIdx in memory to find the general offset in .postingsIdx. Then we do a constant time scan in .postingsIdx to find the mapping of the token to the posting list meta data. If no term is found here then we know it doesnt exist in our index. Afterwads, we have the offset to seek to the correct posting list in .postings and read the postings from there.

# Process of making the inverted index
We can write to .docs and .urls constantly, so we can keep these files open and write to them for every file we read. However, we will need to build partial index files since we don't know if a token will appear in a later document, so we can't store it all in memory. We need to temporarily save a partial index to a file and then merge at the end. To start, our partial files will be in format 

[token meta data][token][posting list meta data][posting list] (each posting in posting list is in form [posting meta data][actual posting data])

After we build these partial indexes, we will perform a merge to produce .postings, .postingsIdx, .postingsIdxIdx. A partial file i will store docids less than a partial file i+1, which allows us to perform a merge simply without worrying about resorting the docids. The merge will be a k-way merge (similar to how records are merged in relational databases for queries like ORDER BY). In the end, postings inside a posting list will be sorted by docid which will help our queries later.