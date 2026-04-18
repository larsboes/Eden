# EDEN Multi-Agent Architecture — Strands SDK

5 real agents, each a separate Strands Agent instance with its own system prompt and tools. NOT personas in one prompt — genuine multi-agent with independent reasoning.

## Why Real Multi-Agent

- AWS judge will inspect tool calls. Separate agents = separate invocations = visible in AgentCore Observability.
- Each agent has DIFFERENT tools. SENTINEL has solar event tools. AQUA has resource chain tools. They can't access each other's tools.
- Council debate is real: SENTINEL's output becomes ORACLE's input. ORACLE's output becomes AQUA's input. Each step is a separate LLM call with context from the previous agent.
- Strands SDK `agent-workflows` repo has exactly this pattern.

## Agent Definitions

### SENTINEL — Threat Detection

```python
from strands import Agent
from strands.models import BedrockModel

SENTINEL_PROMPT = """You are SENTINEL, the threat detection agent for the EDEN Mars greenhouse.
Your job: detect threats, assess risk, and alert the council.
You speak first on any alert. You are direct, precise, urgent when needed.
Use BBCH codes for crop growth stages. Reference Syngenta KB for stress thresholds.
Always calculate: what is the risk to each crop at its CURRENT growth stage?"""

sentinel = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-6-v1:0"),
    tools=[get_solar_events, read_sensors, query_syngenta_kb, trigger_alert],
    system_prompt=SENTINEL_PROMPT
)
```

### ORACLE — Simulation & Strategy

```python
ORACLE_PROMPT = """You are ORACLE, the simulation engine for the EDEN Mars greenhouse.
Your job: run strategy comparisons, predict outcomes, propose new flight rules.
When given a threat, generate 3 strategies (do nothing, standard, pre-emptive).
For each strategy, query the Syngenta KB for crop stress thresholds and reason about outcomes.
Output structured comparisons: strategy name, predicted crop loss %, resource cost, recovery time.
After real events, compare predicted vs actual and propose flight rule improvements."""

oracle = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-6-v1:0"),
    tools=[run_simulation, query_syngenta_kb, propose_flight_rule],
    system_prompt=ORACLE_PROMPT
)
```

### AQUA — Resource Guardian

```python
AQUA_PROMPT = """You are AQUA, the resource guardian for the EDEN Mars greenhouse.
Your job: manage the water/energy chain (solar → power → desalination → water → crops).
Every liter is accounted for. Every watt matters.
When given a threat + strategy, calculate: water budget, power allocation, storm autonomy.
Use precise numbers. Show the math. Report feasibility."""

aqua = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-6-v1:0"),
    tools=[calculate_resource_chain, execute_pre_storm_protocol, set_actuator, read_sensors],
    system_prompt=AQUA_PROMPT
)
```

### FLORA — Crop Advocate

```python
FLORA_PROMPT = """You are FLORA, the crop advocate for the EDEN Mars greenhouse.
Your job: optimize growth, argue for plant survival, know every crop by growth stage.
You speak like a seasoned farmer. You know these plants personally.
Use BBCH codes. Reference Syngenta KB for growth parameters.
Use professional ag vocabulary: VPD, EC, DLI, PAR, root zone temp.
When a crisis hits, you assess which crops can be saved and which must be sacrificed."""

flora = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-6-v1:0"),
    tools=[read_sensors, query_syngenta_kb, set_actuator, get_nutritional_status],
    system_prompt=FLORA_PROMPT
)
```

### VITA — Crew Nutritionist & Conscience

```python
VITA_PROMPT = """You are VITA, the crew nutritionist and ethical conscience for EDEN.
Your job: translate every crop decision into HUMAN IMPACT.
You track dietary balance, crew preferences, morale. You never let a triage decision pass
without stating its cost to the crew.

Crew:
- Cmdr. Chen: prefers lettuce, calorie target 2,850 kcal/day
- Dr. Okonkwo: vegetarian, prefers lentil soup, 2,700 kcal/day
- Eng. Volkov: higher calorie need (EVA), prefers potato, 3,300 kcal/day
- Spc. Reyes: botanist, prefers spinach, 2,850 kcal/day

Food is emotional, not just caloric. State the human cost of every decision."""

vita = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-6-v1:0"),
    tools=[get_nutritional_status, calculate_triage, query_syngenta_kb],
    system_prompt=VITA_PROMPT
)
```

## Council Orchestrator

The orchestrator is NOT an LLM. It's deterministic Python code that sequences the agents.

