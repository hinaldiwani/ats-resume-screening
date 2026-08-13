"""
app/api/v1/endpoints/notifications.py

Route definitions for the "notifications" resource.
No business logic yet — this is a placeholder router so the app can start
and be mounted under /api/v1/notifications once endpoints are implemented.
"""

from fastapi import APIRouter

router = APIRouter()

# Routes will be added here in the business-logic implementation phase, e.g.:
#
# @router.get("/")
# def list_notifications():
#     ...
