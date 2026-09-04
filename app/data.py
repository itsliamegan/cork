from typing import Any
from uuid import UUID as Id

from helios.store import types, Attribute, Model, NotFoundError, Schema

class User(Model):
	attrs = [
		Attribute("name", types.Str())
	]

class Pin(Model):
	attrs = [
		Attribute("url", types.Str()),
		Attribute("title", types.Str()),
		Attribute("board_id", types.UUID(), nullable = True),
		Attribute("user_id", types.UUID()),
	]

class Board(Model):
	attrs = [
		Attribute("title", types.Str()),
		Attribute("user_id", types.UUID()),
	]

schema = Schema([
	User,
	Pin,
	Board,
])

def find_owned(ctx, model_type: type[Model], id: Id) -> Model:
	model = ctx.store.find_one(model_type, id)
	if model.user_id != ctx.auth.user.id:
		raise NotFoundError(model_type, id)
	return model

def find_all_owned(ctx, model_type: type[Model], **attrs: dict[str, Any]) -> list[Model]:
	models = ctx.store.find_by(model_type, user_id = ctx.auth.user.id)
	owned = []
	for model in models:
		for name in attrs:
			if getattr(model, name) != attrs[name]:
				break
		else:
			owned.append(model)
	return owned
