import subprocess
import os
from github import Github, InputGitTreeElement, GithubException
import base64
import time
import logging

logger = logging.getLogger(__name__)

class GitHelper:
    def __init__(self, repo_full_name, token, default_branch):
        self.repo_full_name = repo_full_name
        self.token = token
        self.clone_path = f"/tmp/{repo_full_name.replace('/', '_')}"
        self.default_branch = default_branch
        self.github_api = Github(token)
        self.repo = self.github_api.get_repo(repo_full_name)
        logger.info(f"GitHelper initialized for repo: {repo_full_name}")

    def _get_auth_url(self):
        """Get the authenticated Git URL with the installation token"""
        if not self.token:
            raise ValueError("No GitHub token provided")
        return f"https://x-access-token:{self.token}@github.com/{self.repo_full_name}.git"

    def clone_repo(self):
        logger.info(f"Cloning repo {self.repo_full_name} to {self.clone_path}")
        if os.path.exists(self.clone_path):
            logger.info("Clone path exists, removing and re-cloning.")
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
                    logger.error(f"Error processing file {file_content.path}: {e}")

    def create_branch(self, branch_name: str, from_branch: str = "") -> None:
        """Create a new branch from a base branch"""
        logger.info(f"Creating branch '{branch_name}' from '{from_branch or self.default_branch}'")
        try:
            source_branch = from_branch if from_branch else self.default_branch
            source = self.repo.get_branch(source_branch)
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Successfully created branch '{branch_name}'")
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                logger.warning(f"Branch '{branch_name}' already exists. Not creating again.")
            else:
                logger.error(f"Error creating branch '{branch_name}': {e}")
                raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while creating branch '{branch_name}': {e}")
            raise

    def switch_branch(self, branch_name: str) -> None:
        """Switch to a different branch"""
        logger.info(f"Switching to branch '{branch_name}'")
        try:
            ref = self.repo.get_git_ref(f"heads/{branch_name}")
            if not ref:
                raise ValueError(f"Branch {branch_name} does not exist")
                
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
                        
            logger.info(f"Successfully switched to branch '{branch_name}'")
        except Exception as e:
            logger.error(f"Error switching to branch '{branch_name}': {e}")
            raise

    def commit_and_push(self, commit_message: str, branch: str = "") -> None:
        """
        Commit and push changes to a specific branch
        """
        logger.info(f"Committing and pushing to branch '{branch or self.default_branch}'")
        try:
            target_branch = branch or self.default_branch
            branch_ref = self.repo.get_branch(target_branch)
            latest_commit = self.repo.get_commit(branch_ref.commit.sha)
            
            tree_elements = []
            for root, _, files in os.walk(self.clone_path):
                for name in files:
                    file_path = os.path.join(root, name)
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    repo_path = os.path.relpath(file_path, self.clone_path)
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
            
            new_tree = self.repo.create_git_tree(
                tree_elements,
                base_tree=latest_commit.commit.tree
            )
            new_commit = self.repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[latest_commit.commit]
            )
            
            ref = self.repo.get_git_ref(f"heads/{target_branch}")
            ref.edit(new_commit.sha)
            
            logger.info(f"Successfully committed and pushed to '{target_branch}'")
        except Exception as e:
            logger.error(f"Error in commit_and_push: {e}")
            raise

    def cleanup_branch(self, branch_name: str) -> None:
        """Delete a branch (useful for cleaning up after PR creation)"""
        logger.info(f"Cleaning up branch '{branch_name}'")
        try:
            ref = self.repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
            logger.info(f"Successfully deleted branch '{branch_name}'")
        except Exception as e:
            logger.error(f"Error cleaning up branch '{branch_name}': {e}")
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
        """
        logger.info(f"Creating pull request from '{head_branch}' to '{base_branch}'")
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            logger.info(f"Successfully created PR #{pr.number}: {pr.html_url}")
            return {
                'number': pr.number,
                'html_url': pr.html_url,
                'title': pr.title,
                'state': pr.state
            }
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
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
        """
        logger.info(f"Starting commit and PR creation for issue #{issue_number}")
        try:
            target_base = base_branch or self.default_branch
            if not branch_name:
                branch_name = f"fix/issue-{issue_number}"
            
            logger.info(f"Step 1: Create new branch '{branch_name}' from '{target_base}'")
            self.create_branch(branch_name, from_branch=target_base)
            
            logger.info(f"Step 2: Switch to new branch '{branch_name}'")
            self.switch_branch(branch_name)
            
            logger.info(f"Step 3: Commit changes to '{branch_name}'")
            self.commit_and_push(commit_message, branch=branch_name)
            
            logger.info("Step 4: Create pull request")
            pr_result = self.create_pull_request(
                title=pr_title,
                head_branch=branch_name,
                base_branch=target_base,
                body=pr_body
            )
            
            logger.info("Commit and PR creation successful.")
            return {
                'success': True,
                'branch': branch_name,
                'pr': pr_result
            }
        except Exception as e:
            logger.error(f"Error in commit_and_create_pr for issue #{issue_number}: {e}")
            try:
                if branch_name:
                    self.cleanup_branch(branch_name)
            except:
                pass
            raise