import secrets
from typing import cast
from uuid import UUID

from helios.auth.password import Digest
from helios.database import Model, NotFoundError, Scalar, Store

from app.user import User


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
		def check(cls, value: object):
			if not isinstance(value, cls):
				raise TypeError(f"expected a Code, got {type(value).__name__}")

		@classmethod
		def encode(cls, value: Recovery.Code) -> Scalar:
			cls.check(value)
			return value.digest.encode()

		@classmethod
		def decode(cls, value: Scalar) -> Recovery.Code:
			if not isinstance(value, str):
				raise TypeError(f"expected a string, got {type(value).__name__}")
			return cls(Digest.decode(value))

	user_id: UUID
	code: Code

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
