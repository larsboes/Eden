# Strands SDK Multi-Agent Research Document

**Version:** strands-agents 1.30.0
**Date:** 2026-03-19
**Researcher:** Claude (RESEARCHER agent)
**Purpose:** Enable EDEN parliament migration from ThreadPoolExecutor to Strands native multi-agent patterns

---

## EXECUTIVE SUMMARY

Strands SDK 1.30.0 has **TWO first-class multi-agent patterns** built into the core SDK (NOT the tools package):

1. **`Swarm`** — Self-organizing agent teams with shared context and handoff-based coordination. Agents pass control to each other via a `handoff_to_agent()` tool. **SEQUENTIAL** execution — one agent at a time.

2. **`Graph` (via `GraphBuilder`)** — Directed graph with dependency-based execution. Supports **TRUE PARALLEL** execution of independent nodes via `asyncio.create_task`. This is the one we want.

**Critical Finding:** The `Swarm` pattern is NOT what we need for the parliament. It runs agents ONE AT A TIME with handoffs. The `Graph` pattern runs independent nodes in parallel using asyncio tasks — this is the true parallelism we're after.

---

## PATTERN 1: GRAPH (GraphBuilder) — RECOMMENDED FOR EDEN

### Import Path
```python
from strands.multiagent import GraphBuilder, GraphResult
from strands.multiagent.graph import Graph, GraphNode, GraphState, GraphEdge
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
```

### Constructor Signature (GraphBuilder)
```python
builder = GraphBuilder()
builder.add_node(executor: AgentBase | MultiAgentBase, node_id: str | None = None) -> GraphNode
builder.add_edge(from_node: str | GraphNode, to_node: str | GraphNode, condition: Callable[[GraphState], bool] | None = None) -> GraphEdge
builder.set_entry_point(node_id: str) -> GraphBuilder
builder.set_max_node_executions(max_executions: int) -> GraphBuilder
builder.set_execution_timeout(timeout: float) -> GraphBuilder
builder.set_node_timeout(timeout: float) -> GraphBuilder
builder.set_graph_id(graph_id: str) -> GraphBuilder
builder.reset_on_revisit(enabled: bool = True) -> GraphBuilder
builder.set_hook_providers(hooks: list[HookProvider]) -> GraphBuilder
graph: Graph = builder.build()
```

### Graph Constructor (internal, created by builder.build())
```python
Graph(
    nodes: dict[str, GraphNode],
    edges: set[GraphEdge],
    entry_points: set[GraphNode],
    max_node_executions: int | None = None,      # Safety limit
    execution_timeout: float | None = None,       # Total timeout seconds
    node_timeout: float | None = None,            # Per-node timeout seconds
    reset_on_revisit: bool = False,               # Reset node state on revisit
    session_manager: SessionManager | None = None,
    hooks: list[HookProvider] | None = None,
    id: str = "default_graph",
    trace_attributes: Mapping[str, AttributeValue] | None = None,
)
```

### How It Handles Parallelism — THE KEY INSIGHT

The Graph pattern uses `asyncio.create_task` for TRUE parallel execution. From `graph.py` line 706-764:

```python
async def _execute_nodes_parallel(self, nodes, invocation_state):
    event_queue: asyncio.Queue = asyncio.Queue()

    # Start ALL node streams as independent asyncio tasks
    tasks = [
        asyncio.create_task(
            self._stream_node_to_queue(node, event_queue, invocation_state)
        )
        for node in nodes
    ]

    # Consume events from queue as they arrive (real-time merging)
    while any(not task.done() for task in tasks):
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue
        if isinstance(event, Exception):
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise event
        if event is not None:
            yield event
```

**This means**: All nodes in the same "batch" (same depth level in the DAG) run as concurrent asyncio tasks. Each node's Bedrock API call runs in a separate thread (Bedrock's `_stream` method uses `asyncio.to_thread`), so we get true I/O parallelism even though Python has the GIL.

### How Agents Communicate

In the Graph pattern, output flows along edges:
- Entry point nodes receive the raw task as input
- Downstream nodes receive a formatted text containing:
  - `Original Task: <task>`
  - `Inputs from previous nodes:` with each dependency's output

The `_build_node_input()` method (line 1030-1113) constructs this.

### Dependency Resolution

