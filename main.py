from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from github import Github, Issue
import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Pydantic model for the request body
class NewIssue(BaseModel):
    title: str
    body: str

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3003",
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
            }
        )
    return issue_list

@app.post("/issues")
def create_issue(issue: NewIssue):
    # For now, just return the data that was sent
    return {"title": issue.title, "body": issue.body}
