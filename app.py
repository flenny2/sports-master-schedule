"""
Sports Master Schedule — entry point.
Run: python app.py
"""

from flask import Flask
from app.routes import main


def create_app():
    app = Flask(__name__)
    app.register_blueprint(main)
    return app


if __name__ == "__main__":
    app = create_app()
    print("\n  Sports Master Schedule")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)
