from fastapi import APIRouter, Body, Depends, Request
from typing import List
from google import genai

router = APIRouter(prefix="/ai", tags=["ai"])

def get_gemini_client(request: Request) -> genai.Client:
    return request.app.state.gemini_client

@router.post("/sort-issues", response_model=List[str])
async def sort_issues(
    issue_titles: List[str] = Body(..., embed=True),
    client: genai.Client = Depends(get_gemini_client)
):
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
            model="gemini-1.5-flash",
            contents=prompt
        )

        if not response.text:
            return issue_titles[:5] # Fallback to the first 5

        sorted_titles = response.text.strip().split('\n')
        return sorted_titles

    except Exception as e:
        # In case of any error with the AI, fallback to the original list
        return issue_titles[:5]