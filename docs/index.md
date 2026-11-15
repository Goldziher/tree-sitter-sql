---
layout: default
---

# tree-sitter-sql

Goldziher maintains this SQL grammar in [tree-sitter-sql](https://github.com/Goldziher/tree-sitter-sql).
Browse the generated parser sources on the [gh-pages branch](https://github.com/Goldziher/tree-sitter-sql/tree/gh-pages/src).
The [branch history](https://github.com/Goldziher/tree-sitter-sql/commits/gh-pages) contains older artifacts.

The artifacts can also be found here:

{% for file in site.static_files %}
[{{ file.path }}](/tree-sitter-sql{{ file.path }})
{% endfor %}
