"""Birthday API entry point"""

from src.app import admin_endpoints, app, endpoints, logger

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
