import json

import pytest

import app.swarm.content_pages.tools as content_page_tools
from app.swarm import models


@pytest.fixture
def deps(mocker):
    run_config = models.RunConfig(task="Test task", id="run-1", name="Test Run")
    context_repo = mocker.MagicMock()
    content_pages_repo = mocker.MagicMock()
    return models.AgentDependencies(
        run_config=run_config,
        context_repository=context_repo,
        content_pages_repository=content_pages_repo,
    )


def test_read_page_returns_content(deps):
    deps.content_pages["main"] = "# Hello\n\nContent."
    assert content_page_tools.read_page(deps, "main") == "# Hello\n\nContent."


def test_read_sub_page_returns_content(deps):
    deps.content_pages["sub/glossary"] = "Glossary content"
    assert content_page_tools.read_page(deps, "sub/glossary") == "Glossary content"


def test_read_missing_page_returns_error(deps):
    result = content_page_tools.read_page(deps, "main")
    assert "not found" in result
    assert "Existing pages: []" in result


def test_read_missing_page_lists_existing(deps):
    deps.content_pages["main"] = "Main"
    deps.content_pages["sub/faq"] = "FAQ"
    result = content_page_tools.read_page(deps, "missing")
    assert "main" in result
    assert "sub/faq" in result


def test_list_pages_returns_json_array(deps):
    deps.content_pages["main"] = "Main"
    result = content_page_tools.list_pages(deps)
    pages = json.loads(result)
    assert pages == ["main"]


def test_list_pages_includes_sub_pages(deps):
    deps.content_pages["main"] = "Main"
    deps.content_pages["sub/related"] = "Related"
    result = content_page_tools.list_pages(deps)
    pages = json.loads(result)
    assert "main" in pages
    assert "sub/related" in pages


def test_list_pages_empty_store(deps):
    result = content_page_tools.list_pages(deps)
    assert "No content pages have been created yet" in result


def test_single_main_page_per_run(deps):
    deps.content_pages["main"] = "v1"
    assert deps.content_pages["main"] == "v1"
    deps.content_pages["main"] = "v2"
    assert deps.content_pages["main"] == "v2"
    assert len(deps.content_pages) == 1


def test_writer_can_create_multiple_sub_pages(deps):
    deps.content_pages["main"] = "Main"
    deps.content_pages["sub/related"] = "Related"
    deps.content_pages["sub/glossary"] = "Glossary"
    assert len(deps.content_pages) == 3


def test_content_pages_starts_empty(deps):
    assert deps.content_pages == {}