Nodes execute when ALL their dependencies are satisfied (completed). The system auto-detects entry points (nodes with no dependencies). Conditional edges are supported via `condition: Callable[[GraphState], bool]`.

### Performance Characteristics

- All nodes at the same DAG depth execute truly in parallel
- Per-node timeout via `node_timeout` parameter
- Global timeout via `execution_timeout` parameter
- Max executions safety limit via `max_node_executions`
- Fail-fast: if any node fails, all other parallel nodes are cancelled immediately

### EDEN Parliament Architecture with Graph

```python
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.multiagent import GraphBuilder

# Create shared model (each Agent gets its OWN boto3 client)
def make_agent(name, prompt, tools):
    return Agent(
        model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-6", max_tokens=4096),
        tools=tools,
        system_prompt=prompt,
        callback_handler=None,  # Suppress printing
        name=name,
        description=f"{name} specialist agent",
    )

# Round 1: All 12 specialists + FLORA zones in parallel
demeter = make_agent("DEMETER", DEMETER_PROMPT, tools)
terra   = make_agent("TERRA", TERRA_PROMPT, tools)
aqua    = make_agent("AQUA", AQUA_PROMPT, tools)
# ... all 12 agents ...
coordinator = make_agent("COORDINATOR", COORDINATOR_PROMPT, tools)

builder = GraphBuilder()

# Add all specialist nodes (these will be entry points — no dependencies)
demeter_node = builder.add_node(demeter, "DEMETER")
terra_node   = builder.add_node(terra, "TERRA")
aqua_node    = builder.add_node(aqua, "AQUA")
# ... all specialists ...

# Add coordinator node
coord_node = builder.add_node(coordinator, "COORDINATOR")

# Connect all specialists -> coordinator
builder.add_edge("DEMETER", "COORDINATOR")
builder.add_edge("TERRA", "COORDINATOR")
builder.add_edge("AQUA", "COORDINATOR")
# ... all edges ...

# Configure limits
builder.set_execution_timeout(300.0)  # 5 min max
builder.set_node_timeout(120.0)       # 2 min per node
builder.set_max_node_executions(20)

graph = builder.build()

# Execute! All specialists run in parallel, then coordinator runs
result: GraphResult = graph("Analyze greenhouse zones and recommend actions")
```

### What the Graph Gives Us

1. **TRUE parallel execution** of all 12+ specialists (asyncio tasks, not ThreadPoolExecutor)
2. **Automatic dependency resolution** — coordinator only runs after ALL specialists complete
3. **Built-in timeouts** — per-node and global
4. **Fail-fast behavior** — one failure cancels all parallel nodes
5. **Event streaming** — real-time events as each agent progresses
6. **Metrics accumulation** — total token usage, latency across all nodes
7. **Session management** — serialize/deserialize state for resume

---

## PATTERN 2: SWARM — NOT RECOMMENDED FOR EDEN PARLIAMENT

### Import Path
```python
from strands.multiagent import Swarm, SwarmResult
from strands.multiagent.swarm import SwarmNode, SwarmState, SharedContext
```

### Constructor Signature
```python
Swarm(
    nodes: list[Agent],                           # List of Agent instances
    *,
    entry_point: Agent | None = None,             # Starting agent
    max_handoffs: int = 20,                       # Max handoffs between agents
    max_iterations: int = 20,                     # Max node executions
    execution_timeout: float = 900.0,             # Total timeout (15 min)
    node_timeout: float = 300.0,                  # Per-node timeout (5 min)
    repetitive_handoff_detection_window: int = 0, # Detect loops
    repetitive_handoff_min_unique_agents: int = 0,
    session_manager: SessionManager | None = None,
    hooks: list[HookProvider] | None = None,
    id: str = "default_swarm",
    trace_attributes: Mapping[str, AttributeValue] | None = None,
)
```

### How Swarm Works

1. Starts with `entry_point` agent (or first in list)
2. Each agent gets a `handoff_to_agent(agent_name, message, context)` tool injected
3. Agent runs, optionally calls `handoff_to_agent` to pass control
4. If no handoff → swarm considers task COMPLETE
5. If handoff → next agent runs with shared context
6. **SEQUENTIAL** — only ONE agent executes at a time

### Why NOT for EDEN

The Swarm is designed for "pass the baton" workflows where agents collaborate sequentially. Our parliament needs ALL 12 specialists to analyze simultaneously, then a coordinator to synthesize. That's a DAG, not a swarm.

