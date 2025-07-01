import webbrowser
import threading
from app import app  # assuming `app` is your Flask app instance

PORT = 5000  # or whatever port you use

def open_browser():
    webbrowser.open_new(f"http://127.0.0.1:{PORT}/")

if __name__ == "__main__":
    # Launch the browser in a separate thread after a short delay
    threading.Timer(0, open_browser).start()
    app.run(debug=True, port=PORT)
