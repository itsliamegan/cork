from lib.store import types, Attribute, Model, ModelTypes

class Pin(Model):
	attrs = [
		Attribute("url", types.Str()),
		Attribute("title", types.Str()),
		Attribute("hidden", types.Bool(), default = False),
	]

model_types = ModelTypes([
	Pin,
])
