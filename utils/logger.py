import os
import logging
from datetime import datetime


# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create a log filename with timestamp
log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # File handler - writes to file
        logging.FileHandler(log_filename),
        # Stream handler - writes to console
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
