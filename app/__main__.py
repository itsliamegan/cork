from pathlib import Path
from werkzeug.serving import run_simple

from . import app

run_simple(
	"0.0.0.0",
	4000,
	app,
	use_reloader = True,
	extra_files = [str(Path("app", "assets")), str(Path("app", "views"))],
	static_files = {"/static": str(Path("public", "static"))}
)
