# Cork: Resource Architecture

A design decision record, September 2026. Companion to `hierarchy.md`.

This document describes a proposed architecture for Cork, the steps to get
there, and the reasoning behind it. It is a snapshot of a decision made at a
particular moment with 7 users and 187 pins. It should be read as the state of
an argument, not as a settled conclusion. One decision inside it is still open,
and it is marked as such.

---

## Part 1: The architecture

### Summary

Cork currently uses one object, the Board, to do five separate jobs. It is a
read-later queue, a channel for sharing with a specific person, a project
collection, the permission boundary, and the deletion boundary. This
architecture takes those jobs apart and gives each one its own object.

Two of those objects are relationships that used to be implicit. They carry
almost everything that was previously tangled.

### The objects

**User.** Unchanged. A person who can sign in.

**Pin.** A save. It has a creator, a URL, a title, and the creator's note. It
belongs to its creator permanently and does not depend on any board. This is
the most important change in the document.

**Board.** A name. It has no contents of its own and no owner column.

**Placement.** A pin appearing on a board. It records which pin, which board,
who added it, what position it holds, and whether it has been removed. A pin
can have many placements, or none.

**Membership.** A person having access to a board. It is flat, with no roles.

**Comment.** A message attached to a placement, with an author.

**Seen.** A record that a user has seen a placement.

### The rules

1. A pin is deleted only by its creator. Deleting it removes it everywhere.
2. Removing a pin from a board never deletes the pin.
3. Deleting a board deletes its placements. Every pin survives in its
   creator's collection.
4. A user can see a pin if they created it, or if a live placement of it sits
   on a board they are a member of.
5. Adding a person to a board shows them everything already on it.

Rule 4 is the important one. Visibility is calculated, not stored. There is no
visibility column anywhere in the model.

### Field sketch

```
user        id, name, open_in_new_tab
pin         id, creator_id, raw_url, normalized_url, norm_version, title, note
board       id, title, deleted_at
membership  board_id, user_id, joined_at
placement   id, board_id, pin_id, added_by, position, deleted_at
comment     id, placement_id, author_id, body
seen        placement_id, user_id, seen_at
ordering    user_id, board_id, position          (unchanged)
```

`raw_url` holds the URL exactly as the user submitted it. `normalized_url` is
derived from it and is what deduplication queries run against. `norm_version`
records which normalization rule produced it, so that fixing a rule later is a
backfill rather than a loss.

### What is deliberately absent

There is no owner on Board. There is no visibility column on Pin. There is no
tag table, no saved query, no typed relation between pins, and no Resource
table. Part 3 explains why each of these was left out.

### The one open decision

`placement.pin_id` can point at the original pin or at a copy of it.

Pointing at the original gives one comment thread, one unread state, and shared
annotation across everyone who can see the pin. It also means the creator's
note travels with the pin into boards the creator did not choose.

Pointing at a copy contains that leak and keeps each person's saves their own.
It costs the shared thread and the shared read state.

Everything else in this architecture works under either choice. This is why the
decision could be deferred. It cannot be deferred past the point where
placements are built.

---

## Part 2: The steps

### Stage zero: durability

This has nothing to do with the architecture and it goes first.

Cork runs on Gunicorn with two workers. Each worker is a separate process. Each
request loads the entire JSON store at the start and writes it back at the end.
If two requests overlap, the second write erases everything the first one did.
Without atomic file replacement, two processes writing at once can also leave
the file malformed, which loses the whole store rather than one change.

1. Write the store to a temporary file and use `os.replace` to move it over the
   real one. This makes the worst case a lost update instead of a lost store.
2. Skip the write entirely on requests that changed nothing. Most traffic is
   reads. This removes most of the contention.
3. Take a `fcntl.flock` across the load-modify-write for requests that do
   change something. A file lock works across processes; an in-process lock
   does not.
4. Back up `store.json` on a schedule, and again immediately before running any
   migration.

Setting workers to 1 would also serialize things, and it is faster to type.
Relying on it is risky, because Gunicorn's default sync worker handles one
request at a time, so any slow request blocks the whole application. Fetching
page titles from remote servers during a save would do exactly that.

### Stage one: placements

This delivers the feature users asked for. It adds one record type.

**Data.** Write a migration script. For every pin with a `board_id`, create a
placement with that board, that pin, `added_by` set to the pin's creator, and a
position derived from the current newest-first order. Then remove `board_id`
from Pin. The script is short, runs once over a few hundred records, and is
exactly reversible while every pin still has one placement.

**Behavior.** Change board deletion so it removes placements, shares, and
orderings, and leaves pins alone. Move the authorization check from "this pin's
board is owned by or shared with me" to rule 4 above. Write that check once, in
one place, and route every read through it.

**Interface.** Six changes, one of which is a new screen.

