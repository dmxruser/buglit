import subprocess
import os

class GitHelper:
    def __init__(self, repo_full_name, token, default_branch):
        self.repo_full_name = repo_full_name
        self.token = token
        self.clone_path = f"/tmp/{repo_full_name.replace('/', '_')}"
        self.default_branch = default_branch

    def _get_auth_url(self):
        """Get the authenticated Git URL with the installation token"""
        if not self.token:
            raise ValueError("No GitHub token provided")
        return f"https://x-access-token:{self.token}@github.com/{self.repo_full_name}.git"

    def clone_repo(self):
        if os.path.exists(self.clone_path):
            # Update the existing repo
            try:
                # Configure the remote URL with the current token
                subprocess.run(
                    ["git", "remote", "set-url", "origin", self._get_auth_url()],
                    check=True,
                    cwd=self.clone_path,
                    capture_output=True,
                    text=True
                )
                subprocess.run(
                    ["git", "fetch", "origin", self.default_branch],
                    check=True,
                    cwd=self.clone_path,
                    capture_output=True,
                    text=True
                )
                subprocess.run(
                    ["git", "reset", "--hard", f"origin/{self.default_branch}"],
                    check=True,
                    cwd=self.clone_path,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Error updating repository: {e.stderr}")
                raise
        else:
            # Clone a fresh copy
            try:
                subprocess.run(
                    ["git", "clone", self._get_auth_url(), self.clone_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Error cloning repository: {e.stderr}")
                raise

    def commit_and_push(self, commit_message):
        try:
            # Configure Git user
            subprocess.run(
                ["git", "config", "user.name", "BugLit Bot"],
                check=True,
                cwd=self.clone_path,
                capture_output=True,
                text=True
            )
            subprocess.run(
                ["git", "config", "user.email", "bot@buglit.app"],
                check=True,
                cwd=self.clone_path,
                capture_output=True,
                text=True
            )
            
            # Configure the remote URL with the current token
            subprocess.run(
                ["git", "remote", "set-url", "origin", self._get_auth_url()],
                check=True,
                cwd=self.clone_path,
                capture_output=True,
                text=True
            )
            
            # Add all changes (including untracked files)
            subprocess.run(
                ["git", "add", "-A"],
                check=True,
                cwd=self.clone_path,
                capture_output=True,
                text=True
            )
            
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.clone_path,
                capture_output=True,
                text=True
            )
            
            # If there are changes (exit code 1 means differences exist)
            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    check=True,
                    cwd=self.clone_path,
                    capture_output=True,
                    text=True
                )
                subprocess.run(
                    ["git", "push", "origin", f"HEAD:{self.default_branch}"],
                    check=True,
                    cwd=self.clone_path,
                    capture_output=True,
                    text=True
                )
                print("Successfully committed and pushed changes")
            else:
                print("No changes to commit")
                
        except subprocess.CalledProcessError as e:
            print(f"Error in commit_and_push: {e.stderr}")
            raise