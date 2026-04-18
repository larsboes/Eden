"""Tests for Strands SDK adapter — agent factory + BedrockModel wrapper."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from eden.adapters.strands_adapter import StrandsAgentFactory


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_mcp_client():
    """Mock SyngentaKBAdapter that reports available with 2 tools."""
    client = MagicMock()
    client.is_available.return_value = True
    client.list_tools.return_value = [
        MagicMock(name="search_knowledge_base"),
        MagicMock(name="get_crop_profile"),
    ]
    return client


@pytest.fixture
def mock_nasa_client():
    """Mock NasaMCPAdapter that reports available with 3 tools."""
    client = MagicMock()
    client.is_available.return_value = True
    client.list_tools.return_value = [
        MagicMock(name="get_insight_weather"),
        MagicMock(name="get_donki_flr"),
        MagicMock(name="get_mars_rover_photos"),
    ]
    return client


@pytest.fixture
def factory():
    """Factory with no MCP client."""
    return StrandsAgentFactory(mcp_client=None)


@pytest.fixture
def factory_with_mcp(mock_mcp_client):
    """Factory with a single mock MCP client (backwards compat)."""
    return StrandsAgentFactory(mcp_client=mock_mcp_client)


@pytest.fixture
def factory_with_both(mock_mcp_client, mock_nasa_client):
    """Factory with both Syngenta + NASA MCP clients."""
    return StrandsAgentFactory(mcp_clients=[mock_mcp_client, mock_nasa_client])


def _make_mock_tool():
    """Create a mock @tool-decorated function."""
    fn = MagicMock()
    fn.__name__ = "read_sensors"
    fn.__doc__ = "Read sensors"
    return fn


# ── Factory construction ─────────────────────────────────────────────────


class TestConstruction:
    def test_factory_no_mcp(self, factory):
        assert factory._mcp_client is None
        assert factory._mcp_clients == []

    def test_factory_with_single_mcp(self, factory_with_mcp, mock_mcp_client):
        assert factory_with_mcp._mcp_client is mock_mcp_client
        assert len(factory_with_mcp._mcp_clients) == 1

    def test_factory_with_multiple_mcp(self, factory_with_both, mock_mcp_client, mock_nasa_client):
        assert len(factory_with_both._mcp_clients) == 2

    def test_factory_mcp_client_and_mcp_clients_combined(self, mock_mcp_client, mock_nasa_client):
        """When both mcp_client and mcp_clients are provided, they combine."""
        factory = StrandsAgentFactory(mcp_client=mock_mcp_client, mcp_clients=[mock_nasa_client])
        assert len(factory._mcp_clients) == 2
        assert factory._mcp_clients[0] is mock_mcp_client
        assert factory._mcp_clients[1] is mock_nasa_client


# ── MCP tools retrieval ──────────────────────────────────────────────────


class TestMCPTools:
    def test_no_mcp_returns_empty(self, factory):
        tools = factory._get_mcp_tools()
        assert tools == []

    def test_single_mcp_returns_tools(self, factory_with_mcp):
        tools = factory_with_mcp._get_mcp_tools()
        assert len(tools) == 2

    def test_multiple_mcp_combines_tools(self, factory_with_both):
        """Tools from both Syngenta (2) + NASA (3) should be combined."""
        tools = factory_with_both._get_mcp_tools()
        assert len(tools) == 5

    def test_mcp_unavailable_returns_empty(self, factory_with_mcp, mock_mcp_client):
        mock_mcp_client.is_available.return_value = False
        tools = factory_with_mcp._get_mcp_tools()
        assert tools == []

    def test_one_mcp_down_still_gets_other(self, factory_with_both, mock_mcp_client):
        """If Syngenta is down, NASA tools should still be returned."""
        mock_mcp_client.is_available.return_value = False
        tools = factory_with_both._get_mcp_tools()
        assert len(tools) == 3  # Only NASA tools

    def test_mcp_exception_returns_empty(self, factory_with_mcp, mock_mcp_client):
        mock_mcp_client.is_available.side_effect = RuntimeError("broken")
        tools = factory_with_mcp._get_mcp_tools()
        assert tools == []


# ── create_specialist ────────────────────────────────────────────────────


class TestCreateSpecialist:
    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_creates_agent_with_correct_args(self, mock_mcp_tools):
        """Verify Agent is created with the right prompt and tools."""
        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        mock_tool = _make_mock_tool()
        MockAgent = MagicMock()

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            agent = factory.create_specialist(
                name="DEMETER",
                system_prompt="You are DEMETER...",
                tools=[mock_tool],
                model=mock_model,
            )

            MockAgent.assert_called_once_with(
                model=mock_model,
                tools=[mock_tool],
                system_prompt="You are DEMETER...",
                callback_handler=None,
                name="DEMETER",
            )

    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools")
    def test_combines_local_and_mcp_tools(self, mock_mcp_tools):
        """Agent should receive both local tools and MCP tools."""
        mcp_tool_1 = MagicMock()
        mcp_tool_2 = MagicMock()
        mock_mcp_tools.return_value = [mcp_tool_1, mcp_tool_2]

        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        local_tool = _make_mock_tool()
        MockAgent = MagicMock()

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            factory.create_specialist(
                name="SENTINEL",
                system_prompt="You are SENTINEL...",
                tools=[local_tool],
                model=mock_model,
            )

            call_args = MockAgent.call_args
            all_tools = call_args.kwargs["tools"]
            assert len(all_tools) == 3  # 1 local + 2 MCP
            assert local_tool in all_tools
            assert mcp_tool_1 in all_tools
            assert mcp_tool_2 in all_tools

    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_returns_agent_instance(self, mock_mcp_tools):
        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        MockAgent = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            agent = factory.create_specialist(
                name="AQUA",
                system_prompt="You are AQUA...",
                tools=[],
                model=mock_model,
            )
            assert agent is not None


# ── create_flora ─────────────────────────────────────────────────────────


class TestCreateFlora:
    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_creates_flora_with_zone_prompt(self, mock_mcp_tools):
        """FLORA agent should have zone_id and crop_name injected into prompt."""
        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        MockAgent = MagicMock()

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            factory.create_flora(
                zone_id="alpha",
                crop_name="Tomato",
                tools=[],
                model=mock_model,
            )

            call_args = MockAgent.call_args
            prompt = call_args.kwargs["system_prompt"]
            assert "alpha" in prompt
            assert "Tomato" in prompt

    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_flora_prompt_contains_plant_voice(self, mock_mcp_tools):
        """FLORA prompt should contain first-person plant voice instructions."""
        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        MockAgent = MagicMock()

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            factory.create_flora(
                zone_id="beta",
                crop_name="Lettuce",
                tools=[],
                model=mock_model,
            )

            call_args = MockAgent.call_args
            prompt = call_args.kwargs["system_prompt"].lower()
            assert "voice" in prompt or "speak" in prompt or "feel" in prompt


# ── create_bedrock_model ─────────────────────────────────────────────────


class TestCreateBedrockModel:
    def test_creates_bedrock_model(self):
        """Should create a BedrockModel with specified params."""
        MockBedrockModel = MagicMock(return_value=MagicMock())
        mock_module = MagicMock()
        mock_module.BedrockModel = MockBedrockModel

        factory = StrandsAgentFactory()
        with patch.dict(sys.modules, {
            "strands.models": MagicMock(),
            "strands.models.bedrock": mock_module,
        }):
            model = factory.create_bedrock_model(
                model_id="us.anthropic.claude-sonnet-4-20250514",
                region_name="us-west-2",
            )
            MockBedrockModel.assert_called_once_with(
                model_id="us.anthropic.claude-sonnet-4-20250514",
                region_name="us-west-2",
                max_tokens=512,
                temperature=0.3,
            )
            assert model is not None

    def test_fallback_when_strands_not_installed(self):
        """When strands is not installed, should return None gracefully."""
        factory = StrandsAgentFactory()
        with patch.dict(sys.modules, {
            "strands": None,
            "strands.models": None,
            "strands.models.bedrock": None,
        }):
            try:
                model = factory.create_bedrock_model()
            except Exception:
                pytest.fail("create_bedrock_model should not raise when strands unavailable")


# ── Integration with all 12 specialists ──────────────────────────────────


class TestAllSpecialists:
    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_create_all_twelve_specialists(self, mock_mcp_tools):
        """Verify all 12 specialist agents can be created."""
        from eden.application.agent import _SPECIALIST_PROMPTS

        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        MockAgent = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            agents = {}
            for name, prompt in _SPECIALIST_PROMPTS.items():
                if name == "FLORA":
                    agents[name] = factory.create_flora(
                        zone_id="alpha", crop_name="Tomato",
                        tools=[], model=mock_model,
                    )
                else:
                    agents[name] = factory.create_specialist(
                        name=name, system_prompt=prompt,
                        tools=[], model=mock_model,
                    )

            assert len(agents) == 12
            assert MockAgent.call_count == 12

    @patch("eden.adapters.strands_adapter.StrandsAgentFactory._get_mcp_tools", return_value=[])
    def test_each_agent_gets_unique_prompt(self, mock_mcp_tools):
        """Each specialist should have a distinct system prompt."""
        from eden.application.agent import _SPECIALIST_PROMPTS

        factory = StrandsAgentFactory()
        mock_model = MagicMock()
        prompts_seen = set()
        MockAgent = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, {"strands": MagicMock(Agent=MockAgent)}):
            for name, prompt in _SPECIALIST_PROMPTS.items():
                if name == "FLORA":
                    factory.create_flora(
                        zone_id="alpha", crop_name="Tomato",
                        tools=[], model=mock_model,
                    )
                else:
                    factory.create_specialist(
                        name=name, system_prompt=prompt,
                        tools=[], model=mock_model,
                    )

            for call in MockAgent.call_args_list:
                prompts_seen.add(call.kwargs["system_prompt"])

            # All 12 agents should have unique prompts
            assert len(prompts_seen) == 12