- A pins view showing everything the user created, regardless of board. This
  becomes necessary the moment pins can exist without one.
- An add-to-board action on an existing pin. This is the feature users asked
  for and it does not exist today in any form.
- Two verbs where there is now one. "Remove from this board" is available to
  whoever added the placement and to the pin's creator. "Delete pin" stays with
  the creator alone.
- The pin form's board selector becomes optional, so a pin can be saved
  unfiled.
- Pin detail gains a section listing the boards a pin sits on. This is also the
  disclosure surface for rule 4: listing the boards is the same as telling the
  user who can see the pin.
- The board delete confirmation currently promises to delete the pins. After
  this change that text is false and must be rewritten.

**One thing to settle before building.** The Inbox was designed once already
and dropped, which is why `pin.board_id` is nullable. Find out why it was
dropped. If the reason was scope, restore it. If the reason was that unfiled
pins felt like a place things go to be forgotten, that objection has not
expired.

### Stage two: independent additions

Each of these adds one record type without touching the others. Take them one
at a time, and only when use makes the need visible.

- **Manual pin ordering within a board.** The `position` column already exists
  on placement. The drag-and-drop controller already exists for board ordering
  and can be reused.
- **Comments on placements.**
- **The feed.** Keep `seen` in its own file with its own lock. Stage zero
  removed writes from the read path, and a feed puts them back, so it should
  not share a lock with pins.
- **Flat board permissions.** Keep board ownership until last. It is currently
  the only guardrail, and removing it becomes safe only after board deletion
  stops destroying pins.

### Not yet

A `resource` table. Bibliographic identity across DOI, arXiv, and publisher
URLs. File uploads. Tags, saved queries, typed relations between pins. A move
to SQL.

Each of these is likely to be wanted eventually. Each will be designed better
with a second concrete case in front of it. Putting `raw_url`,
`normalized_url`, and `norm_version` on Pin in stage one keeps all of them
available later.

---

## Part 3: The reasoning

### The problem was misdiagnosed

`hierarchy.md` framed this as a problem about categorization. Hierarchy forces
one home per item. Non-hierarchy dissolves the item into pure relation. Neither
is adequate.

That framing is coherent, and it does not match the failure Cork was actually
having.

Board was doing five jobs at once. The document's theory addressed one of them,
the project collection. The practical objection to the obvious fix, that
letting a pin belong to several boards "encounters edge cases with sharing,"
was about two others, permission and deletion. This is why the problem felt
unsolvable. The question about knowledge and the question about authorization
were riding on the same object, so every improvement to one broke the other.

The authorization question is not an epistemic question and no amount of
reasoning about categorization dissolves it. It is answered by writing down who
can do what in sentences a user would accept, which is what the rules in Part 1
are.

### Two claims in the original document that do not hold up

**Hierarchy does not require exactly one category.** Single-parent containment
does. Filesystems have allowed multiple parents through hard links since early
Unix. The constraint survives because it buys unambiguous paths, unambiguous
deletion, and inheritable permissions. Those are exactly the three things Cork
gives up here. The cost of single parenthood is paid at filing time and the
benefit is collected at authorization time, so a system where filing is the
main activity is paying badly. That is a better version of the objection than
the one in the document.

**Tags do not fail because meta-information becomes dominant.** They fail
because each tag says very little. A tag is a claim about a whole resource,
made by an unnamed author, for an unstated reason. "This pin is tagged
foucault" does not say whether the pin is by Foucault, about Foucault, cites
him, or disputes him. The weakness is in the claim, not in the quantity of
claims. The document also groups tags with zettelkasten, which does not work,
since zettelkasten is a link system and Obsidian is largely an implementation
of one.

The cleaner distinction is by the shape of the assertion. A tag is applied to a
whole thing with no target. A link connects two things and sits at a point
inside a document, with a sentence around it. Containment connects two things
and is exclusive. Obsidian's contribution is a connection that is located,
attributed, and surrounded by context. Placement in this architecture is the
same kind of object at a coarser grain.

### Why the single-user precedents only go so far

Obsidian and a personal Zotero library are single-writer systems. Their answers
to categorization are cheap because nobody has to negotiate with anyone. Cork
is a multi-writer system, and that is its distinguishing feature.

Zotero is instructive anyway, because it already separates the two jobs. An
item can sit in any number of collections, and adding it to one does not copy
it. Sharing is not handled by collections at all. It is handled by the library,
which is a hard partition: group libraries are separate from the personal
library, items dragged in become separate copies, and permissions apply to the
whole library regardless of who added what.

This architecture takes Zotero's principle and rejects its copy semantics.
Copies are clean, and they are incompatible with a single comment thread and a
single unread state, which Cork's workflows want. That is a deliberate
departure and it is the hardest thing here to reverse.

### Why the rejected options were rejected

