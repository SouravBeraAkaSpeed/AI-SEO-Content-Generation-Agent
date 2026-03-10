from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import JobCreate, ArticleJob, JobStatus
from services import AgentWorkflow
from dotenv import load_dotenv
load_dotenv()  

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SEO Content Agent API")


def run_job_background(job_id: str):
    # Create a fresh session for the background task
    db = next(get_db())
    workflow = AgentWorkflow(db)
    workflow.process_job(job_id)


@app.post("/jobs", response_model=dict)
def create_article_job(
    job_req: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    job = ArticleJob(
        topic=job_req.topic,
        target_word_count=job_req.target_word_count,
        language=job_req.language,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger background agent processing
    background_tasks.add_task(run_job_background, job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job successfully queued.",
    }


@app.get("/jobs/{job_id}", response_model=dict)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ArticleJob).filter(ArticleJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {"job_id": job.id, "status": job.status, "topic": job.topic}

    # Compare against the Enum, not raw strings
    if job.status == JobStatus.FAILED:
        response["error"] = job.error_message
    elif job.status == JobStatus.COMPLETED:
        response["result"] = job.final_output

    return response


@app.post("/jobs/{job_id}/retry")
def retry_failed_job(
    job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Demonstrates durability. Retries a failed job from its last successful state."""
    job = db.query(ArticleJob).filter(ArticleJob.id == job_id).first()
    
    # Compare against the Enum
    if not job or job.status != JobStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only FAILED jobs can be retried.")

    # Rollback status using Enum members, not strings
    if not job.serp_data:
        job.status = JobStatus.PENDING
    elif not job.outline_data:
        job.status = JobStatus.SERP_ANALYZED
    else:
        job.status = JobStatus.OUTLINE_GENERATED

    job.error_message = None
    db.commit()

    background_tasks.add_task(run_job_background, job.id)
    return {"message": f"Job {job_id} resuming from state: {job.status.value}"}