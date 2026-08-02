"""Fetches and prepares the source painting as a numpy pixel array."""
import os
import subprocess
import urllib.request

import numpy as np
from PIL import Image, ImageFilter

from . import config


class SourceUnavailableError(RuntimeError):
    pass


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_downloaded(asset_path=None, url=None):
    asset_path = asset_path or os.path.join(_project_root(), config.ASSET_PATH)
    url = url or config.SOURCE_URL
    if os.path.exists(asset_path):
        return asset_path

    os.makedirs(os.path.dirname(asset_path), exist_ok=True)
    tmp_path = asset_path + ".tmp"
    data = None

    # Prefer curl: it uses the system CA trust store, which sidesteps
    # urllib's SSL cert-bundle issues on some macOS Python installs.
    try:
        subprocess.run(
            ["curl", "-fsSL", "--max-time", "20", "-o", tmp_path, url],
            check=True,
        )
        data = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    if data is None:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = response.read()
            with open(tmp_path, "wb") as f:
                f.write(payload)
        except Exception as exc:
            raise SourceUnavailableError(
                f"Could not download reference painting from {url}: {exc}\n"
                f"Place a copy manually at: {asset_path}"
            ) from exc

    os.replace(tmp_path, asset_path)
    return asset_path


def load_source_array(max_width=None, blur_radius=None, asset_path=None):
    max_width = max_width or config.SOURCE_MAX_WIDTH
    blur_radius = config.SOURCE_BLUR_RADIUS if blur_radius is None else blur_radius
    path = ensure_downloaded(asset_path)

    try:
        img = Image.open(path).convert("RGB")
    except Exception as exc:
        raise SourceUnavailableError(f"Could not read image at {path}: {exc}") from exc

    if img.width > max_width:
        new_h = round(img.height * (max_width / img.width))
        img = img.resize((max_width, new_h), Image.LANCZOS)

    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))

    return np.asarray(img, dtype=np.uint8)
