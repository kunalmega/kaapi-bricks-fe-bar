"""Entry point — python app.py"""
import os
import uvicorn
from agent_server.app import app  # noqa

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
