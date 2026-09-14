from pathlib import Path

from app.config import Config, ENV_FILE
from app.wsgi import Application

app = Application(Config.load(env_file=ENV_FILE))


def main():
	from werkzeug.serving import run_simple

	asset_files = [str(file) for file in Path("app", "assets").glob("**/*")]
	view_files = [str(file) for file in Path("app", "views").glob("**/*.html")]

	try:
		run_simple(
			"0.0.0.0",
			4000,
			app,
			use_reloader=True,
			extra_files=[*asset_files, *view_files],
			static_files={"/static": str(Path("public", "static"))},
		)
	finally:
		app.close()
