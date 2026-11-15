"""Check that compaction preserves generated rows and rejects unknown input."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("compact-parser.py")
DENSE_PREFIX = "".join(f"  [STATE({state})] = {{\n    [sym_a] = ACTIONS(3),\n  }},\n" for state in range(2_000))
SOURCE = (
    "#define LARGE_STATE_COUNT 2001\n"
    "#define STATE_COUNT 2003\n\n"
    "static const uint16_t ts_parse_table[LARGE_STATE_COUNT][SYMBOL_COUNT] = {\n"
    + DENSE_PREFIX
    + """  [STATE(2000)] = {
    [sym_a] = ACTIONS(8),
    [sym_b] = ACTIONS(8),
    [sym_c] = STATE(8),
  },
};

static const uint16_t ts_small_parse_table[] = {
  [0] = 1,
    ACTIONS(5), 1,
      sym_a,
  [4] = 1,
    STATE(8), 1,
      sym_b,
};

static const uint32_t ts_small_parse_table_map[] = {
  [SMALL_STATE(2001)] = 0,
  [SMALL_STATE(2002)] = 4,
};
"""
)


class CompactParserTests(unittest.TestCase):
    """Exercise the file written by the compaction command."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parser = Path(directory.name) / "parser.c"

    def compact(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), str(self.parser)], capture_output=True, text=True)

    def test_retains_actions_and_keeps_sparse_offsets_consistent(self) -> None:
        self.parser.write_text(SOURCE, encoding="utf-8")
        result = self.compact()
        self.assertEqual(result.returncode, 0, result.stderr)
        compacted = self.parser.read_text(encoding="utf-8")
        self.assertEqual(
            compacted,
            "#define LARGE_STATE_COUNT 2000\n"
            "#define STATE_COUNT 2003\n\n"
            "static const uint16_t ts_parse_table[LARGE_STATE_COUNT][SYMBOL_COUNT] = {\n"
            + DENSE_PREFIX
            + """};

static const uint16_t ts_small_parse_table[] = {
  [0] = 2,
    ACTIONS(8), 2,
      sym_a, sym_b,
    STATE(8), 1,
      sym_c,
  [8] = 1,
    ACTIONS(5), 1,
      sym_a,
  [12] = 1,
    STATE(8), 1,
      sym_b,
};

static const uint32_t ts_small_parse_table_map[] = {
  [SMALL_STATE(2000)] = 0,
  [SMALL_STATE(2001)] = 8,
  [SMALL_STATE(2002)] = 12,
};
""",
        )
        result = self.compact()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.parser.read_text(encoding="utf-8"), compacted)

    def test_rejects_unknown_rows_and_bad_offsets_without_replacing_input(self) -> None:
        cases = (
            ("[sym_c] = STATE(8)", "[sym_c] = UNRECOGNIZED(8)", "unexpected entry in dense state 2000"),
            ("[SMALL_STATE(2002)] = 4", "[SMALL_STATE(2002)] = 3", "sparse table and offset map disagree"),
            ("      sym_a,\n  [4]", "      [3] = sym_a,\n  [4]", "unexpected sparse initializer"),
        )
        for original, replacement, diagnostic in cases:
            with self.subTest(replacement=replacement):
                source = SOURCE.replace(original, replacement)
                self.parser.write_text(source, encoding="utf-8")
                result = self.compact()
                self.assertEqual(result.returncode, 1)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(self.parser.read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
