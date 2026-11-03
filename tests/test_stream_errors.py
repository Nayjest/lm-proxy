import json

from lm_proxy.base_types import ChatCompletionRequest, RequestContext
from lm_proxy.bootstrap import bootstrap
from lm_proxy.config import Config
from lm_proxy.core import process_stream


async def llm_failing(_prompt, callback=None, **_kwargs):
    raise RuntimeError("upstream failed")


async def test_stream_error_chunk_carries_exception_message_and_type():
    bootstrap(Config(connections={}))
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hi"}], stream=True
    )
    ctx = RequestContext(request=request)
    chunks = [c async for c in process_stream(llm_failing, request, ctx)]
    errors = [json.loads(c.removeprefix("data: "))["error"] for c in chunks if '"error": {' in c]
    assert errors == [{"message": "upstream failed", "type": "RuntimeError"}]
