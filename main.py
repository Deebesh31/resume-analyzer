"""Local development entry point for the Flask app.

Render serves app:app with Gunicorn. This file remains as a convenient local
command: python main.py
"""

from app import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
