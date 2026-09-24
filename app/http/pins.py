from collections import Counter
from typing import cast
from uuid import UUID

from helios import http
from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app.data import (
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
from app.views.pins.placements import PlacementOption


def _referring_board_id(
	ctx: Context,
	raw_url: str | None,
	placements: list[Placement],
) -> UUID | None:
	match = ctx.get(URLs).match(raw_url)
	if match is None or match.route.name != "boards.show":
		return None
	for placement in placements:
		if placement.board_id == match.params["id"]:
			return placement.board_id
	return None


def _pin_return_url(
	ctx: Context,
	raw_url: str | None,
	pin: Pin,
	placements: list[Placement],
) -> URL:
	urls = ctx.get(URLs)
	fallback = urls.route("pins.show", {"id": pin.id})
	match = urls.match(raw_url)
	if match is not None and match.route.name == "pins.index":
		return urls.route("pins.index")
	board_id = _referring_board_id(ctx, raw_url, placements)
	if board_id is None:
		return fallback
	try:
		find_accessible_board(ctx, board_id)
	except NotFoundError:
		return fallback
	return urls.route("boards.show", {"id": board_id})


def build_placement_options(ctx: Context) -> list[PlacementOption]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	boards = find_all_accessible_boards(ctx)
	board_ids = {board.id for board in boards}
	shares_by_board_id: dict[UUID, list[Share]] = {board.id: [] for board in boards}
	for share in store.query(Share).where_in(board_id=board_ids).all():
		shares_by_board_id[share.board_id].append(share)

	viewer_ids = {board.creator_id for board in boards}
	viewer_ids.update(
		share.user_id for shares in shares_by_board_id.values() for share in shares
	)
	users_by_id = {
		viewer.id: viewer for viewer in store.query(User).where_in(id=viewer_ids).all()
	}
	placement_options = []
	for board in boards:
		visible_user_ids = {share.user_id for share in shares_by_board_id[board.id]}
		visible_user_ids.add(board.creator_id)
		visible_user_ids.discard(user.id)
		others = [users_by_id[user_id] for user_id in visible_user_ids]
		placement_options.append(PlacementOption(board=board, others=others))
	return placement_options


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	pins = (
		store.query(Pin).where(creator_id=user.id).order_by("created_at", "desc").all()
	)
	board_counts = Counter(
		placement.pin_id
		for placement in store.query(Placement)
		.where_in(pin_id=[pin.id for pin in pins])
		.all()
	)
	pin_rows = [{"pin": pin, "board_count": board_counts[pin.id]} for pin in pins]

	return views.render(
		"pins.index",
		{
			"pin_rows": pin_rows,
			"open_in_new_tab": user.open_in_new_tab,
		},
	)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("url", parser.Required(parser.Str())),
			Field("note", parser.Optional(parser.Str())),
			Field("board_id", parser.List(parser.UUID())),
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
		note=input["note"] or "",
		creator_id=user.id,
	)
	for board in boards:
		Placement.create(store, pin, board, user)

	match = urls.match(input["return_to"])
	if (
		match is not None
		and match.route.name == "boards.show"
		and match.params["id"] in {board.id for board in boards}
	):
		return Response.redirect(urls.route("boards.show", match.params))
	else:
		return Response.redirect(urls.route("pins.index"))


def new(req: Request, ctx: Context) -> Response:
	views = ctx.get(Views)
	urls = ctx.get(URLs)

	board_id = req.url.query.get("board_id")
	if isinstance(board_id, str):
		try:
			id = UUID(board_id)
		except ValueError:
			raise http.error.NotFoundError()
		board = find_accessible_board(ctx, id)
		selected_board_ids = {board.id}
		return_to = urls.route("boards.show", {"id": board.id})
	else:
		board = None
		selected_board_ids = set()
		return_to = urls.route("pins.index")

	return views.render(
		"pins.new",
		{
			"originating_board": board,
			"placement_options": build_placement_options(ctx),
			"selected_board_ids": selected_board_ids,
			"return_to": return_to,
		},
	)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	pin = find_accessible_pin(ctx, id)
	placements = find_pin_placements(store, pin.id)
	accessible_placements = []
	accessible_boards = []
	for placement in placements:
		try:
			board = find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)
		accessible_boards.append(board)
	contextual_placement = find_contextual_placement(
		accessible_placements,
		_referring_board_id(ctx, req.referrer, accessible_placements),
	)
	adder = (
		store.find_one(User, contextual_placement.adder_id)
		if contextual_placement is not None
		else None
	)
	return views.render(
		"pins.show",
		{
			"pin": pin,
			"accessible_boards": accessible_boards,
			"creator": store.find_one(User, pin.creator_id),
			"adder": adder,
			"is_unfiled": not placements,
			"open_in_new_tab": user.open_in_new_tab,
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	views = ctx.get(Views)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)
	accessible_placements = []
	for placement in placements:
		try:
			find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)

	return views.render(
		"pins.edit",
		{
			"pin": pin,
			"placement_options": build_placement_options(ctx),
			"selected_board_ids": {
				placement.board_id for placement in accessible_placements
			},
			"return_to": _pin_return_url(ctx, req.referrer, pin, placements),
		},
	)


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
			Field("board_id", parser.List(parser.UUID())),
			Field("note", parser.Optional(parser.Str())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = set(input["board_id"])
	try:
		boards_by_id = {
			board_id: find_accessible_board(ctx, board_id) for board_id in board_ids
		}
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	return_to = _pin_return_url(ctx, input["return_to"], pin, placements)
	accessible_placements = []
	for placement in placements:
		try:
			find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)
	for placement in accessible_placements:
		if placement.board_id not in board_ids:
			store.delete(placement)
	existing_board_ids = {placement.board_id for placement in placements}
	for board_id in board_ids - existing_board_ids:
		Placement.create(store, pin, boards_by_id[board_id], user)
	pin.url = input["url"]
	pin.title = input["title"]
	pin.note = input["note"] or ""
	store.save(pin)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	urls = ctx.get(URLs)

	pin = find_owned(ctx, Pin, id)
	store.delete(pin)

	return Response.redirect(urls.route("pins.index"))
