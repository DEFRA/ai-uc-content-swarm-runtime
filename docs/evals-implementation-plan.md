# Evals Implementation Plan

Detailed implementation plan for the eval strategy defined in [`docs/evals-strategy.md`](./evals-strategy.md).

---

## Production Code Change

Only one production file changes: `app/swarm/runner.py`. Return a `SwarmRunResult` instead of a bare string, exposing usage and group_chat for eval inspection.

### New dataclass

```python
# app/swarm/models.py
@dataclass
class SwarmRunResult:
    output: str
    usage: pydantic_ai.RunUsage
    group_chat: list[AgentExchange]
```

### Runner change

```python
# app/swarm/runner.py — return SwarmRunResult + log usage
entry = await manager.manager_agent.run(...)

logger.info(
    "Swarm run completed",
    extra={
        "run_id": config.id,
        "request_tokens": run_usage.request_tokens,
        "response_tokens": run_usage.response_tokens,
        "total_tokens": run_usage.total_tokens,
    },
)

return models.SwarmRunResult(
    output=entry.output,
    usage=run_usage,
    group_chat=run_dependencies.group_chat,
)
```

Update `app/swarm/router.py` to use `result.output` from `SwarmRunResult`.

---

## Directory Structure

```
evals/
├── conftest.py                    # ALLOW_MODEL_REQUESTS=False, EVAL_ENV gating
├── fixtures/
│   ├── deps.py                    # AgentDependencies factories with FunctionModel
│   └── context.py                 # FileContextRepository (reads from local fs, not S3)
├── unit/
│   ├── test_researcher_evals.py   # 5-8 evals: grounding, tool calls, uncertainty
│   └── test_manager_evals.py      # 5-8 evals: delegation, markdown output, convergence
├── integration/
│   ├── test_handoff_evals.py      # Manager→Researcher delegation quality
│   └── test_context_chain_evals.py # Document access through full chain
├── e2e/
│   ├── conftest.py                # requires_llm marker, ALLOW_MODEL_REQUESTS=True for dev/test
│   ├── test_swarm_output.py       # Full swarm via pydantic-evals Dataset
│   └── evaluators/
│       ├── faithfulness.py        # LLM-as-judge: output grounded in source docs
│       ├── format_compliance.py   # Deterministic: valid GOV.UK markdown
│       └── completeness.py        # LLM-as-judge: all task aspects addressed
├── datasets/
│   ├── golden.yaml                # 10-15 cases initially
│   └── context_docs/              # Test policy document fixtures (public/synthetic only — no sensitive data)
└── results/                       # gitignored, written by E2E runs
```

---

## Taskipy Task Definitions

Add to `pyproject.toml`:

```toml
[tool.taskipy.tasks]
eval-unit = "uv run pytest evals/unit -vv --tb=short"
eval-integration = "uv run pytest evals/integration -vv --tb=short"
eval-e2e = "uv run pytest evals/e2e -vv --tb=short"
eval-local = "uv run task eval-unit && uv run task eval-integration"
eval-all = "uv run task eval-unit && uv run task eval-integration && uv run task eval-e2e"
```

---

## CI Pipeline Changes

### scan.yml — add to existing test step

```yaml
- name: Run eval suite (unit + integration)
  run: uv run task eval-local
  env:
    EVAL_ENV: ci
```

Zero LLM cost, fast. Runs on every PR.

### New: evals-e2e.yml

```yaml
name: E2E Evals

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: dev
        type: choice
        options:
          - dev
          - test
  schedule:
    - cron: "0 6 * * 1-5"  # Weekdays at 06:00 UTC

permissions:
  id-token: write
  contents: read

jobs:
  e2e-evals:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'dev' }}
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --group dev

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: eu-west-2

      - name: Run E2E evals
        run: uv run task eval-all
        env:
          EVAL_ENV: ${{ github.event.inputs.environment || 'dev' }}
          ALLOW_MODEL_REQUESTS: "true"

      - name: Upload eval results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: eval-results-${{ github.run_id }}
          path: evals/results/
```

---

## Environment-Aware conftest Patterns

### Root conftest — prevent accidental LLM calls

```python
# evals/conftest.py
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # Prevent accidental real LLM calls
```

### E2E conftest — gate on environment

