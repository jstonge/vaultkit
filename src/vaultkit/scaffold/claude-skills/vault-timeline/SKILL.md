---
name: vault-timeline
description: Build a timeline note in `synthesis/`, either of the readings (the reading notes in publication order) or of one concept (when did MCP come out, when did Skills ship — events that cut across notes, each tied to the readings behind it). Use this whenever the user asks for a timeline, a history, what happened when, how an idea developed, or wants the readings placed in time. Distinct from vault-synthesis, which compares by __GROUP__ rather than by date.
---

# Vault timeline

A reading note says what one source claims. A timeline says where it sits in
time. It's the first half of a curriculum — chronology — before anyone argues
about what depends on what.

There are two kinds, and they answer different questions. Know which one the
user wants before you start; if the request doesn't say, ask.

| | raw timeline | conceptual timeline |
| --- | --- | --- |
| unit | a reading note | an event in the world |
| date | when the source was published | when the thing happened |
| scope | every dated reading | one concept |
| made by | `vaultkit timeline`, nearly all of it | you, from the readings, with sources |
| slug | `timeline` | `timeline-<concept>` |

The dates differ more than they seem to. An article about Skills can come out
months after Skills did. On a raw timeline the article's date is right. On a
conceptual one it's only evidence, and the event's own date has to come from
the text or a lookup. Never copy a `published:` date into a conceptual
timeline as the event's date without checking.

Both land in `__BUNDLE__/synthesis/`, not the bundle root. The root is for the
user's own thinking, and a generated timeline there would blur that.

## Raw timeline

`vaultkit timeline` does the work: sort the reading notes by `published:`,
group them by year, make the text safe for Mermaid, link each note.

**1. See what you have.**

```sh
vaultkit timeline
```

It prints a Mermaid block and a dated list of links. The count on stderr is
the notes with no usable `published:`; they're listed at the bottom, not in
the diagram.

**2. Check the dates.** A date from page metadata is a guess. Be suspicious of
a documentation page or a repo, whose date is more often the last edit than a
publication; the `vault-note` skill says to leave `published:` empty for
those. Read the archive in `sources/` for anything that looks off. Say in chat
which dates you doubt and why. Fix one with
`vaultkit note … --force --set published=YYYY-MM-DD` only when the archive
shows the right date, and ask the user about the undated rather than guessing.

**3. Create the note, then add the diagram** — see **Writing the note** below.
Add nothing to the diagram that isn't a reading: this timeline is the readings
and only the readings.

## Conceptual timeline

**1. Find the readings behind the concept.**

```sh
vaultkit timeline --tag mcp
vaultkit timeline --tag skills --notes some-slug,another-slug
```

`--tag` takes the vault's `tags:`; `--notes` takes slugs, for a concept no tag
covers. This gives you the candidate readings by publication date, which is a
starting point and nothing more. If a tag is missing, the error lists the tags
in use.

**2. Read them, and list the events.** Open each reading and its archive in
`sources/`. An event is something that happened and has a date: a release, an
announcement, a spec revision, a paper. For each one, write down the date, the
event, the readings that support it, and where the date came from. There are
three sources, and the note says which:

- **The reading's text** — the archive states it ("released in March 2025").
  Cite the note.
- **A date the reading implies** — an announcement post dated the day it
  announced. Say the date is the post's.
- **A lookup.** A date from your own knowledge or a web search, with the date
  you looked it up, per `AGENTS.md`. A release date goes stale in a way an
  archive doesn't. Ask the user before leaning on these for more than a few
  events.

A year or a month is an honest date when that's all the source gives. Few
events, each placed on purpose, beat a chronicle of everything the concept
touched.

**3. Create the note, then add the diagram** — see **Writing the note**
below. The diagram's periods are the event dates, in date order, with ` - `
where an event's text would have had a colon (Mermaid has no escape for `:`).
An event can't link, so each one also gets a line in the list below the
diagram:

```
- 2024-11-25 — MCP announced. Evidence: [Introducing the Model Context Protocol](../reading/anthropic-model-context-protocol.md). Date: the announcement post.
- 2025-03 — Spec revision adds … Evidence: [MCP documentation](../reading/mcp-docs-intro.md). Date: looked up 2026-11-24.
```

**4. Say what the readings don't settle.** Events with one source, dates you
couldn't confirm, readings that disagree. A thin stretch says as much about
the reading as about the concept.

## Writing the note

```sh
vaultkit note --template synthesis --slug <slug> --title "<title>" \
    --model <your model id> --no-archive \
    --description "One sentence: what the timeline shows." <<'EOF'
Three to five sentences on what the order shows: what came first and what it
was answering, where it turned, what's missing from the record.
EOF
```

That text goes under a `> [!agent] <name> summary` banner. Write what the
dates reveal, not a description of the diagram.

Don't put the diagram in that callout, which would nest it in a quote. Open the
note and, above `## Thinking`, add:

```
## Timeline

> [!agent] <name> timeline
> Assembled from <`published:` on the reading notes | the events listed below,
> each dated from the source named>. Argue with it under Thinking rather than
> editing it into agreement.

<the diagram, then the dated list>
```

Mermaid draws periods in the order written, so keep them in date order. Then
run `vaultkit check`.

## Attribution

Everything you put in the note sits under a `> [!agent] <name>` banner. See
`AGENTS.md`. Never run `vaultkit verify` — that's the user saying they've
checked the timeline against its sources.

## What stays yours

`## Thinking` is the user's, under their `### <name>` heading. Never write
there. Which events matter, and whether the order tells a story, is the
thinking; put it in chat as an observation.

## Keeping it current

When reading notes land or dates change, re-run the command and replace the
diagram and list under `## Timeline`. For a conceptual timeline the command
knows only the readings, so re-add the events you'd dated by hand and check
whether any new reading adds or corrects one. Don't re-run
`vaultkit note --force` for this: it rewrites the summary and isn't needed.
