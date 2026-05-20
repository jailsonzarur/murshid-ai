from fastapi import APIRouter

from src.features.resolutions.routes.create_resolution import router as create_resolution_router
from src.features.resolutions.routes.evaluate_question_response import router as evaluate_question_response_router
from src.features.resolutions.routes.evaluate_resolution import router as evaluate_resolution_router
from src.features.resolutions.routes.get_active_resolution import router as get_active_resolution_router
from src.features.resolutions.routes.get_exam_resolutions import router as get_exam_resolutions_router
from src.features.resolutions.routes.get_resolution import router as get_resolution_router
from src.features.resolutions.routes.pause_resolution import router as pause_resolution_router
from src.features.resolutions.routes.resume_resolution import router as resume_resolution_router
from src.features.resolutions.routes.submit_resolution import router as submit_resolution_router
from src.features.resolutions.routes.upsert_question_response import router as upsert_question_response_router

router = APIRouter(tags=["Resolutions"])

router.include_router(get_active_resolution_router, prefix="/exams")
router.include_router(get_exam_resolutions_router, prefix="/exams")
router.include_router(create_resolution_router, prefix="/exams")
router.include_router(get_resolution_router, prefix="/resolutions")
router.include_router(upsert_question_response_router, prefix="/resolutions")
router.include_router(evaluate_question_response_router, prefix="/resolutions")
router.include_router(evaluate_resolution_router, prefix="/resolutions")
router.include_router(pause_resolution_router, prefix="/resolutions")
router.include_router(resume_resolution_router, prefix="/resolutions")
router.include_router(submit_resolution_router, prefix="/resolutions")

__all__ = ["router"]
