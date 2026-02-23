import tempfile
import requests
from pathlib import Path

def download_from_r2(file_url: str) -> Path:
    """
    Mock implementation.
    Later replace with signed R2 logic.
    """
    response = requests.get(file_url, stream=True)
    response.raise_for_status()

    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    for chunk in response.iter_content(1024 * 1024):
        tmp_file.write(chunk)

    tmp_file.close()
    return Path(tmp_file.name)


def cleanup_temp_file(path: Path):
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass