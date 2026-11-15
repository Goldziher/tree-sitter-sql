"""Store most SQL parse states in Tree-sitter's sparse table format for WASM."""

import argparse
import re
import stat
import tempfile
from collections import defaultdict
from pathlib import Path

# Dense lookup is faster, but each dense state reserves one cell per symbol.
# Keep the first 2,000 states, which Tree-sitter orders by descending entry count.
DENSE_STATE_LIMIT = 2_000
DENSE_HEADER = "static const uint16_t ts_parse_table[LARGE_STATE_COUNT][SYMBOL_COUNT] = {\n"
SPARSE_HEADER = "static const uint16_t ts_small_parse_table[] = {\n"
MAP_HEADER = "static const uint32_t ts_small_parse_table_map[] = {\n"
DENSE_ROW = re.compile(r"  \[STATE\((\d+)\)\] = \{\n((?:    [^\n]+\n)*)  \},\n")
DENSE_ENTRY = re.compile(r"    \[([A-Za-z_][A-Za-z_0-9]*)\] = ((?:STATE|ACTIONS)\(\d+\)),")
SPARSE_ROW_START = re.compile(r"^  \[(\d+)\] = (\d+),\n", re.MULTILINE)
MAP_ENTRY = re.compile(r"  \[SMALL_STATE\((\d+)\)\] = (\d+),\n")


def table_body(source: str, header: str) -> tuple[int, int]:
    """Find the bounds of a generated initializer body."""
    if source.count(header) != 1:
        raise ValueError(f"expected one generated initializer for {header.strip()}")
    start = source.index(header) + len(header)
    end = source.index("\n};\n", start) + 1
    return start, end


def define(source: str, name: str) -> re.Match[str]:
    """Locate a generated numeric define."""
    matches = list(re.finditer(rf"^#define {name} (\d+)$", source, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f"expected one numeric definition of {name}")
    return matches[0]


def group_symbols(row: str, state: int) -> dict[str, list[str]]:
    """Group each symbol by its shift or action-list value."""
    groups: dict[str, list[str]] = defaultdict(list)
    seen = set()
    for line in row.splitlines():
        match = DENSE_ENTRY.fullmatch(line)
        if match is None or match[1] in seen:
            raise ValueError(f"unexpected entry in dense state {state}")
        symbol, action = match.groups()
        seen.add(symbol)
        groups[action].append(symbol)
    return groups


def convert_dense_rows(body: str, dense_count: int) -> tuple[int, str, str, int]:
    """Encode the dense rows after the retained prefix as sparse rows."""
    position = 0
    replacement_start = 0
    values = []
    offsets = []
    offset = 0
    for state in range(dense_count):
        row = DENSE_ROW.match(body, position)
        if row is None or int(row[1]) != state:
            raise ValueError(f"unexpected dense row for state {state}")
        if state == DENSE_STATE_LIMIT:
            replacement_start = position
        position = row.end()
        if state < DENSE_STATE_LIMIT:
            continue
        groups = group_symbols(row[2], state)
        offsets.append(f"  [SMALL_STATE({state})] = {offset},\n")
        values.append(f"  [{offset}] = {len(groups)},\n")
        offset += 1
        for action, symbols in groups.items():
            values.append(f"    {action}, {len(symbols)},\n      {', '.join(symbols)},\n")
            offset += 2 + len(symbols)
    if position != len(body):
        raise ValueError("unexpected text after generated dense rows")
    return replacement_start, "".join(values), "".join(offsets), offset


def shift_sparse_offsets(body: str, mapping: str, dense_count: int, state_count: int, shift: int) -> tuple[str, str]:
    """Move the old sparse rows and their map entries forward together."""
    position = 0
    offsets = []
    shifted_map = []
    for state in range(dense_count, state_count):
        entry = MAP_ENTRY.match(mapping, position)
        if entry is None or int(entry[1]) != state:
            raise ValueError(f"unexpected sparse map entry for state {state}")
        offset = int(entry[2])
        if (offsets and offset <= offsets[-1]) or (not offsets and offset != 0):
            raise ValueError(f"nonsequential sparse offset for state {state}")
        offsets.append(offset)
        shifted_map.append(f"  [SMALL_STATE({state})] = {offset + shift},\n")
        position = entry.end()
    if position != len(mapping) or offsets != [int(row[1]) for row in SPARSE_ROW_START.finditer(body)]:
        raise ValueError("generated sparse table and offset map disagree")
    shifted_body = SPARSE_ROW_START.sub(lambda row: f"  [{int(row[1]) + shift}] = {row[2]},\n", body)
    return shifted_body, "".join(shifted_map)


def compact(source: str) -> str:
    """Reduce the number of dense states while preserving all parse actions."""
    dense_define = define(source, "LARGE_STATE_COUNT")
    dense_count = int(dense_define[1])
    state_count = int(define(source, "STATE_COUNT")[1])
    dense_start, dense_end = table_body(source, DENSE_HEADER)
    if not 2 <= dense_count < state_count <= 65_536:
        raise ValueError("unexpected generated state counts")
    if dense_count <= DENSE_STATE_LIMIT:
        return source
    sparse_start, sparse_end = table_body(source, SPARSE_HEADER)
    map_start, map_end = table_body(source, MAP_HEADER)
    if not dense_define.end() < dense_start < dense_end < sparse_start < sparse_end < map_start < map_end:
        raise ValueError("unexpected generated initializer order")
    keep, new_sparse, new_map, shift = convert_dense_rows(source[dense_start:dense_end], dense_count)
    old_sparse, old_map = shift_sparse_offsets(
        source[sparse_start:sparse_end], source[map_start:map_end], dense_count, state_count, shift
    )
    return "".join(
        (
            source[: dense_define.start(1)],
            str(DENSE_STATE_LIMIT),
            source[dense_define.end(1) : dense_start + keep],
            source[dense_end:sparse_start],
            new_sparse,
            old_sparse,
            source[sparse_end:map_start],
            new_map,
            old_map,
            source[map_end:],
        )
    )


def replace_parser(path: Path, source: str) -> None:
    """Atomically replace the parser after validation and conversion succeed."""
    mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as temporary:
        staged = Path(temporary.name)
        try:
            temporary.write(source)
            temporary.close()
            staged.chmod(mode)
            staged.replace(path)
        finally:
            staged.unlink(missing_ok=True)


def main() -> None:
    """Compact a generated parser in place."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parser", type=Path, help="generated src/parser.c")
    path = parser.parse_args().parser
    try:
        source = path.read_text(encoding="utf-8")
        compacted = compact(source)
        if compacted != source:
            replace_parser(path, compacted)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{path}: {error}\n")


if __name__ == "__main__":
    main()
