import unittest
from posting import Posting
from pathlib import Path


TMP_FILENAME = "tests/tmp/out.tmp"

class TestPosting(unittest.TestCase):
    def test_simplePostingSerialization(self):

        file_path = Path(TMP_FILENAME)
        file_path.unlink(missing_ok=True)

        p = Posting(101, [1], 10, 5)
        n = p.nbytes
        with open(TMP_FILENAME, "wb") as f:
            f.write(p.serialize())

        with open(TMP_FILENAME, "rb") as f:
            data = f.read(n)
            read_posting, _ = Posting.deserialize(data, 0)

        file_path.unlink(missing_ok=True)
        self.assertEqual(p, read_posting)

    def test_MultiplePositions(self):

        file_path = Path(TMP_FILENAME)
        file_path.unlink(missing_ok=True)

        p = Posting(101, [1,2,3], 10, 5)
        n = p.nbytes
        with open(TMP_FILENAME, "wb") as f:
            f.write(p.serialize())

        with open(TMP_FILENAME, "rb") as f:
            data = f.read(n)
            read_posting, _ = Posting.deserialize(data, 0)

        file_path.unlink(missing_ok=True)
        self.assertEqual(p, read_posting)
        



if __name__ == "__main__":
    unittest.main()