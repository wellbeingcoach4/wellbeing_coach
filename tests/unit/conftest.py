import os
import sys
from pathlib import Path

import sqlalchemy


# Prevent imports from requiring postgres/psycopg2 during unit tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Ensure project root is importable when running pytest directly.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_real_create_engine = sqlalchemy.create_engine


def _patched_create_engine(url, *args, **kwargs):
    if str(url).startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
    return _real_create_engine(url, *args, **kwargs)


sqlalchemy.create_engine = _patched_create_engine
