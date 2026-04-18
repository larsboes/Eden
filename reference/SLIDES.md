# Syngenta + AWS START HACK 2026 — Enablement Session Slides

> Source: `reference/pdfs/enablement-session.pdf`
> Presenters: Mirko Carrara (AWS TAM), Marzia Mura (AWS SA), Roberto Catalano (AWS SA)
> Date: St Gallen, 18 March 2026

---

## Slide 1: Title

**Agriculture's Next Frontier — Tech Onboarding**

Syngenta | powered by AWS

Syngenta + AWS Hackathon Challenge

---

## Slide 2: The Challenge

**Our Challenge: To design an autonomous AI agent system to manage a Martian greenhouse**

Your mission, should you choose to accept it, is to design and prototype an autonomous AI agent system capable of managing a greenhouse on Mars.

Your system should be able to:

- **Monitor and Control the Environment**: Maintain optimal conditions for plant growth (temperature, humidity, light, water)
- **Manage Resources**: Efficiently use and recycle precious resources like water and nutrients
- **Detect and Respond to Plant Stress**: Identify plant health issues (e.g., nutrient deficiencies, disease) and trigger automated responses
- **Optimize for Growth**: Learn and adapt to find the most effective strategies for growing crops in an alien environment

*Visual: Webcam screenshot labeled "CAM-01 | Cucumber Claude" showing plants in a grow tent, dated 03/11/2026 19:02:03*

---

## Slide 3: Step 1 — Sign In

**Sign in using your preferred method**

AWS Workshop Studio at `https://join.workshops.aws`

Options: Email one-time password (OTP), Login with Amazon, Amazon employee

---

## Slide 4: Step 2 — Event Access Code

**Enter the event access code**

A 12-digit code given to your team. Each session has a unique code.

---

## Slide 5: Step 3 — Review Terms and Join

**Review terms and join event**

Accept terms and conditions, then join the event.

---

## Slide 6: Step 4 — Get Started with Workshop

**Get started with the workshop**

Click "Get started" to access the workshop content. Labs divided into basic and advanced modules.

---

## Slide 7: Step 5 — Access AWS Account

**Access the AWS Management Console or generate AWS CLI credentials as needed**

From the Workshop Studio sidebar:
- "Open AWS console" (us-east-1)
- "Get AWS CLI credentials"

Shows: AWS Console, DynamoDB wizard for creating tables.

---

## Slide 8: Know Your Land — AWS

Basic AWS infrastructure overview:
- **Region** → **AWS Account** → **VPC** → **Private subnet** + **Public subnet**

---

## Slide 9: Agent Security — Containment

**Execute agents in a secure, isolated runtime environment**

1. Contain what can happen — Agent runs inside a sandboxed environment

---

## Slide 10: Agent Security — Policy Enforcement

**Enforce deterministic policies on every agent-tool interaction**

Agent → Gateway → routes to:
- Check Syngenta Documentation
- Check Weather on Mars

2. Control what agents can DO

---

## Slide 11: Syngenta Resources

**Syngenta Knowledge Base Architecture**

Your Account (AI Agent) → `/mcp` Endpoint → Gateway → Syngenta AWS Account (Amazon Bedrock Knowledge Base)

**Knowledge Base contains 7 domains:**

1. **Mars Environmental Constraints** — Physical and environmental conditions on Mars and their implications for agriculture and system design
2. **Controlled Environment Agriculture Principles** — Core principles of controlled agriculture systems (hydroponics and environmental control) enabling plant growth in isolated environments
3. **Crop Profiles** — Structured crop characteristics, growth cycles, and resource requirements to support AI-driven crop management
4. **Plant Stress and Response Guide** — Stress detection and mitigation strategies so AI agents can respond effectively to environmental and physiological issues
5. **Human Nutritional Strategy** — Nutritional requirements and optimization logic linking greenhouse production to astronaut dietary needs
6. **Greenhouse Operational Scenarios** — Operational events and failure modes to guide AI agent in the decision-making process under conditions
7. **Innovation Impact (Mars to Earth)** — Connections between autonomous agriculture concepts and Earth applications, emphasizing sustainability and real-world value

---

## Slide 12: AWS Toolkit

**Official AWS GitHub Repos:**
- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Fullstack AgentCore Solution Template (FAST)](https://github.com/awslabs/fullstack-solution-template-for-agentcore)
- [End-to-end Customer Support Agent with AgentCore](https://github.com/awslabs/end-to-end-customer-support-agent-with-agentcore)

**Strands Multi-Agent Patterns and SDK:**
- [Strands Python Deployment to Amazon Bedrock AgentCore Runtime](https://github.com/strands-agents/strands-python-deployment-to-agentcore-runtime)
- [Agent Workflows: Building Multi-Agent Systems with Strands Agents SDK](https://github.com/strands-agents/agent-workflows)
- [Multi-agent Patterns](https://github.com/strands-agents/multi-agent-patterns)

---

## Slide 13: AgentCore Runtime

**CONTAIN WHAT CAN HAPPEN**

AgentCore Runtime — Keep agent isolated, scoped, and secure at runtime.

Architecture:
- Session 1 → MicroVM Kernel 1 (Firecracker MicroVM)
- Session 2 → MicroVM Kernel 2

Each session gets its own isolated Firecracker MicroVM.

---

## Slide 14: AgentCore — Secure and Scalable Runtime

**Secure and scalable runtime for agents and tools**

```
Agent or tool code
├── Models (Bedrock, Strands, etc.)
├── Framework (Strands SDK, LangChain, CrewAI)
├── + AgentCore Runtime decorator
├── + AgentCore Identity config
└── + AgentCore Observability config
         ↓ configure
    Docker file
         ↓ launch
    Amazon ECR Repository → AgentCore Runtime
                              ├── Runtime Agent
                              └── Runtime Endpoint ← user → Application → invoke
```

---

## Slide 15: AgentCore Gateway

**CONTROL WHAT AGENTS CAN DO**

AgentCore Gateway — Tool curation and Fine-Grained Access Control

```
Agent (MCP Client) → /mcp → AgentCore Gateway → Interceptors →
    ├── API Endpoint Target
    ├── AWS Lambda Target
    └── MCP Server Target
```

Operations: List tools, Invoke tool, Search

---

## Slide 16: Discord Server

Discord: `https://discord.gg/BQxYYxpU`

---

## Slide 17: Next Steps

**Next Step: Agriculture's NextFrontier Starts Now!**

Teams! Come to the Syngenta booth and get:
1. AWS activation codes to get Your Team environment for farming on Mars Mission
2. Insight and activation codes on how to accelerate with AWS AI coding Kiro
3. Meet the experts — Syngenta AWS

---

## Slide 18: Closing

**IT'S TIME TO BUILD!**

Syngenta | powered by AWS — Syngenta + AWS Hackathon Challenge
