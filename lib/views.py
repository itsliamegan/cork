from jinja2 import DictLoader, Environment, select_autoescape
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from lib.app import Component, Context
from lib.http import Request

class Component(Component):
	def __init__(self, dir: Path):
		self.dir = dir
		self.engine = None

	def boot(self):
		self.engine = load(self.dir)

	def before(self, req: Request, ctx: Context):
		ctx.views = self.engine

class Views:
	def __init__(self, tmpls: dict[str, str] | None = None):
		if tmpls is None:
			tmpls = {}
		self.jinja = Environment(
			loader = DictLoader(tmpls),
			autoescape = select_autoescape
		)
		self.jinja.filters["elapsed"] = elapsed

	def render(self, name: str, assigns: dict[str, Any] | None = None) -> str:
		if assigns is None:
			assigns = {}
		tmpl = self.jinja.get_template(name)
		return tmpl.render(**assigns)

def load(views_dir: Path) -> Views:
	tmpls = {}
	for (dir, dirs, files) in views_dir.walk():
		parts = dir.relative_to(views_dir).parts
		for file in files:
			path = dir.joinpath(file)
			if path.suffix == ".html":
				name = ".".join(parts + (path.stem,))
				with open(path, "r") as stream:
					src = stream.read()
					tmpls[name] = src
	return Views(tmpls)

def elapsed(then: datetime, now: datetime = None) -> str:
	if now is None:
		now = datetime.now(UTC)
	diff = now - then
	if diff.days == 0:
		mins = diff.seconds / 60
		hours = diff.seconds / (60 * 60)
		if mins < 1:
			return "less than a minute ago"
		elif hours < 1:
			return f"{round(mins)} {pluralize("minute", round(mins))} ago"
		else:
			return f"{round(hours)} {pluralize("hour", round(hours))} ago"
	elif diff.days < 7:
		return f"{diff.days} {pluralize("day", diff.days)} ago"
	else:
		return then.strftime("%b %-d, %Y")

def pluralize(noun: str, count: int) -> str:
	if count == 1:
		return noun
	else:
		return noun + "s"
