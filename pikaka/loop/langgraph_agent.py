"""THE LOOP, as a compiled LangGraph — the same turn, expressed as a graph.

This is the LangGraph port of run_loop (agent.py): reason → act → observe,
drawn as nodes and conditional edges instead of a while-loop. The two
guardrails survive unchanged:

    1. model stops asking for tools  → natural end   (agent → finalize)
    2. max_iterations reached        → hard stop     (tools  → finalize)

What LangGraph buys over the hand-rolled loop: the control flow is data, not
code — you can visualise the graph, interrupt/resume at any node, and attach
per-node retries/timeouts without touching the reasoning logic. The client
(the multi-provider bridge in models.py) and the ToolRegistry are reused
verbatim, so GLM / Anthropic / etc. all keep working with zero adapters.

Signature is identical to run_loop and it returns the same LoopResult, so
app.py can switch engines with a one-line flag and fail open back to the loop.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from pikaka.loop.agent import LoopResult, Observer

# Guardrail 2's fixed reply — keep the exact string run_loop uses.
_HARD_STOP = "(I hit my iteration limit before finishing — try breaking the request into smaller steps.)"


class _AgentState(TypedDict, total=False):
    """LangGraph state for one turn. `messages` is the working memory — replaced
    wholesale at each node, mirroring the append-only list the loop maintains."""
    messages: list[dict[str, Any]]
    iterations: int
    reply: str
    has_tools: bool
    tool_calls: list[dict[str, Any]]


def run_loop_langgraph(
    client,
    model: str,
    system: str,
    messages: list[dict],
    tools,
    max_iterations: int = 10,
    max_tokens: int = 2048,
    observer: Observer | None = None,
    stream: bool = False,
) -> LoopResult:
    """LangGraph version of run_loop — same signature, same LoopResult.

    `messages` is mutated in place (reflected back at the end) exactly like
    run_loop, so callers that keep the working memory can't tell the engines
    apart. stream=True emits "text" deltas through the observer inside the
    agent node, so the dashboard still sees tokens appear live.
    """
    notify = observer or (lambda kind, ev: None)

    # Degenerate guard: `for iteration in range(1, 1)` is empty in run_loop —
    # mirror it so a nonsensical max_iterations can't cause an extra LLM call.
    if max_iterations <= 0:
        return LoopResult(reply=_HARD_STOP, iterations=0)

    can_stream = stream and hasattr(client.messages, "stream")

    # --- nodes ------------------------------------------------------------
    # Each node closes over client/system/tools/etc. — the graph carries only
    # the turn's actual state (working memory + progress), never the harness.

    def agent_node(state: _AgentState) -> dict:
        """reason: one LLM call over the current working memory."""
        response = None
        if can_stream:
            try:
                with client.messages.stream(
                    model=model, system=system, messages=state["messages"],
                    tools=tools.schemas(), max_tokens=max_tokens,
                ) as s:
                    for delta in s.text_stream:
                        notify("text", {"delta": delta})
                    response = s.get_final_message()
            except Exception:
                response = None  # any streaming hiccup → fall back to one call
        if response is None:
            response = client.messages.create(
                model=model,
                system=system,
                messages=state["messages"],
                tools=tools.schemas(),
                max_tokens=max_tokens,
            )
        iteration = state["iterations"] + 1
        notify("llm", {"iteration": iteration, "stop_reason": response.stop_reason,
                       "usage": {"in": response.usage.input_tokens, "out": response.usage.output_tokens}})

        messages = state["messages"] + [{"role": "assistant", "content": response.content}]
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text = "".join(b.text for b in response.content if b.type == "text")
        return {
            "messages": messages,
            "iterations": iteration,
            "reply": text,  # the reply IF this turns out to be the last step
            "has_tools": bool(tool_uses),
        }

    def tools_node(state: _AgentState) -> dict:
        """act + observe: run every requested tool, feed results back."""
        tool_calls = list(state["tool_calls"])
        tool_results = []
        for call in state["messages"][-1]["content"]:
            if getattr(call, "type", "") != "tool_use":
                continue
            output = tools.execute(call.name, call.input, notify=notify)
            event = {"tool": call.name, "args": call.input, "output": output}
            tool_calls.append(event)
            notify("tool", event)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": output}
            )
        messages = state["messages"] + [{"role": "user", "content": tool_results}]
        return {"messages": messages, "tool_calls": tool_calls}

    def finalize(state: _AgentState) -> dict:
        """Pick the turn's reply: the natural answer, or the hard-stop message."""
        return {"reply": _HARD_STOP if state["has_tools"] else state["reply"]}

    # --- routing ----------------------------------------------------------
    def route_after_agent(state: _AgentState) -> str:
        # guardrail 1: no tool request → the model is talking to the human
        return "tools" if state["has_tools"] else "finalize"

    def route_after_tools(state: _AgentState) -> str:
        # guardrail 2: keep looping only while under max_iterations
        return "agent" if state["iterations"] < max_iterations else "finalize"

    # --- build & run ------------------------------------------------------
    graph = StateGraph(_AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "finalize": "finalize"})
    graph.add_conditional_edges("tools", route_after_tools, {"agent": "agent", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    # The graph is rebuilt per call (it closes over this turn's client/tools),
    # so compile here — it's microseconds and keeps run_loop_langgraph a drop-in.
    final_state = graph.compile().invoke(
        {
            "messages": messages,
            "iterations": 0,
            "reply": "",
            "has_tools": False,
            "tool_calls": [],
        },
        config={"recursion_limit": max(100, max_iterations * 3 + 5)},
    )

    # run_loop mutates `messages` in place; mirror that contract.
    messages[:] = final_state["messages"]

    return LoopResult(
        reply=final_state["reply"],
        tool_calls=final_state["tool_calls"],
        iterations=final_state["iterations"],
    )
