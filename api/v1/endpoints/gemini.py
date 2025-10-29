import os
import logging
import subprocess
from google import genai
from fastapi import HTTPException
from models.schemas import Command
from git_helper import GitHelper
from config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, client):
        self.client = client

    def generate_fix(self, command: Command, git_helper: GitHelper, relative_paths: list[str], file_contents: str):
        prompt = (
            f"Fix the issue: {command.command}\n"
            f"Issue #{command.issue.number}: {command.issue.title}\n"
            f"Description: {command.issue.body}\n\n"
            f"Here is a list of files in the repository:\n"
            f"{'\n'.join(relative_paths)}\n\n"
            f"File contents:\n{file_contents}\n\n"
            f"IMPORTANT: You MUST use one of the exact file paths from the list above in your response.\n"
            f"Return the full content of the modified file in this format:\n"
            f"<file_path>\n```<language>\n<file_content>\n```"
            f"Think about this step by step."
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            response_text = response.text

            if response_text is None:
                raise HTTPException(status_code=500, detail="No response from Gemini")

            lines = response_text.split("\n")

            if len(lines) < 3:
                raise HTTPException(status_code=500, detail="Invalid response format from Gemini")

            file_name = lines[0].strip()

            if file_name not in relative_paths:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file path provided by AI: {file_name}. Must be one of {', '.join(relative_paths)}"
                )

            file_content = "\n".join(lines[2:-1])

            return file_name, file_content

        except Exception as e:
            logger.error(f"Error generating fix with Gemini: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating fix with Gemini: {e}")

