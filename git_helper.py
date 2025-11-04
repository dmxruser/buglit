import subprocess
import os
from github import Github, InputGitTreeElement
import base64
import time

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

    def create_branch(self, branch_name: str, from_branch: str = "") -> None:
        """Create a new branch from a base branch"""
        try:
            # Get the source branch (default to default_branch if not specified)
            source_branch = from_branch if from_branch else self.default_branch
            source = self.repo.get_branch(source_branch)
            
            # Create new branch reference
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            
            print(f"Created branch {branch_name} from {source_branch}")
            
        except Exception as e:
            print(f"Error creating branch: {e}")
            raise

    def switch_branch(self, branch_name: str) -> None:
        """Switch to a different branch"""
        try:
            # Get branch reference
            ref = self.repo.get_git_ref(f"refs/heads/{branch_name}")
            if not ref:
                raise ValueError(f"Branch {branch_name} does not exist")
                
            # Update working directory
            contents = [self.repo.get_contents("", ref=branch_name)]
            while contents:
                current = contents.pop()
                if isinstance(current, list):
                    contents.extend(current)
                elif current.type == "dir":
                    contents.append(self.repo.get_contents(current.path, ref=branch_name))
                else:
                    file_path = os.path.join(self.clone_path, current.path)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb') as f:
                        f.write(current.decoded_content)
                        
            print(f"Switched to branch {branch_name}")
            
        except Exception as e:
            print(f"Error switching branch: {e}")
            raise

    def commit_and_push(self, commit_message: str, branch: str = "") -> None:
        """
        Commit and push changes to a specific branch
        
        Args:
            commit_message: The commit message
            branch: Branch to commit to (defaults to default branch if empty)
        """
        try:
            # Use specified branch or default branch
            target_branch = branch or self.default_branch
            
            # Get the target branch's latest commit
            branch_ref = self.repo.get_branch(target_branch)
            latest_commit = self.repo.get_commit(branch_ref.commit.sha)
            
            # Create a new tree with the updated files
            tree_elements = []
            for root, _, files in os.walk(self.clone_path):
                for name in files:
                    file_path = os.path.join(root, name)
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Get path relative to repo root
                    repo_path = os.path.relpath(file_path, self.clone_path)
                    
                    # Create blob for file content
                    blob = self.repo.create_git_blob(
                        base64.b64encode(content).decode('utf-8'),
                        'base64'
                    )
                    tree_elements.append(
                        InputGitTreeElement(
                            path=repo_path,
                            mode='100644',
                            type='blob',
                            sha=blob.sha
                        )
                    )
            
            # Create new tree and commit
            new_tree = self.repo.create_git_tree(
                tree_elements,
                base_tree=latest_commit.commit.tree
            )
            new_commit = self.repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[latest_commit.commit]
            )
            
            # Update branch reference
            ref = self.repo.get_git_ref(f"refs/heads/{target_branch}")
            ref.edit(new_commit.sha)
            
            print(f"Successfully committed and pushed to {target_branch}")
                
        except Exception as e:
            print(f"Error in commit_and_push: {e}")
            raise

    def cleanup_branch(self, branch_name: str) -> None:
        """Delete a branch (useful for cleaning up after PR creation)"""
        try:
            ref = self.repo.get_git_ref(f"refs/heads/{branch_name}")
            ref.delete()
            print(f"Deleted branch {branch_name}")
        except Exception as e:
            print(f"Error cleaning up branch: {e}")
            raise

    def create_pull_request(
        self,
        title: str,
        head_branch: str,
        base_branch: str,
        body: str = ""
    ) -> dict:
        """
        Create a pull request
        
        Args:
            title: PR title
            head_branch: Source branch (the branch with your changes)
            base_branch: Target branch (usually 'main' or 'master')
            body: PR description/body text
            
        Returns:
            Dict with PR details
        """
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            print(f"Created PR #{pr.number}: {pr.html_url}")
            
            return {
                'number': pr.number,
                'html_url': pr.html_url,
                'title': pr.title,
                'state': pr.state
            }
            
        except Exception as e:
            print(f"Error creating pull request: {e}")
            raise

    def commit_and_create_pr(
        self,
        commit_message: str,
        pr_title: str,
        issue_number: int,
        pr_body: str = "",
        base_branch: str = None,
        branch_name: str = None
    ) -> dict:
        """
        Complete workflow: create branch, commit changes, and create PR
        
        Args:
            commit_message: Commit message for changes
            pr_title: Pull request title
            issue_number: The issue number to use for the branch name
            pr_body: Pull request description
            base_branch: Target branch for PR (defaults to default_branch)
            branch_name: Custom branch name (auto-generated if not provided)
            
        Returns:
            Dict with branch name, commit info, and PR details
        """
        try:
            # Use default branch if not specified
            target_base = base_branch or self.default_branch
            
            # Generate branch name if not provided
            if not branch_name:
                branch_name = f"fix/issue-{issue_number}"
            
            # Step 1: Create new branch from base
            print(f"Creating branch {branch_name} from {target_base}...")
            self.create_branch(branch_name, from_branch=target_base)
            
            # Step 2: Switch to new branch
            print(f"Switching to branch {branch_name}...")
            self.switch_branch(branch_name)
            
            # Step 3: Commit changes to new branch
            print(f"Committing changes to {branch_name}...")
            self.commit_and_push(commit_message, branch=branch_name)
            
            # Step 4: Create pull request
            print(f"Creating pull request...")
            pr_result = self.create_pull_request(
                title=pr_title,
                head_branch=branch_name,
                base_branch=target_base,
                body=pr_body
            )
            
            return {
                'success': True,
                'branch': branch_name,
                'pr': pr_result
            }
            
        except Exception as e:
            print(f"Error in commit_and_create_pr: {e}")
            # Try to clean up the branch if PR creation failed
            try:
                if branch_name:
                    self.cleanup_branch(branch_name)
            except:
                pass
            raise