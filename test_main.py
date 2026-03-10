import pytest
from fastapi.testclient import TestClient
from main import app
from models import FinalArticleOutput, SEOMetadata, InternalLink, ExternalLink
from services import SEOValidator

client = TestClient(app)

# --- Dummy Data to satisfy Pydantic strict length validators ---
valid_internal_links = [
    InternalLink(anchor_text="link1", suggested_target_topic="topic1", context_for_placement="ctx1"),
    InternalLink(anchor_text="link2", suggested_target_topic="topic2", context_for_placement="ctx2"),
    InternalLink(anchor_text="link3", suggested_target_topic="topic3", context_for_placement="ctx3")
]

valid_external_links = [
    ExternalLink(source_name="src1", url_or_entity="url1", reason_for_citation="rsn1"),
    ExternalLink(source_name="src2", url_or_entity="url2", reason_for_citation="rsn2")
]
# -----------------------------------------------------------------

def test_create_job():
    response = client.post("/jobs", json={
        "topic": "best productivity tools for remote teams",
        "target_word_count": 1500
    })
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert response.json()["status"] == "PENDING"

def test_seo_validator_passes():
    valid_output = FinalArticleOutput(
        metadata=SEOMetadata(
            title_tag="15 Best Productivity Tools for Remote Teams (2025)",
            meta_description="Discover the top tools to boost your team's efficiency.",
            primary_keyword="Productivity Tools for Remote Teams",
            secondary_keywords=["collaboration software"]
        ),
        article_markdown="# Best Productivity Tools for Remote Teams\n\nIntroduction here...",
        internal_links=valid_internal_links, 
        external_references=valid_external_links, 
        faq_section=[]
    )
    assert SEOValidator.validate(valid_output) == True

def test_seo_validator_fails_missing_h1():
    invalid_output = FinalArticleOutput(
        metadata=SEOMetadata(
            title_tag="Best Tools", meta_description="Desc", 
            primary_keyword="Tools", secondary_keywords=[]
        ),
        article_markdown="Just starting without an H1 header...",
        internal_links=valid_internal_links, 
        external_references=valid_external_links, 
        faq_section=[]
    )
    with pytest.raises(ValueError, match="must start with an H1"):
        SEOValidator.validate(invalid_output)

def test_seo_validator_fails_missing_keyword_in_title():
    invalid_output = FinalArticleOutput(
        metadata=SEOMetadata(
            title_tag="Awesome Apps for Working from Home", # Missing primary keyword
            meta_description="Desc", 
            primary_keyword="Productivity Tools", secondary_keywords=[]
        ),
        article_markdown="# Productivity Tools\n\n...",
        internal_links=valid_internal_links, 
        external_references=valid_external_links, 
        faq_section=[]
    )
    with pytest.raises(ValueError, match="Primary keyword missing from Title Tag"):
        SEOValidator.validate(invalid_output)