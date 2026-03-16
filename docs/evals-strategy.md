# Evals Strategy for AI Content Swarm

## System Under Test

The swarm consists of two pydantic-ai agents running on AWS Bedrock (Claude Haiku):

- **Manager Agent** — Coordinates the swarm, delegates to specialist agents, synthesises a final GOV.UK guidance markdown document
- **Researcher Agent** — Analyses source policy documents via S3-backed context repository, surfaces evidence and findings

**Flow:** `SwarmRunner.start_run(RunConfig)` → Manager receives task → Manager calls `ask_researcher_agent` tool → Researcher fetches/analyses policy docs → Manager synthesises final output

**Key data already captured:** `AgentExchange` objects in `group_chat` (agent name, message, response, timestamp), `RunUsage` for token tracking.

---

## Evaluation Layers

### Layer 1: Unit Evals (Individual Agents)

**Purpose:** Verify each agent behaves correctly in isolation.

**Tooling:** pydantic-ai `TestModel` and `FunctionModel` with `Agent.override()`

**What to test:**

| Agent | Eval | Method |
|---|---|---|
| Researcher | Returns grounded evidence from provided documents | `FunctionModel` with known doc content, assert output references source material |
| Researcher | Calls `list_policy_documents` and `get_document_content` tools appropriately | `TestModel` with `capture_run_messages`, inspect tool call sequence |
| Researcher | Flags uncertainty when documents are insufficient | `FunctionModel` with sparse/irrelevant docs |
| Manager | Delegates to researcher when task requires evidence | `FunctionModel`, verify `ask_researcher_agent` tool call occurs |
| Manager | Produces valid markdown output | Deterministic format checks on output |
| Manager | Stops iteration when diminishing returns | `FunctionModel` with repeated similar responses, check conversation length |

**Implementation pattern:**

```python
# tests/evals/unit/test_researcher_evals.py
from pydantic_ai.models.function import FunctionModel
from pydantic_ai import capture_run_messages

async def test_researcher_grounds_in_source_documents():
    """Researcher should reference specific content from provided documents."""
    fake_doc_content = "The grant requires 50 hectares minimum land size."

    def mock_llm(messages, info):
        # Return response that references source material
        return ModelResponse(parts=[TextPart(
            "The policy specifies a minimum of 50 hectares land size for grant eligibility."
        )])

    with researcher_agent.override(model=FunctionModel(mock_llm)):
        result = await researcher_agent.run("What are the land requirements?", deps=fake_deps)

    assert "50 hectares" in result.output
```

**CI integration:** Run on every PR. Target: < 2 minutes. Set `ALLOW_MODEL_REQUESTS = False` in conftest.py to prevent accidental real LLM calls.

---

### Layer 2: Integration Evals (Agent Handoffs)

**Purpose:** Verify the manager-researcher delegation works correctly — right questions asked, responses properly incorporated.

**What to test:**

| Eval | Method |
|---|---|
| Manager passes clear, specific questions to researcher | Inspect `group_chat` exchanges — LLM-as-judge scores the `message` field for clarity |
| Researcher response is incorporated into final output | Compare `group_chat` response content against final output |
| Multi-turn exchanges converge (not circular) | Check that each exchange adds new information |
| Context documents are accessible through the full chain | End-to-end with mocked S3 (moto), verify researcher can access docs manager referenced |

**Implementation pattern:**

```python
# tests/evals/integration/test_handoff_evals.py
async def test_manager_researcher_handoff_quality():
    """Manager should ask specific, actionable questions to researcher."""
    test_model = FunctionModel(mock_manager_delegates_then_synthesises)

    with manager_agent.override(model=test_model):
        with researcher_agent.override(model=FunctionModel(mock_researcher)):
            runner = SwarmRunner(context_repository=fake_repo)
            config = RunConfig(task="Summarise grant eligibility", id="eval-1", name="handoff-test")
            result = await runner.start_run(config)

    # Inspect the group_chat for handoff quality
    exchanges = deps.group_chat
    for exchange in exchanges:
        assert len(exchange.message) > 20  # Not a trivial delegation
```

**CI integration:** Run on every PR. Target: < 5 minutes.

---

### Layer 3: End-to-End Evals (Full Swarm Output Quality)

