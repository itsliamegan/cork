from urllib.parse import urlsplit
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import (
	Board,
	Pin,
	Placement,
	User,
	find_accessible_board,
	find_accessible_pin,
	find_all_accessible_boards,
	find_owned,
	find_sole_placement,
)


def _pin_return_url(raw_url: str | None, pin: Pin, placement: Placement) -> URL:
	fallback = URL(f"/pins/{pin.id}")
	if not isinstance(raw_url, str):
		return fallback

	try:
		path = urlsplit(raw_url).path
	except ValueError:
		return fallback

	if path == f"/pins/{pin.id}":
		return URL(path)
	if path == f"/boards/{placement.board_id}":
		return URL(path)
	return fallback


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)

	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("url", parser.Required(parser.Str())),
			Field("note", parser.Str()),
			Field("board_id", parser.Required(parser.UUID())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = find_accessible_board(ctx, input["board_id"])

	pin = store.create(
		Pin,
		title=input["title"],
		url=input["url"],
		note=input["note"],
		creator_id=auth.user.id,
	)
	store.create(
		Placement,
		pin_id=pin.id,
		board_id=board.id,
		adder_id=auth.user.id,
	)

	return Response.redirect(URL(f"/boards/{board.id}"))


def new(req: Request, ctx: Context, id: UUID) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	board_id = id
	board = find_accessible_board(ctx, board_id)
	boards = find_all_accessible_boards(ctx)
	html = views.render(
		"pins.new",
		{
			"board": board,
			"board_id": board_id,
			"boards": boards,
			"current_user": auth.user,
		},
	)
	return Response.html(html)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	pin = find_accessible_pin(ctx, id)
	placement = find_sole_placement(store, pin.id)
	board = find_accessible_board(ctx, placement.board_id)
	creator = store.find_one(User, pin.creator_id)
	html = views.render(
		"pins.show",
		{
			"pin": pin,
			"board": board,
			"creator": creator,
			"current_user": auth.user,
			"open_in_new_tab": auth.user.open_in_new_tab,
		},
	)
	return Response.html(html)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	pin = find_owned(ctx, Pin, id)
	placement = find_sole_placement(store, pin.id)
	board = store.find_one(Board, placement.board_id)
	boards = find_all_accessible_boards(ctx)
	html = views.render(
		"pins.edit",
		{
			"pin": pin,
			"placement": placement,
			"board": board,
			"boards": boards,
			"current_user": auth.user,
			"return_to": _pin_return_url(req.referrer, pin, placement),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	pin = find_owned(ctx, Pin, id)
	placement = find_sole_placement(store, pin.id)

	form = Form(
		[
			Field("url", parser.Required(parser.Str())),
			Field("title", parser.Required(parser.Str())),
			Field("board_id", parser.Required(parser.UUID())),
			Field("note", parser.Optional(parser.Str())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = find_accessible_board(ctx, input["board_id"])
	return_to = _pin_return_url(input["return_to"], pin, placement)

	pin.url = input["url"]
	pin.title = input["title"]
	pin.note = input["note"] or ""
	placement.board_id = board.id
	store.save(pin)
	store.save(placement)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	pin = find_owned(ctx, Pin, id)
	placement = find_sole_placement(store, pin.id)
	board_url = URL(f"/boards/{placement.board_id}")

	store.delete(placement.id)
	store.delete(pin.id)

	return Response.redirect(board_url)
