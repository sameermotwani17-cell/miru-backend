"""Vercel Python function entrypoint.

Vercel turns every ``.py`` file under ``api/`` into its own serverless
function, so this directory deliberately contains exactly one file. The rest
of the backend lives one level up and is imported from here, which keeps the
deployment to a single function (the Hobby plan caps you at 12).

``vercel.json`` rewrites every incoming path to this function, and Vercel
passes the original URL through, so FastAPI still matches its real routes
(``/api/session/start``, ``/api/interview/turn``, ...).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402

# Vercel's Python runtime looks for a module-level ASGI app named `app`.
__all__ = ["app"]
