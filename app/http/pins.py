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

from app import Access, Ownership, Pin, Placement, User
from app.access import NotPermitted
from app.views.pins.placements import PlacementOption


class PinForm(Form):
	rules = Rules({"board_ids": [Distinct()]})

	title: str
	url: str | None = None
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
	auth = ctx.get(Authenticator[User])

	access = Access(store, auth.user)
	boards = access.find_boards()
	store.load(boards, "creator", "shares.user")
	placement_options = []
	for board in boards:
		viewers = [board.creator, *(share.user for share in board.shares)]
		others = [viewer for viewer in viewers if viewer.id != auth.user.id]
		placement_options.append(PlacementOption(board=board, others=others))
	return placement_options


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)

	pins = Ownership(store, auth.user).find_pins()
	pins.sort(key=lambda pin: pin.created_at, reverse=True)
	board_counts = (
		store.query(Placement)
		.where({"pin.creator_id": auth.user.id})
		.count_by("pin_id")
	)
	pin_rows = [
		{"pin": pin, "board_count": board_counts.get(pin.id, 0)} for pin in pins
	]

	return views.render(
		"pins.index",
		{
			"pin_rows": pin_rows,
		},
	)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)

	form, errors = PinForm.validate(req.input)
	if "board_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	access = Access(store, auth.user)
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

	Pin.create(
		store,
		access,
		title=form.title,
		url=form.url,
		note=form.note,
		boards=boards,
	)

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
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)
	submission = ctx.get(Submission)
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	board_id = req.url.query.first("board_id")
	if board_id is not None:
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
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	store.load(pin, "creator", "placements")
	placements = pin.find_accessible_placements(store, access)
	store.load(placements, "board")
	adder = Placement.find_adder(
		store,
		placements,
		_referring_board_id(ctx, req.referrer, placements),
	)
	return views.render(
		"pins.show",
		{
			"access": access,
			"pin": pin,
			"accessible_boards": [placement.board for placement in placements],
			"adder": adder,
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)
	submission = ctx.get(Submission)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	if not pin.is_editable_by(access):
		raise NotPermitted(pin)
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
	auth = ctx.get(Authenticator[User])
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	pin = access.find_pin(id)

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
	pin.edit(
		store,
		access,
		title=form.title,
		url=form.url,
		note=form.note,
		boards=boards,
	)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	pin.delete(store, access)

	return Response.redirect(urls.route("pins.index"))
