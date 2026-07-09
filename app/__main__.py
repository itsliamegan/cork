from pathlib import Path
from werkzeug.serving import run_simple

from . import app

asset_files = [str(file) for file in Path("app", "assets").glob("**/*")]
view_files = [str(file) for file in Path("app", "views").glob("**/*.html")]

run_simple(
	"0.0.0.0",
	4000,
	app,
	use_reloader = True,
	extra_files = [*asset_files, *view_files],
	static_files = {"/static": str(Path("public", "static"))}
)
