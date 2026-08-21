"""Zero-network smoke test: run_loop_langgraph must match run_loop on the same
scripted inputs. No LLM, no API key — a fake client returns canned responses."""

from types import SimpleNamespace

from pikaka.loop.agent import run_loop
from pikaka.loop.langgraph_agent import run_loop_langgraph


class FakeClient:
    """Scripted client: pops the next canned response off a queue."""
    def __init__(self, responses):
        self._responses = list(responses)
        self.messages = self  # client.messages.create -> self.create

    def create(self, **kw):
        return self._responses.pop(0)


class FakeTools:
    def schemas(self):
        return [{"name": "echo", "description": "echo", "input_schema": {}}]

    def execute(self, name, args, notify=None):
        return f"echo:{args.get('x')}"


def text_block(t):
    return SimpleNamespace(type="text", text=t)


def tool_use_block(name, args):
    return SimpleNamespace(type="tool_use", id="t1", name=name, input=args)


def resp(content, stop="end_turn", in_t=10, out_t=5):
    return SimpleNamespace(
        content=content,
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=in_t, output_tokens=out_t),
    )


def fresh_messages():
    return [{"role": "user", "content": "hi"}]


# Case 1: natural end, no tools
r_loop = run_loop(FakeClient([resp([text_block("Hello!")])]), "m", "sys", fresh_messages(), FakeTools())
r_lg = run_loop_langgraph(FakeClient([resp([text_block("Hello!")])]), "m", "sys", fresh_messages(), FakeTools())
assert r_loop.reply == r_lg.reply == "Hello!", (r_loop.reply, r_lg.reply)
assert r_loop.iterations == r_lg.iterations == 1, (r_loop.iterations, r_lg.iterations)

# Case 2: one tool call, then natural end
seq = [resp([tool_use_block("echo", {"x": "a"})], stop="tool_use"), resp([text_block("done")])]
r_loop = run_loop(FakeClient(seq), "m", "sys", fresh_messages(), FakeTools())
r_lg = run_loop_langgraph(FakeClient(seq), "m", "sys", fresh_messages(), FakeTools())
assert r_loop.reply == r_lg.reply == "done", (r_loop.reply, r_lg.reply)
assert r_loop.iterations == r_lg.iterations == 2, (r_loop.iterations, r_lg.iterations)
assert len(r_lg.tool_calls) == 1 and r_lg.tool_calls[0]["tool"] == "echo"
assert r_lg.tool_calls[0]["output"] == "echo:a", r_lg.tool_calls[0]

# Case 3: hard stop — the model never stops asking for tools
seq = [resp([tool_use_block("echo", {"x": "i"})], stop="tool_use") for _ in range(10)]
r_loop = run_loop(FakeClient(seq), "m", "sys", fresh_messages(), FakeTools(), max_iterations=3)
r_lg = run_loop_langgraph(FakeClient(seq), "m", "sys", fresh_messages(), FakeTools(), max_iterations=3)
assert r_loop.iterations == r_lg.iterations == 3, (r_loop.iterations, r_lg.iterations)
assert r_loop.reply == r_lg.reply, (r_loop.reply, r_lg.reply)
assert "iteration limit" in r_lg.reply

print("SMOKE OK — run_loop and run_loop_langgraph agree on all 3 cases")
