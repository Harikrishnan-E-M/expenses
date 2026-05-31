from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv(override=True)

from app import create_app

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "1") == "1", use_reloader=False)
