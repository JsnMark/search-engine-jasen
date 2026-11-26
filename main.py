import logging
import sys
from search_engine.indexer import Indexer
from search_engine.parsers.json_parser import JSONDocumentParser



if __name__ == "__main__":
    if sys.version_info < (3, 14):
        raise RuntimeError(
            f"Python 3.14+ is required, but you are running {sys.version_info.major}.{sys.version_info.minor}."
        )
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
    )

    in_path = "data/ANALYST"
    out_name = "myOut"
    
    ixr = Indexer(in_path, out_name, JSONDocumentParser())
    ixr.create_index()