The Swarm pattern would be useful if we wanted an interactive debugging workflow:
- SENTINEL detects anomaly → hands off to PATHFINDER
- PATHFINDER diagnoses → hands off to TERRA for soil check
- TERRA confirms → hands off to COORDINATOR for action

### Swarm Shared Context
```python
# Agents share context via SharedContext
# During handoff, context dict is stored per-node:
swarm.shared_context.add_context(node, key, value)
# Each agent receives a formatted prompt including:
# - Handoff message
# - User request
# - Previous agents history
# - Shared knowledge from previous agents
# - Available agents for collaboration
```

---

## PATTERN 3: A2A AGENT (Agent-to-Agent Protocol)

### Import Path
```python
from strands.agent.a2a_agent import A2AAgent
from strands.multiagent.a2a.server import A2AServer  # (if hosting)
from strands.multiagent.a2a.executor import StrandsA2AExecutor
```

### What It Is
A2A is a remote agent protocol. `A2AAgent` wraps a remote agent endpoint and lets you call it like a local agent. NOT needed for our use case (all agents run locally).

---

## CONFIGURING BEDROCK MODEL

### Exact Import and Constructor
```python
from strands.models.bedrock import BedrockModel
import botocore.config

model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-6",  # Global inference profile
    max_tokens=4096,        # IMPORTANT: reduce from 16384
    temperature=0.3,
    boto_client_config=botocore.config.Config(
        max_pool_connections=50,    # For 14+ concurrent agents
        read_timeout=120,           # Default is 120s
        retries={"max_attempts": 3, "mode": "adaptive"},
    ),
)
```

### Global Inference Profile
The `global.` prefix routes to the fastest available region automatically. The default model in strands-agents 1.30.0 is `us.anthropic.claude-sonnet-4-20250514-v1:0`. The prefix mapping:
- `us` → US regions
- `eu` → EU regions
- `ap` → APAC regions
- `global` → auto-routes to fastest region (WHAT WE WANT)

### CRITICAL: Each Agent Gets Its Own BedrockModel Instance

From the source code, each `Agent()` call that receives a `BedrockModel` instance uses that model's `self.client` (a single boto3 client). If you share one `BedrockModel` across 14 agents running in parallel, they all share one boto3 client with its connection pool.

**Recommendation:** Create a SEPARATE `BedrockModel` instance for each agent OR create one with a very large connection pool:

```python
# Option A: Shared model with big connection pool (simpler)
boto_config = botocore.config.Config(
    max_pool_connections=50,  # Must be >= number of concurrent agents
    read_timeout=120,
    retries={"max_attempts": 3, "mode": "adaptive"},
)
shared_model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-6",
    max_tokens=4096,
    boto_client_config=boto_config,
)

# Option B: Separate model per agent (safer, isolated failures)
def make_model():
    return BedrockModel(
        model_id="global.anthropic.claude-sonnet-4-6",
        max_tokens=4096,
        boto_client_config=botocore.config.Config(
            read_timeout=120,
            retries={"max_attempts": 3, "mode": "adaptive"},
        ),
    )
```

**Analysis:** Looking at the Graph's `_execute_nodes_parallel`, each node runs as an independent asyncio task. Each task calls `node.executor.stream_async()` which eventually calls `BedrockModel._stream()` in a separate thread via `asyncio.to_thread()`. If all agents share one BedrockModel, they share one boto3 client, but boto3 clients ARE thread-safe for concurrent requests. The key constraint is `max_pool_connections` in botocore config — it defaults to 10, which would bottleneck 14 agents.

**Verdict:** Option A (shared model with `max_pool_connections=50`) works but risks all agents dying if one Bedrock call causes an issue. Option B (separate models) is more resilient. For a hackathon, Option A is fine.

---

## MAX_TOKENS ANALYSIS

### Current Problem
Using `max_tokens=16384` means each of the 14 agents can generate up to 16K tokens of output. That's:
- 14 agents x 16K tokens = 224K output tokens per cycle
- At ~$0.015/1K output tokens = $3.36 per cycle just for output
- Plus massive latency — generating 16K tokens takes ~30-60 seconds

### Recommendation
```python
max_tokens=4096   # For specialists (they output JSON arrays, rarely >1K tokens)
max_tokens=8192   # For COORDINATOR only (needs to write longer synthesis)
```

