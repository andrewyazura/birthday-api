"""Birthday API entry point"""

from app import app, endpoints, admin_endpoints, logger

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
