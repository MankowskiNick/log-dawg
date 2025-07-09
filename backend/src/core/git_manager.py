"""
Git repository management module
"""
import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from src.models.schemas import GitInfo, GitCommitInfo
from src.core.config import config_manager

class GitManager:
    """Manages git repository operations"""
    
    def __init__(self):
        self.config = config_manager.config
        self.settings = config_manager.settings
        self.repo_path = Path(self.config.repository.local_path)
        self._repo = None
        self._last_pull_time = None
        self.logger = logging.getLogger(f"{__name__}.GitManager")
        
        # Log initialization
        self.logger.info(f"GitManager initialized with repo_path: {self.repo_path}")
        self.logger.info(f"Target repository URL: {self.config.repository.url}")
        self.logger.info(f"Target branch: {self.config.repository.branch}")
        self.logger.info(f"Auth method: {self.config.repository.auth_method}")
    
    def _get_repo(self) -> Repo:
        """Get or initialize the git repository"""
        if self._repo is None:
            self.logger.debug(f"Initializing repository at path: {self.repo_path}")
            self.logger.debug(f"Repository path exists: {self.repo_path.exists()}")
            
            try:
                self._repo = Repo(self.repo_path)
                self.logger.info(f"Successfully opened existing repository at {self.repo_path}")
            except (InvalidGitRepositoryError, NoSuchPathError) as e:
                self.logger.info(f"Repository doesn't exist or is invalid: {e}")
                self.logger.info("Attempting to clone repository...")
                # Repository doesn't exist, clone it
                self._clone_repository()
                self._repo = Repo(self.repo_path)
                self.logger.info("Repository cloned and opened successfully")
        
        return self._repo
    
    def _clone_repository(self):
        """Clone the repository if it doesn't exist"""
        self.logger.info("Starting repository clone process")
        self.logger.debug(f"Creating parent directories for: {self.repo_path.parent}")
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build clone command with authentication
        clone_url = self._get_authenticated_url()
        self.logger.info(f"Cloning repository from {self.config.repository.url}")
        self.logger.debug(f"Target branch: {self.config.repository.branch}")
        self.logger.debug(f"Local path: {self.repo_path}")
        # Note: Not logging the full authenticated URL to avoid exposing tokens
        
        try:
            self.logger.info("Executing git clone command...")
            Repo.clone_from(clone_url, self.repo_path, branch=self.config.repository.branch)
            self.logger.info(f"Repository cloned successfully to {self.repo_path}")
        except GitCommandError as e:
            self.logger.error(f"Git clone command failed: {e}")
            self.logger.error(f"Clone URL (sanitized): {self.config.repository.url}")
            self.logger.error(f"Target branch: {self.config.repository.branch}")
            raise RuntimeError(f"Failed to clone repository: {e}")
    
    def _get_authenticated_url(self) -> str:
        """Get repository URL with authentication if needed"""
        url = self.config.repository.url
        
        if self.config.repository.auth_method == "token" and self.settings.git_token:
            # For HTTPS with token authentication
            if url.startswith("https://github.com/"):
                username = self.settings.git_username or "oauth2"
                return url.replace("https://", f"https://{username}:{self.settings.git_token}@")
            elif url.startswith("https://"):
                # Generic HTTPS with token
                return url.replace("https://", f"https://{self.settings.git_token}@")
        
        # For SSH or other auth methods, return as-is
        return url
    
    def pull_latest_changes(self, force: bool = True) -> Dict[str, Any]:
        """Pull latest changes from the repository"""
        self.logger.info("Starting git pull operation")
        
        try:
            repo = self._get_repo()
            
            # Log current repository state
            self.logger.debug(f"Repository working directory: {repo.working_dir}")
            self.logger.debug(f"Available remotes: {[r.name for r in repo.remotes]}")
            
            # Ensure we're on the correct branch
            target_branch = self.config.repository.branch
            current_branch = repo.active_branch.name
            
            self.logger.info(f"Target branch: {target_branch}")
            self.logger.info(f"Current branch: {current_branch}")
            self.logger.debug(f"Available local branches: {[b.name for b in repo.branches]}")
            
            # Fetch remote references first
            self.logger.info("Fetching remote references...")
            origin = repo.remotes.origin
            self.logger.debug(f"Origin remote URL: {origin.url}")
            
            try:
                fetch_info = origin.fetch()
                self.logger.info(f"Fetch completed. Fetched refs: {[str(info) for info in fetch_info]}")
                
                # Log available remote branches after fetch
                remote_refs = [ref.name for ref in origin.refs]
                self.logger.debug(f"Available remote refs after fetch: {remote_refs}")
                
            except GitCommandError as fetch_error:
                self.logger.error(f"Failed to fetch from remote: {fetch_error}")
                raise
            
            if current_branch != target_branch:
                self.logger.info(f"Need to switch from '{current_branch}' to '{target_branch}'")
                
                # Check if target branch exists locally
                local_branch_names = [b.name for b in repo.branches]
                if target_branch in local_branch_names:
                    self.logger.info(f"Checking out existing local branch: {target_branch}")
                    repo.git.checkout(target_branch)
                else:
                    # Check if remote branch exists
                    remote_branch_ref = f'origin/{target_branch}'
                    if remote_branch_ref in remote_refs:
                        self.logger.info(f"Creating new local branch '{target_branch}' tracking '{remote_branch_ref}'")
                        repo.git.checkout('-b', target_branch, remote_branch_ref)
                    else:
                        error_msg = f"Remote branch '{remote_branch_ref}' does not exist. Available remote refs: {remote_refs}"
                        self.logger.error(error_msg)
                        raise RuntimeError(error_msg)
            
            # Get current commit before pull
            old_commit = repo.head.commit.hexsha
            self.logger.info(f"Current commit before pull: {old_commit[:8]}")
            
            # Pull latest changes
            self.logger.info("Executing git pull...")
            pull_info = origin.pull()
            self.logger.info(f"Pull completed. Pull info: {[str(info) for info in pull_info]}")
            
            # Get new commit after pull
            new_commit = repo.head.commit.hexsha
            self.logger.info(f"Current commit after pull: {new_commit[:8]}")
            
            self._last_pull_time = datetime.now()
            
            result = {
                "success": True,
                "old_commit": old_commit,
                "new_commit": new_commit,
                "changes_pulled": old_commit != new_commit,
                "branch": target_branch,
                "pull_time": self._last_pull_time,
                "pull_info": [str(info) for info in pull_info]
            }
            
            if old_commit != new_commit:
                self.logger.info(f"Repository updated: {old_commit[:8]} -> {new_commit[:8]}")
            else:
                self.logger.info("Repository already up to date")
            
            return result
            
        except GitCommandError as e:
            error_msg = f"Git pull failed: {e}"
            self.logger.error(error_msg)
            self.logger.error(f"Git command that failed: {e.command}")
            self.logger.error(f"Git command stderr: {e.stderr}")
            return {
                "success": False,
                "error": error_msg,
                "pull_time": datetime.now()
            }
        except Exception as e:
            error_msg = f"Unexpected error during git pull: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "pull_time": datetime.now()
            }
    
    def get_git_info(self) -> GitInfo:
        """Get current git repository information"""
        try:
            repo = self._get_repo()
            
            current_commit = repo.head.commit.hexsha
            branch = repo.active_branch.name
            
            # Get recent commits
            recent_commits = []
            max_commits = self.config.git_analysis.max_commits_to_analyze
            
            for commit in repo.iter_commits(max_count=max_commits):
                commit_info = {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                    "changed_files": list(commit.stats.files.keys())
                }
                recent_commits.append(commit_info)
            
            # Get changed files from recent commits
            changed_files = set()
            for commit_info in recent_commits:
                changed_files.update(commit_info["changed_files"])
            
            return GitInfo(
                current_commit=current_commit,
                branch=branch,
                recent_commits=recent_commits,
                changed_files=list(changed_files),
                last_pull_time=self._last_pull_time or datetime.now()
            )
            
        except Exception as e:
            # Return minimal info if there's an error
            return GitInfo(
                current_commit="unknown",
                branch="unknown",
                recent_commits=[],
                changed_files=[],
                last_pull_time=datetime.now()
            )
    
    def get_recent_commits(self, max_count: int = None) -> List[GitCommitInfo]:
        """Get detailed information about recent commits"""
        if max_count is None:
            max_count = self.config.git_analysis.max_commits_to_analyze
        
        try:
            repo = self._get_repo()
            commits = []
            
            for commit in repo.iter_commits(max_count=max_count):
                # Get file changes
                changed_files = list(commit.stats.files.keys())
                
                # Filter by file extensions if configured
                if self.config.git_analysis.file_extensions_to_include:
                    filtered_files = []
                    for file_path in changed_files:
                        file_ext = Path(file_path).suffix
                        if file_ext in self.config.git_analysis.file_extensions_to_include:
                            filtered_files.append(file_path)
                    changed_files = filtered_files
                
                commit_info = GitCommitInfo(
                    hash=commit.hexsha,
                    author=str(commit.author),
                    date=commit.committed_datetime,
                    message=commit.message.strip(),
                    changed_files=changed_files,
                    additions=commit.stats.total['insertions'],
                    deletions=commit.stats.total['deletions']
                )
                commits.append(commit_info)
            
            return commits
            
        except Exception as e:
            print(f"Error getting recent commits: {e}")
            return []
    
    def get_file_content(self, file_path: str, commit_hash: str = None) -> Optional[str]:
        """Get content of a file at a specific commit"""
        try:
            repo = self._get_repo()
            
            if commit_hash:
                commit = repo.commit(commit_hash)
                try:
                    blob = commit.tree[file_path]
                    return blob.data_stream.read().decode('utf-8')
                except KeyError:
                    return None
            else:
                # Get current file content
                full_path = self.repo_path / file_path
                if full_path.exists():
                    return full_path.read_text(encoding='utf-8')
                return None
                
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get current git repository status"""
        try:
            repo = self._get_repo()
            
            return {
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files,
                "active_branch": repo.active_branch.name,
                "remote_url": repo.remotes.origin.url if repo.remotes else None,
                "last_commit": {
                    "hash": repo.head.commit.hexsha,
                    "message": repo.head.commit.message.strip(),
                    "author": str(repo.head.commit.author),
                    "date": repo.head.commit.committed_datetime.isoformat()
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "repository_exists": self.repo_path.exists()
            }
    
    def get_diff_context(self, file_paths: List[str], max_commits: int = 3) -> Dict[str, Any]:
        """Get diff context for specific files from recent commits"""
        try:
            repo = self._get_repo()
            context = {}
            
            for file_path in file_paths:
                file_context = {
                    "current_content": self.get_file_content(file_path),
                    "recent_changes": []
                }
                
                # Get recent commits that modified this file
                commits_with_file = list(repo.iter_commits(
                    paths=file_path, 
                    max_count=max_commits
                ))
                
                for i, commit in enumerate(commits_with_file):
                    if i < len(commits_with_file) - 1:
                        # Get diff with previous commit
                        prev_commit = commits_with_file[i + 1]
                        diff = repo.git.diff(prev_commit.hexsha, commit.hexsha, file_path)
                        
                        file_context["recent_changes"].append({
                            "commit": commit.hexsha[:8],
                            "author": str(commit.author),
                            "date": commit.committed_datetime.isoformat(),
                            "message": commit.message.strip(),
                            "diff": diff
                        })
                
                context[file_path] = file_context
            
            return context
            
        except Exception as e:
            print(f"Error getting diff context: {e}")
            return {}
