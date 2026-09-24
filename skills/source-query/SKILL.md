---
name: source-query
description: Retrieve user-registered study sources and answer with page citations.
---

# source-query

Use Hermes' terminal tool from the repository root. Never query SQLite directly;
use the Source Engine CLI.

1. If the user names a source (“según X”, “using this guide”), run
   `python3 scripts/source_cli.py list-sources` and identify that registered
   source. If it is not listed, say that it is not registered; do not silently
   substitute another source.
2. Search with
   `python3 scripts/source_cli.py search-source "QUERY" --source-id ID` for a
   named source. Otherwise search all active sources, optionally filtering by
   subject or topic.
3. Answer from the returned snippets only when a source was explicitly
   requested. Cite each supported claim with the returned source title and page.
4. If the results do not contain enough evidence, say so. Do not invent page
   numbers or present model knowledge as source content.
5. If the user did not request source-only and general knowledge helps, put it in
   a separate paragraph labelled `Contexto general`. If they requested
   “únicamente esta fuente”, omit unsupported general knowledge.

For a question not tied to a specific source, prioritize matching registered
materials and cite the relevant title and page. Search is lexical over extracted
page text; an empty result means the requested wording was not found, not that
the source necessarily says nothing about the idea.
