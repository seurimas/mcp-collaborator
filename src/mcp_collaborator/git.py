import logging
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)
from enum import Enum
import git
from pydantic import BaseModel

class GitStatus(BaseModel):
    checkout_path: str

class GitDiffUnstaged(BaseModel):
    checkout_path: str

class GitDiffStaged(BaseModel):
    checkout_path: str

class GitDiff(BaseModel):
    checkout_path: str
    target: str

class GitCommit(BaseModel):
    checkout_path: str
    message: str

class GitAdd(BaseModel):
    checkout_path: str
    files: list[str]

class GitReset(BaseModel):
    checkout_path: str

class GitLog(BaseModel):
    checkout_path: str
    max_count: int = 10

class GitCreateBranch(BaseModel):
    checkout_path: str
    branch_name: str
    base_branch: str | None = None

class GitCheckout(BaseModel):
    checkout_path: str

class GitShow(BaseModel):
    checkout_path: str
    revision: str

class GitInit(BaseModel):
    checkout_path: str

class GitTools(str, Enum):
    STATUS = "git_status"
    DIFF_UNSTAGED = "git_diff_unstaged"
    DIFF_STAGED = "git_diff_staged"
    DIFF = "git_diff"
    COMMIT = "git_commit"
    # ADD = "git_add" # Done automatically during editing now.
    RESET = "git_reset"
    LOG = "git_log"
    # CREATE_BRANCH = "git_create_branch" # Baked into the checkout tool now.
    CHECKOUT = "git_checkout"
    SHOW = "git_show"
    # INIT = "git_init" # Presumed to be done before this tool is called.

def git_status(repo: git.Repo) -> str:
    return repo.git.status()

def git_diff_unstaged(repo: git.Repo) -> str:
    return repo.git.diff()

def git_diff_staged(repo: git.Repo) -> str:
    return repo.git.diff("--cached")

def git_diff(repo: git.Repo, target: str) -> str:
    return repo.git.diff(target)

def git_commit(repo: git.Repo, message: str) -> str:
    commit = repo.index.commit(message)
    return f"Changes committed successfully with hash {commit.hexsha}"

# def git_add(repo: git.Repo, files: list[str]) -> str:
#     repo.index.add(files)
#     return "Files staged successfully"

def git_reset(repo: git.Repo) -> str:
    repo.index.reset()
    return "All staged changes reset"

def git_log(repo: git.Repo, max_count: int = 10) -> list[str]:
    commits = list(repo.iter_commits(max_count=max_count))
    log = []
    for commit in commits:
        log.append(
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message}\n"
        )
    return log

# def git_create_branch(repo: git.Repo, branch_name: str, base_branch: str | None = None) -> str:
#     if base_branch:
#         base = repo.refs[base_branch]
#     else:
#         base = repo.active_branch

#     repo.create_head(branch_name, base)
#     return f"Created branch '{branch_name}' from '{base.name}'"

def git_checkout(repo: git.Repo, branch_name: str) -> str:
    repo.git.checkout(b=branch_name)
    return f"Initialized new working checkout path: '{branch_name}'"

# def git_init(repo_path: str) -> str:
#     try:
#         repo = git.Repo.init(path=repo_path, mkdir=True)
#         return f"Initialized empty Git repository in {repo.git_dir}"
#     except Exception as e:
#         return f"Error initializing repository: {str(e)}"

def git_show(repo: git.Repo, revision: str) -> str:
    commit = repo.commit(revision)
    output = [
        f"Commit: {commit.hexsha}\n"
        f"Author: {commit.author}\n"
        f"Date: {commit.authored_datetime}\n"
        f"Message: {commit.message}\n"
    ]
    if commit.parents:
        parent = commit.parents[0]
        diff = parent.diff(commit, create_patch=True)
    else:
        diff = commit.diff(git.NULL_TREE, create_patch=True)
    for d in diff:
        output.append(f"\n--- {d.a_path}\n+++ {d.b_path}\n")
        output.append(d.diff.decode('utf-8'))
    return "".join(output)
