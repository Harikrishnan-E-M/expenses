from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv(override=True)

from app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "1") == "1", use_reloader=False)
