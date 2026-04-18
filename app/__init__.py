"""
Flask application factory.

Gunicorn/Render import this as `app:create_app()`. The top-level
`app.py` wrapper still works for `python app.py` local dev.
"""

from flask import Flask


def create_app():
    flask_app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )
    # Import here to avoid circular imports — routes.py imports from
    # this package.
    from app.routes import main
    flask_app.register_blueprint(main)
    return flask_app