```python
import json
from datetime import datetime

class CouncilOrchestrator:
    """Sequences agent calls for council sessions. Deterministic flow, not LLM."""

    def __init__(self, sentinel, oracle, aqua, flora, vita, flight_rules, log_callback):
        self.sentinel = sentinel
        self.oracle = oracle
        self.aqua = aqua
        self.flora = flora
        self.vita = vita
        self.flight_rules = flight_rules
        self.log = log_callback  # writes to DynamoDB / dashboard stream

    def check_flight_rules(self, sensor_data):
        """Layer 0: Deterministic rules. Execute BEFORE any agent reasoning."""
        triggered = []
        for rule in self.flight_rules:
            if self.evaluate_rule(rule, sensor_data):
                triggered.append(rule)
                self.log(agent="FLIGHT_CTRL", msg=f"{rule['id']} triggered: {rule['action']}", type="alert")
                self.execute_rule_action(rule)
        return triggered

    def council_session(self, trigger: str, sensor_data: dict) -> dict:
        """Full council debate. Each agent sees previous agents' output."""
        session = {"trigger": trigger, "timestamp": datetime.utcnow().isoformat(), "debate": []}

        # 1. SENTINEL assesses the threat
        sentinel_input = f"Assess this threat: {trigger}\nCurrent sensors: {json.dumps(sensor_data)}"
        sentinel_response = self.sentinel(sentinel_input)
        session["debate"].append({"agent": "SENTINEL", "msg": str(sentinel_response)})
        self.log(agent="SENTINEL", msg=str(sentinel_response), type="alert")

        # 2. ORACLE generates strategies based on SENTINEL's assessment
        oracle_input = f"SENTINEL assessed: {sentinel_response}\nGenerate 3 strategies with predicted outcomes."
        oracle_response = self.oracle(oracle_input)
        session["debate"].append({"agent": "ORACLE", "msg": str(oracle_response)})
        self.log(agent="ORACLE", msg=str(oracle_response), type="decision")

        # 3. AQUA evaluates resource feasibility
        aqua_input = f"Threat: {trigger}\nStrategies: {oracle_response}\nCheck resource feasibility."
        aqua_response = self.aqua(aqua_input)
        session["debate"].append({"agent": "AQUA", "msg": str(aqua_response)})
        self.log(agent="AQUA", msg=str(aqua_response), type="info")

        # 4. FLORA assesses crop impact
        flora_input = f"Threat: {trigger}\nSENTINEL: {sentinel_response}\nAssess crop impact and recommend actions."
        flora_response = self.flora(flora_input)
        session["debate"].append({"agent": "FLORA", "msg": str(flora_response)})
        self.log(agent="FLORA", msg=str(flora_response), type="info")

        # 5. VITA calculates human cost
        vita_input = f"FLORA recommends: {flora_response}\nAQUA resources: {aqua_response}\nWhat is the crew impact?"
        vita_response = self.vita(vita_input)
        session["debate"].append({"agent": "VITA", "msg": str(vita_response)})
        self.log(agent="VITA", msg=str(vita_response), type="triage")

        # 6. Council vote (deterministic: select strategy with lowest crew impact)
        session["vote"] = self.resolve_vote(session["debate"])
        self.log(agent="COUNCIL", msg=f"VOTE: {session['vote']['decision']}", type="decision")

        return session

    def evaluate_rule(self, rule, sensor_data):
        """Evaluate a single flight rule against current sensor data."""
        # Implementation: parse trigger condition, evaluate against sensor_data
        # This is deterministic — no LLM needed
        pass

    def execute_rule_action(self, rule):
        """Execute a flight rule action (actuator commands)."""
        pass

    def resolve_vote(self, debate):
        """Resolve council vote from debate entries."""
        # Tiebreaker: human safety > crop survival > resource conservation > optimization
        return {"decision": "Strategy C adopted", "reasoning": "Lowest crew impact"}
```

## Data Flow

```
Sensors (Pi HTTP / simulated)
    ↓
Flight Rules Engine (Layer 0 — deterministic, 0ms)
    ↓ (if no rule matches, or if novel situation)
Council Orchestrator
    ↓
SENTINEL → ORACLE → AQUA → FLORA → VITA → COUNCIL VOTE
    ↓
Actions (actuator commands + DynamoDB state + dashboard stream)
    ↓
Post-event: ORACLE compares predicted vs actual → proposes new flight rules
```

## AgentCore Deployment

Each agent can share the same AgentCore Runtime endpoint. The entrypoint routes by agent name:

```python
@app.entrypoint
async def invoke(payload, context=None):
    action = payload.get("action", "council")
    trigger = payload.get("trigger", "")
    sensor_data = payload.get("sensor_data", {})

    if action == "council":
        return orchestrator.council_session(trigger, sensor_data)
    elif action == "check_rules":
        return orchestrator.check_flight_rules(sensor_data)
    elif action == "agent":
        agent_name = payload.get("agent")
        prompt = payload.get("prompt")
        return agents[agent_name](prompt)
```

## MCP Gateway Integration

All agents share one MCP client connection to the AgentCore Gateway:

```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

GATEWAY_URL = "https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"

mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL))

# The Syngenta KB tool is: kb-start-hack-target___knowledge_base_retrieve
# Input: {"query": "...", "max_results": 5}
# No auth needed (confirmed by probe)

with mcp_client:
    kb_tools = mcp_client.list_tools_sync()
    # Add KB tools to agents that need them: SENTINEL, ORACLE, FLORA, VITA
    sentinel = Agent(model=model, tools=[get_solar_events, read_sensors] + kb_tools, ...)
    oracle = Agent(model=model, tools=[run_simulation] + kb_tools, ...)
```

## Model Choice

- Use `claude-sonnet-4-6` for all agents (fast, capable, cost-effective for hackathon)
- NOT claude-opus (too slow for live demo — each council session would take 60s+)
- Temperature: 0.3 for SENTINEL/AQUA (precise), 0.5 for FLORA/VITA (personality)

## Demo Timing

A full council session = 5 sequential LLM calls. With Sonnet at ~2s per call = ~10-15s total.
This is FAST ENOUGH for a live demo. The audience sees agents appearing one by one in the log — which is MORE dramatic than everything appearing at once.
