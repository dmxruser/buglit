import sys
import logging
import traceback
from .app import create_app
from .v1.api import api_router

# Configure basic logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

try:
    # Create and configure the app
    app = create_app()
    
    # Mount API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Log startup information
    logger.info("BugLit API initialized successfully")
    
except Exception as e:
    # Log any startup errors
    logger.error(f"Fatal error during startup: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)