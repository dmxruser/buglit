import subprocess
import os
from github import Github

class GitHelper:
    def __init__(self, repo_full_name, token, default_branch):
        self.repo_full_name = repo_full_name
        self.token = token
        self.clone_path = f"/tmp/{repo_full_name.replace('/', '_')}"
        self.default_branch = default_branch
        self.github_api = Github(token)
        self.repo = self.github_api.get_repo(repo_full_name)

    def _get_auth_url(self):
        """Get the authenticated Git URL with the installation token"""
        if not self.token:
            raise ValueError("No GitHub token provided")
        return f"https://x-access-token:{self.token}@github.com/{self.repo_full_name}.git"

    def clone_repo(self):
        if os.path.exists(self.clone_path):
            # For simplicity, we'll just remove and re-clone for now
            # A more sophisticated approach would be to update the existing files
            subprocess.run(["rm", "-rf", self.clone_path])

        os.makedirs(self.clone_path, exist_ok=True)
        
        contents = self.repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self.repo.get_contents(file_content.path))
            else:
                try:
                    file_path = os.path.join(self.clone_path, file_content.path)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb') as f:
                        f.write(file_content.decoded_content)
                except Exception as e:
                    print(f"Error processing file {file_content.path}: {e}")

    def commit_and_push(self, commit_message):
        try:
            # Get the default branch
            branch = self.repo.get_branch(self.default_branch)
            
            # Get the latest commit of the default branch
            latest_commit = self.repo.get_commit(branch.commit.sha)
            
            # Create a new tree with the updated files
            tree_elements = []
            for root, _, files in os.walk(self.clone_path):
                for name in files:
                    file_path = os.path.join(root, name)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # PyGithub expects paths relative to the repo root
                    repo_path = os.path.relpath(file_path, self.clone_path)
                    
                    # Create a blob for the file content
                    blob = self.repo.create_git_blob(content, 'utf-8')
                    tree_elements.append(
                        {
                            "path": repo_path,
                            "mode": '100644',  # file mode
                            "type": 'blob',
                            "sha": blob.sha
                        }
                    )
            
            # Create a new tree
            new_tree = self.repo.create_git_tree(tree_elements, base_tree=latest_commit.commit.tree)
            
            # Create a new commit
            new_commit = self.repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[latest_commit.commit]
            )
            
            # Update the branch reference
            ref = self.repo.get_git_ref(f"heads/{self.default_branch}")
            ref.edit(new_commit.sha)
            
            print("Successfully committed and pushed changes")
                
        except Exception as e:
            print(f"Error in commit_and_push: {e}")
            raise