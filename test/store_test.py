from lib.store import decode, encode, types, Attribute, Model, ModelTypes, Store

class Article(Model):
	attrs = [
		Attribute("title", types.Str()),
		Attribute("unread", types.Bool(), default = True),
	]

def test_creates_model():
	store = Store()

	article = store.create(Article, title = "Intro")

	assert article.id is not None
	assert article.created_at is not None
	assert article.title == "Intro"
	assert article.unread == True

def test_finds_all_models():
	store = Store()
	store.create(Article)
	store.create(Article)

	articles = store.find_all(Article)

	assert len(articles) == 2

def test_finds_one_model():
	store = Store()
	article = store.create(Article)

	found = store.find_one(Article, article.id)

	assert found == article

def test_encodes_and_decodes_store():
	store = Store()
	article = store.create(Article, title = "Intro")

	encoded = encode(store)
	decoded = decode(encoded, ModelTypes([Article]))
	found = decoded.find_one(Article, article.id)

	assert found.id == article.id
	assert found.title == article.title
	assert found.unread == article.unread
