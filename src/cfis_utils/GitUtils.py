from src.cfis_utils.TerminalUtils import TerminalUtils
import re

class GitUtils:
    
    @staticmethod
    def clone(repo_url: str, path: str):
        """
        Clone a git repository to the specified path.
        """
        return TerminalUtils.run_command(f"cd {path} && git clone {repo_url} .", interactive=True)
    
    @staticmethod
    def checkout(branch: str, path:  str):
        """
        Checkout a specific branch in the git repository.
        """
        return TerminalUtils.run_command(f"cd {path} && git checkout {branch}", interactive=False)
    
    @staticmethod
    def pull(path: str):
        """
        Pull the latest changes from the remote repository.
        """
        return TerminalUtils.run_command(f"cd {path} && git pull", interactive=True)
    
    @staticmethod
    def get_remote_branches(path: str):
        """
        Get the list of remote branches in the git repository.
        """
        result =  TerminalUtils.run_command(f"cd {path} && git branch -r", interactive=False)
        if result.exit_code != 0:
            return None
        branches = [ "/".join(x.strip().split('/')[1:]) for x in result.stdout.splitlines() if "HEAD" not in x]
        return branches

    @staticmethod
    def get_current_branch(path: str):
        """
        Get the current branch in the git repository.
        """
        result = TerminalUtils.run_command(f"cd {path} && git branch --show-current", interactive=False)
        if result.exit_code != 0:
            return None
        return result.stdout.strip()

    @staticmethod
    def get_current_tag(path: str):
        """
        Get the current tag in the git repository.
        """
        result = TerminalUtils.run_command(f"cd {path} && git describe --tags", interactive=False)
        if result.exit_code != 0:
            return None
        return result.stdout.strip()

    @staticmethod
    def get_tags(path: str):
        """
        Get the list of tags in the git repository.
        """
        result = TerminalUtils.run_command(f"cd {path} && git --no-pager tag --sort=-creatordate", interactive=False)
        if result.exit_code != 0:
            return None
        tags = result.stdout.splitlines()
        return [tag.strip() for tag in tags if tag.strip()]

    @staticmethod
    def fetch(path: str):
        """
        Fetch changes from the remote repository.
        """
        return TerminalUtils.run_command(f"cd {path} && git fetch", interactive=True)
    
    @staticmethod
    def create_tag(tag_name: str, path: str):
        """
        Create a new lightweight tag in the git repository.
        """
        return TerminalUtils.run_command(f"cd {path} && git tag {tag_name}", interactive=False)

    @staticmethod
    def push_tag(tag_name: str, path: str):
        """
        Push a specific tag to the remote repository (assumed 'origin').
        """
        return TerminalUtils.run_command(f"cd {path} && git push origin {tag_name}", interactive=True)

    @staticmethod
    def check_sync_status(path: str):
        """
        Checks if the working directory/staging area are clean AND if the branch
        is synchronized with its remote counterpart using 'git status -sb'.

        Returns:
            bool: True if clean (no file changes AND branch is not ahead/behind remote), False otherwise.
            str: Status message ("clean", "uncommitted changes or untracked files",
                 "branch is ahead or behind remote", "error").
        """
        # 1. Run git status -sb
        command = f"cd {path} && git status -sb"
        status_result = TerminalUtils.run_command(command, interactive=False)

        if status_result.exit_code != 0:
            error_msg = f"error: 'git status -sb' failed. Stderr: {status_result.stderr.strip()}"
            return False, error_msg

        # 2. Check the output.
        output_lines = status_result.stdout.strip().splitlines()

        if not output_lines:
             final_status = "error: no output from 'git status -sb'"
             is_clean = False
             return is_clean, final_status

        # Check for file changes (any line other than the first '##' line)
        if len(output_lines) > 1:
            final_status = "uncommitted changes or untracked files"
            is_clean = False
        # If only the branch status line exists, check if it's ahead or behind
        elif output_lines[0].startswith("##"):
            branch_status_line = output_lines[0]
            # Use regex to check for [ahead N] or [behind M]
            if re.search(r"\[(ahead|behind) \d+\]", branch_status_line):
                final_status = "branch is ahead or behind remote"
                is_clean = False
            else:
                # Only the branch line, and it's not ahead/behind
                final_status = "clean"
                is_clean = True
        else:
            # Unexpected output format (e.g., doesn't start with ##)
             final_status = "error: unexpected output format from 'git status -sb'"
             is_clean = False

        # Return
        return is_clean, final_status