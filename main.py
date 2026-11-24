import logging
from search_engine.indexer import Indexer
from search_engine.parsers.json_parser import JSONDocumentParser




if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
    )

    in_path = "data/ANALYST"
    out_name = "myOut"
    
    ixr = Indexer(in_path, out_name, JSONDocumentParser())
    ixr.create_index()
    # ic.create("data/DEV", "out", "myInvIndex")