**Typed relations between pins.** A Connection object with a type, an author,
and a note. Bush's memex is the honest precedent, and it is a better one than
Obsidian, because his trails were shareable: a user could photograph a trail
and pass it to a friend, and could add comments to it. The problems are that
almost nobody types relations by hand, that an open vocabulary of relation
types reproduces the tag problem one level up, and that graph views are more
appealing in screenshots than in use. This addresses expressiveness, and nobody
has complained about expressiveness.

**Saved queries.** A group defined by a predicate rather than by a list, in the
lineage of Gifford's semantic file systems, where a directory name is
interpreted as a query, and of Zotero's saved searches, which store criteria
rather than results. The problems are that query construction is a usability
cliff, that a shared query resolves differently for each viewer, and that
results shift under you, which destroys the thing that makes a curated board
valuable. This addresses retrieval. At 187 pins there is nothing to retrieve
that scrolling will not find.

**A canonical Resource table now.** Canonicalization buys duplicate detection,
"who else saved this," and a stable place to attach archived copies and
bibliographic data. None of that is what is failing. Normalization also has no
clean answer: `utm_source` is noise, `?v=` on YouTube is the entire identity of
the resource, and telling them apart requires a per-host rule list that will
always be somewhat wrong. Storing `raw_url` alongside `normalized_url` keeps
normalization a derived value that can be recomputed, which turns an
irreversible decision into a reversible one. An index on the normalized column
already answers the useful queries.

There is also a deeper reason to keep it thin. For research use the same paper
appears at a DOI landing page, a JSTOR URL, an arXiv abstract, an arXiv PDF,
and a copy on a faculty site. That is five URLs and one work, and no URL
normalization will ever merge them. Zotero does not try; its duplicate
detection uses title, DOI, and ISBN. The identity that will eventually matter
is bibliographic, not locational, and it arrives at the same time as file
uploads, which are another locator that is not a URL. Designing for both at
once will produce a better answer than designing for either alone.

**Moving to SQL.** Nothing in this architecture needs a relational store.
Many-to-many is a list of records, and at these counts every query is a scan
over a few thousand objects in memory. Migrating now would mean doing two hard
things at once with no way to tell which one broke.

The choice is also not between a JSON file and writing an ORM. If transactions
become necessary, SQLite can hold one table per model with the object in a JSON
text column, plus generated columns over the fields that get filtered on and
indexes on those. Generated columns arrived in SQLite 3.31.0 in January 2020,
and the JSON functions have been compiled in by default since 3.38. The model
layer stays as it is. What changes is that a write touches one row inside a
transaction. That is a persistence swap, not an ORM.

### The trade-offs being accepted

**This is more machinery than 187 pins requires.** The argument for doing it
now is that schema is expensive to change later and features are not, and that
Cork is days old rather than years old. That is a bet. The alternative bet, add
multiple placements, fix the cascading delete, and stop, is defensible.

**Visibility becomes a query, and a query can be wrong.** Every read path has
to apply rule 4. Nothing in the model will remind anyone. A miss is a privacy
bug, not a display bug. This is why the rule should exist in exactly one place.

**Union visibility is not glanceable.** With one board per pin, who can see a
pin was obvious. Now it is the union of the membership of every board the pin
sits on, and no user will track that in their head. It has to be shown in the
interface, which is work that did not exist before.

**Flat board permissions leave no arbiter.** Anyone can add anyone, and adding
someone reveals everything already there. Soft deletion is the only backstop.
This is fine for three close friends and would need revisiting at thirty users.

**Annotation still travels.** Comments are scoped to a placement, but a pin's
own note goes wherever the pin goes. Someone adding a pin to a board with an
outsider exposes a note written for a different audience. This is the residual
leak and it is the same thing as the open decision in Part 1.

**Duplicate URLs remain duplicates.** Deduplication is a query, not a
guarantee.

### What the architecture does not claim

It does not solve the problem `hierarchy.md` set out to solve. It sets that
problem aside by removing containment as the organizing relation, which makes
the hierarchy question moot rather than answered. Boards here are closer to
Notion views than to directories.

The categorization problem the document describes is real and will return,
probably when Cork holds tens of thousands of pins and a decade of accreted
boards. The theory will be worth returning to then. It is not what is failing
now.

---

## Open questions

1. Does `placement.pin_id` point at the original pin or at a copy?
2. Why was the Inbox dropped, and does that reason still apply?
3. When a board is deleted, or a user leaves it, what happens to the route back
   to pins that user found there but did not create? Is an "added by me" view
   enough?
4. Should a placement carry its own note, separate from the pin's note and from
   the comment thread? This is the adder's framing of why a pin belongs in a
   particular board.
5. Is unread scoped globally or per board, and does re-adding an old pin to a
   new shared board count as a new notification? The architecture assumes yes,
   which is why `seen` keys on placement.
