"""Minimal server — isolates the crash."""
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Try importing our agent app and add its routes
    try:
        from agent_server.app import app as agent_app
        # Mount agent app routes onto main app
        from fastapi.routing import APIRoute
        for route in agent_app.routes:
            app.routes.append(route)
        logger.info("agent_server.app mounted successfully")
    except Exception as e:
        logger.error(f"agent_server.app import failed: {e}", exc_info=True)

        @app.get("/error")
        def error_info():
            return {"import_error": str(e)}

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
