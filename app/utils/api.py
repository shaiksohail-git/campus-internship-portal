"""Consistent JSON API envelope + pagination helpers.

Success:  {"success": true,  "data": {}, "message": "..."}
Error:    {"success": false, "error": {"code": "...", "message": "..."}}
"""

import math

from flask import jsonify, request

from app.config import Config
from app.utils.errors import ValidationError


def ok(data=None, message="", status=200):
    return jsonify({"success": True, "data": data, "message": message}), status


def json_body():
    """Parse request JSON; returns {} when the body is empty."""
    if not request.is_json:
        raise ValidationError("Request body must be JSON.")
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError("Request body contains invalid JSON.")
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def paginate(query, page=None, per_page=None):
    """Paginate a SQLAlchemy query; returns (items, pagination_dict)."""
    page = page or request.args.get("page", 1, type=int)
    per_page = per_page or request.args.get("limit", Config.PER_PAGE, type=int)
    page = max(page or 1, 1)
    per_page = min(max(per_page or Config.PER_PAGE, 1), 100)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(math.ceil(total / per_page), 1) if total else 0

    return items, {
        "page": page,
        "limit": per_page,
        "total": total,
        "pages": pages,
    }