**Purpose:** Grade the final output of the complete swarm pipeline against a golden dataset.

**Tooling:** `pydantic-evals` — first-party pydantic evaluation framework.

**Eval dimensions:**

| Dimension | Type | Description |
|---|---|---|
| **Correctness** | LLM-as-judge (reference-based) | Are all factual claims accurate against source documents? |
| **Faithfulness** | LLM-as-judge | Does output avoid introducing information not in source documents? |
| **Completeness** | LLM-as-judge | Does output address all aspects of the task? |
| **Relevance** | LLM-as-judge (reference-free) | Is the output focused on what was asked? |
| **Format compliance** | Deterministic | Is the output valid GOV.UK-style markdown? |
| **Hallucination** | LLM-as-judge | Does the agent fabricate information not present in policy docs? |

**Golden dataset structure:**

```yaml
# evals/datasets/golden.yaml
# NOTE: All context_documents must reference public GOV.UK content or synthetic fixtures.
# Official sensitive documents are restricted to production only.
cases:
  - name: basic_farming_grant_summary
    inputs:
      task: "Summarise the key points of the Sustainable Farming Incentive guidance"
      context_documents:
        - id: "doc-1"
          name: "Sustainable Farming Incentive guidance (GOV.UK)"
          path: "evals/datasets/context_docs/sfi-guidance.md"
    expected_criteria:
      must_mention: ["payment rates", "eligibility criteria", "land management actions"]
      must_not_hallucinate: true
      min_sources_referenced: 1
    reference_output: "Optional gold-standard answer for comparison"

  - name: multi_document_comparison
    inputs:
      task: "Compare Countryside Stewardship and Sustainable Farming Incentive eligibility"
      context_documents:
        - id: "doc-1"
          name: "Countryside Stewardship guidance (GOV.UK)"
          path: "evals/datasets/context_docs/countryside-stewardship-guidance.md"
        - id: "doc-2"
          name: "Sustainable Farming Incentive guidance (GOV.UK)"
          path: "evals/datasets/context_docs/sfi-guidance.md"
    expected_criteria:
      must_mention: ["land eligibility", "agreement length", "payment structure"]
      must_compare_both_documents: true

  - name: insufficient_context
    inputs:
      task: "What are the penalties for non-compliance with food safety regulations?"
      context_documents: []
    expected_criteria:
      should_acknowledge_insufficient_info: true
      must_not_hallucinate: true
```

**Implementation with pydantic-evals:**

```python
# evals/e2e/test_swarm_evals.py
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge, Evaluator, EvaluatorContext

class FaithfulnessEvaluator(Evaluator[SwarmInput, str]):
    async def evaluate(self, ctx: EvaluatorContext[SwarmInput, str]) -> float:
        # Check output claims against source documents
        ...

class FormatComplianceEvaluator(Evaluator[SwarmInput, str]):
    async def evaluate(self, ctx: EvaluatorContext[SwarmInput, str]) -> float:
        # Check markdown structure, GOV.UK style compliance
        ...

dataset = Dataset.from_file("evals/datasets/golden.yaml")
dataset.evaluators = [
    LLMJudge(rubric=CORRECTNESS_RUBRIC),
    FaithfulnessEvaluator(),
    FormatComplianceEvaluator(),
]

report = dataset.evaluate_sync(run_swarm_task)
report.print(include_input=True, include_output=True)
```

**LLM-as-judge rubric:**

```
You are evaluating a GOV.UK guidance document produced by an AI agent system.

INPUT TASK: {task}
AVAILABLE SOURCE DOCUMENTS: {documents}
AGENT OUTPUT: {output}

Score on each dimension (0-5):
1. CORRECTNESS: Are all factual claims accurate and supported by the source documents?
2. COMPLETENESS: Does the output address all aspects of the task?
3. FAITHFULNESS: Does the output avoid introducing information not in the sources?
4. RELEVANCE: Is the output focused on what was asked?
5. FORMAT: Does the output follow GOV.UK guidance style (clear, plain English, structured)?

For each score, provide a one-sentence justification.
Output as JSON: {"correctness": X, "completeness": X, "faithfulness": X, "relevance": X, "format": X}
```

