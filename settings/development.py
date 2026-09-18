"""Local-development settings. SQLite is the default database from base."""

import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
