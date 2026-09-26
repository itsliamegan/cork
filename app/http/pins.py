from collections import Counter
from typing import cast
from uuid import UUID

from helios import http
from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store
from helios.form import Form, Rules, Submission, Submissions
from helios.form.rule import Distinct
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app import Access, Board, Ownership, Pin, Placement, Share, User
from app.views.pins.placements import PlacementOption


class PinForm(Form):
	rules = Rules({"board_ids": [Distinct()]})
	messages = {"url.required": "URL must be provided."}

	title: str
	url: str
	note: str = ""
	board_ids: list[UUID] = []
	return_to: str | None = None


def _referring_board_id(
	ctx: Context,
	raw_url: str | None,
	placements: list[Placement],
) -> UUID | None:
	urls = ctx.get(URLs)

	match = urls.match(raw_url)
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

	match = urls.match(raw_url)
	if match is not None and match.route.name == "pins.index":
		return urls.route("pins.index")
	board_id = _referring_board_id(ctx, raw_url, placements)
	if board_id is None:
		return urls.route("pins.show", {"id": pin.id})
	return urls.route("boards.show", {"id": board_id})


def build_placement_options(ctx: Context) -> list[PlacementOption]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	access = Access(store, user)
	boards = access.find_boards()
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

	pins = Ownership(store, user).find_pins()
	pins.sort(key=lambda pin: pin.created_at, reverse=True)
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
		},
	)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	form, errors = PinForm.validate(req.input)
	if "board_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	access = Access(store, user)
	try:
		boards = [access.find_board(board_id) for board_id in form.board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	if errors:
		submissions.flash(errors, req.input)
		match = urls.match(form.return_to) if "return_to" not in errors else None
		if match is not None and match.route.name == "boards.show":
			query = {"board_id": str(match.params["id"])}
			return Response.redirect(urls.route("pins.new", query=query))
		else:
			return Response.redirect(urls.route("pins.new"))

	pin = store.create(
		Pin,
		title=form.title,
		url=form.url,
		note=form.note,
		creator_id=user.id,
	)
	Placement.replace(store, pin, boards, access)

	match = urls.match(form.return_to)
	if (
		match is not None
		and match.route.name == "boards.show"
		and match.params["id"] in {board.id for board in boards}
	):
		return Response.redirect(urls.route("boards.show", match.params))
	else:
		return Response.redirect(urls.route("pins.index"))


def new(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	submission = ctx.get(Submission)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	access = Access(store, user)
	board_id = req.url.query.get("board_id")
	if isinstance(board_id, str):
		try:
			id = UUID(board_id)
		except ValueError:
			raise http.error.NotFoundError()
		board = access.find_board(id)
		selected_board_ids = [board.id]
		return_to = urls.route("boards.show", {"id": board.id})
	else:
		board = None
		selected_board_ids = []
		return_to = urls.route("pins.index")

	return views.render(
		"pins.new",
		{
			"originating_board": board,
			"placement_options": build_placement_options(ctx),
			"selected_board_ids": set(
				submission.value("board_ids", selected_board_ids)
			),
			"return_to": return_to,
		},
	)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	access = Access(store, user)
	pin = access.find_pin(id)
	placements = pin.find_accessible_placements(store, access)
	boards = (
		store.query(Board)
		.where_in(id=[placement.board_id for placement in placements])
		.all()
	)
	adder = Placement.find_adder(
		store,
		placements,
		_referring_board_id(ctx, req.referrer, placements),
	)
	return views.render(
		"pins.show",
		{
			"pin": pin,
			"accessible_boards": boards,
			"creator": store.find_one(User, pin.creator_id),
			"adder": adder,
			"is_unfiled": not pin.find_placements(store),
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	submission = ctx.get(Submission)
	user = cast(User, auth.user)

	ownership = Ownership(store, user)
	access = Access(store, user)
	pin = ownership.find_pin(id)
	placements = pin.find_accessible_placements(store, access)
	selected_board_ids = [placement.board_id for placement in placements]

	return views.render(
		"pins.edit",
		{
			"pin": pin,
			"placement_options": build_placement_options(ctx),
			"selected_board_ids": set(
				submission.value("board_ids", selected_board_ids)
			),
			"return_to": _pin_return_url(
				ctx,
				req.referrer,
				pin,
				placements,
			),
		},
	)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	ownership = Ownership(store, user)
	access = Access(store, user)
	pin = ownership.find_pin(id)

	form, errors = PinForm.validate(req.input)
	if "board_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	try:
		boards = [access.find_board(board_id) for board_id in form.board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	if errors:
		submissions.flash(errors, req.input)
		return Response.redirect(urls.route("pins.edit", {"id": pin.id}))

	return_to = _pin_return_url(
		ctx,
		form.return_to,
		pin,
		pin.find_accessible_placements(store, access),
	)
	Placement.replace(store, pin, boards, access)
	pin.url = form.url
	pin.title = form.title
	pin.note = form.note
	store.save(pin)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	ownership = Ownership(store, user)
	pin = ownership.find_pin(id)
	store.delete(pin)

	return Response.redirect(urls.route("pins.index"))
