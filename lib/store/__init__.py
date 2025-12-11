import json
from datetime import datetime, UTC
from inspect import get_annotations as get_annots
from pathlib import Path
from typing import Any
from uuid import uuid4, UUID

import lib.store.types as types
from lib.app import Component, Context

class Component(Component):
	def __init__(self, file: Path, model_types: "ModelTypes"):
		self.file = file
		self.model_types = model_types

	def before(self, ctx: Context):
		ctx.store = load(self.file, self.model_types)

	def after(self, ctx: Context):
		save(self.file, ctx.store)

class Attribute:
	def __init__(self, name: str, typ: types.Type, default: Any | None = None):
		self.name = name
		self.type = typ
		self.default = default

	def __repr__(self) -> str:
		return f"Attribute({repr(self.name)}, {repr(self.type)}, default = {repr(self.default)})"

class Model:
	attrs = []

	def __init__(self, id: UUID, created_at: datetime, attrs: dict[str, Any]):
		for attr in type(self).attrs:
			val = attrs.get(attr.name)
			if val is None:
				val = attr.default
			attrs[attr.name] = val
		self.id = id
		self.created_at = created_at
		self.attrs = attrs

	def __getattr__(self, name: str) -> Any:
		if name in self.attrs:
			return self.attrs[name]
		else:
			return super().__getattribute__(name)

	def __repr__(self) -> str:
		return f"{type(self).__name__}({repr(self.id)})"

class ModelTypes:
	def __init__(self, raw_model_types: list[type[Model]]):
		model_types = {}
		for model_type in raw_model_types:
			model_types[model_type.__name__] = model_type
		self.model_types = model_types

	def get(self, name: str) -> type[Model]:
		return self.model_types[name]

class Store:
	def __init__(self, models: dict[UUID, Model] | None = None):
		if models is None:
			models = {}
		self.models = models

	def find_all(self, model_type: type[Model]) -> list[Model]:
		models = []
		for model in self.models.values():
			if type(model) == model_type:
				models.append(model)
		return models

	def find_one(self, model_type: type[Model], id: UUID) -> Model | None:
		return self.models.get(id, None)

	def create(self, model_type: type[Model], **attrs: dict[str, Any]) -> Model:
		id = uuid4()
		created_at = datetime.now(UTC)
		model = model_type(id, created_at, attrs)
		self.models[id] = model
		return model

def load(path: Path, model_types: ModelTypes) -> Store:
	with open(path, "r") as file:
		data = json.load(file)
		store = decode(data, model_types)
		return store

def save(path: Path, store: Store):
	with open(path, "w") as file:
		data = encode(store)
		json.dump(data, file)

def encode(store: Store) -> dict[str, Any]:
	data = {}
	for id, model in store.models.items():
		model_data = {}
		model_data["_type"] = type(model).__name__
		model_data["id"] = types.UUID().encode(model.id)
		model_data["created_at"] = types.Date().encode(model.created_at)
		for attr in type(model).attrs:
			raw_attr_val = getattr(model, attr.name)
			attr_val = attr.type.encode(raw_attr_val)
			model_data[attr.name] = attr_val
		data[str(id)] = model_data
	return data

def decode(data: dict[str, Any], model_types: ModelTypes) -> Store:
	models = {}
	for model_data in data.values():
		model_type = model_types.get(model_data["_type"])
		id = types.UUID().decode(model_data["id"])
		created_at = types.Date().decode(model_data["created_at"])
		del model_data["_type"]
		del model_data["id"]
		del model_data["created_at"]
		model = model_type(id, created_at, model_data)
		models[id] = model
	return Store(models)
