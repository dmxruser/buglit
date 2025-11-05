from fastapi import APIRouter, HTTPException
from main import get_issues, client
from models.schemas import Command, NewIssue
import os
import logging
import subprocess
from git_helper import GitHelper
from config import settings
from main import get_github_app_installation, create_jwt, get_installation_access_token
import json
import requests

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/gemini-cron")
def gemini_cron():
    """Run a command to fix an issue."""
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API is not configured")
    
    try:
        # 1. Get issues
        repo_full_name = "expressjs/express" # or get from config
        issues = get_issues(repo_full_name)
        if not issues:
            return {"message": "No open issues found."}
            
        # 2. Pick the first issue
        issue = issues[0]
        
        # 3. Create Command object
        command = Command(
            command=issue['title'],
            issue=NewIssue(
                number=issue['number'],
                title=issue['title'],
                body=issue['body'],
                repo_full_name=issue['repo_full_name']
            )
        )

        # Get installation and access token
        g = get_github_app_installation(command.issue.repo_full_name)
        repo = g.get_repo(command.issue.repo_full_name)
        
        # Get the installation ID to retrieve fresh token for GitHelper
        jwt_token = create_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        repo_owner, repo_name = command.issue.repo_full_name.split('/')
        inst_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/installation'
        inst_response = requests.get(inst_url, headers=headers)
        installation_id = inst_response.json()['id']
        installation_token = get_installation_access_token(installation_id)
        
        # Clone repository using GitHelper
        git_helper = GitHelper(
            command.issue.repo_full_name,
            installation_token,
            repo.default_branch
        )
        git_helper.clone_repo()
        
        # Read all files and get relative paths
        file_contents = ""
        relative_paths = []
        for root, _, files in os.walk(git_helper.clone_path):
            if ".git" in root:
                continue
            
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    relative_path = os.path.relpath(file_path, git_helper.clone_path)
                    relative_paths.append(relative_path)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_contents += f"--- {relative_path} ---\n{f.read()}\n"
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
        
        # Generate fix using Gemini
        prompt = (
            f"You are an AI software engineer. Your task is to fix the following issue.\n"
            f"Issue: {command.command}\n"
            f"Issue #{command.issue.number}: {command.issue.title}\n"
            f"Description: {command.issue.body}\n\n"
            f"Here is a list of files in the repository:\n"
            f"{chr(10).join(relative_paths)}\n\n"
            f"File contents:
{file_contents}
\n"
            f"Please provide a plan to fix the issue. The plan should be a sequence of actions.\n"
            f"The available actions are:\n"
            f"- `REPLACE`: replace a block of text in a file.\n"
            f"- `RUN`: run a shell command.\n"
            f"- `WRITE`: write content to a new file.\n"
            f"\n"
            f"You must respond with a JSON array of actions. Each action is an object with 'action', 'file_path' (for REPLACE/WRITE), 'old_string', 'new_string' (for REPLACE), 'content' (for WRITE), and 'command' (for RUN).\n"
            f"For the 'REPLACE' action, 'old_string' must be an exact match of the content to be replaced, including indentation.\n"
            f"Example response:\n"
            f"["
            f"  {{"
            f"    \"action\": \"REPLACE\",\n"
            f"    \"file_path\": \"src/main.py\",\n"
            f"    \"old_string\": \"    return a + b\",\n"
            f"    \"new_string\": \"    return a - b\"\n"
            f"  }},
"
            f"  {{"
            f"    \"action\": \"RUN\",\n"
            f"    \"command\": \"pytest\"\n"
            f"  }}
"
            f"]
"
            f"Now, provide the plan to fix the issue."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text
        
        # Parse response
        if response_text is None:
            raise HTTPException(status_code=500, detail="No response from Gemini")
        
        try:
            # Clean the response to extract only the JSON part
            json_response_text = response_text.strip()
            if json_response_text.startswith("```json"):
                json_response_text = json_response_text[7:]
            if json_response_text.endswith("```"):
                json_response_text = json_response_text[:-3]
            
            plan = json.loads(json_response_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response from Gemini: {response_text}")

        for step in plan:
            action = step.get("action")
            if action == "REPLACE":
                file_path_str = step.get("file_path")
                if not file_path_str:
                    raise HTTPException(status_code=400, detail=f"Invalid REPLACE action: missing file_path")
                
                file_path = os.path.join(git_helper.clone_path, file_path_str)
                old_string = step.get("old_string")
                new_string = step.get("new_string")
                
                if not all([old_string is not None, new_string is not None]):
                    raise HTTPException(status_code=400, detail=f"Invalid REPLACE action: {step}")

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content.replace(old_string, new_string)

                if content == new_content:
                    logger.warning(f"REPLACE action did not change file {file_path}. Old string might not have been found.")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

            elif action == "RUN":
                command_to_run = step.get("command")
                if not command_to_run:
                    raise HTTPException(status_code=400, detail=f"Invalid RUN action: {step}")
                
                result = subprocess.run(
                    command_to_run,
                    shell=True,
                    check=False,
                    cwd=git_helper.clone_path,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Command '{command_to_run}' executed with exit code {result.returncode}")
                if result.stdout:
                    logger.info(f"stdout:\n{result.stdout}")
                if result.stderr:
                    logger.error(f"stderr:\n{result.stderr}")
                
                if result.returncode != 0:
                    raise HTTPException(status_code=400, detail=f"Command '{command_to_run}' failed with exit code {result.returncode}:\n{result.stderr}")


            elif action == "WRITE":
                file_path_str = step.get("file_path")
                if not file_path_str:
                    raise HTTPException(status_code=400, detail=f"Invalid WRITE action: missing file_path")

                file_path = os.path.join(git_helper.clone_path, file_path_str)
                content = step.get("content")
                if content is None:
                    raise HTTPException(status_code=400, detail=f"Invalid WRITE action: {step}")
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        # Commit and create a pull request
        pr_title = f"Fix for issue #{command.issue.number}: {command.issue.title}"
        pr_body = f"Addresses issue #{command.issue.number}: {command.issue.title}\n\n{command.issue.body}"
        
        pr_result = git_helper.commit_and_create_pr(
            commit_message=pr_title,
            pr_title=pr_title,
            issue_number=command.issue.number,
            pr_body=pr_body,
            base_branch=repo.default_branch # Use the default branch as the base
        )
        
        return {"message": "Pull request created successfully", "status": "completed", "pr_info": pr_result}
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}")
        raise HTTPException(status_code=400, detail=f"Git error: {e}")
    except Exception as e:
        logger.error(f"Error in run_command: {e}")
        raise HTTPException(status_code=500, detail=str(e))