from lib.store import types, Attribute, Model, ModelTypes

class Pin(Model):
	attrs = [
		Attribute("url", types.Str()),
		Attribute("title", types.Str()),
		Attribute("hidden", types.Bool(), default = False),
		Attribute("board_id", types.UUID(), nullable = True),
	]

class Board(Model):
	attrs = [
		Attribute("title", types.Str()),
	]

model_types = ModelTypes([
	Pin,
	Board,
])
