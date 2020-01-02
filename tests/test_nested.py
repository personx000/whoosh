from whoosh import fields, query, sorting
from whoosh.util.testing import TempIndex


def test_nested_parent():
    schema = fields.Schema(name=fields.ID(stored=True), type=fields.ID,
                           part=fields.ID, price=fields.NUMERIC)
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(name=u"iPad", type=u"product")
                w.add_document(part=u"screen", price=100)
                w.add_document(part=u"battery", price=50)
                w.add_document(part=u"case", price=20)

            with w.group():
                w.add_document(name=u"iPhone", type=u"product")
                w.add_document(part=u"screen", price=60)
                w.add_document(part=u"battery", price=30)
                w.add_document(part=u"case", price=10)

            with w.group():
                w.add_document(name=u"Mac mini", type=u"product")
                w.add_document(part=u"hard drive", price=50)
                w.add_document(part=u"case", price=50)

        with ix.searcher() as s:
            pq = query.Term("type", "product")
            cq = query.Term("price", 50)
            q = query.NestedParent(pq, cq)

            r = s.search(q)
            assert sorted([hit["name"] for hit in r]) == ["Mac mini", "iPad"]


def test_scoring():
    schema = fields.Schema(kind=fields.ID,
                           name=fields.KEYWORD(scorable=True, stored=True))
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(kind=u"class", name=u"Index")
                w.add_document(kind=u"method", name=u"add document")
                w.add_document(kind=u"method", name=u"add reader")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Accumulator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"get result")
            with w.group():
                w.add_document(kind=u"class", name=u"Calculator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"add all")
                w.add_document(kind=u"method", name=u"add some")
                w.add_document(kind=u"method", name=u"multiply")
                w.add_document(kind=u"method", name=u"close")

        with ix.searcher() as s:
            q = query.NestedParent(query.Term("kind", "class"),
                                   query.Term("name", "add"))
            r = s.search(q)
            assert ([hit["name"] for hit in r] ==
                    ["Calculator", "Index", "Accumulator"])


def test_missing():
    schema = fields.Schema(kind=fields.ID,
                           name=fields.KEYWORD(scorable=True, stored=True,
                                               lowercase=False))
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(kind=u"class", name=u"Index")
                w.add_document(kind=u"method", name=u"add document")
                w.add_document(kind=u"method", name=u"add reader")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Accumulator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"get result")
            with w.group():
                w.add_document(kind=u"class", name=u"Calculator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"add all")
                w.add_document(kind=u"method", name=u"add some")
                w.add_document(kind=u"method", name=u"multiply")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Deleter")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"delete")

        with ix.searcher() as s:
            q = query.NestedParent(query.Term("kind", "class"),
                                   query.Term("name", "add"))

            r = s.search(q)
            assert ([hit["name"] for hit in r] ==
                    ["Calculator", "Index", "Accumulator", "Deleter"])

        with ix.writer() as w:
            w.delete_by_term("name", "Accumulator")
            w.delete_by_term("name", "Calculator")

        with ix.searcher() as s:
            pq = query.Term("kind", "class")
            assert len(list(pq.docs(s))) == 2
            q = query.NestedParent(pq, query.Term("name", "add"))
            r = s.search(q)
            assert [hit["name"] for hit in r] == ["Index", "Deleter"]


def test_nested_delete():
    schema = fields.Schema(kind=fields.ID,
                           name=fields.KEYWORD(scorable=True, stored=True,
                                               lowercase=False))
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(kind=u"class", name=u"Index")
                w.add_document(kind=u"method", name=u"add document")
                w.add_document(kind=u"method", name=u"add reader")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Accumulator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"get result")
            with w.group():
                w.add_document(kind=u"class", name=u"Calculator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"add all")
                w.add_document(kind=u"method", name=u"add some")
                w.add_document(kind=u"method", name=u"multiply")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Deleter")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"delete")

        # Delete "Accumulator" class
        with ix.writer() as w:
            q = query.NestedParent(query.Term("kind", "class"),
                                   query.Term("name", "Accumulator"))
            w.delete_by_query(q)

        # Check that Accumulator AND ITS METHODS are deleted
        with ix.searcher() as s:
            r = s.search(query.Term("kind", "class"))
            assert (sorted(hit["name"] for hit in r) ==
                    ["Calculator", "Deleter", "Index"])

            names = [fs["name"] for _, fs in s.reader().iter_docs()]
            assert names == ["Index", "add document", "add reader", "close",
                             "Calculator", "add", "add all", "add some",
                             "multiply", "close", "Deleter", "add", "delete"]

        # Delete any class with a close method
        with ix.writer() as w:
            q = query.NestedParent(query.Term("kind", "class"),
                                   query.Term("name", "close"))
            w.delete_by_query(q)

        # Check the CLASSES AND METHODS are gone
        with ix.searcher() as s:
            names = [fs["name"] for _, fs in s.reader().iter_docs()]
            assert names == ["Deleter", "add", "delete"]


def test_all_parents_deleted():
    schema = fields.Schema(kind=fields.ID,
                           name=fields.KEYWORD(scorable=True, stored=True,
                                               lowercase=False))
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(kind=u"class", name=u"Index")
                w.add_document(kind=u"method", name=u"add document")
                w.add_document(kind=u"method", name=u"add reader")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Accumulator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"get result")
            with w.group():
                w.add_document(kind=u"class", name=u"Calculator")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"add all")
                w.add_document(kind=u"method", name=u"add some")
                w.add_document(kind=u"method", name=u"multiply")
                w.add_document(kind=u"method", name=u"close")
            with w.group():
                w.add_document(kind=u"class", name=u"Deleter")
                w.add_document(kind=u"method", name=u"add")
                w.add_document(kind=u"method", name=u"delete")

        with ix.writer() as w:
            w.delete_by_term("name", "Index")
            w.delete_by_term("name", "Accumulator")
            w.delete_by_term("name", "Calculator")
            w.delete_by_term("name", "Deleter")

        with ix.searcher() as s:
            q = query.NestedParent(query.Term("kind", "class"),
                                   query.Term("name", "add"))
            r = s.search(q)
            assert r.is_empty()