The specialists output `[{"severity": "...", "reasoning": "...", "action": "...", "zone_id": "..."}]` — rarely exceeding 500-1000 tokens. Setting max_tokens=4096 is generous and will dramatically reduce latency.

---

## HOOK SYSTEM FOR MONITORING

### Available Hook Events for Multi-Agent
```python
from strands.hooks import (
    BeforeMultiAgentInvocationEvent,   # Before graph/swarm starts
    AfterMultiAgentInvocationEvent,    # After graph/swarm completes
    BeforeNodeCallEvent,               # Before each node executes
    AfterNodeCallEvent,                # After each node completes
    MultiAgentInitializedEvent,        # When graph/swarm is constructed
)
```

### Example: Streaming Progress to EventBus
```python
from strands.hooks import HookProvider, HookRegistry, BeforeNodeCallEvent, AfterNodeCallEvent

class ParliamentProgressHooks(HookProvider):
    def __init__(self, event_bus):
        self.event_bus = event_bus

    def register_hooks(self, registry: HookRegistry):
        registry.add_callback(BeforeNodeCallEvent, self.on_node_start)
        registry.add_callback(AfterNodeCallEvent, self.on_node_complete)

    def on_node_start(self, event: BeforeNodeCallEvent):
        self.event_bus.publish("agent_started", {
            "agent_name": event.node_id,
            "round": 1,
        })

    def on_node_complete(self, event: AfterNodeCallEvent):
        self.event_bus.publish("agent_complete", {
            "agent_name": event.node_id,
        })
```

### BeforeNodeCallEvent.cancel_node
You can cancel a node from a hook:
```python
def on_node_start(self, event: BeforeNodeCallEvent):
    if some_condition:
        event.cancel_node = "Skipping this agent due to resource constraints"
```

---

## COMPLETE EDEN PARLIAMENT IMPLEMENTATION BLUEPRINT

### Architecture: 3-Layer Graph

```
Layer 0 (Entry Points - ALL PARALLEL):
  DEMETER, TERRA, AQUA, HELIOS, ATMOS, VITA,
  HESTIA, SENTINEL, ORACLE, CHRONOS, PATHFINDER,
  FLORA-alpha, FLORA-beta, FLORA-gamma

Layer 1 (Depends on ALL Layer 0):
  COORDINATOR
```

This is a simple fan-in graph. All specialists are entry points (no dependencies). The coordinator depends on all specialists.

### Key Implementation Details

1. **Each specialist agent** needs its own `Agent` instance (Strands requires unique instances per node)
2. **The Graph auto-detects entry points** — nodes with no incoming edges become entry points
3. **Input to coordinator** is automatically built from all specialist outputs (via `_build_node_input`)
4. **reset_on_revisit** should be TRUE so agents start fresh each cycle
5. **callback_handler=None** disables the default print handler (important for parallel execution)

### Expected Performance

- **Current:** ~10 min per parliament cycle (14 agents sequential via ThreadPoolExecutor, each generating 16K tokens)
- **With Graph + reduced max_tokens:** ~30-60 seconds (14 agents truly parallel, 4K token limit)
- **Breakdown:** All 14 specialists run simultaneously (~15-30s each), then coordinator runs once (~15-30s)

### Handling the 2-Round Deliberation

The current system has 3 rounds. With the Graph pattern, there are two approaches:

**Approach A: Single Graph (simpler, recommended for hackathon)**
- Skip deliberation round (Round 2) entirely
- Just do Round 1 (all specialists parallel) → Round 3 (coordinator)
- The coordinator already has all specialist opinions to synthesize

**Approach B: Nested Graphs (preserves deliberation)**
```python
# Build a 3-layer graph:
# Layer 0: All specialists (parallel)
# Layer 1: Deliberation agents (parallel, depends on Layer 0)
# Layer 2: Coordinator (depends on Layer 1)
```

With conditional edges, you could even make the deliberation layer conditional on whether there are conflicts.

---

## BOTO3 CONNECTION POOLING FOR 14+ CONCURRENT STREAMS

### The Problem
boto3's default `max_pool_connections=10`. With 14 concurrent Bedrock streaming calls, 4 agents would block waiting for connections.

