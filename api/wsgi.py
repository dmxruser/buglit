import sys
import os
import logging
import traceback
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

try:
    from api.index import app
    
    # Log successful startup
    logger.info("BugLit WSGI initialized successfully", extra={
        "service": "buglit",
        "environment": "production",
        "python_path": sys.path
    })
    
except Exception as e:
    # Log any import or initialization errors
    logger.error("Failed to initialize WSGI application", extra={
        "error": str(e),
        "traceback": traceback.format_exc(),
        "service": "buglit",
        "python_path": sys.path
    })
    raise