def test_everything_is_a_parent():
    schema = fields.Schema(id=fields.STORED, kind=fields.ID,
                           name=fields.ID(stored=True))
    k = u"alfa"
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(id=0, kind=k, name=u"one")
            w.add_document(id=1, kind=k, name=u"two")
            w.add_document(id=2, kind=k, name=u"three")
            w.add_document(id=3, kind=k, name=u"four")
            w.add_document(id=4, kind=k, name=u"one")
            w.add_document(id=5, kind=k, name=u"two")
            w.add_document(id=6, kind=k, name=u"three")
            w.add_document(id=7, kind=k, name=u"four")
            w.add_document(id=8, kind=k, name=u"one")
            w.add_document(id=9, kind=k, name=u"two")
            w.add_document(id=10, kind=k, name=u"three")
            w.add_document(id=11, kind=k, name=u"four")

        with ix.searcher() as s:
            pq = query.Term("kind", k)
            cq = query.Or([query.Term("name", "two"),
                           query.Term("name", "four")])
            q = query.NestedParent(pq, cq)
            r = s.search(q)
            assert [hit["id"] for hit in r] == [1, 3, 5, 7, 9, 11]


def test_no_parents():
    schema = fields.Schema(id=fields.STORED, kind=fields.ID,
                           name=fields.ID(stored=True))
    k = u"alfa"
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(id=0, kind=k, name=u"one")
            w.add_document(id=1, kind=k, name=u"two")
            w.add_document(id=2, kind=k, name=u"three")
            w.add_document(id=3, kind=k, name=u"four")
            w.add_document(id=4, kind=k, name=u"one")
            w.add_document(id=5, kind=k, name=u"two")
            w.add_document(id=6, kind=k, name=u"three")
            w.add_document(id=7, kind=k, name=u"four")
            w.add_document(id=8, kind=k, name=u"one")
            w.add_document(id=9, kind=k, name=u"two")
            w.add_document(id=10, kind=k, name=u"three")
            w.add_document(id=11, kind=k, name=u"four")

        with ix.searcher() as s:
            pq = query.Term("kind", "bravo")
            cq = query.Or([query.Term("name", "two"),
                           query.Term("name", "four")])
            q = query.NestedParent(pq, cq)
            r = s.search(q)
            assert r.is_empty()


