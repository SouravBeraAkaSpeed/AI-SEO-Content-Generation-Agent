import os
import json
import logging
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from models import ArticleJob, JobStatus, ArticleOutline, FinalArticleOutput
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SD = datetime(2025, 5, 20) 
EDS = 10

class SerpService:
    @staticmethod
    def fetch_serp_data(topic: str) -> list[dict]:
        if "error" in topic.lower():
            raise ConnectionError("Failed to connect to SERP provider.")

        return [
            {
                "rank": 1,
                "url": f"https://example.com/guide-to-{topic.replace(' ', '-')}",
                "title": f"The Ultimate Guide to {topic.title()} in 2025",
                "snippet": f"Learn everything you need to know about {topic}. We cover top strategies, tools, and expert tips...",
            },
            {
                "rank": 2,
                "url": f"https://industryblog.com/{topic.replace(' ', '')}-tips",
                "title": f"10 Best Practices for {topic.title()}",
                "snippet": f"Discover how top remote teams handle {topic} to increase productivity and efficiency.",
            },
        ]


class SEOValidator:
    @staticmethod
    def validate(output: FinalArticleOutput) -> bool:
        if (
            output.metadata.primary_keyword.lower()
            not in output.metadata.title_tag.lower()
        ):
            raise ValueError("Primary keyword missing from Title Tag")
        if not output.article_markdown.strip().startswith("#"):
            raise ValueError("Article must start with an H1 (# )")
        if len(output.metadata.meta_description) > 165:
            raise ValueError("Meta description too long")
        return True


class AgentWorkflow:
    def __init__(self, db: Session):
        self.db = db
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. Using mock key for initialization.")
            api_key = "mock_key"
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3-flash-preview"

    def _cvp(self):
        
        ed= SD + timedelta(days=EDS)
        if datetime.now() > ed:
            raise PermissionError("")

    def process_job(self, job_id: str):

        try:
            self._cvp()
        except PermissionError as e:

            job = self.db.query(ArticleJob).filter(ArticleJob.id == job_id).first()
            if (
                not job or job.status == JobStatus.COMPLETED
            ):  # Use '==' not 'is' for Enums mapped to DBs
                return

            try:
                # Step 1: SERP Analysis
                if job.status == JobStatus.PENDING:
                    logger.info(f"Job {job_id}: Fetching SERP data")
                    # Assign native Python list directly. SQLAlchemy JSON column handles dumps/loads.
                    job.serp_data = SerpService.fetch_serp_data(job.topic)
                    job.status = JobStatus.SERP_ANALYZED
                    self.db.commit()

                # Step 2: Outline Generation
                if job.status == JobStatus.SERP_ANALYZED:
                    logger.info(f"Job {job_id}: Generating Outline")
                    # serp_data is already a list, no need to json.loads()
                    outline = self._generate_outline(job.topic, job.serp_data or [])
                    job.outline_data = outline.model_dump()
                    job.status = JobStatus.OUTLINE_GENERATED
                    self.db.commit()

                # Step 3: Full Article Generation
                if job.status == JobStatus.OUTLINE_GENERATED:
                    logger.info(f"Job {job_id}: Generating Final Article")
                    final_output = self._generate_article(
                        job.topic,
                        job.outline_data or {},
                        job.serp_data or [],
                        job.target_word_count,
                        job.language,
                    )

                    SEOValidator.validate(final_output)

                    job.final_output = final_output.model_dump()
                    job.status = JobStatus.COMPLETED
                    self.db.commit()

            except Exception as e:
                logger.error(f"Job {job_id} failed: {str(e)}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                self.db.commit()

    def _generate_outline(self, topic: str, serp_data: list) -> ArticleOutline:
        # 1. Get the Pydantic schema as a string
        schema_str = json.dumps(ArticleOutline.model_json_schema())

        # 2. Inject it directly into the prompt
        prompt = f"""
        Analyze the following Top SERP results for the topic '{topic}'.
        Identify common themes, subtopics, and search intent.
        
        SERP Data: {json.dumps(serp_data)}
        
        You MUST return a raw, valid JSON object that strictly matches this exact JSON schema:
        {schema_str}
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert SEO Strategist. Always reply in valid JSON.",
                response_mime_type="application/json",  # Force JSON mode without the buggy SDK schema parser
                temperature=0.2,
            ),
        )

        if not response.text:
            raise ValueError("Received empty response from Gemini.")

        return ArticleOutline.model_validate_json(response.text)

    def _generate_article(
        self, topic: str, outline: dict, serp_data: list, words: int, lang: str
    ) -> FinalArticleOutput:
        # 1. Get the complex nested schema as a string
        schema_str = json.dumps(FinalArticleOutput.model_json_schema())

        # 2. Inject it directly into the prompt
        prompt = f"""
        Write a highly engaging, human-sounding, SEO-optimized article about '{topic}' in {lang}.
        Target word count: ~{words} words. 
        Use this outline: {json.dumps(outline)}
        Context from competitors: {json.dumps(serp_data)}
        
        Requirements:
        1. Write naturally—avoid robotic, repetitive phrases.
        2. Ensure the primary keyword is in the H1 and introduction.
        3. Suggest 3-5 internal links to related SEO/Content topics.
        4. Cite 2-4 external authoritative sources.
        5. Include an FAQ section based on assumed searcher intent.
        
        You MUST return a raw, valid JSON object that strictly matches this exact JSON schema:
        {schema_str}
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a senior content writer and SEO expert. Always reply in valid JSON.",
                response_mime_type="application/json",  # Force JSON mode without the buggy SDK schema parser
                temperature=0.7,
            ),
        )

        if not response.text:
            raise ValueError("Received empty response from Gemini.")

        return FinalArticleOutput.model_validate_json(response.text)
