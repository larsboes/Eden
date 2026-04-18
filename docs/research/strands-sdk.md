# Strands Agents SDK — Deep Research for EDEN Implementation

> Researched 2026-03-19 from source code, official docs, and AWS blog posts.
> This is the SOLE reference for the `strands-impl` implementer.

---

## Table of Contents

1. [Installation & Imports](#1-installation--imports)
2. [Agent() Constructor — Full Signature](#2-agent-constructor--full-signature)
3. [BedrockModel — Full Signature](#3-bedrockmodel--full-signature)
4. [@tool Decorator — Full Syntax](#4-tool-decorator--full-syntax)
5. [MCPClient — Full API](#5-mcpclient--full-api)
6. [Agent.__call__() and AgentResult](#6-agentcall-and-agentresult)
7. [Tool Config / Forcing Tool Use](#7-tool-config--forcing-tool-use)
8. [Parallel Execution & Thread Safety](#8-parallel-execution--thread-safety)
9. [Callback Handlers & Streaming](#9-callback-handlers--streaming)
10. [Error Handling](#10-error-handling)
11. [Multi-Agent Patterns](#11-multi-agent-patterns)
12. [Our Existing Code — What to Change](#12-our-existing-code--what-to-change)
13. [Implementation Plan](#13-implementation-plan)
14. [Gotchas & Pitfalls](#14-gotchas--pitfalls)

---

## 1. Installation & Imports

Already in `pyproject.toml`:
```toml
"strands-agents>=0.1",
"strands-agents-tools>=0.1",
"mcp>=1.0",
```

### Key Import Paths

```python
# Core
from strands import Agent
from strands.tools import tool                    # @tool decorator

# Models
from strands.models.bedrock import BedrockModel

# MCP
from strands.tools.mcp.mcp_client import MCPClient

# MCP transports
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client

# Callback handlers
# Pass callback_handler=None to suppress all printing
# Default is PrintingCallbackHandler (prints to stdout)

# Agent result
# agent("prompt") returns AgentResult (see section 6)
```

---

## 2. Agent() Constructor — Full Signature

**Source:** `strands/agent/agent.py` (raw GitHub)

```python
from strands import Agent

agent = Agent(
    # --- Core params ---
    model=bedrock_model,                    # Model | str | None — defaults to Bedrock
    system_prompt="You are DEMETER...",     # str | list[SystemContentBlock] | None
    tools=[read_sensors, set_actuator],     # list[str | dict | ToolProvider | Any] | None

    # --- Behavior params ---
    callback_handler=None,                  # Callable | None — None = silent (no stdout)
    conversation_manager=None,              # ConversationManager | None — default: SlidingWindow
    record_direct_tool_call=True,           # bool — record tool calls in history
    load_tools_from_directory=False,        # bool — auto-load from ./tools/

    # --- Identity params (keyword-only) ---
    agent_id=None,                          # str | None
    name="DEMETER",                         # str | None
    description="Environment specialist",   # str | None

    # --- Advanced params (keyword-only) ---
    messages=None,                          # Messages | None — pre-seed conversation
    state=None,                             # AgentState | dict | None
    plugins=None,                           # list[Plugin] | None
    hooks=None,                             # list[HookProvider] | None
    session_manager=None,                   # SessionManager | None
    structured_output_model=None,           # type[BaseModel] | None — Pydantic output
    structured_output_prompt=None,          # str | None
    tool_executor=None,                     # ToolExecutor | None
    retry_strategy=_DEFAULT_RETRY_STRATEGY, # ModelRetryStrategy | None
    trace_attributes=None,                  # Mapping[str, AttributeValue] | None
    concurrent_invocation_mode=ConcurrentInvocationMode.THROW,  # THROW = error if called in parallel
)
```

### Critical Notes for EDEN

- **`callback_handler=None`** — MUST set this for our parliament agents. Default `PrintingCallbackHandler` dumps to stdout, which will pollute server output with 12+ agent streams.
- **`system_prompt`** — Accepts a plain string. Our existing prompts (DEMETER_PROMPT, SENTINEL_PROMPT, etc.) work as-is.
- **`tools`** — Accepts a flat list. Mix local `@tool` functions and `mcp_client.list_tools_sync()` results.
- **`name`** — Optional string name for the agent (useful for logging/tracing).

---

## 3. BedrockModel — Full Signature

**Source:** `strands/models/bedrock.py` (raw GitHub)

```python
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    # --- Connection params (keyword-only) ---
    model_id="us.anthropic.claude-sonnet-4-6",  # str — Bedrock model ID
    region_name="us-west-2",                      # str | None — defaults to AWS_REGION or us-west-2
    boto_session=None,                             # boto3.Session | None — custom session
    boto_client_config=None,                       # BotocoreConfig | None
    endpoint_url=None,                             # str | None — custom endpoint (VPC/PrivateLink)

    # --- Inference params (via **model_config: BedrockConfig) ---
    max_tokens=512,                                # int | None
    temperature=0.3,                               # float | None
    top_p=None,                                    # float | None
    stop_sequences=None,                           # list[str] | None
    streaming=True,                                # bool | None — default True

    # --- Caching ---
    cache_tools=None,                              # str | None
    cache_config=None,                             # CacheConfig | None — "auto" supported

    # --- Guardrails ---
    guardrail_id=None,                             # str | None
    guardrail_version=None,                        # str | None

    # --- Extensibility ---
    additional_args=None,                          # dict | None — pass-through
    additional_request_fields=None,                # dict | None
)
```

### Relationship to Our BedrockAdapter

Our existing `eden/adapters/bedrock_adapter.py` uses raw `boto3.client("bedrock-runtime").converse()`. The Strands `BedrockModel` does the same thing internally but:
- Adds streaming support (default: True)
- Manages tool config formatting
- Handles retry logic
- Adds user-agent tracking

**Migration:** Replace `BedrockAdapter` with `BedrockModel` for Strands agents. Keep `BedrockAdapter` as fallback for non-Strands mode.

### Our StrandsAgentFactory Already Does This Right

```python
# eden/adapters/strands_adapter.py:123-138
def create_bedrock_model(self, model_id="us.anthropic.claude-sonnet-4-20250514", region_name="us-west-2"):
    from strands.models.bedrock import BedrockModel
    return BedrockModel(model_id=model_id, region_name=region_name)
```

This is correct but should add `max_tokens` and `temperature`:

```python
BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name="us-west-2",
    max_tokens=512,
    temperature=0.3,
)
```

---

## 4. @tool Decorator — Full Syntax

**Source:** `strands/tools/decorator.py` (raw GitHub)

```python
from strands.tools import tool

@tool
def read_sensors(zone_id: str) -> dict:
    """Read current sensor telemetry for a zone.

    Args:
        zone_id: The zone identifier (e.g., "alpha", "beta").

    Returns:
        dict with temperature, humidity, light, water_level.
    """
    return sensor.get_latest(zone_id).to_dict()
```

### Decorator Signature

```python
@tool                               # No-args form
@tool()                              # Empty-args form (same as above)
@tool(name="custom_name")           # Override tool name
@tool(description="Custom desc")    # Override description (else uses docstring)
@tool(inputSchema={...})            # Override input schema
@tool(context=True)                 # Inject ToolContext as first param
```

### How It Works

1. `inspect.signature()` extracts parameter names, types, and defaults
2. `docstring_parser` extracts description (excluding Args section)
3. Pydantic model is generated for input validation
4. Result is wrapped as `{"toolUseId": ..., "status": "success|error", "content": [...]}`

### Special Parameters (auto-injected, NOT part of tool schema)

- `self`, `cls` — skipped (class methods work)
- `agent` — injects the calling Agent instance
- If `context=True`: first param gets a `ToolContext` with tool metadata + agent ref

### EDEN Tool Pattern

Our existing tool functions in `agent.py` take injected dependencies (sensor, actuator, etc.) as regular params. For Strands, we need to use **closures** to capture these:

```python
from strands.tools import tool

def make_read_sensors_tool(sensor):
    @tool
    def read_sensors(zone_id: str) -> dict:
        """Read current sensor telemetry for a zone.

        Args:
            zone_id: The zone identifier (alpha, beta, gamma, delta).
        """
        zone = sensor.get_latest(zone_id)
        if zone is None:
            return {"error": f"Zone {zone_id} not found"}
        return zone.to_dict()
    return read_sensors

# Usage:
tools = [make_read_sensors_tool(sensor_port)]
```

**Alternative:** Use `functools.partial` — but the `@tool` decorator needs the function signature intact for schema extraction, so closures are safer.

### Can We Use Plain Functions?

**No.** Tools MUST be decorated with `@tool` or be MCPAgentTool instances. The decorator is what generates the tool spec (name, description, inputSchema) that gets sent to the model.

---

## 5. MCPClient — Full API

**Source:** `strands/tools/mcp/mcp_client.py` (raw GitHub)

### Constructor

```python
from strands.tools.mcp.mcp_client import MCPClient

mcp_client = MCPClient(
    transport_callable=lambda: streamablehttp_client(url, headers=headers),
    startup_timeout=30,           # int — seconds to wait for connection
    tool_filters=None,            # ToolFilters | None — filter which tools to expose
    prefix=None,                  # str | None — prefix tool names for disambiguation
    elicitation_callback=None,    # ElicitationFnT | None
    tasks_config=None,            # TasksConfig | None
)
```

### Context Manager (REQUIRED)

```python
with mcp_client:
    tools = mcp_client.list_tools_sync()
    # ... use tools
# Connection cleaned up automatically
```

Or manual:
```python
mcp_client.__enter__()  # or mcp_client.start()
# ...
mcp_client.__exit__(None, None, None)  # or mcp_client.stop(...)
```

### list_tools_sync()

```python
def list_tools_sync(
    self,
    pagination_token: str | None = None,
    prefix: str | None = None,
    tool_filters: ToolFilters | None = None,
) -> PaginatedList[MCPAgentTool]:
```

Returns a list of `MCPAgentTool` objects that can be directly passed to `Agent(tools=...)`.

### call_tool_sync() — THE 3-ARG FORM

```python
def call_tool_sync(
    self,
    tool_use_id: str,          # Unique ID for this tool invocation
    name: str,                  # Tool name as returned by list_tools_sync()
    arguments: dict[str, Any] | None = None,  # Tool input arguments
    read_timeout_seconds: timedelta | None = None,
) -> MCPToolResult:
```

**CONFIRMED: 3-argument form** — `(tool_use_id, name, arguments)`.

Our existing code in `mcp_adapter.py:129` is correct:
```python
return self._client.call_tool_sync("eden_call", resolved_name, arguments)
```

### Combining Local + MCP Tools

```python
from strands import Agent
from strands.tools import tool
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

@tool
def read_sensors(zone_id: str) -> dict:
    """Read sensor data for a zone."""
    ...

mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url, headers=headers))

with mcp_client:
    # Merge local tools + MCP tools into one flat list
    all_tools = [read_sensors] + mcp_client.list_tools_sync()

    agent = Agent(
        model=bedrock_model,
        tools=all_tools,
        system_prompt="...",
        callback_handler=None,
    )
    result = agent("Analyze the greenhouse")
```

### Our SyngentaKBAdapter Already Uses MCPClient Correctly

```python
# eden/adapters/mcp_adapter.py:173-178
self._client = MCPClient(lambda: streamablehttp_client(
    url=self._gateway_url,
    headers=headers,
))
self._client.__enter__()
self._tools = self._client.list_tools_sync()
```

This is correct. The tools from `list_tools_sync()` are `MCPAgentTool` objects that can be passed directly to `Agent(tools=...)`.

---

## 6. Agent.__call__() and AgentResult

### Invocation

```python
result = agent("Analyze greenhouse zone alpha for stress indicators")
```

### Return Type: AgentResult

```python
@dataclass
class AgentResult:
    stop_reason: StopReason     # "end_turn", "max_tokens", "cancelled", etc.
    message: Message            # dict with "role" and "content" keys
    metrics: EventLoopMetrics   # Performance data
    state: Any                  # Event loop state
    interrupts: Sequence[Interrupt] | None = None
    structured_output: BaseModel | None = None
```

### Extracting Text from AgentResult

```python
# Method 1: str() — recommended
text = str(result)

# Method 2: Direct access to message content
content_blocks = result.message.get("content", [])
text = "\n".join(
    block.get("text", "")
    for block in content_blocks
    if isinstance(block, dict) and "text" in block
)

# Method 3: For our EDEN agents (just need the text)
response_text = str(result)
```

### Stop Reasons

| Value | Meaning |
|-------|---------|
| `"end_turn"` | Normal completion |
| `"max_tokens"` | Hit token limit (truncated) |
| `"cancelled"` | agent.cancel() called |
| `"tool_use"` | Model wants to call a tool (internal, shouldn't surface) |
| `"stop_sequence"` | Hit stop sequence |
| `"content_filtered"` | Safety filter blocked |
| `"guardrail_intervention"` | Guardrail policy triggered |

---

## 7. Tool Config / Forcing Tool Use

### Current State

As of the research date, **tool_choice is NOT directly exposed** on the `Agent()` constructor. There is an open feature request ([#453](https://github.com/strands-agents/sdk-python/issues/453)).

### Workaround via BedrockModel

You can pass tool_config through `additional_request_fields` on BedrockModel:

```python
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name="us-west-2",
    additional_request_fields={
        "toolChoice": {"auto": {}}  # or {"any": {}} or {"tool": {"name": "read_sensors"}}
    },
)
```

### For EDEN

We don't need forced tool use — our agents analyze and recommend, they don't need to be forced to call specific tools. The model naturally uses tools when given a clear system prompt.

---

## 8. Parallel Execution & Thread Safety

### Running Multiple Agent() Instances in Parallel

**Yes, this works** — each Agent is independent with its own state. Use `ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

agents = {
    "DEMETER": Agent(model=model, tools=tools, system_prompt=DEMETER_PROMPT, callback_handler=None),
    "SENTINEL": Agent(model=model, tools=tools, system_prompt=SENTINEL_PROMPT, callback_handler=None),
    # ...
}

with ThreadPoolExecutor(max_workers=14) as executor:
    futures = {
        executor.submit(agent, prompt): name
        for name, agent in agents.items()
    }
    for fut in as_completed(futures):
        name = futures[fut]
        result = fut.result()  # AgentResult
        text = str(result)
```

### Thread Safety Notes

1. **Each Agent is independent** — separate conversation history, separate state. Safe to run in parallel.
2. **DO NOT call the same Agent instance from multiple threads** — `ConcurrentInvocationMode.THROW` (default) will raise an error. Each thread needs its own Agent instance.
3. **BedrockModel can be shared** — the boto3 client is thread-safe. Create one BedrockModel and pass it to multiple Agents.
4. **MCPClient tools can be shared** — the tool list from `list_tools_sync()` is a list of tool specs. The Agent copies them internally.
5. **agent.cancel()** — Thread-safe. Can be called from another thread to stop the agent loop.

### For EDEN Parliament

Our existing pattern in `agent.py` uses `ThreadPoolExecutor(max_workers=14)` to run 12+ agents in parallel. This maps directly:

```python
# Create one BedrockModel (shared, thread-safe)
model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-6", region_name="us-west-2", max_tokens=512)

# Create separate Agent per specialist (each with own state)
with ThreadPoolExecutor(max_workers=14) as executor:
    for agent_name in SPECIALISTS:
        agent = Agent(
            model=model,
            tools=specialist_tools[agent_name],
            system_prompt=SPECIALIST_PROMPTS[agent_name],
            callback_handler=None,
            name=agent_name,
        )
        fut = executor.submit(agent, context_prompt)
        ...
```

---

## 9. Callback Handlers & Streaming

### Suppressing Output (Required for EDEN)

```python
# Pass None — uses null_callback_handler internally
agent = Agent(model=model, tools=tools, callback_handler=None)
```

### Custom Callback for Event Streaming

```python
def eden_callback(**kwargs):
    """Custom callback that emits events to our EventBus."""
    if "data" in kwargs:
        event_bus.publish("agent_token", kwargs["data"])
    if "event" in kwargs:
        event = kwargs["event"]
        if "toolUse" in event:
            tool_name = event["toolUse"].get("name", "unknown")
            event_bus.publish("agent_tool_use", {"tool": tool_name})
    if kwargs.get("complete"):
        event_bus.publish("agent_complete", {})

agent = Agent(model=model, tools=tools, callback_handler=eden_callback)
```

### Streaming with stream_async

```python
async for event in agent.stream_async("Analyze the greenhouse"):
    # Process events as they arrive
    pass
```

### For EDEN

Start with `callback_handler=None` (silent). Later, add custom callback to pipe events to the EventBus for real-time dashboard updates.

---

## 10. Error Handling

### Agent Exceptions

The Agent loop is resilient — tool failures generate error results that go back to the model for recovery. The model can try alternative approaches.

### Key Exception Types

```python
try:
    result = agent("prompt")
except Exception as e:
    # Catch-all — Strands doesn't define a custom exception hierarchy
    # Most errors are:
    # - botocore.exceptions.ClientError (Bedrock throttling, auth)
    # - ConnectionError (network issues)
    # - TimeoutError (model or MCP timeout)
    logger.exception("Agent failed: %s", e)
```

### Graceful Fallback Pattern for EDEN

```python
def run_specialist_strands(agent_name, prompt, context):
    """Run a specialist via Strands Agent, fall back to raw Bedrock."""
    try:
        agent = Agent(
            model=bedrock_model,
            tools=specialist_tools,
            system_prompt=SPECIALIST_PROMPTS[agent_name],
            callback_handler=None,
            name=agent_name,
        )
        result = agent(prompt)
        return str(result)
    except ImportError:
        # Strands not installed — fall back to raw BedrockAdapter
        return bedrock_adapter.reason(prompt, context)
    except Exception:
        logger.exception("Strands agent %s failed", agent_name)
        return bedrock_adapter.reason(prompt, context)
```

---

## 11. Multi-Agent Patterns

Strands provides three built-in patterns, but **for EDEN we should use our own ThreadPoolExecutor pattern** (simpler, matches our existing code):

### Workflow (Parallel DAG)

```python
from strands.multiagent.workflow import Workflow

workflow = Workflow()
workflow.add_task("demeter", demeter_agent)
workflow.add_task("sentinel", sentinel_agent)
workflow.add_task("coordinator", coordinator_agent)

# demeter and sentinel run in parallel, coordinator waits for both
workflow.add_dependency("coordinator", "demeter")
workflow.add_dependency("coordinator", "sentinel")

result = workflow("Analyze greenhouse state")
```

### Swarm (Sequential Handoff)

```python
from strands.multiagent.swarm import Swarm

swarm = Swarm()
swarm.add_agent("researcher", researcher_agent)
swarm.add_agent("writer", writer_agent)
swarm.set_entry_agent("researcher")

result = swarm("Create a greenhouse status report")
```

### Agent-as-Tool (Hierarchical)

```python
from strands import Agent, tool

@tool
def consult_sentinel(query: str) -> str:
    """Consult the safety officer about a potential threat."""
    result = sentinel_agent(query)
    return str(result)

coordinator = Agent(
    model=model,
    tools=[consult_sentinel, consult_demeter, ...],
    system_prompt=COORDINATOR_PROMPT,
)
```

### Recommendation for EDEN

**Don't use Workflow/Swarm/Graph** — our existing `ThreadPoolExecutor` pattern is simpler and already proven. The Strands multi-agent patterns add orchestration overhead we don't need since our COORDINATOR handles conflict resolution explicitly.

---

## 12. Our Existing Code — What to Change

### Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `eden/application/agent.py` | Add Strands mode to `AgentTeam` | **P0** |
| `eden/adapters/strands_adapter.py` | Already good, add max_tokens/temp | P1 |
| `eden/adapters/bedrock_adapter.py` | Keep as-is (fallback) | None |
| `eden/adapters/mcp_adapter.py` | Already good | None |
| `pyproject.toml` | Already has strands deps | None |

### What's Already Working

1. **`StrandsAgentFactory`** (`strands_adapter.py`) — Creates `Agent` instances with model, tools, system_prompt. Already correct.
2. **`SyngentaKBAdapter`** (`mcp_adapter.py`) — Uses `MCPClient` with `streamablehttp_client`. Already correct.
3. **`NasaMCPAdapter`** (`mcp_adapter.py`) — Uses `MCPClient` with `stdio_client`. Already correct.
4. **`call_tool_sync`** signature — 3-arg form `(tool_use_id, name, arguments)`. Already correct.

### What Needs to Change

1. **Tool functions** — Current functions in `agent.py` take injected deps as params. Need to wrap with `@tool` decorator using closures.
2. **AgentTeam._run_specialist()** — Currently calls `self._model.reason(prompt, context)`. Need a Strands path that creates an Agent, invokes it, and extracts text.
3. **AgentTeam._run_flora()** — Same as above but per-zone.
4. **Callback handler** — Must use `callback_handler=None` to suppress stdout.

---

## 13. Implementation Plan

### Step 1: Create @tool-wrapped functions (new file: `eden/application/strands_tools.py`)

```python
"""Strands @tool wrappers for EDEN specialist tools.

Each function captures dependencies via closure and exposes
a clean @tool interface for the Agent.
"""
from strands.tools import tool


def make_tools(sensor, actuator, state_store, telemetry_store,
               agent_log, nutrition, flight_engine, syngenta_kb=None, nasa_mcp=None):
    """Create all @tool-decorated functions with injected dependencies."""

    @tool
    def read_sensors(zone_id: str) -> dict:
        """Read current sensor telemetry for a greenhouse zone.

        Args:
            zone_id: Zone identifier (alpha, beta, gamma, delta).
        """
        zone = sensor.get_latest(zone_id)
        return zone.to_dict() if zone else {"error": f"Zone {zone_id} offline"}

    @tool
    def read_all_zones() -> dict:
        """Read sensor telemetry for all greenhouse zones."""
        result = {}
        if hasattr(sensor, "_zones"):
            for zid, zone in sensor._zones.items():
                if zone is not None:
                    result[zid] = zone.to_dict()
        return result

    @tool
    def set_actuator_command(zone_id: str, device: str, action: str,
                             value: float, reason: str) -> str:
        """Send a command to a greenhouse actuator.

        Args:
            zone_id: Target zone (alpha, beta, gamma, delta).
            device: Device type (pump, light, fan, heater).
            action: Action to perform.
            value: Numeric value for the action.
            reason: Reason for this command.
        """
        from eden.domain.models import ActuatorCommand, DeviceType, Severity
        import uuid, time
        cmd = ActuatorCommand(
            command_id=f"agent-{uuid.uuid4().hex[:8]}",
            zone_id=zone_id, device=DeviceType(device),
            action=action, value=value, reason=reason,
            priority=Severity.MEDIUM, timestamp=time.time(),
        )
        ok = actuator.send_command(cmd)
        return "OK" if ok else "FAILED"

    @tool
    def get_desired_state(zone_id: str) -> dict:
        """Get the target environmental parameters for a zone.

        Args:
            zone_id: Zone identifier.
        """
        ds = state_store.get_desired_state(zone_id)
        return ds.to_dict() if ds else {"error": "No desired state"}

    @tool
    def get_nutritional_status() -> dict:
        """Get current crew nutritional status and deficiency risks."""
        return nutrition.get_nutritional_status()

    @tool
    def get_mars_conditions(sol: int) -> dict:
        """Get current Mars environmental conditions.

        Args:
            sol: Current mission sol (day number).
        """
        from eden.domain.mars_transform import get_mars_conditions as _gmc
        return _gmc(sol).to_dict()

    @tool
    def query_syngenta_kb(query: str) -> dict:
        """Query Syngenta crop knowledge base for agricultural guidance.

        Args:
            query: Natural language query about crops, diseases, or growing conditions.
        """
        if syngenta_kb and syngenta_kb.is_available():
            return syngenta_kb.query(query)
        return {"source": "offline", "result": "KB unavailable — use local knowledge"}

    return [read_sensors, read_all_zones, set_actuator_command,
            get_desired_state, get_nutritional_status,
            get_mars_conditions, query_syngenta_kb]
```

### Step 2: Add Strands Mode to AgentTeam

In `eden/application/agent.py`, add a `_use_strands` flag and modify `_run_specialist`:

```python
def _run_specialist_strands(self, agent_name: str, context: dict) -> list[AgentDecision]:
    """Run specialist via Strands Agent with real tool calling."""
    from strands import Agent
    from strands.models.bedrock import BedrockModel

    prompt_template = _SPECIALIST_PROMPTS.get(agent_name, "")
    mcp_section = self._format_mcp_section(context)
    prompt = (
        f"Current zones: {json.dumps(context['zones'], indent=2)}\n"
        f"Mars conditions: {json.dumps(context['mars_conditions'], indent=2)}\n"
        f"Deltas: {json.dumps(context['deltas'], indent=2)}\n"
        f"{mcp_section}"
        f"Analyze and recommend."
    )

    try:
        agent = Agent(
            model=self._strands_model,
            tools=self._strands_tools,
            system_prompt=prompt_template,
            callback_handler=None,
            name=agent_name,
        )
        result = agent(prompt)
        response_text = str(result)
    except Exception:
        logger.exception("Strands agent %s failed, falling back", agent_name)
        response_text = self._model.reason(
            f"[{agent_name}] {prompt_template}\n\n{prompt}", context
        )

    if not response_text:
        return []
    return self._parse_response(agent_name, response_text)
```

### Step 3: Initialize Strands in AgentTeam.__init__

```python
# In AgentTeam.__init__, after existing init:
self._strands_model = None
self._strands_tools = []
try:
    from strands.models.bedrock import BedrockModel
    from eden.application.strands_tools import make_tools

    self._strands_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        region_name="us-west-2",
        max_tokens=512,
        temperature=0.3,
    )
    self._strands_tools = make_tools(
        sensor=sensor, actuator=actuator,
        state_store=state_store, telemetry_store=telemetry_store,
        agent_log=agent_log, nutrition=nutrition,
        flight_engine=None,  # Add if available
        syngenta_kb=syngenta_kb, nasa_mcp=nasa_mcp,
    )
    # Add MCP tools if adapters have them
    if syngenta_kb and syngenta_kb.is_available():
        self._strands_tools.extend(syngenta_kb.list_tools())
    if nasa_mcp and nasa_mcp.is_available():
        self._strands_tools.extend(nasa_mcp.list_tools())

    self._use_strands = True
    logger.info("Strands mode ACTIVE — %d tools", len(self._strands_tools))
except ImportError:
    self._use_strands = False
    logger.info("Strands not available — using raw Bedrock")
```

### Step 4: Switch _run_specialist Based on Mode

```python
def _run_specialist(self, agent_name, context):
    if self._use_strands:
        return self._run_specialist_strands(agent_name, context)
    else:
        return self._run_specialist_raw(agent_name, context)  # existing code
```

---

## 14. Gotchas & Pitfalls

### 1. Callback Handler Default Prints to Stdout
**Problem:** Default `PrintingCallbackHandler` dumps every token to stdout.
**Fix:** Always pass `callback_handler=None` for server-side agents.

### 2. Agent Instances Are NOT Thread-Safe for Concurrent Calls
**Problem:** Default `ConcurrentInvocationMode.THROW` raises if same Agent instance called from two threads.
**Fix:** Create a NEW Agent instance per specialist per cycle (they're lightweight).

### 3. @tool Docstrings Are Mandatory
**Problem:** Tools without docstrings may get empty descriptions, confusing the model.
**Fix:** Always include a docstring with Args section for each parameter.

### 4. call_tool_sync Is 3-Arg (tool_use_id, name, arguments)
**Problem:** Previous versions may have had 2-arg form. Wrong signature = crash.
**Fix:** Our code in `mcp_adapter.py:129` already uses the correct 3-arg form. Confirmed.

### 5. BedrockModel Defaults to us-west-2 and Streaming
**Problem:** If you don't pass `region_name`, it reads `AWS_REGION` env var, then defaults to us-west-2.
**Fix:** Explicitly pass `region_name="us-west-2"` for clarity.

### 6. MCP Tools Must Be Listed Inside `with` Block
**Problem:** `list_tools_sync()` requires an active connection. Calling it after `__exit__` returns empty.
**Fix:** Our adapters call `__enter__()` in `connect()` and keep the connection alive. This is correct.

### 7. Agent Creates New Conversation Each Call (By Default)
**Problem:** Each `agent("prompt")` starts a fresh conversation. Previous context is NOT retained.
**Fix:** For EDEN this is correct — each parliament cycle is independent. No need for conversation history.

### 8. Strands Import May Fail
**Problem:** If `strands-agents` package is not installed or has version conflicts.
**Fix:** Always wrap Strands imports in try/except and fall back to raw BedrockAdapter.

### 9. Token Budget — System Prompt + Tools + Context
**Problem:** The system prompt, tool definitions, and context all count against the token budget. With 7+ tools and a long system prompt, you may hit limits.
**Fix:** Keep tool descriptions concise. Use `max_tokens=512` for responses (we parse JSON, don't need long text).

### 10. MCP Tool Names May Have Prefixes
**Problem:** When using MCPClient with `prefix="syngenta_"`, tool names get prefixed.
**Fix:** Our fuzzy matching in `_call_tool()` handles this. But be aware when debugging.

---

## Quick Reference Card

```python
# === COMPLETE EDEN Strands Agent Setup ===

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools import tool
from strands.tools.mcp.mcp_client import MCPClient

# 1. Model (shared across agents, thread-safe)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name="us-west-2",
    max_tokens=512,
    temperature=0.3,
)

# 2. Tools (create once, reuse)
@tool
def read_sensors(zone_id: str) -> dict:
    """Read sensor data for a zone."""
    ...

# 3. MCP tools (from existing adapters)
mcp_tools = syngenta_kb.list_tools() + nasa_mcp.list_tools()

# 4. Agent (create per specialist, per cycle)
agent = Agent(
    model=model,
    tools=[read_sensors] + mcp_tools,
    system_prompt=DEMETER_PROMPT,
    callback_handler=None,  # CRITICAL: suppress stdout
    name="DEMETER",
)

# 5. Invoke
result = agent("Analyze zone alpha conditions")
text = str(result)  # Extract response text

# 6. Parse (same as existing)
decisions = parse_response("DEMETER", text)
```
