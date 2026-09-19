import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.memory.store import Store  # noqa: E402


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()
