from fastapi import APIRouter, Body, HTTPException, status
from typing import List, Dict
from google import genai
import os
import json
from config import settings # Import settings

router = APIRouter(prefix="/ai", tags=["ai"])

client = genai.Client(api_key=settings.GEMINI_API_KEY) # Pass API key explicitly

@router.post("/sort-issues", response_model=List[str])
async def sort_issues(issue_titles: List[str] = Body(..., embed=True)):
    """
    Sorts issues by importance using the Gemini API.
    """
    try:
        prompt = (
            f"From the following list of issue titles, identify the top 3-5 most critical. "
            f"Return only the titles, separated by newlines.\n\n"
            f"Issue Titles:\n{', '.join(issue_titles)}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if not response.text:
            return issue_titles[:5] # Fallback to the first 5

        sorted_titles = response.text.strip().split('\n')
        return sorted_titles

    except Exception as e:
        # In case of any error with the AI, fallback to the original list
        return issue_titles[:5]

@router.post("/categorize-issues", response_model=Dict[str, List[str]])
async def categorize_issues(issue_titles: List[str] = Body(..., embed=True)):
    """
    Categorizes issues into Major, Minor, or Bug using the Gemini API.
    """
    try:
        prompt = (
            f"Categorize the following issue titles into 'Major', 'Minor', or 'Bug'. "
            f"Return the result as a JSON object with keys 'Major', 'Minor', and 'Bug', "
            f"and the values as lists of the issue titles.\n\n"
            f"Issue Titles:\n{', '.join(issue_titles)}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if not response.text:
            return {"Major": [], "Minor": issue_titles, "Bug": []}

        # Clean the response to extract only the JSON part
        json_response_str = response.text.strip()
        if json_response_str.startswith("```json"):
            json_response_str = json_response_str[7:-3].strip()

        categorized_issues = json.loads(json_response_str)
        return categorized_issues

    except Exception as e:
        # Fallback in case of any error
        return {"Major": [], "Minor": issue_titles, "Bug": []}
