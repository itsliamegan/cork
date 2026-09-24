from datetime import UTC, datetime, timedelta
import secrets
from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.auth.password import Digest
from helios.database import Model, NotFoundError, Scalar, Store, attr
from helios.http import URL


class User(Model):
	table = "users"

	name = attr(str)
	open_in_new_tab = attr(bool, default=False)


class Recovery(Model):
	table = "recoveries"

	class Code:
		ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
		LENGTH = 16

		def __init__(self, digest: Digest, plaintext: str | None = None):
			self.digest = digest
			self.plaintext = plaintext

		@classmethod
		def generate(cls) -> Recovery.Code:
			plaintext = "".join(secrets.choice(cls.ALPHABET) for _ in range(cls.LENGTH))
			return cls(Digest.generate(plaintext), plaintext)

		def matches(self, candidate: str) -> bool:
			return self.digest.matches(candidate)

		@classmethod
		def check(cls, val: object):
			if not isinstance(val, cls):
				raise TypeError(f"expected a Code, got {type(val).__name__}")

		@classmethod
		def encode(cls, val: Recovery.Code) -> Scalar:
			cls.check(val)
			return val.digest.encode()

		@classmethod
		def decode(cls, val: Scalar) -> Recovery.Code:
			if not isinstance(val, str):
				raise TypeError(f"expected a string, got {type(val).__name__}")
			return cls(Digest.decode(val))

	user_id = attr(UUID)
	code = attr(Code)

	@classmethod
	def create(cls, store: Store, user: User) -> Recovery:
		code = cls.Code.generate()
		while cls.find_by_code(store, cast(str, code.plaintext)) is not None:
			code = cls.Code.generate()
		for recovery in store.find_by(cls, user_id=user.id):
			store.delete(recovery)
		return store.create(
			cls,
			user_id=user.id,
			code=code,
		)

	@classmethod
	def redeem(cls, store: Store, code: str) -> tuple[User, Recovery] | None:
		recovery = cls.find_by_code(store, code)
		if recovery is None:
			return None
		try:
			user = store.find_one(User, recovery.user_id)
		except NotFoundError:
			return None
		new_recovery = cls.create(store, user)
		return user, new_recovery

	@classmethod
	def find_by_code(cls, store: Store, code: str) -> Recovery | None:
		for recovery in store.find_all(cls):
			if recovery.code.matches(code):
				return recovery
		return None

	@classmethod
	def find_owned(cls, store: Store, id: UUID, user: User) -> Recovery:
		recovery = store.find_one(cls, id)
		if recovery.user_id != user.id:
			raise NotFoundError(cls, id)
		return recovery


class Invite(Model):
	table = "invites"

	class Token:
		def __init__(self, value: str):
			self.value = value

		@classmethod
		def generate(cls) -> Invite.Token:
			return cls(secrets.token_urlsafe(32))

		@classmethod
		def check(cls, val: object):
			if not isinstance(val, cls):
				raise TypeError(f"expected a Token, got {type(val).__name__}")

		@classmethod
		def encode(cls, val: Invite.Token) -> Scalar:
			cls.check(val)
			return val.value

		@classmethod
		def decode(cls, val: Scalar) -> Invite.Token:
			if not isinstance(val, str):
				raise TypeError(f"expected a string, got {type(val).__name__}")
			return cls(val)

	token = attr(Token)
	creator_id = attr(UUID)
	target_id = attr(UUID, nullable=True)
	expires_at = attr(datetime)

	@classmethod
	def create(
		cls,
		store: Store,
		creator: User,
		*,
		target: User | None = None,
	) -> Invite:
		token = cls.Token.generate()
		duration = timedelta(hours=24) if target is not None else timedelta(days=7)
		expires_at = datetime.now(UTC) + duration
		return store.create(
			cls,
			token=token,
			creator_id=creator.id,
			target_id=target.id if target is not None else None,
			expires_at=expires_at,
		)

	@classmethod
	def find_valid(cls, store: Store, token: str) -> Invite | None:
		invite = store.query(cls).where(token=cls.Token(token)).first()
		if invite is None or invite.expires_at <= datetime.now(UTC):
			return None
		return invite

	@classmethod
	def find_created_by(cls, store: Store, id: UUID, creator: User) -> Invite:
		invite = store.find_one(cls, id)
		if invite.creator_id != creator.id:
			raise NotFoundError(cls, id)
		return invite

	def find_target(self, store: Store) -> User | None:
		if self.target_id is None:
			return None
		else:
			return store.find_one(User, self.target_id)

	def redeem(self, store: Store, name: str) -> User:
		if self.target_id is not None:
			user = store.find_one(User, self.target_id)
		else:
			user = store.create(User, name=name)
		store.delete(self)
		return user


class Pin(Model):
	table = "pins"

	url = attr(str)
	title = attr(str)
	note = attr(str, default="")
	creator_id = attr(UUID)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url


class Board(Model):
	table = "boards"

	title = attr(str)
	creator_id = attr(UUID)


class Placement(Model):
	table = "placements"

	pin_id = attr(UUID)
	board_id = attr(UUID)
	adder_id = attr(UUID)
	position = attr(int, default=0)

	@classmethod
	def create(
		cls,
		store: Store,
		pin: Pin,
		board: Board,
		adder: User,
	) -> Placement:
		duplicate = store.query(cls).where(pin_id=pin.id, board_id=board.id).first()
		if duplicate is not None:
			raise ValueError(f"Pin {pin.id} is already placed on Board {board.id}")
		return store.create(
			cls,
			pin_id=pin.id,
			board_id=board.id,
			adder_id=adder.id,
		)


class Share(Model):
	table = "shares"

	board_id = attr(UUID)
	user_id = attr(UUID)


class Ordering(Model):
	table = "orderings"

	user_id = attr(UUID)
	board_id = attr(UUID)
	position = attr(int)


models = [
	User,
	Recovery,
	Invite,
	Pin,
	Board,
	Placement,
	Share,
	Ordering,
]


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
