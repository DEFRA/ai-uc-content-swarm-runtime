import pydantic_ai

import app.swarm.models as models

manager_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@manager_agent.system_prompt
def system_prompt() -> str:
    return """You are a manager agent coordinating specialist agents to create guidance content.
Track progress, identify when clarification is needed from the designer, coordinate task assignments, and facilitate group discussion between agents."""
