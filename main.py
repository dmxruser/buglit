from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from github import Github, GithubException, Auth
import requests
import os
import subprocess
from pydantic import BaseModel
from dotenv import load_dotenv
import jwt
import time
from google import genai
from git_helper import GitHelper

# Load environment variables
load_dotenv()

# GitHub App credentials
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Load private key
try:
    with open("buglit.2025-10-15.private-key.pem", "r") as key_file:
        GITHUB_PRIVATE_KEY = key_file.read()
    
    if not GITHUB_PRIVATE_KEY.startswith('-----BEGIN RSA PRIVATE KEY-----'):
        raise ValueError("Invalid private key format")
except FileNotFoundError:
    raise RuntimeError("Private key file not found")
except ValueError as e:
    raise RuntimeError(f"Private key error: {e}")

# Initialize Gemini API - reads GEMINI_API_KEY from environment automatically
client = genai.Client()

app = FastAPI()

# Pydantic models
class NewIssue(BaseModel):
    title: str
    body: str
    number: int
    repo_full_name: str

class Command(BaseModel):
    command: str
    issue: NewIssue

# CORS configuration
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

# Helper functions
def create_jwt() -> str:
    """Create a JWT token for GitHub App authentication."""
    if not GITHUB_APP_ID:
        raise HTTPException(status_code=500, detail="GITHUB_APP_ID is not configured")
    
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + 600,
        'iss': int(GITHUB_APP_ID)
    }
    return jwt.encode(payload, GITHUB_PRIVATE_KEY, algorithm='RS256')

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
        print(f"Error fetching app installations: {e}")
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
        print(f"Error fetching repositories: {e}")
        return []

# Routes
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/login/github")
def login_github():
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}"
    )

@app.get("/auth/github/callback")
def auth_github_callback(code: str):
    """Handle GitHub OAuth callback."""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
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
    
    return RedirectResponse(f"http://localhost:3000/?token={access_token}")

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

@app.post("/run-command")
def run_command(command: Command):
    """Run a command to fix an issue."""
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
        
        # Read all files
        file_contents = ""
        for root, _, files in os.walk(git_helper.clone_path):
            if ".git" in root:
                continue
            
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    relative_path = os.path.relpath(file_path, git_helper.clone_path)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_contents += f"--- {relative_path} ---\n{f.read()}\n"
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")
        
        # Generate fix using Gemini
        prompt = (
            f"Fix the issue: {command.command}\n"
            f"Issue #{command.issue.number}: {command.issue.title}\n"
            f"Description: {command.issue.body}\n\n"
            f"File contents:\n{file_contents}\n\n"
            f"Return the full content of the modified file in this format:\n"
            f"<file_name>\n```<language>\n<file_content>\n```"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text
        
        # Parse response
        if response_text is not None:
            lines = response_text.split("\n")

        file_name = lines[0].strip()
        file_content = "\n".join(lines[2:-1])
        
        # Write changes
        file_path = os.path.join(git_helper.clone_path, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        # Commit and push
        git_helper.commit_and_push(
            f"Fix issue #{command.issue.number}: {command.issue.title}"
        )
        
        return {"message": "Changes applied and committed successfully", "status": "completed"}
    
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        raise HTTPException(status_code=400, detail=f"Git error: {e}")
    except Exception as e:
        print(f"Error in run_command: {e}")
        raise HTTPException(status_code=500, detail=str(e))