import subprocess
import os

class GitHelper:
    def __init__(self, repo_full_name, token):
        self.repo_full_name = repo_full_name
        self.token = token
        self.clone_path = f"/tmp/{repo_full_name.replace('/', '_')}"

    def clone_repo(self):
        if os.path.exists(self.clone_path):
            # a reset and pull would be better
            subprocess.run(["rm", "-rf", self.clone_path], check=True)
        clone_url = f"https://{self.token}@github.com/{self.repo_full_name}.git"
        subprocess.run(["git", "clone", clone_url, self.clone_path], check=True)

    def commit_and_push(self, commit_message):
        subprocess.run(["git", "config", "user.name", "Gemini"], check=True, cwd=self.clone_path)
        subprocess.run(["git", "config", "user.email", "<>"], check=True, cwd=self.clone_path)
        subprocess.run(["git", "commit", "-am", commit_message], check=True, cwd=self.clone_path)
        subprocess.run(["git", "push"], check=True, cwd=self.clone_path)
