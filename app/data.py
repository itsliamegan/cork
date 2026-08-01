from helios.store import types, Attribute, Model, Schema

class User(Model):
	attrs = [
		Attribute("name", types.Str())
	]

class Pin(Model):
	attrs = [
		Attribute("url", types.Str()),
		Attribute("title", types.Str()),
		Attribute("board_id", types.UUID(), nullable = True),
	]

class Board(Model):
	attrs = [
		Attribute("title", types.Str()),
	]

schema = Schema([
	User,
	Pin,
	Board,
])
