from datetime import datetime
from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store

from app.board import Board
from app.ordering import Ordering
from app.pin import Pin
from app.placement import Placement
from app.share import Share
from app.user import User


def find_owned[T: Pin | Board](ctx: Context, model_type: type[T], id: UUID) -> T:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	model = store.find_one(model_type, id)

	if model.creator_id != user.id:
		raise NotFoundError(model_type, id)
	return model


def find_pin_placements(store: Store, pin_id: UUID) -> list[Placement]:
	return store.find_by(Placement, pin_id=pin_id)


def find_contextual_placement(
	placements: list[Placement],
	board_id: UUID | None = None,
) -> Placement | None:
	if board_id is not None:
		for placement in placements:
			if placement.board_id == board_id:
				return placement
	if not placements:
		return None
	return min(placements, key=lambda placement: str(placement.id))


def can_access_board(ctx: Context, board: Board) -> bool:
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	if board.creator_id == user.id:
		return True
	share = (
		ctx.get(Store).query(Share).where(board_id=board.id, user_id=user.id).first()
	)
	return share is not None


def find_accessible_board(ctx: Context, id: UUID) -> Board:
	board = ctx.get(Store).find_one(Board, id)
	if not can_access_board(ctx, board):
		raise NotFoundError(Board, id)
	return board


def can_remove_placement(
	ctx: Context,
	placement: Placement,
	pin: Pin,
	board: Board,
) -> bool:
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	return can_access_board(ctx, board) and user.id in {
		pin.creator_id,
		placement.adder_id,
		board.creator_id,
	}


def find_accessible_pin(ctx: Context, id: UUID) -> Pin:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	pin = store.find_one(Pin, id)
	if pin.creator_id == user.id:
		return pin
	board_ids = [placement.board_id for placement in find_pin_placements(store, pin.id)]
	owned_board = (
		store.query(Board).where_in(id=board_ids).where(creator_id=user.id).first()
	)
	share = (
		store.query(Share).where_in(board_id=board_ids).where(user_id=user.id).first()
	)
	if owned_board is None and share is None:
		raise NotFoundError(Pin, id)
	return pin


def find_all_accessible_boards(ctx: Context) -> list[Board]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	shared_board_ids = {
		share.board_id for share in store.find_by(Share, user_id=user.id)
	}
	owned_boards = store.find_by(Board, creator_id=user.id)
	shared_boards = store.query(Board).where_in(id=shared_board_ids).all()
	return [*owned_boards, *shared_boards]


def order_accessible_boards(ctx: Context, boards: list[Board]) -> list[Board]:
	def created_at(board: Board) -> datetime:
		if board.created_at is None:
			raise ValueError("cannot order an unsaved board")
		return board.created_at

	board_ids = {board.id for board in boards}
	positions = {}
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	for ordering in store.find_by(Ordering, user_id=user.id):
		if ordering.board_id not in board_ids:
			continue
		position = positions.get(ordering.board_id)
		if position is None or ordering.position < position:
			positions[ordering.board_id] = ordering.position

	unpositioned = sorted(
		(board for board in boards if board.id not in positions),
		key=created_at,
		reverse=True,
	)
	positioned = sorted(
		(board for board in boards if board.id in positions),
		key=created_at,
		reverse=True,
	)
	positioned.sort(key=lambda board: positions[board.id])

	return [*unpositioned, *positioned]
