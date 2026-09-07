from fastapi import APIRouter

from src.features.subjects.routes.create_subject import router as create_subject_router
from src.features.subjects.routes.delete_subject import router as delete_subject_router
from src.features.subjects.routes.delete_subject_document import router as delete_document_router
from src.features.subjects.routes.list_subject_documents import router as list_documents_router
from src.features.subjects.routes.list_subject_options import router as list_options_router
from src.features.subjects.routes.list_subjects import router as list_subjects_router
from src.features.subjects.routes.poll_subjects import router as poll_subjects_router
from src.features.subjects.routes.update_subject import router as update_subject_router

router = APIRouter(tags=["Subjects"])

router.include_router(list_options_router, prefix="/subjects")
router.include_router(list_subjects_router, prefix="/subjects")
router.include_router(poll_subjects_router, prefix="/subjects")
router.include_router(create_subject_router, prefix="/subjects")
router.include_router(update_subject_router, prefix="/subjects")
router.include_router(delete_subject_router, prefix="/subjects")
router.include_router(list_documents_router, prefix="/subjects")
router.include_router(delete_document_router, prefix="/subjects")

__all__ = ["router"]
