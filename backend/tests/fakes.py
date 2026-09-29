"""Stand-ins for the LangChain models, so tests never touch the network."""


class FakeClassifier:
    """Mimics the structured-output runnable returned by get_classifier_llm()."""

    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.exc:
            raise self.exc
        return self.result


class Chunk:
    """Mimics an AIMessageChunk: only `.content` is read by the router."""

    def __init__(self, content):
        self.content = content


class FakeChat:
    """Mimics the chat model returned by get_chat_llm()."""

    def __init__(self, chunks=(), fail_before_first=False, fail_after=None):
        self.chunks = list(chunks)
        self.fail_before_first = fail_before_first
        self.fail_after = fail_after
        self.calls = []

    def astream(self, messages):
        self.calls.append(messages)

        async def gen():
            if self.fail_before_first:
                raise ConnectionError("upstream down")
            for i, content in enumerate(self.chunks):
                if self.fail_after is not None and i == self.fail_after:
                    raise ConnectionError("dropped mid-stream")
                yield Chunk(content)

        return gen()