```python
# evals/e2e/conftest.py
import os
import pytest
from pydantic_ai import models

EVAL_ENV = os.environ.get("EVAL_ENV", "local")

# Only allow real model requests in dev/test environments
if EVAL_ENV in ("dev", "test"):
    models.ALLOW_MODEL_REQUESTS = True


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_llm: mark test as requiring real LLM access")


def pytest_collection_modifyitems(config, items):
    if EVAL_ENV in ("local", "ci"):
        skip_llm = pytest.mark.skip(reason=f"requires_llm: skipped in EVAL_ENV={EVAL_ENV}")
        for item in items:
            if "requires_llm" in item.keywords:
                item.add_marker(skip_llm)
```

### Usage in E2E tests

```python
# evals/e2e/test_swarm_output.py
import pytest

@pytest.mark.requires_llm
async def test_golden_dataset_scores():
    dataset = Dataset.from_file("evals/datasets/golden.yaml")
    # ...
```

---

## Golden Dataset Format

```yaml
# evals/datasets/golden.yaml
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

> **Data sensitivity constraint:** All context documents used in golden datasets must be sourced from publicly available GOV.UK content or written as synthetic test fixtures. Official sensitive documents must never be used outside of the production environment. See the [Data Sensitivity](./evals-strategy.md#data-sensitivity) section in the evals strategy for full details.

Golden dataset management:
- Start with 10-15 cases covering happy path, edge cases, and insufficient context
- Store test policy documents in `evals/datasets/context_docs/` (committed to repo) — **public/synthetic content only**
- Source context docs from published GOV.UK pages (e.g. farming grants guidance, Countryside Stewardship, export licensing) or write synthetic fixtures
- Cases are reviewed and updated as the swarm's capabilities evolve
- Add cases for any production failure mode discovered post-deployment

---

## Phased Delivery

### Phase 1: Foundation

**Deliverables:**
- Add `pydantic-evals` to dev dependency group in `pyproject.toml`
- Create `evals/` directory structure with conftest files and `ALLOW_MODEL_REQUESTS = False`
- Modify `runner.py` to return `SwarmRunResult` + log usage
- Update `router.py` caller to use `result.output`
- Add taskipy eval tasks to `pyproject.toml`
- Add `evals/results/` to `.gitignore`

**Verification:** `uv run task eval-local` runs and passes (no evals yet, just structure).

### Phase 2: Unit Evals (Layer 1)

**Deliverables:**
- `test_researcher_evals.py`: grounding in docs, tool calls, uncertainty flagging (5-8 evals)
- `test_manager_evals.py`: delegation, markdown output, convergence (5-8 evals)
- Add `eval-local` to `scan.yml` CI

**Verification:** `uv run task eval-unit` passes with 10-16 evals, zero LLM calls.

### Phase 3: Integration Evals (Layer 2)

**Deliverables:**
- `test_handoff_evals.py`: delegation quality, group_chat inspection
- `test_context_chain_evals.py`: document access through full chain

**Verification:** `uv run task eval-integration` passes with 5-8 evals, zero LLM calls.

### Phase 4: E2E Evals + Golden Dataset (Layer 3)

**Deliverables:**
- Golden dataset (10-15 YAML cases) + context doc fixtures
- Custom evaluators (faithfulness, format compliance, completeness)
- `test_swarm_output.py` using pydantic-evals Dataset
- New `evals-e2e.yml` workflow

**Verification:** `EVAL_ENV=dev uv run task eval-e2e` runs golden dataset against real Bedrock, produces scored results in `evals/results/`.

### Phase 5: Regression Tracking (Layer 4)

**Deliverables:**
- Baseline scores committed after first E2E run
- Score comparison logic: fail if any dimension drops >1.0, warn if avg drops >0.5
- Token usage + exchange count tracking per case

**Verification:** `uv run task eval-local` completes in <2 min, `EVAL_ENV=dev uv run task eval-all` completes in <15 min.

---

## Files to Modify and Reuse

### Modify

| File | Change |
|---|---|
| `app/swarm/models.py` | Add `SwarmRunResult` dataclass |
| `app/swarm/runner.py` | Return `SwarmRunResult`, log token usage |
| `app/swarm/router.py` | Use `result.output` from `SwarmRunResult` |
| `pyproject.toml` | Add `pydantic-evals` dev dep, add taskipy eval tasks |
| `.gitignore` | Add `evals/results/` |
| `.github/workflows/scan.yml` | Add `uv run task eval-local` to CI step |

### Reuse

| File | Reuse |
|---|---|
| `tests/swarm/prompts/fakes.py` | `FakeFileSystem` for prompt loading in eval fixtures |
| `tests/conftest.py` | Env var stub pattern for Bedrock model configs |
| `app/swarm/context/repository.py` | `AbstractContextRepository` interface for `FileContextRepository` |
