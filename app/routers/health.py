from fastapi import APIRouter
from app.schemas import HealthStatus

router = APIRouter(tags=["system"])

@router.get(
    "/health",
    summary="Health & readiness status",
    description="""
### PURPOSE
Return a minimal response indicating that the API service is **alive**, responsive,
and able to accept incoming requests. This acts as a lightweight heartbeat endpoint.

### USE CASES
- Infrastructure probes such as Kubernetes **liveness** or **readiness** checks  
- External uptime monitoring services (e.g., UptimeRobot, StatusCake, Pingdom)  
- Load balancer health checks  
- Simple automation workflows to confirm the API is reachable  

### INTERPRETATION
- A response of `{"status": "ok"}` indicates the API process is up and serving requests  
- Does **not** validate database connectivity or dependencies unless extended  
- Ideal for systems that need a fast, low‑overhead “is the server up?” check  
""",
    response_model=HealthStatus,
    response_description="Health status response showing basic API availability",
    responses={
        200: {
            "description": "API is running normally",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            }
        }
    }
)
def health():
    return {"status": "ok"}