from fastapi import APIRouter, Header, HTTPException
import os

router = APIRouter()

@router.post("/load-etl")
def load_etl(x_admin_key: str | None = Header(None)):
    if x_admin_key != os.getenv("ADMIN_LOAD_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    from scripts.run_etl import main as run_etl
    run_etl()
    return {"status": "OK", "message": "ETL completed successfully"}