import html
import json

import pytest

from gradwindow.programme_adapters.api_payload import decode_api_json


@pytest.mark.parametrize("rendered", [False, True])
def test_api_json_preserves_nested_data_and_entities(rendered):
    payload = [{"title": {"rendered": "Science & Society <MSc>"}, "id": 42}]
    content = json.dumps(payload)
    if rendered:
        content = f'<html><head><meta charset="utf-8"></head><body><pre>{html.escape(content)}</pre></body></html>'
    assert decode_api_json(content) == payload


@pytest.mark.parametrize(
    "content",
    [
        "<html><body>Verify you are human<pre>[]</pre></body></html>",
        '<script type="application/json">[]</script>',
        "<pre>[]</pre><pre>[]</pre>",
        "<form><pre>[]</pre></form>",
        "<pre>Access denied</pre>",
    ],
)
def test_api_json_rejects_error_and_embedded_documents(content):
    with pytest.raises(ValueError):
        decode_api_json(content)
