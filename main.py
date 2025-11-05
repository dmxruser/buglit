import os
import logging
import logging.config
import time
import jwt
import requests
import subprocess
from pathlib import Path
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import sys
from pathlib import Path
from github import Github, Auth, GithubException
from google import genai

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config import settings
from api.v1.api import api_router
from services.github_service import GitHubService
from models.schemas import NewIssue, Command
from git_helper import GitHelper

# Configure Gemini

client = genai.Client()


# Configure logging
logging.config.dictConfig({  # type: ignore
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not settings.DEBUG else "DEBUG",
    },
})

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BugLit application")
    
    # Ensure temp directory exists
    settings.TEMP_DIR.mkdir(exist_ok=True, parents=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down BugLit application")

app = FastAPI(
    title="BugLit API",
    description="API for BugLit - AI-powered bug fixing tool",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

app.state.gemini_client = client

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3003",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Mount API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files (for frontend)
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Helper functions
def create_jwt() -> str:
    """Create a JWT token for GitHub App authentication."""
    if not settings.GITHUB_APP_ID:
        raise HTTPException(status_code=500, detail="GITHUB_APP_ID is not configured")
    
    logger.info(f"Creating JWT for App ID: {settings.GITHUB_APP_ID}")
    
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + 600,
        'iss': int(settings.GITHUB_APP_ID)
    }
    
    try:
        key_str = settings.GITHUB_PRIVATE_KEY
        logger.info(f"Private key loaded. Starts with: '{key_str[:30]}', ends with: '{key_str[-30:]}'")
        
        # Use the private key bytes directly for JWT encoding
        return jwt.encode(payload, settings.private_key_bytes, algorithm='RS256')
        
    except Exception as e:
        logger.error(f"Error creating JWT: {str(e)}")
        if hasattr(settings, 'private_key_bytes'):
            logger.error(f"Key type: {type(settings.private_key_bytes).__name__}")
            logger.error(f"Key length: {len(settings.private_key_bytes) if hasattr(settings.private_key_bytes, '__len__') else 'N/A'}")
        raise HTTPException(status_code=500, detail="Failed to create authentication token")

def get_installation_access_token(installation_id: int) -> str:
    """Get an access token for a specific installation."""
    jwt_token = create_jwt()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    response = requests.post(url, headers=headers)
    
    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail="Could not get installation access token"
        )
    
    return response.json()['token']

def get_github_app_installation(repo_full_name: str) -> Github:
    """Get a Github instance for a specific repository."""
    jwt_token = create_jwt()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    repo_owner, repo_name = repo_full_name.split('/')
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/installation'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Could not get installation for {repo_full_name}"
        )
    
    installation_id = response.json()['id']
    access_token = get_installation_access_token(installation_id)
    
    # Use Auth.Token for newer PyGithub versions
    auth = Auth.Token(access_token)
    return Github(auth=auth)

def get_app_installations() -> list:
    """Get all installations of the GitHub App."""
    try:
        jwt_token = create_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(
            'https://api.github.com/app/installations',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching app installations: {e}")
        return []

def get_installation_repositories(installation_id: int) -> list:
    """Get repositories for a specific installation."""
    try:
        jwt_token = create_jwt()
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get installation token
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        token_response = requests.post(url, headers=headers, timeout=10)
        
        if token_response.status_code != 201:
            return []
        
        installation_token = token_response.json()['token']
        
        # Get repositories
        headers = {
            'Authorization': f'token {installation_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(
            'https://api.github.com/installation/repositories',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        return response.json().get('repositories', [])
    except Exception as e:
        logger.error(f"Error fetching repositories: {e}")
        return []

# Routes
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/login/github")
def login_github():
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}"
    )

@app.get("/api/auth/github/callback")
def auth_github_callback(code: str):
    """Handle GitHub OAuth callback."""
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code
    }
    headers = {"Accept": "application/json"}
    
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        params=params,
        headers=headers
    )
    
    access_token = response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")
    
    return RedirectResponse(f"{settings.FRONTEND_URL}/?token={access_token}")

@app.get("/issues")
def get_issues(repo: str = "expressjs/express"):
    """Get open issues from a repository."""
    try:
        g = get_github_app_installation(repo)
        repo_obj = g.get_repo(repo)
        issues = repo_obj.get_issues(state="open").get_page(0)[:30]
        
        return [
            {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "repo_full_name": repo_obj.full_name,
            }
            for issue in issues
        ]
    except GithubException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching issues: {e}")

@app.post("/issues")
def create_issue(issue: NewIssue):
    """Create an issue (placeholder)."""
    return {"title": issue.title, "body": issue.body}

@app.get("/user/repos")
async def get_user_repos():
    """Get all repositories accessible to the app."""
    try:
        installations = get_app_installations()
        if not installations:
            return []
        
        repo_list = []
        for installation in installations:
            installation_id = installation.get('id')
            if not installation_id:
                continue
            
            repos = get_installation_repositories(installation_id)
            repo_list.extend([repo['full_name'] for repo in repos if 'full_name' in repo])
        
        return repo_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import json
@app.post("/run-command")
def run_command(command: Command):
    """Run a command to fix an issue."""
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API is not configured")
    
    try:
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
            f"{'\\n'.join(relative_paths)}\n\n"
            f"File contents:\n{file_contents}\n\n"
            f"Please provide a plan to fix the issue. The plan should be a sequence of actions.\n"
            f"The available actions are:\n"
            f"- `REPLACE`: replace a block of text in a file.\n"
            f"- `RUN`: run a shell command.\n"
            f"- `WRITE`: write content to a new file.\n"
            f"\n"
            f"You must respond with a JSON array of actions. Each action is an object with 'action', 'file_path' (for REPLACE/WRITE), 'old_string', 'new_string' (for REPLACE), 'content' (for WRITE), and 'command' (for RUN).\n"
            f"For the 'REPLACE' action, 'old_string' must be an exact match of the content to be replaced, including indentation.\n"
            f"Example response:\n"
            f"[\n"
            f"  {{\n"
            f"    \"action\": \"REPLACE\",\n"
            f"    \"file_path\": \"src/main.py\",\n"
            f"    \"old_string\": \"    return a + b\",\n"
            f"    \"new_string\": \"    return a - b\"\n"
            f"  }},\n"
            f"  {{\n"
            f"    \"action\": \"RUN\",\n"
            f"    \"command\": \"pytest\"\n"
            f"  }}\n"
            f"]\n"
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