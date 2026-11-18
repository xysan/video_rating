from datetime import date
from app.models import VideoSnapshot

EXCLUDED_UP = "善良的诚哥"
MIN_PUBLISH_DATE = date(2026, 10, 1)

def video_scope():
    return (VideoSnapshot.publish_date >= MIN_PUBLISH_DATE, VideoSnapshot.up_name != EXCLUDED_UP)
