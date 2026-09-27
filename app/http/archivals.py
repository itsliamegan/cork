from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Form, Rules
from helios.form.rule import Rule, RuleError
from helios.http import Headers, Request, Response, Status
from helios.routing import URLs

from app import Access, Archival, Pin, Placement, User


@dataclass(init=False)
class OneOf(Rule[str]):
	name = "one_of"
	allowed: frozenset[str]

	def __init__(self, allowed: Iterable[str]):
		self.allowed = frozenset(allowed)

	def check(self, value: str):
		if value not in self.allowed:
			raise RuleError("must be one of the allowed values")


class ArchivalForm(Form):
	rules = Rules({"section": [OneOf(["archived"])]})

	section: str | None = None


def create(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	placement = store.find_one(Placement, id)
	board = Access(store, user).find_board(placement.board_id)
	pin = store.find_one(Pin, placement.pin_id)

	Archival.archive(store, placement, user)
	flash["archived"] = {"placement_id": str(placement.id), "title": pin.title}
	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	placement = store.find_one(Placement, id)
	board = Access(store, user).find_board(placement.board_id)
	form, errors = ArchivalForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	Archival.unarchive(store, placement, user)
	board_url = urls.route("boards.show", {"id": board.id})
	if form.section is None:
		return Response.redirect(board_url)
	else:
		return Response(
			Status.FOUND,
			Headers({"Location": f"{board_url}#archived"}),
		)