### The Solution
```python
import botocore.config

config = botocore.config.Config(
    max_pool_connections=50,     # Generously above 14
    read_timeout=120,            # Match Bedrock default
    connect_timeout=10,          # Fast failure on connection issues
    retries={
        "max_attempts": 3,       # Retry throttled requests
        "mode": "adaptive",      # Adaptive retry with backoff
    },
    tcp_keepalive=True,          # Keep connections alive
)
```

### Connection Pool Architecture
Each `BedrockModel` instance creates one `boto3.client("bedrock-runtime")`. That client has one urllib3 connection pool. The `max_pool_connections` setting controls how many simultaneous HTTP connections that pool can hold.

When using the Graph pattern:
- Each node's agent calls `BedrockModel._stream()` via `asyncio.to_thread()`
- This runs in a thread from the asyncio thread pool
- Each thread opens an HTTP connection to Bedrock
- All 14 threads need simultaneous connections

---

## WHAT DOES NOT EXIST (Confirmed by source code review)

The following DO NOT exist in strands-agents 1.30.0:
- ~~`SwarmAgent`~~ — The class is called `Swarm`, nodes are `SwarmNode`
- ~~`AgentOrchestrator`~~ — Does not exist
- ~~`AgentTeam`~~ — Not a Strands concept (this is our custom class name)
- ~~`ParallelAgent`~~ — Does not exist
- ~~`from strands import Swarm`~~ — Must use `from strands.multiagent import Swarm`
- ~~`from strands import GraphBuilder`~~ — Must use `from strands.multiagent import GraphBuilder`
- ~~Direct parallel execution in Swarm~~ — Swarm is ALWAYS sequential (one node at a time)
- ~~Shared model state between Graph nodes~~ — Each node is independent

---

## STRANDS_TOOLS.AGENT_GRAPH (DEPRECATED — DO NOT USE)

The `strands_tools.agent_graph` module is a DEPRECATED tool (it emits a deprecation warning). It uses `ThreadPoolExecutor` and a custom `AgentNode`/`AgentGraph` class with message queues. This is the OLD way of doing multi-agent in strands-tools. The NEW way is `strands.multiagent.graph.Graph`.

---

## CONCURRENCY MODE ON AGENT

Each Strands `Agent` has a `concurrent_invocation_mode` parameter:
```python
from strands.types.agent import ConcurrentInvocationMode

agent = Agent(
    ...,
    concurrent_invocation_mode=ConcurrentInvocationMode.THROW,  # default: raises if called concurrently
)
```

The Graph pattern handles this correctly — each node gets its own agent instance, so there's no concurrent invocation of the same agent. However, if you accidentally reuse the same Agent instance as two different graph nodes, you'll get a `ValueError: Duplicate node instance detected`.

---

## RETRY STRATEGY

Each Agent has a built-in retry strategy for model throttling:
```python
from strands.event_loop._retry import ModelRetryStrategy

agent = Agent(
    ...,
    retry_strategy=ModelRetryStrategy(
        max_attempts=6,     # default
        initial_delay=4.0,  # seconds
        max_delay=240.0,    # seconds
    ),
)
```

With 14 concurrent agents hitting Bedrock, throttling is likely. The adaptive retry with exponential backoff handles this automatically.

---

## SUMMARY: WHAT THE IMPLEMENTER NEEDS TO DO

1. **Replace `ThreadPoolExecutor` in `AgentTeam.analyze()`** with a `GraphBuilder`-based graph
2. **Create 14 separate `Agent` instances** (11 specialists + N FLORA zones + coordinator)
3. **Wire edges** from all specialists → coordinator
4. **Set `max_tokens=4096`** for specialists, `8192` for coordinator
5. **Set `max_pool_connections=50`** on the botocore config
6. **Set `callback_handler=None`** on all agents (parallel printing is chaos)
7. **Use hooks** to stream progress to the EventBus
8. **Consider dropping Round 2 deliberation** for simplicity — the coordinator can synthesize without it
9. **The graph is re-invocable** — call `graph(task)` each reconciliation cycle with `reset_on_revisit=True`

### Files to Modify
- `/Users/btr-dev/Documents/informatik/astrofarm/eden/application/agent.py` — Replace `AgentTeam.analyze()` internals
- No new files needed — the Strands SDK already has everything

### Key Import Block
```python
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.multiagent import GraphBuilder, GraphResult
from strands.multiagent.base import Status, NodeResult
from strands.hooks import HookProvider, HookRegistry, BeforeNodeCallEvent, AfterNodeCallEvent
import botocore.config
```
