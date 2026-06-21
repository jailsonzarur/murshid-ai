from fastapi import APIRouter

from src.features.lectures.routes.delete_lecture import router as delete_lecture_router
from src.features.lectures.routes.finish_lecture import router as finish_lecture_router
from src.features.lectures.routes.get_lecture import router as get_lecture_router
from src.features.lectures.routes.import_lecture import router as import_lecture_router
from src.features.lectures.routes.list_lectures import router as list_lectures_router
from src.features.lectures.routes.pause_lecture import router as pause_lecture_router
from src.features.lectures.routes.process_segment import router as process_segment_router
from src.features.lectures.routes.resume_lecture import router as resume_lecture_router
from src.features.lectures.routes.start_lecture import router as start_lecture_router

router = APIRouter(tags=["Lectures"])

router.include_router(start_lecture_router, prefix="/lectures")
router.include_router(list_lectures_router, prefix="/lectures")
router.include_router(get_lecture_router, prefix="/lectures")
router.include_router(pause_lecture_router, prefix="/lectures")
router.include_router(resume_lecture_router, prefix="/lectures")
router.include_router(finish_lecture_router, prefix="/lectures")
router.include_router(process_segment_router, prefix="/lectures")
router.include_router(delete_lecture_router, prefix="/lectures")
router.include_router(import_lecture_router, prefix="/lectures")

__all__ = ["router"]
