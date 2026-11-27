# Draft the rows of the source map

You are drafting rows for one company's source map, the table in
`access/stack.md` that says, for each kind of data the team's work needs,
where it lives, which connected tool reads it, and what to do when that tool
is not connected. A skill reads these rows to find its data and to say plainly
when it cannot reach it. Draft the rows from what the person tells you and the
material they name, and from nothing else.

## What to ask first

Ask these as one question, in plain words, and let them answer in their own
words:

<!-- ask -->
Where does each of these live for you, and which connected tool reads it: your
ad spend, your pipeline, your customer conversations, and how people use your
product? Name only the ones you have.
<!-- end ask -->

Write their answer, word for word, into the answer file this step hands out.
If they name another kind of data the team's work needs, it may be a row too.

## The rows to write

Write the section exactly like this, with one row per kind of data they
named:

```markdown
## Where the material lives

| Kind of data | Business | Where it lives | What reads it | If that is not connected |
|---|---|---|---|---|
| Ad spend | whole company | the place they named | the tool they named, or nothing | what to do instead |
```

- **Where it lives** and **What reads it** are written in the person's own
  words, exactly as they said them. A place or a tool they did not name is
  never a row, however usual it would be for a company like theirs. When they
  said nothing reads it yet, write `nothing`.
- **Business** is `whole company`, or the short name of one business the
  base's map lists when the data is only that business's.
- **If that is not connected** says what a person or a skill does instead,
  such as asking somebody for an export. Every row needs one; a row without it
  is not used.
- Never write a password, a key, a token, or a web address that carries one.
  A row holding anything shaped like one is refused.
- Never use a long dash of any kind. Use a comma, use round brackets, or write
  the sentence again.

## Draft first, ask afterwards

Write every row now, from what they said. Where something is genuinely their
call, such as which business a kind of data belongs to, write your best
reading and mark it inline like this: `[your call: is this only the courier
app's spend?]`. Then stop and let them read the rows. Do not interview them one
row at a time.
