import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import List, Union
from dotenv import load_dotenv
from app.constants import ROUND_TABLE_HOTKEY

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(".env")

# Path to store TOLERANCE_OFFSET
TOLERANCE_OFFSET_FILE = Path("tolerance_offset.json")
EXECUTOR_ENABLED_FILE = Path("executor_enabled.json")

def load_tolerance_offset() -> Union[float, str]:
    """Load TOLERANCE_OFFSET from file, return default if file doesn't exist."""
    if TOLERANCE_OFFSET_FILE.exists():
        try:
            with open(TOLERANCE_OFFSET_FILE, 'r') as f:
                data = json.load(f)
                value = data.get("tolerance_offset", 0.001)
                # Convert to float if it's a number string, otherwise keep as string
                if isinstance(value, str) and not value.startswith('*'):
                    try:
                        return float(value)
                    except ValueError:
                        return value
                return value
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading tolerance_offset from file: {e}")
            return 0.001
    return 0.001

def save_tolerance_offset(value: Union[float, str]) -> bool:
    """Save TOLERANCE_OFFSET to file."""
    try:
        with open(TOLERANCE_OFFSET_FILE, 'w') as f:
            json.dump({"tolerance_offset": value}, f)
        return True
    except IOError as e:
        print(f"Error saving tolerance_offset to file: {e}")
        return False



def read_executor_enabled() -> bool:
    """True if executor_enabled.json has \"enabled\": true. Default True if file missing."""
    path = REPO_ROOT / EXECUTOR_ENABLED_FILE
    if not path.is_file():
        return True
    try:
        with open(path) as f:
            return json.load(f).get("enabled", True)
    except Exception:
        return True


def set_executor_enabled(enabled: bool) -> None:
    """Write executor_enabled.json. Raises on IO error."""
    path =  REPO_ROOT / EXECUTOR_ENABLED_FILE
    with open(path, "w") as f:
        json.dump({"enabled": enabled}, f)



class Settings(BaseModel):
    VERSION: str = "1.1.0"
    NETWORK: str = os.getenv("NETWORK", "ws://127.0.0.1:9944")
    #NETWORK: str = "ws://161.97.128.68:9944"

    # WALLET_NAMES: List[str] = []
    # DELEGATORS: List[str] = []
    DEFAULT_RATE_TOLERANCE: float = 0.005
    DEFAULT_MIN_TOLERANCE: bool = False
    DEFAULT_RETRIES: int = 1
    DEFAULT_DEST_HOTKEY: str = ROUND_TABLE_HOTKEY
    USE_ERA: bool = os.getenv("USE_ERA", "false").lower() == "true"
    
    # WALLET_NAMES: List[str] = os.getenv("WALLET_NAMES", "").split(",")
    # DELEGATORS: List[str] = os.getenv("DELEGATORS", "").split(",")
    WALLET_NAMES: List[str] = ["soon", "soon_2"]
    DELEGATORS: List[str] = [
        "5GF98kTXSaGPRE5wMJfjqZ5kooMMzvZRpbaQ7YEawxaCQyZk",
        "5H3MFE2fg4FTRRcReET1uzAVLLzVBeJnzxgHw63nZxtGwWtk",
    ]
    
    ADMIN_HASH: str = "$2b$12$CqCJKab8CIgqnPU/.eT41.kzdl4d6a3/Vx70R50GAom7Im0tjGemm"
    TOLERANCE_OFFSET: Union[float, str] = load_tolerance_offset()
    EXECUTOR_ENABLED: bool = read_executor_enabled()

settings = Settings()