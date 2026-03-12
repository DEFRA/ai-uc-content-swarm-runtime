import os
from abc import ABC, abstractmethod

import aiofiles


class PromptNotFoundError(Exception):
    """Raised when a prompt file cannot be found."""


class FileSystem:
    def directory_exists(self, path: str) -> bool:
        return os.path.isdir(path)

    async def read_file(self, path: str) -> str:
        async with aiofiles.open(path) as f:
            return str(await f.read()).strip()


class AbstractPromptRepository(ABC):
    @abstractmethod
    async def get_prompt_by_name(self, name: str) -> str:
        """Retrieve a prompt by name.

        Args:
            name: The name of the prompt file (e.g., "manager_prompt.txt").

        Returns:
            The content of the prompt file.

        Raises:
            PromptNotFoundError: If the prompt file cannot be found.
        """


class FileSystemPromptRepository(AbstractPromptRepository):
    def __init__(self, fs: FileSystem = FileSystem()):
        self.prompt_directory = os.path.join(os.path.dirname(__file__))
        self.fs = fs
        self._cache: dict[str, str] = {}

    async def get_prompt_by_name(self, name: str) -> str:
        if name in self._cache:
            return self._cache[name]

        full_path = os.path.join(self.prompt_directory, name)

        try:
            content = await self.fs.read_file(full_path)
        except FileNotFoundError as err:
            msg = f"Prompt not found: {name}"
            raise PromptNotFoundError(msg) from err

        self._cache[name] = content

        return content
