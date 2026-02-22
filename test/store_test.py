from lib.store import decode, encode, types, Attribute, Model, ModelError, ModelTypes, Store

from uuid import uuid4

class Article(Model):
	attrs = [
		Attribute("title", types.Str()),
		Attribute("subtitle", types.Str(), nullable = True),
		Attribute("unread", types.Bool(), default = True),
		Attribute("author_id", types.UUID(), default = uuid4()),
	]

def test_creates_model():
	store = Store()

	article = store.create(Article, title = "Intro")

	assert article.id is not None
	assert article.created_at is not None
	assert article.title == "Intro"
	assert article.unread == True

def test_doesnt_create_model_with_missing_attr():
	store = Store()

	try:
		store.create(Article)
		assert False
	except ModelError:
		pass

def test_finds_all_models():
	store = Store()
	store.create(Article, title = "Intro")
	store.create(Article, title = "Re: Intro")

	articles = store.find_all(Article)

	assert len(articles) == 2

def test_finds_one_model():
	store = Store()
	article = store.create(Article, title = "Intro")

	found = store.find_one(Article, article.id)

	assert found == article

def test_finds_model_by_attrs():
	store = Store()
	store.create(Article, title = "Intro", unread = False)
	store.create(Article, title = "Re: Intro", unread = True)
	store.create(Article, title = "Re: Re: Intro", unread = True)

	found = store.find_by(Article, unread = True)

	assert len(found) == 2

def test_encodes_and_decodes_store():
	store = Store()
	article = store.create(Article, title = "Intro")

	encoded = encode(store)
	decoded = decode(encoded, ModelTypes([Article]))
	found = decoded.find_one(Article, article.id)

	assert found.id == article.id
	assert found.title == article.title
	assert found.unread == article.unread

def test_encodes_and_decodes_attrs_with_complex_types():
	store = Store()
	article = store.create(Article, title = "Intro")

	encoded = encode(store)
	decoded = decode(encoded, ModelTypes([Article]))
	found = decoded.find_one(Article, article.id)

	assert found.author_id == article.author_id

def test_encodes_and_decodes_nullable_attrs():
	store = Store()
	article = store.create(Article, title = "Intro")

	encoded = encode(store)
	decoded = decode(encoded, ModelTypes([Article]))
	found = decoded.find_one(Article, article.id)

	assert found.subtitle == None
