import re

from sqlalchemy import func

from app.models import VideoSnapshot


def flatten(value):
    if isinstance(value, dict):
        if "value" in value:
            return flatten(value["value"])
        return flatten(value.get("text", value.get("name", "")))
    if isinstance(value, list):
        return ", ".join(filter(None, (flatten(v) for v in value)))
    return str(value) if value is not None else ""


def extract_bv(raw):
    fields = raw.get("fields", {})
    candidates = [fields.get("BV号"), fields.get("标题")]
    def find(value):
        if isinstance(value, dict):
            for item in value.values():
                result = find(item)
                if result:
                    return result
        elif isinstance(value, list):
            for item in value:
                result = find(item)
                if result:
                    return result
        elif isinstance(value, str):
            match = re.search(r"BV[0-9A-Za-z]{10}(?![0-9A-Za-z])", value)
            if match:
                return match.group()
        return None
    return next((bv for value in candidates if (bv := find(value))), None)


def field(name):
    # 只投影允许公开的 JSON 子字段，不将完整 raw_payload 带入成员查询。
    return func.json_extract(VideoSnapshot.raw_payload, '$.fields."' + name + '"').label(name)


def decode_field(value):
    import json
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value
