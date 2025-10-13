from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from github import Github, Issue, GithubException
import os
import subprocess
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from git_helper import GitHelper

# Load environment variables from .env file
load_dotenv()
client = genai.Client()


app = FastAPI()

# Pydantic model for the request body
class NewIssue(BaseModel):
    title: str
    body: str
    number: int
    repo_full_name: str

class Command(BaseModel):
    command: str
    issue: NewIssue

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3003",
    "http://localhost:5173",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/issues")
def get_issues(repo: str = "expressjs/express"):
    try:
        g = Github(os.environ.get("GITHUB_TOKEN"))
        repo = g.get_repo(repo)
        issues = repo.get_issues(state="open").get_page(0)[:30]
        issue_list = []
        for issue in issues:
            issue_list.append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "repo_full_name": repo.full_name,
                }
            )
        return issue_list
    except GithubException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching issues from Github: {e}")


@app.post("/issues")
def create_issue(issue: NewIssue):
    # For now, just return the data that was sent
    return {"title": issue.title, "body": issue.body}

@app.get("/user/repos")
def get_user_repos():
    try:
        g = Github(os.environ.get("GITHUB_TOKEN"))
        user = g.get_user()
        repos = user.get_repos()
        repo_list = []
        for repo in repos:
            repo_list.append(repo.full_name)
        return repo_list
    except GithubException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching repositories from Github. Is your token valid? {e}")

@app.post("/run-command")
def run_command(command: Command):
    try:
        git_helper = GitHelper(command.issue.repo_full_name, os.environ.get("GITHUB_TOKEN"))
        git_helper.clone_repo()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning repository: {e}")

    file_contents = ""
    for root, _, files in os.walk(git_helper.clone_path):
        for name in files:
            file_path = os.path.join(root, name)
            # ignore .git files
            if ".git" in file_path:
                continue
            relative_path = os.path.relpath(file_path, git_helper.clone_path)
            with open(file_path, "r") as f:
                file_contents += f"--- {relative_path} ---\n"
                file_contents += f.read()
                file_contents += "\n"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Fix the issue shown by this bug: {command.command}, Issue Number: {command.issue.number}, Title: {command.issue.title}, Body: {command.issue.body}\n\nFile contents:\n{file_contents}\n\nReturn the full content of the modified file. The response should be in the format:\n<file_name>\n```<language>\n<file_content>\n```",
    )

    response_text = response.text
    file_name = response_text.split("\n")[0]
    file_content = "\n".join(response_text.split("\n")[2:-1])

    with open(os.path.join(git_helper.clone_path, file_name), "w") as f:
        f.write(file_content)

    try:
        git_helper.commit_and_push(f"Fix issue #{command.issue.number}: {command.issue.title}")
        return "Changes applied and committed successfully."
    except subprocess.CalledProcessError as e:
        return f"Error applying changes: {e}"
