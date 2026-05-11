from fastapi import APIRouter

from src.features.categories.models import CategoryModel  # noqa: F401
from src.features.exams.routes.delete_exam import router as delete_exam_router
from src.features.exams.routes.get_exam_questions import router as get_exam_questions_router
from src.features.exams.routes.get_exams import router as get_exams_router
from src.features.exams.routes.upload_exam import router as upload_exam_router
from src.features.questions.models import OptionModel, QuestionModel  # noqa: F401

router = APIRouter(tags=["Exams"])

router.include_router(get_exams_router, prefix="/exams")
router.include_router(get_exam_questions_router, prefix="/exams")
router.include_router(upload_exam_router, prefix="/exams")
router.include_router(delete_exam_router, prefix="/exams")

__all__ = ["router"]
