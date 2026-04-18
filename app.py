"""
Sports Master Schedule — local dev entry point.
Run: python app.py  (uses Flask's dev server on :5000)

For production, Render / gunicorn imports `create_app` directly
from the `app` package via `app:create_app()`.
"""

from app import create_app


if __name__ == "__main__":
    flask_app = create_app()
    print("\n  Sports Master Schedule")
    print("  http://localhost:5000\n")
    flask_app.run(debug=True, port=5000)
