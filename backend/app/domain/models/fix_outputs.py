from pydantic import BaseModel


class PRDescriptionOutput(BaseModel):
    """Fix Manager's LLM output: a PR title/body summarizing a FixGroup."""

    title: str
    body: str


class ProposedPatchOutput(BaseModel):
    """Fix Worker's LLM output for one file - file_path is supplied by the
    caller (from the finding's originating task scope), not generated here.
    """

    new_content: str
    commit_message: str