**CI integration:** Run on merge to main or nightly. Target: < 15 minutes. Multiple runs per case (3x) to handle non-determinism, take median scores.

---

### Layer 4: Regression Evals

**Purpose:** Detect quality degradation when prompts, models, or code change.

**Approach:**
- Maintain baseline scores from the golden dataset
- On each eval run, compare against baseline
- Hard fail if any dimension drops > 1.0 point on the 0-5 scale
- Soft warn if average score drops > 0.5

**Track over time:**
- Score per dimension per test case
- Token usage per agent (from `RunUsage`)
- Latency per run
- Number of agent exchanges per run

---

## Recommended Tooling

| Tool | Purpose | Why |
|---|---|---|
| **pydantic-ai TestModel/FunctionModel** | Unit + integration evals | First-party, already in your dependency tree, zero additional deps |
| **pydantic-evals** | E2E eval framework | First-party pydantic package, YAML datasets, built-in LLM-as-judge, custom evaluators |
| **pytest** | Test runner for all eval layers | Already your test runner, familiar patterns |
| **moto** | AWS S3 mocking for context docs | Already in your dev deps |

**Optional additions if needed later:**
- **deepeval** — 60+ pre-built metrics (hallucination, toxicity, bias) if you need broader coverage
- **braintrust** — Production monitoring + eval lifecycle management at scale

---

## Environment Strategy

### Environment Mapping

| Eval Layer | Local | CI (PRs) | Dev (AWS) | Test (AWS) | Prod |
|---|---|---|---|---|---|
| **Unit** (per-agent, FunctionModel) | Yes | Yes | Yes | Yes | — |
| **Integration** (handoffs, FunctionModel) | Yes | Yes | Yes | Yes | — |
| **E2E** (full swarm, real Bedrock) | No | No | Yes (nightly) | Yes (pre-release) | — |
| **Regression** (score tracking) | No | No | Built from E2E | Built from E2E | — |
| **Data allowed** | Synthetic / public only | Synthetic / public only | Public only | Public only | Official sensitive |

- **Local + CI**: Layers 1-2 only. Use pydantic-ai `FunctionModel` — zero LLM calls, zero cost.
- **Dev (remote)**: All layers including E2E with real Bedrock. Nightly weekday schedule.
- **Test (remote)**: All layers as a pre-release gate. Same cost profile as dev.
- **Prod**: No evals run in production. Production is the only environment where official sensitive documents are permitted.

### Data Sensitivity

Official sensitive documents must **only** be used in the **production** environment. All eval and test environments (local, CI, dev, test) must exclusively use non-sensitive data:

- **Synthetic data** — hardcoded strings, `FunctionModel` responses, and fabricated test fixtures (used in unit and integration layers)
- **Publicly available GOV.UK content** — published guidance pages, policy papers, and legislation (used in E2E golden datasets)

