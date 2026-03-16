import re

import pydantic_ai

import app.swarm.models as models

manager_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@manager_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("manager.md")


@manager_agent.tool
async def dispatch(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
    agent_name: models.AgentName,
    task: str,
) -> str:
    """Dispatch a task to a named sub-agent in the swarm.

    Args:
        agent_name: The agent to dispatch the task to.
        task: The task or question for the agent.
    """
    group_chat = ctx.deps.group_chat

    if agent_name not in group_chat.agents:
        active = ", ".join(str(a) for a in group_chat.agents)
        return f"Agent '{agent_name}' is not active. Currently active agents: {active}"

    agent = group_chat.agents[agent_name]
    transcript = group_chat.format_transcript()

    prompt_parts = [f"Topic: {ctx.deps.run_config.task}"]
    if transcript:
        prompt_parts.append(transcript)
    prompt_parts.append(f"Task: {task}")
    prompt = "\n\n".join(prompt_parts)

    response = await agent.run(
        model=ctx.deps.get_model_for_agent(agent_name),
        user_prompt=prompt,
        deps=ctx.deps,
        usage=ctx.usage,
    )

    group_chat.transcript.append(
        models.AgentExchange(
            agent_name=agent_name.value,
            message=task,
            response=response.output,
        )
    )

    mentions = re.findall(r"@(\w+)", response.output, re.IGNORECASE)
    result = f"[{agent_name}]: {response.output}"

    if mentions:
        result += f"\n\nMentioned agents: {', '.join(f'@{m}' for m in mentions)}"

    return result