def test_nested_children():
    schema = fields.Schema(t=fields.ID(stored=True),
                           track=fields.NUMERIC(stored=True),
                           album_name=fields.TEXT(stored=True),
                           song_name=fields.TEXT(stored=True))
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            with w.group():
                w.add_document(t=u"album", album_name=u"alfa bravo charlie")
                w.add_document(t=u"track", track=1,
                               song_name=u"delta echo foxtrot")
                w.add_document(t=u"track", track=2,
                               song_name=u"golf hotel india")
                w.add_document(t=u"track", track=3,
                               song_name=u"juliet kilo lima")
            with w.group():
                w.add_document(t=u"album", album_name=u"mike november oskar")
                w.add_document(t=u"track", track=1,
                               song_name=u"papa quebec romeo")
                w.add_document(t=u"track", track=2,
                               song_name=u"sierra tango ultra")
                w.add_document(t=u"track", track=3,
                               song_name=u"victor whiskey xray")
            with w.group():
                w.add_document(t=u"album", album_name=u"yankee zulu one")
                w.add_document(t=u"track", track=1,
                               song_name=u"two three four")
                w.add_document(t=u"track", track=2,
                               song_name=u"five six seven")
                w.add_document(t=u"track", track=3,
                               song_name=u"eight nine ten")

        with ix.searcher() as s:
            pq = query.Term("t", "album")
            aq = query.Term("album_name", "november")

            r = s.search(query.NestedChildren(pq, pq), limit=None)
            assert len(r) == 9
            assert [str(hit["t"]) for hit in r] == ["track"] * 9

            ncq = query.NestedChildren(pq, aq)
            assert list(ncq.docs(s)) == [5, 6, 7]
            r = s.search(ncq, limit=None)
            assert len(r) == 3
            assert ([str(hit["song_name"]) for hit in r] ==
                    ["papa quebec romeo", "sierra tango ultra",
                     "victor whiskey xray"])

            zq = query.NestedChildren(pq, query.Term("album_name", "zulu"))
            f = sorting.StoredFieldFacet("song_name")
            r = s.search(zq, sortedby=f)
            assert [hit["track"] for hit in r] == [3, 2, 1]


def test_nested_skip():
    schema = fields.Schema(
        id=fields.ID(unique=True, stored=True),
        name=fields.TEXT(stored=True),
        name_ngrams=fields.NGRAMWORDS(minsize=4, field_boost=1.2),
        type=fields.TEXT,
    )

    domain = [
        (u"book_1", u"The Dark Knight Returns", u"book"),
        (u"chapter_1", u"The Dark Knight Returns", u"chapter"),
        (u"chapter_2", u"The Dark Knight Triumphant", u"chapter"),
        (u"chapter_3", u"Hunt the Dark Knight", u"chapter"),
        (u"chapter_4", u"The Dark Knight Falls", u"chapter")
    ]

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            for id, name, typ in domain:
                w.add_document(id=id, name=name, name_ngrams=name, type=typ)

        with ix.searcher() as s:
            all_parents = query.Term("type", "book")
            wanted_parents = query.Term("name", "dark")
            children_of_wanted_parents = query.NestedChildren(all_parents,
                                                              wanted_parents)

            r1 = s.search(children_of_wanted_parents)
            assert r1.scored_length() == 4
            assert [hit["id"] for hit in r1] == ["chapter_1", "chapter_2",
                                                 "chapter_3", "chapter_4"]

            wanted_children = query.And([query.Term("type", "chapter"),
                                         query.Term("name", "hunt")])

            r2 = s.search(wanted_children)
            assert r2.scored_length() == 1
            assert [hit["id"] for hit in r2] == ["chapter_3"]

            complex_query = query.And([children_of_wanted_parents,
                                       wanted_children])

            r3 = s.search(complex_query)
            assert r3.scored_length() == 1
            assert [hit["id"] for hit in r3] == ["chapter_3"]


