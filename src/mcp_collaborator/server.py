"""MCP Text Editor Server implementation, with git integrations."""

import logging
import traceback
from collections.abc import Sequence
from typing import Any, List

from git import Repo
from mcp_collaborator.git import (
    GitCheckout,
    GitCommit,
    GitDiff,
    GitDiffStaged,
    GitDiffUnstaged,
    GitLog,
    GitReset,
    GitShow,
    GitStatus,
    GitTools,
    git_checkout,
    git_commit,
    git_diff,
    git_diff_staged,
    git_diff_unstaged,
    git_log,
    git_reset,
    git_show,
    git_status,
)

import click
from pathlib import Path

from mcp.server import Server
from mcp.types import TextContent, Tool

from .handlers import (
    AppendTextFileContentsHandler,
    CreateTextFileHandler,
    DeleteTextFileContentsHandler,
    GetTextFileContentsHandler,
    InsertTextFileContentsHandler,
    PatchTextFileContentsHandler,
)
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-collaborator")


@click.command()
@click.option("--repository", "-r", type=Path, help="Git repository path")
@click.option("--checkouts", "-c", type=Path, help="Checkout root path")
async def main(repository: Path, checkouts: Path) -> None:
    app = Server("mcp-collaborator")

    # Initialize tool handlers
    get_contents_handler = GetTextFileContentsHandler()
    patch_file_handler = PatchTextFileContentsHandler()
    create_file_handler = CreateTextFileHandler()
    append_file_handler = AppendTextFileContentsHandler()
    delete_contents_handler = DeleteTextFileContentsHandler()
    insert_file_handler = InsertTextFileContentsHandler()


    @app.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name=GitTools.STATUS,
                description="Shows the working tree status",
                inputSchema=GitStatus.schema(),
            ),
            Tool(
                name=GitTools.DIFF_UNSTAGED,
                description="Shows changes in the working directory that are not yet staged",
                inputSchema=GitDiffUnstaged.schema(),
            ),
            Tool(
                name=GitTools.DIFF_STAGED,
                description="Shows changes that are staged for commit",
                inputSchema=GitDiffStaged.schema(),
            ),
            Tool(
                name=GitTools.DIFF,
                description="Shows differences between branches or commits",
                inputSchema=GitDiff.schema(),
            ),
            Tool(
                name=GitTools.COMMIT,
                description="Records changes to the repository",
                inputSchema=GitCommit.schema(),
            ),
            Tool(
                name=GitTools.RESET,
                description="Unstages all staged changes",
                inputSchema=GitReset.schema(),
            ),
            Tool(
                name=GitTools.LOG,
                description="Shows the commit logs",
                inputSchema=GitLog.schema(),
            ),
            Tool(
                name=GitTools.CHECKOUT,
                description="Checks out a new branch to begin work. The checkout path used here must be the same as the one used in all other tools.",
                inputSchema=GitCheckout.schema(),
            ),
            Tool(
                name=GitTools.SHOW,
                description="Shows the contents of a commit",
                inputSchema=GitShow.schema(),
            ),
            get_contents_handler.get_tool_description(),
            create_file_handler.get_tool_description(),
            append_file_handler.get_tool_description(),
            delete_contents_handler.get_tool_description(),
            insert_file_handler.get_tool_description(),
            patch_file_handler.get_tool_description(),
        ]


    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
        """Handle tool calls."""
        logger.info(f"Calling tool: {name}")

        checkout = Path(checkouts, arguments["checkout_path"])
        
        if name == GitTools.CHECKOUT:
            repo = Repo.clone_from(repository, checkout)
            status = git_checkout(repo, arguments["checkout_path"])
            return [TextContent(
                type="text",
                text=status
            )]

        try:
            match name:
                case GitTools.STATUS:
                    repo = Repo(checkout)
                    status = git_status(repo)
                    return [TextContent(
                        type="text",
                        text=f"Repository status:\n{status}"
                    )]

                case GitTools.DIFF_UNSTAGED:
                    repo = Repo(checkout)
                    diff = git_diff_unstaged(repo)
                    return [TextContent(
                        type="text",
                        text=f"Unstaged changes:\n{diff}"
                    )]

                case GitTools.DIFF_STAGED:
                    repo = Repo(checkout)
                    diff = git_diff_staged(repo)
                    return [TextContent(
                        type="text",
                        text=f"Staged changes:\n{diff}"
                    )]

                case GitTools.DIFF:
                    repo = Repo(checkout)
                    diff = git_diff(repo, arguments["target"])
                    return [TextContent(
                        type="text",
                        text=f"Diff with {arguments['target']}:\n{diff}"
                    )]

                case GitTools.COMMIT:
                    repo = Repo(checkout)
                    result = git_commit(repo, arguments["message"])
                    return [TextContent(
                        type="text",
                        text=result
                    )]

                case GitTools.RESET:
                    repo = Repo(checkout)
                    result = git_reset(repo)
                    return [TextContent(
                        type="text",
                        text=result
                    )]

                case GitTools.LOG:
                    repo = Repo(checkout)
                    log = git_log(repo, arguments.get("max_count", 10))
                    return [TextContent(
                        type="text",
                        text="Commit history:\n" + "\n".join(log)
                    )]

                case GitTools.SHOW:
                    repo = Repo(checkout)
                    result = git_show(repo, arguments["revision"])
                    return [TextContent(
                        type="text",
                        text=result
                    )]
                case get_contents_handler.name:
                    return await get_contents_handler.run_tool(arguments)
                case create_file_handler.name:
                    return await create_file_handler.run_tool(arguments)
                case append_file_handler.name:
                    return await append_file_handler.run_tool(arguments)
                case delete_contents_handler.name:
                    return await delete_contents_handler.run_tool(arguments)
                case insert_file_handler.name:
                    return await insert_file_handler.run_tool(arguments)
                case patch_file_handler.name:
                    return await patch_file_handler.run_tool(arguments)
                case _:
                    raise ValueError(f"Unknown tool: {name}")
        except ValueError:
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error executing command: {str(e)}") from e

    """Main entry point for the MCP callaborator server."""
    logger.info(f"Starting MCP collaborator server v{__version__}")
    try:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
