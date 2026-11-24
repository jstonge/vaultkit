---
name: vault-practice
description: Draft exercises and projects that go with the reading path — small things to do or build, each requiring the readings it practises, and chains of them toward one finished project. Use this whenever the user wants hands-on practice, exercises, a project, milestones, something to build alongside the reading, or a path for someone to learn by doing. Distinct from vault-curriculum, which orders the readings; this adds the doing.
---

# Vault practice

The curriculum says what to read and in what order. This adds what to *do*:
exercises, which are small, and projects, which are chains of them. Both are
notes, and both use the same `requires:` edges as the readings, so
`vaultkit graph` puts them in one order: a reading just before the exercise
that needs it.

- **An exercise** is one thing to do or build. It requires the one or two
  readings it practises. It finishes in one sitting and ends in something that
  visibly works.
- **A project** is a chain of exercises toward one finished thing. A milestone
  is an exercise that requires the readings it needs *and the previous
  milestone*. The project note describes the finished thing and requires only
  its last milestone; the rest follow from the edges.

These land in `__BUNDLE__/exercises/` and `__BUNDLE__/projects/`, not the
bundle root.

**The user decides what's in the curriculum.** You draft; nothing is written
until they've said yes to it in chat, one exercise at a time. Never run
`vaultkit verify`: that's the user saying they have done the exercise
themselves and it works.

## What makes an exercise

- **One tangible win.** A thing that runs, prints, or passes. "Read about tool
  calling" is a reading.
- **A "done when" you can check by running something.** A script that prints
  the right output, a test that passes, a response that contains the tool
  call. If the win can't be checked, the step isn't an exercise. `vaultkit
  check` warns on an empty `## Done when`.
- **Grounded in the readings.** Take the steps, names and commands from the
  readings and their archives in `sources/`, not from memory. Your own
  knowledge of an API is untrusted: it's often a version behind. When a step
  needs a fact no archive holds, look it up, and say so in the exercise with
  the date you looked it up (`AGENTS.md`).
- **Small steps for a novice.** The first exercise should ask for little: a
  first call, one change, one visible result. A beginner who fails the first
  exercise stops. If the path has no easy way in, that is a gap in the
  readings, and you say so.
- **Requires what it uses, nearest only.** The same rule as for readings: name
  what in the exercise assumes something from a reading, and don't add an edge
  the graph already implies.

## The loop

**0. Ask what the end is.** What should the learner be able to do at the
end, what do they have to start (Python? an API key? a machine that runs
code?), and how long should one exercise take? The answer to the first
question is the project.

**1. See what the path covers.**

```sh
vaultkit graph --approach hands-on
vaultkit graph --approach hands-on --known a,b
```

Read the hands-on readings and their archives. For each, ask: after reading
this, what could a learner now *do*? Propose a list of exercises: a title, the
one-line win, what it requires, and its depth. Mark the ones you're unsure
fit. Work the way the curriculum interview does: a round at a time, with a
reason for each, and push back once if the user agrees too quickly.

Where no reading makes an exercise possible, report the gap: "nothing covers
making a first call; here's what I'd read". Don't write the missing background
into the exercise to cover it.

**2. Write each approved exercise.**

```sh
vaultkit note --template exercise --slug <slug> --title "<title>" \
    --model <your model id> --no-archive \
    --description "One sentence: what the learner builds." <<'EOF'
Two or three sentences: what you'll build and what it shows. Why now, after
these readings.
EOF
```

That text goes under a `> [!agent] <name> summary` banner. Then open the note
and fill the two sections, with a banner above `## Steps`:

```
> [!agent] <name> exercise
> Drafted from the readings this requires. Untested until someone does it.

## Steps
<numbered steps, with the commands or code from the readings, cited>

## Done when
<one thing to run and what it shows>
```

If you can run the steps, run them and change "untested" to what you ran and
the result. If you can't, leave it. Add `requires:` as quoted wikilinks, to a
reading (`"[[reading/slug]]"`) or an earlier exercise (`"[[exercises/slug]]"`),
and set `depth:`. The template sets `approach: [hands-on]`; add `foundations`
if the exercise also teaches the idea.

**3. Chain a project.** Each milestone is an exercise, and each requires the
one before it. Then:

```sh
vaultkit note --template project --slug <slug> --title "<title>" \
    --model <your model id> --no-archive \
    --description "One sentence: the thing that exists at the end." <<'EOF'
What the project is, and why this order.
EOF
vaultkit graph --to <slug>
```

`graph --to` prints the project and everything it requires in order: the
milestones, with the readings between them. Under `## Milestones`, list the
exercises in that order, each with a link; under `## Goal` and
`## Finished when`, say what exists at the end and how to tell. The project
requires only its last milestone.

**4. Check.**

```sh
vaultkit check
vaultkit graph --canvas curriculum.canvas --approach hands-on
```

Say what the path still lacks: a stretch with no exercise, an exercise with
nothing before it, a milestone that jumps too far.

## Attribution

Everything you write sits under a `> [!agent] <name>` banner (`AGENTS.md`).
The exercises are an agent's draft until the user has done them, and the
banner says "untested" until then. Don't remove it.

## What stays yours

`readStatus:`, `verified`, and any `### <name>` section. Whether an exercise
is the right size, or the project the right goal, is the user's; if the
path suggests splitting or retitling a reading note, say so in chat.

## Keeping it current

When a reading changes or a new one lands, check whether an exercise should
now require it. When an exercise fails for the first learner, fix the steps
and say what changed; don't leave the old steps under a "tested" banner.