def test_relation():
    from whoosh import analysis
    from whoosh.query.joins import RelationQuery
    from whoosh.reading import MultiReader

    sa = analysis.SimpleAnalyzer()
    schema = fields.Schema(
        id=fields.Numeric(unique=True, stored=True, column=True, signed=False),
        name=fields.Text(stored=True, analyzer=sa),
        artist=fields.Text(stored=True, analyzer=sa),
        type=fields.Id(stored=True),
        parent=fields.Numeric(stored=True, column=True, signed=False),
        sales=fields.Numeric(column=True),
    )

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(id=2, type="album", name="Back in Black",
                           artist="AC/DC", sales=50)

            w.add_document(id=11, type="song", name="Billie Jean", parent=1)
            w.add_document(id=12, type="song", name="Thriller", parent=1)
            w.add_document(id=13, type="song", name="Beat It", parent=1)

        with ix.writer(merge=False) as w:
            w.add_document(id=3, type="album", name="Blood Sugar Sex Magik",
                           artist="Red Hot Chili Peppers", sales=13)

            w.add_document(id=21, type="song", name="Hells Bells", parent=2)
            w.add_document(id=22, type="song", name="Shoot to Thrill",
                           parent=2)
            w.add_document(id=23, type="song", name="Back in Black",
                           parent=2)

        with ix.writer(merge=False) as w:
            w.add_document(id=1, type="album", name="Thriller",
                           artist="Michael Jackson", sales=65)

            w.add_document(id=31, type="song", name="Suck My Kiss",
                           parent=3)
            w.add_document(id=32, type="song", name="Give it Away",
                           parent=3)
            w.add_document(id=33, type="song", name="Under the Bridge",
                           parent=3)

        with ix.searcher() as s:
            assert isinstance(s.reader(), MultiReader)

            def ids(q):
                return " ".join(sorted(str(hit["id"]) for hit in s.search(q)))

            # Songs on albums with more than 40m in sales
            q = RelationQuery("id", query.And([
                query.Term("type", "album"),
                query.NumericRange("sales", 40, None)
            ]), "parent", query.Term("type", "song"))
            assert ids(q) == "11 12 13 21 22 23"

            # Songs with "black" in the title on albums by AC/DC
            q = RelationQuery("id", query.And([
                query.Term("type", "album"),
                query.Term("artist", "ac"),
            ]), "parent", query.Term("name", "black"))
            assert ids(q) == "23"

            # Albums containing songs with "it" in the title
            assert ids(query.Term("name", "it")) == "13 32"
            q = RelationQuery("parent", query.And([
                query.Term("type", "song"),
                query.Term("name", "it"),
            ]), "id", query.Term("type", "album"))
            assert ids(q) == "1 3"

            # Songs with sibling songs with "bridge" in the title
            # relation 1: song -> album
            q1 = RelationQuery("parent", query.And([query.Term("type", "song"),
                                                query.Term("name", "bridge")]),
                               "id", query.Term("type", "album"))
            assert ids(q1) == "3"
            # relation 2: album(s) from q1 -> songs
            q2 = RelationQuery("id", q1,
                               "parent", query.Term("type", "song"))
            assert ids(q2) == "31 32 33"



