import enum
import uuid
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from database import Base



class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    SERP_ANALYZED = "SERP_ANALYZED"
    OUTLINE_GENERATED = "OUTLINE_GENERATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ArticleJob(Base):
    __tablename__ = "article_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic: Mapped[str] = mapped_column(String, index=True)
    target_word_count: Mapped[int] = mapped_column(Integer, default=1500)
    language: Mapped[str] = mapped_column(String, default="English")
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    serp_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    outline_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    final_output: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

# --- Pydantic Models (Unchanged) ---
class JobCreate(BaseModel):
    topic: str
    target_word_count: int = Field(default=1500, ge=500, le=3000)
    language: str = "English"

class SerpResult(BaseModel):
    rank: int
    url: str
    title: str
    snippet: str

class InternalLink(BaseModel):
    anchor_text: str
    suggested_target_topic: str
    context_for_placement: str

class ExternalLink(BaseModel):
    source_name: str
    url_or_entity: str
    reason_for_citation: str

class SEOMetadata(BaseModel):
    title_tag: str = Field(description="Max 60 chars, must include primary keyword")
    meta_description: str = Field(description="Max 160 chars, compelling call to action")
    primary_keyword: str
    secondary_keywords: List[str]

class ArticleOutline(BaseModel):
    h1: str
    sections: List[str] = Field(description="List of H2 and H3 headers based on SERP analysis")

class FinalArticleOutput(BaseModel):
    metadata: SEOMetadata
    article_markdown: str = Field(description="Full article in markdown with H1, H2, H3")
    internal_links: List[InternalLink] = Field(min_length=3, max_length=5)
    external_references: List[ExternalLink] = Field(min_length=2, max_length=4)
    faq_section: List[dict[str, str]] = Field(description="List of dicts with 'question' and 'answer'")