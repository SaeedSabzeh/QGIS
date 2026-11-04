import io
import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services import query_point  # noqa: E402


def test_query_point_builds_intersect_query():
    fake = io.BytesIO(json.dumps({"features": []}).encode())
    with mock.patch("urllib.request.urlopen", return_value=fake) as urlopen:
        result = query_point("https://example.test/MapServer/3/", 9.19, 45.46)
    url = urlopen.call_args[0][0]
    assert url.startswith("https://example.test/MapServer/3/query?")
    assert "esriSpatialRelIntersects" in url
    assert "f=json" in url
    assert result == {"features": []}
