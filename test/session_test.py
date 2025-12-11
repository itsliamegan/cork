from uuid import uuid4

from lib.session import decode, encode, Session, Sessions

def test_finds_session_by_id():
	id = uuid4()
	session = Session(id)
	sessions = Sessions()

	sessions.put(session)

	assert sessions.get(id) == session

def test_stores_values():
	id = uuid4()
	session = Session(id)

	session["message"] = "You do not have access."

	assert session["message"] == "You do not have access."

def test_encodes_and_decodes_sessions():
	id = uuid4()
	session = Session(id)
	session["message"] = "You do not have access."
	sessions = Sessions({id: session})

	encoded = encode(sessions)
	decoded = decode(encoded)

	assert decoded.get(id)["message"] == "You do not have access."
