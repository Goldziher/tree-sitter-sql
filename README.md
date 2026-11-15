# tree-sitter-sql

[![Build and test](https://github.com/Goldziher/tree-sitter-sql/actions/workflows/ci.yml/badge.svg)](https://github.com/Goldziher/tree-sitter-sql/actions/workflows/ci.yml)

A permissive SQL grammar for [Tree-sitter](https://github.com/tree-sitter/tree-sitter), maintained by Goldziher as an independent fork of [Derek Stride's tree-sitter-sql](https://github.com/DerekStride/tree-sitter-sql).

The [test corpus](test/corpus) shows which SQL statements and dialect extensions the grammar recognizes. The repository also provides a [syntax highlighting query](queries/highlights.scm) for editors and other Tree-sitter integrations.

## Build from source

You need Node.js with npm and a C compiler. Run these commands from the fork checkout to generate the parser and build a shared library on Linux or macOS.

```sh
git clone https://github.com/Goldziher/tree-sitter-sql.git
cd tree-sitter-sql
npx --yes --package=tree-sitter-cli@0.26.3 -- tree-sitter generate
cc -shared -fPIC -I./src src/parser.c src/scanner.c -o sql.so
```

Generated C sources are available on the [`gh-pages` branch](https://github.com/Goldziher/tree-sitter-sql/tree/gh-pages/src) and in [release archives](https://github.com/Goldziher/tree-sitter-sql/releases) when available. The branch can lag `main`. Pin a specific artifact revision or fork release for reproducible builds.

The [npm package](https://www.npmjs.com/package/@derekstride/tree-sitter-sql), [Rust crate](https://crates.io/crates/tree-sitter-sequel), and [Python package](https://pypi.org/project/tree-sitter-sql/) are upstream distributions. Build from this repository to use the fork's changes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the test commands. For parser bugs, [open an issue](https://github.com/Goldziher/tree-sitter-sql/issues/new) with a minimal SQL example and the expected result.

## Grammar references

- [SQL syntax overview](https://en.wikipedia.org/wiki/SQL_syntax)
- [Apache Phoenix language reference](https://phoenix.apache.org/language/index.html)
- [SQLite expression syntax](https://www.sqlite.org/lang_expr.html)
- [PostgreSQL commands](https://www.postgresql.org/docs/current/sql-commands.html)
- [MariaDB statement syntax](https://mariadb.com/kb/en/sql-statements-structure/)

## License

[MIT](LICENSE).
