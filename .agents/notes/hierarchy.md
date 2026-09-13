# Organization and The Hierarchical Problem

Information management systems eventually face the fundamental problem of
**organization**: how to abstract over multiple resources and form them into
coherent groupings. In this sense they become meta-informational, producing and dealing not only in "information itself" but also in "information about information."

For meta-information, i.e. groups and collections of information, to be useful,
it must be *composable*. It must not be a rigid and single-purpose construction,
but rather a production which emerges in a particular context but is able to be
shaped into different contexts. Imagine if concrete could safely harden, then be
molded again, and hardened again, each time remembering its previous shapes and
affording the construction of new ones; this is the ideal information system.

Information about information does not deal only in the specific resources it
describes, but also concerns the relations between what it does not describe,
i.e. the information outside of it (outside of its inside). By being both
flexible and relational, meta-information facilitates the *investigation* of
information and the *sharing* of information as opposed to the simple *storage*
of information.

Information management systems exist to aid in the production of knowledge and
the facilitation of effective organization. An information management system
which does not produce meta-information, which restricts information to its most
primitive components, is insufficient.

## Non-Solution: Hierarchy

The classical solution to the problem of meta information is categorization in the form of hierarchy. One grouping resource exists to collect all the contained resources, of which some may themselves be groups. This can be represented by an acyclic tree structure.

This structure affords some information retrieval efficiency, but requires
information to possess exactly one category. One winds up producing categories
which are fit for some purposes but not others and then finding their
meta-information always inadequate even in the most ideal scenario. This
inadequacy stops the information in its tracks and prevents it from producing connections and allowing the information retriever to investigate its different possibilities.

Hierarchy cannot solve the problem of knowledge production through information retrieval and categorization.

e.g. filesystems, domain names

## Non-Solution: Non-Hierarchy

The opposing solution to that of hierarchy is simple non-hierarchy. Every resource stands on its own, grouping resources can be freely attached to other resources, and resources themselves can (in some systems) function both as groups and sources. This can be represented by a cyclic graph structure.

This structure affords great information retrieval efficiency when coupled with
a sophisticated search interface. Provided enough points of input, one can
theoretically find any resource. This has two points of degredation, however,
one of them severe. In the first place, this devalues the individual resource.
Whereas before, information was primary while meta-information was a secondary
layer, in this case meta-information is the exclusive product. This is nice from
a theoretical perspective, but when the resource is information itself, managing it under this model always feels "at a distance."

The more fatal flaw in this system is a follow on from this fact. while grouping
is flexibile, one is not *encouraged* to make connections between the groups but
rather *forced* to. Because meta-information is the exclusive resource, information itself ceases to have significant meaning. Rather than encouraging knowledge production, information is stopped in its tracks, forced to be inert and shapeless, rather than having many shapes.

Non-hierarchy cannot solve the problem of knowledge production through information retrieval, categorization, and integration.

e.g. tags, zettelkasten

## Case Study: Obsidian

The Obsidian knowledge management system, taking from knowledge graph systems,
Wikis, and hypertext systems in general, circumvents this problem in a supremely
elegant way. Rather than trying to square the circle of hierarchy and
non-hierarchy, the hypertext system invents a *third form of information*: the
link. Hierarchy exists in the form of directories (and paths/domains on the web
etc.) containing files, but within a file a link can provide connection to
another file or directory. Hierarchy is therefore not disregarded but rather
*subverted*. A graph view over such an information system provides a particular
kind of insight into the information it contains, while hierarchy

Obsidian and Notion solved the problem by introducing a third resource, in
effect subverting the contradiction of hierarchy and non-hierarchy before it
became a problem.

## Case Study: Cork

Cork is a web application for managing digital information. The fundamental
resources are Users, Pins, and Boards. Users are people who use the application.
Pins are URLs with an attached title and note that a User has created. Boards
are groups of Pins that a User has created, and may share with another
User. Users can add Pins to Boards that have been shared with them, but they cannot remove or edit Pins that are not their own.

