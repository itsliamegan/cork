from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import NotFoundError, Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import (
	Board,
	Pin,
	Placement,
	Share,
	User,
	find_accessible_board,
	find_accessible_pin,
	find_all_accessible_boards,
	find_contextual_placement,
	find_owned,
	find_pin_placements,
)


def _referring_board_id(
	raw_url: str | None,
	pin: Pin,
	placements: list[Placement],
) -> UUID | None:
	if not isinstance(raw_url, str):
		return None
	try:
		path = urlsplit(raw_url).path
	except ValueError:
		return None
	for placement in placements:
		if path == f"/boards/{placement.board_id}":
			return placement.board_id
	return None


def _pin_return_url(raw_url: str | None, pin: Pin, placements: list[Placement]) -> URL:
	fallback = URL(f"/pins/{pin.id}")
	if not isinstance(raw_url, str):
		return fallback
	try:
		path = urlsplit(raw_url).path
	except ValueError:
		return fallback
	if path == f"/pins/{pin.id}":
		return URL(path)
	if _referring_board_id(raw_url, pin, placements) is not None:
		return URL(path)
	return fallback


def build_board_options(ctx: Context) -> list[dict[str, Board | str]]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	boards = find_all_accessible_boards(ctx)
	board_ids = {board.id for board in boards}
	shares_by_board_id: dict[UUID, list[Share]] = {board.id: [] for board in boards}
	for share in store.find_all(Share):
		if share.board_id in board_ids:
			shares_by_board_id[share.board_id].append(share)

	viewer_ids = {board.creator_id for board in boards}
	viewer_ids.update(
		share.user_id for shares in shares_by_board_id.values() for share in shares
	)
	users_by_id = {
		user.id: user.name for user in store.find_all(User) if user.id in viewer_ids
	}
	board_options = []
	for board in boards:
		shares = shares_by_board_id[board.id]
		if not shares:
			sharing_label = "Private"
		else:
			visible_user_ids = {share.user_id for share in shares}
			if board.creator_id != auth.user.id:
				visible_user_ids.add(board.creator_id)
			visible_user_ids.discard(auth.user.id)
			viewer_names = sorted(
				(users_by_id[user_id] for user_id in visible_user_ids),
				key=str.casefold,
			)
			sharing_label = f"Shared · {", ".join(viewer_names)}"
		board_options.append({"board": board, "sharing_label": sharing_label})
	return board_options


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("url", parser.Required(parser.Str())),
			Field("note", parser.Str()),
			Field("board_id", parser.Required(parser.List(parser.UUID()))),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = list(dict.fromkeys(input["board_id"]))
	try:
		boards = [find_accessible_board(ctx, board_id) for board_id in board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	pin = store.create(
		Pin,
		title=input["title"],
		url=input["url"],
		note=input["note"],
		creator_id=user.id,
	)
	for board in boards:
		store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=user.id)

	return_to = URL(f"/boards/{boards[0].id}")
	if isinstance(input["return_to"], str):
		try:
			path = urlsplit(input["return_to"]).path
		except ValueError:
			path = ""
		if path in {f"/boards/{board.id}" for board in boards}:
			return_to = URL(path)
	return Response.redirect(return_to)


def new(req: Request, ctx: Context, id: UUID) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	board = find_accessible_board(ctx, id)
	html = views.render(
		"pins.new",
		{
			"board": board,
			"board_options": build_board_options(ctx),
			"current_user": auth.user,
		},
	)
	return Response.html(html)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	pin = find_accessible_pin(ctx, id)
	placements = find_pin_placements(store, pin.id)
	accessible_placements = []
	for placement in placements:
		try:
			find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)
	placement = find_contextual_placement(
		accessible_placements, _referring_board_id(req.referrer, pin, placements)
	)
	board = find_accessible_board(ctx, placement.board_id)
	html = views.render(
		"pins.show",
		{
			"pin": pin,
			"board": board,
			"creator": store.find_one(User, pin.creator_id),
			"current_user": user,
			"open_in_new_tab": user.open_in_new_tab,
		},
	)
	return Response.html(html)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)
	placement = find_contextual_placement(
		placements, _referring_board_id(req.referrer, pin, placements)
	)
	board = store.find_one(Board, placement.board_id)

	html = views.render(
		"pins.edit",
		{
			"pin": pin,
			"board": board,
			"board_options": build_board_options(ctx),
			"placed_board_ids": {placement.board_id for placement in placements},
			"current_user": auth.user,
			"return_to": _pin_return_url(req.referrer, pin, placements),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)

	form = Form(
		[
			Field("url", parser.Required(parser.Str())),
			Field("title", parser.Required(parser.Str())),
			Field("board_id", parser.Required(parser.List(parser.UUID()))),
			Field("note", parser.Optional(parser.Str())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = set(input["board_id"])
	try:
		[find_accessible_board(ctx, board_id) for board_id in board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	return_to = _pin_return_url(input["return_to"], pin, placements)
	existing_board_ids = {placement.board_id for placement in placements}
	for placement in placements:
		if placement.board_id not in board_ids:
			store.delete(placement.id)
	for board_id in board_ids - existing_board_ids:
		store.create(Placement, pin_id=pin.id, board_id=board_id, adder_id=user.id)
	pin.url = input["url"]
	pin.title = input["title"]
	pin.note = input["note"] or ""
	store.save(pin)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)
	raw_return_to = cast(str, req.input.items.get("return_to"))
	board_id = _referring_board_id(raw_return_to, pin, placements)
	if board_id is None:
		board_id = find_contextual_placement(placements).board_id
	return_to = URL(f"/boards/{board_id}")
	for placement in placements:
		store.delete(placement.id)
	store.delete(pin.id)

	return Response.redirect(return_to)
