from app import app
import os

if __name__ == "__main__":
    # Listen on all interfaces (0.0.0.0) and the port provided by Render (default 5000)
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False  # Turn off debug in production
    )
