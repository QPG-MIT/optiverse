import os
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_src_on_path():
    root = os.path.dirname(os.path.dirname(__file__))
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    yield