Golden dataset `context_docs/` must be sourced from one of:
- Published [GOV.UK guidance pages](https://www.gov.uk/search/all) (e.g. farming grants, export licensing)
- Published [policy papers](https://www.gov.uk/search/policy-papers-and-consultations)
- [legislation.gov.uk](https://www.legislation.gov.uk/) content
- Synthetic documents written specifically as test fixtures

Never commit, reference, or use official sensitive, restricted, or unpublished government documents in any eval dataset, test fixture, or CI pipeline.

### Cost Control Measures

| Control | Mechanism |
|---|---|
| **Prevent accidental LLM calls** | `ALLOW_MODEL_REQUESTS = False` in `evals/conftest.py` — any accidental real LLM call raises immediately |
| **Environment gating** | `EVAL_ENV` env var (`local`/`ci`/`dev`/`test`) gates E2E evals via `pytest.mark.skipif` |
| **Model selection** | E2E evals use Haiku only (~$0.25/1M input, $1.25/1M output) |
| **Token budgets** | Fail if any single case exceeds 50,000 tokens (catches runaway agent loops) |
| **Schedule control** | E2E workflow runs nightly on dev (weekdays only), manually on test |

### Per-Environment Cost Estimates

| Environment | Eval Layers | LLM Cost per Run |
|---|---|---|
| Local | Unit + Integration | **$0** (FunctionModel only) |
| CI (PRs) | Unit + Integration | **$0** (FunctionModel only) |
| Dev (nightly) | All (incl. E2E) | **~$0.10-0.30** (15 cases × 3 runs, Haiku) |
| Test (pre-release) | All (incl. E2E) | **~$0.10-0.30** (same profile as dev) |

---

## Implementation Plan

> See [`docs/evals-implementation-plan.md`](./evals-implementation-plan.md) for the detailed implementation plan with code snippets, CI configs, and phased delivery.

### Phase 1: Foundation (Weeks 1-2)

1. **Add `pydantic-evals` to dev dependencies**
   ```toml
   [dependency-groups]
   dev = [
       ...
       "pydantic-evals>=0.1.0",
   ]
   ```

2. **Set up eval directory structure**
   ```
   evals/
   ├── conftest.py              # ALLOW_MODEL_REQUESTS = False, shared fixtures
   ├── datasets/
   │   └── golden.yaml          # Golden dataset (start with 10-15 cases)
   ├── evaluators/
   │   ├── faithfulness.py      # Custom faithfulness evaluator
   │   ├── format_compliance.py # GOV.UK markdown format checker
   │   └── grounding.py         # Source document grounding checker
   ├── unit/
   │   ├── test_researcher.py   # Researcher agent unit evals
   │   └── test_manager.py      # Manager agent unit evals
   ├── integration/
   │   └── test_handoffs.py     # Manager-researcher handoff evals
   └── e2e/
       └── test_swarm.py        # Full pipeline evals
   ```

3. **Add taskipy tasks**
   ```toml
   [tool.taskipy.tasks]
   eval-unit = "uv run pytest evals/unit -vv"
   eval-integration = "uv run pytest evals/integration -vv"
   eval-e2e = "uv run pytest evals/e2e -vv"
   eval = "uv run task eval-unit && uv run task eval-integration && uv run task eval-e2e"
   ```

4. **Lock down test safety**
   ```python
   # evals/conftest.py
   from pydantic_ai import models
   models.ALLOW_MODEL_REQUESTS = False  # Prevent accidental real LLM calls in CI
   ```

### Phase 2: Unit + Integration Evals (Weeks 2-3)

5. Write 5-10 unit evals per agent using `FunctionModel`
6. Write 3-5 integration evals for manager-researcher handoffs
7. Add to CI pipeline (run on every PR)

### Phase 3: E2E Evals + Golden Dataset (Weeks 3-5)

8. Build initial golden dataset (15-20 cases covering happy path, edge cases, insufficient context)
9. Implement custom evaluators (faithfulness, format compliance, grounding)
10. Set up LLM-as-judge with scoring rubric
11. Add to CI pipeline (run on merge to main)

### Phase 4: Regression Tracking (Week 5+)

12. Establish baseline scores from initial golden dataset runs
13. Set up score comparison and threshold-based gating
14. Track metrics over time (scores, token usage, latency)

---

## Key Principles

1. **Start small, iterate** — 20-30 well-curated cases beat 200 noisy ones
2. **Grade outcomes, not paths** — The agent may take different routes to a correct answer; that's fine
3. **Deterministic first** — Max out what you can test without LLM calls before adding LLM-as-judge
4. **Use `group_chat` data** — You already capture `AgentExchange` objects; these are goldmines for integration evals
5. **Multiple runs for non-deterministic evals** — Run 3x minimum, take median scores
6. **Binary checks for critical failures** — Hallucination and format compliance should be pass/fail, not scored
7. **Data classification boundary** — Official sensitive documents are production-only; all evals use synthetic or publicly available data

---

## References

- [Anthropic — Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [pydantic-ai Testing Documentation](https://ai.pydantic.dev/testing/)
- [pydantic-evals Documentation](https://ai.pydantic.dev/evals/)
- [McKinsey QuantumBlack — Evaluations for the Agentic World](https://medium.com/quantumblack/evaluations-for-the-agentic-world-c3c150f0dd5a)
- [Amazon AWS — Evaluating AI Agents: Real-World Lessons](https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents-real-world-lessons-from-building-agentic-systems-at-amazon/)
- [Confident AI — Definitive AI Agent Evaluation Guide](https://www.confident-ai.com/blog/definitive-ai-agent-evaluation-guide)
