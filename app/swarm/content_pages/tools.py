import json

import app.swarm.models as models


def read_page(deps: models.AgentDependencies, page_key: str) -> str:
    """Read the current content of an existing content page.

    Args:
        deps: Agent dependencies carrying the shared content page store.
        page_key: The key of the page to read (e.g. 'main', 'sub/related').

    Returns the markdown content, or an error message if the page does not exist.
    """
    if page_key not in deps.content_pages:
        existing = list(deps.content_pages.keys())
        return f"Page '{page_key}' not found. Existing pages: {existing}"

    return deps.content_pages[page_key]


def list_pages(deps: models.AgentDependencies) -> str:
    """List the keys of all content pages created so far in this run.

    Returns a JSON array of page keys, or a message if no pages exist yet.
    """
    if not deps.content_pages:
        return "No content pages have been created yet."

    return json.dumps(list(deps.content_pages.keys()), indent=2)
