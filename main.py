import logging
import sys
from search_engine.indexer import Indexer
from search_engine.parsers.json_parser import JSONDocumentParser
import argparse


DEFAULT_IN_PATH = "data/ANALYST"
DEFAULT_OUT_NAME = "myOut"

if __name__ == "__main__":
    if sys.version_info < (3, 14):
        raise RuntimeError(
            f"Python 3.14+ is required, but you are running {sys.version_info.major}.{sys.version_info.minor}."
        )
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Index files and run queries")
    parser.add_argument(
        "-i", "--in-path",
        default=DEFAULT_IN_PATH,
        help=f"directory of documents to index (default: {DEFAULT_IN_PATH})",
    )
    parser.add_argument(
        "-o", "--out-name",
        default=DEFAULT_OUT_NAME,
        help=f"name for the index output (default: {DEFAULT_OUT_NAME})",
    )
    parser.add_argument(
        "-s", "--skip-indexing",
        action="store_true",
        help="skip building the index and go straight to search",
    )
    args = parser.parse_args()

    if not args.skip_indexing:
        ixr = Indexer(args.in_path, args.out_name, JSONDocumentParser())
        ixr.create_index()

    # TODO: search