This system, in its current form, effectively has a single level of hierarchy:
Boards contain Pins, that is it.

Such a system was designed to be used by a small group of friends to share links
with one another, but it has grown past this stage to the point where they now
use it independently in addition to collaboratively. Some users make multiple
boards for their different university classes, and others make multiple boards
for sharing with different people. Several times now the request has come up to
let a Pin belong to multiple Boards. You might want to share this Pin with
multiple people, but don't want a single Board to be shared between them; you
might want to save a PDF for a particular paper or research interest, but
realize it's also applicable to something else later.

It is clear that it has outgrown its initial design design. It needs some form
of multiple information retreival, but it cannot get caught in the problem of
hierarchy. It cannot make a flawed compromise that gets the worst of both worlds
and force its users to be stuck using a bad system; Cork was created to avoid
that problem in the first place.

The kitchen sink "just add tags" solution is unsatisfactory because it does not
feel sufficient, and feels messy. The simple "just let pins belong to multiple
boards" solution is unsatisfactory because it encounters edge cases with sharing
and seems like it will run into problems down the line.

This system will expand beyond just external URLs; it will need to eventually
support uploading files, comment threads on Pins between users, and author
management information like Zotero. Long term it could serve the same function
that a directory of Markdown files does, or a Notion space, combined with a
spreadsheet. It's a little amorphous.

## Problem Statement

I am the designer of Cork, and one of the small group of users who value it
highly. I need help working through the possibilities of what to do to change
Cork to accomodate this more flexible form of information retrieval and
exchange. Cork is a personal knowledge management system, and in order to grow
it needs to embrace knowledge rather than trying to capture it.

I would like:

- Responses to this document, thoughts on the solutions it rejects.
- 3 potential solutions to the problem of hierarchy and categorization in Cork.
- Downsides to each of the proposed solutions.
- A suggested path for talking more about these possible solutions, questions
  you would like answered, or information that you think could help us have a
  fruitful conversation about where to go from here in Cork.


## Workflows

1. User(a) encounters something interesting on the internet and wants to read it
   later.
2. User(a) saves Pin(a) in Cork.
3. User(a) goes to the place in Cork that they keep "things saved for later",
   and finds Pin(a).

1. User(a) encounters something interesting on the internet and wants to share
   it with User(b).
2. User(a) saves Pin(a) to Cork in the place they keep "things I'm sharing with
   User(b).
3. User(b) opens Cork at some point and looks at "things shared with me that I
   haven't seen yet", and encounters Pin(a).

1. User(a) is collecting things for an interesting project on Board(a).
2. User(a) comes back to their project to look for Pin(a) and Pin(b).
3. User(a) wants to share Pin(c) from their project with User(b).
4. User(a) is collecting things for a different interesting project, and
   realizes Pin(b) and Pin(d) from earlier Board(a) are related.

## Questions

1. A Pin has a creator which is the User who created it. The User who created
   the Pin can delete the Pin, but only the User who created the Board on which
   the Pin is stored can delete the Board. When a Board is deleted, all its Pins
   are deleted too.
2. User(a) can only add "a new Pin" to User(b)'s Board. A Pin is not shared. If
   it were (see: 3), I think this would be acceptable.
3. Currently, two. I like where one shared URL points but think it would likely
   be complex.
4. "I couldn't decide where to put it," i.e. "I wanted to put it in one place
   but now or later realize it also belongs in another place."
5. Sometimes boards are for specific purposes, like organizing a class syllabus.
   Other boards are social, involving a kind of "check for recently uploaded
   pins that I haven't seen."
6. Currently 7 users (3 of whom are heavy users), 187 Pins, 21 Boards. I just
   published it to them a couple days ago, and think they will continue to use
   it steadily (though not at the current pace).
7. Pins are currently ordered by upload date per Board. Boards are ordered by
   preference per User.
