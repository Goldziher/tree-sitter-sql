# Contributing to tree-sitter-sql

## Getting Started

Follow the [source build instructions](README.md#build-from-source) to clone the fork and generate the parser.

### Testing

Run the grammar corpus and keyword checks after regenerating the parser. The keyword check requires `jq`.

```sh
npx --yes --package=tree-sitter-cli@0.26.3 -- tree-sitter test
scripts/test-keywords.sh
```

Add or update a case in [test/corpus](test/corpus) when changing parser behavior. If a syntax tree changes intentionally,
run this command and review the resulting corpus diff.

```sh
npx --yes --package=tree-sitter-cli@0.26.3 -- tree-sitter test --update
```

### Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), with an optional scope such as `ast`.
If a change breaks the syntax tree, include `!` in the subject and explain the change in a `BREAKING CHANGE` footer.

```text
refactor(ast)!: remove predicate and merge into binary_expression

BREAKING CHANGE: The `predicate` node has been replaced with `binary_expression`.
```

## Releases

Pushing a version tag creates a [draft GitHub release](https://github.com/Goldziher/tree-sitter-sql/releases) with an archive
of the generated parser sources and bindings. Update the version fields in the package and build manifests before tagging.
