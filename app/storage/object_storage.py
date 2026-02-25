from urllib.parse import urlparse
from pathlib import Path
import tempfile
import requests

def download_from_r2(file_url: str) -> Path:
    """
    Mock implementation.
    Later replace with signed R2 logic.
    """
    response = requests.get(file_url, stream=True)
    response.raise_for_status()

    # Extract extension from URL
    parsed = urlparse(file_url)
    suffix = Path(parsed.path).suffix  # e.g. ".pdf"

    print("Parsed path:", parsed.path)
    print("Detected suffix:", suffix)

    if not suffix:
        raise ValueError("Cannot determine file extension from URL")
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    print("Temp file name:", tmp_file.name)

    for chunk in response.iter_content(1024 * 1024):
        tmp_file.write(chunk)

    tmp_file.close()
    return Path(tmp_file.name)


def cleanup_temp_file(path: Path):
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass