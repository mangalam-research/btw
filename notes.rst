TODO: 

* Explore how much we want to use string expansions. It seems to
me there is not much gain in defining "fem.". We can just as well type
"feminine" and be done.

* Do we want to use <choice><sic><corr><reg><orig>?

* Do we want to use <date><time>?

* Do we want to use <name>?



Roles
=====

This is a general outline. Details are spelled out later in this document

visitor: someone without a login on BTW.

user: anybody with a login on BTW. Users can do anything visitors can.

author: has a login, can do everything a user can, plus write, alter article contents.

editor: has a login, can do everything an author can, plus delete articles, alter and delete abbreviations.

superuser: has a login, can do everything whatsoever.

Zotero
======

The bibliographical data is managed over at zotero.org (See the Q&A
section as to why it is so.) BTW itself provides only the following
functionality:

* Allow a BTW visitor to resolve a bibliographical abbreviation (i.e. find out what work it refers to).

* Associate a BTW user with a Zotero user ID and key.

* Allow a BTW author to search the database of already existing associations: search by abbreviation, partial abbreviation, title of work, author, etc.

* Allow a BTW author to search their Zotero library: by title/author, type, etc.

* Allow a BTW author to associate a unique abbreviation (XXX unique to all BTW?) with a specific bibliographical item in their Zotero library. (XXX Or should this be reserved to editors to avoid a mishmash of abbreviations???)

* Allow a BTW editor to change which work an abbreviation is associated with.

* Allow a BTW editor to undefine an abbreviation.

BTW does **not** provide the following functionality:

* Editing, adding, deleting Zotero entries from a Zotero library.

* Organizing a Zotero library.

Zotero and BTW Q&A
==================

**Why not implement our own bibliographical management module?** 

We're avoiding reinventing the wheel. The folks who produced Zotero
think about bibliographies day in and day out. We, on the other hand,
have other fish to fry. We save substantial time using Zotero to
provide the bulk of the functionality rather than implement our own.

**Why Zotero, and not Endnote, RefWorks, or X?**

Zotero offers the right set of features and is open source. The
director of software development used closed-source bibliographical
management software for a while. It was not a pleasant experience.

**Why not implement our own Zotero server?**

We may eventually hit the space limit over at zotero.org and have to
pay for storage space. Moreover, that server is not under our
control. It could go down and cause an outage of BTW, etc. So why not
our own Zotero server? The source is available so it should be a
simple matter, right?

This option has been considered. This is something brought up from
time to time on the Zotero mailing lists and forums. The developers
point out that changes to the protocols between server and clients
might require some carefully choreographed deployment, etc. Those
Zotero users who are using the official client and the official server
(at zotero.org), are automatically taken care of by the Zotero
development team. The developers also point out that supporting
heterogeneous servers is not (currently) a priority for them: the
Zotero client does not even have an interface for this; zotero.org is
hardcoded. So if a user of BTW would want to talk to the zotero.org
server *and* to the Zotero server deployed for BTW, providing this
functionality in a client would be *our* responsibility. Now, consider
the possibility that zotero.org is upgraded to a new protocol but that
we do not have immediate resources at Mangalam to update BTW's own
zotero server. Suddenly the client customized to suppport BTW has to
support two protocols, or users can no longer access their data at
zotero.org. (At the time of writing, 2013-01-02, a new sync protocol
has been announced, which is precisely the kind of change that would
cause trouble.)

The upshot is that if someone implements a server for their own
organization, they have to:

1. Track the server code.

2. Track the client code.

3. Deploy their own customized clients to the people they hope will
use their server besides zotero.org.

4. Hope that end users can manage the complications this causes.

This can of worms ought not to be opened before a substantial reason
exists to open it. The storage fees at zotero.org are relatively
modest, and whatever complications may arise from depending on
zotero.org can be mitigated by caching.

Abbreviations
=============

An abbreviation refers to an entity. Among the possible entities a
given abbreviation may refer to are:

* Primary sources. e.g. the MMK part of "MMK 24:18" to refer to the
  Mūlamadhyamakakārikā chapter 24 verse 18.

* Secondary sources. e.g. the "Cox 1995" part of (Cox 1995, 12).

* Strings. e.g. fem. -> feminine, or BHSD -> Buddhist Hybrid Sanskrit Dictionary  (This kind of abbreviation is called a string expansion.)

Defining an abbreviation means establishing a relationship between the
abbreviation and an entity it refers to. Assigning an abbreviation to
an entity means defining an abbreviation so that it refers to the said
entity.

Abbreviations referring to primary sources and secondary sources are
unique per-article, but not over the whole BTW database.

String expansions are unique BTW-wide. (TODO: do we really want this?)

Why? Uniqueness across an entire work works well when that work is set
in stone in one shot: for instance a paper dictionary. When a work is
a collection of disaparate entities like a journal published over
time, it does not make much sense to insisit on a set of unique
abbreviations that will be implemented across all these disparate
entitites. Journals typically require their contributors to identify
their abbreviations, and may require that *some* abbreviations be
standardized but will not require that all abbreviations be
standardized across the *entire* series. BTW is more like a journal
than like a paper dictionary because the articles are published over
time by different contributors.

The relationship between an abbreviation and the entity it refers to
is mutable.

Mutating the relationship between an abbreviation and entities entails
that the article holding this relationship has been edited. Thus, a
new version of the article comes into being. (Therefore, changing a
string expansion means changing the meaning of all articles that use
this expansion.)

It is likely that as new editions of texts are produced an
abbreviation might have to change. Consider this scenario:

* We need to refer to Smith's edition of the AKBh so we write AKBh.S.

* Later, Stone releases an edition of the AKBh that we want to use in the same article as Smith's. We can't use AKBh.S for both. 

It would be possible to keep AKBh.S for Smith and have AKBh.St for
Stone, but cognitively there has to be an extra effort to realize that
AKBh.S is Smith, and exclude Stone. Changing AKBh.S to AKBh.Sm when
referring to Smith helps the reader distinguish the two editions.

Or this scenario:

* We need to refer to Smith's edition of the AKBh so we write AKBh.S.

* Later, Smith release a new edition of AKBh.

Again we could keep AKBh.S intact and require that the reader do the
addional mind-work to remember that AKBh.S is the old edition and
AKBh.S.2013 is the new one, but if we can change the old AKBh.S to
AKBh.S.1998 we are helping the reader keep the two editions separate
in their mind.

The value of abbreviations is in their shortness so it does not make
sense to insist that abbreviations be long right off the bat *just in
case* they need to be lengthened in the future. Hence, the need to be
able to modify them to handle future cases. Hence, also the decision
to have abbreviations be unique per-article rather than over all of
BTW. Requiring the latter would mean that the author of an article
would also have to take care to pick abbreviations that do not clash
with any other author.
