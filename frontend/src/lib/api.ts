import { clearAuthSession, getAuthorizationHeader } from './auth'
import { navigateTo } from './navigation'
import { showErrorToast } from './toast'
import type {
  Question,
  QuestionResponse,
  ResolutionDetail,
  ResolutionEvaluationTask,
  ResolutionMode,
  ResolutionSummary,
} from '../types/exam'
import type { OrderedExamUploadFile } from '../types/exam-upload'
import type {
  Category,
  LectureDetail,
  LectureSummary,
  ProcessSegmentResponse,
  StartLecturePayload,
} from '../types/lecture'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002'

type ApiEnvelope<TData> = {
  success: boolean
  errors: string[] | null
  data: TData | null
}

type ApiErrorPayload = {
  detail?: string | { msg?: string; message?: string }[]
  errors?: string[] | null
  message?: string
}

type ParseApiResponseOptions = {
  redirectOnUnauthorized?: boolean
  showGlobalErrors?: boolean
}

export type ApiErrorKind = 'global' | 'validation'

export class ApiError extends Error {
  kind: ApiErrorKind
  status: number

  constructor(message: string, status: number, kind: ApiErrorKind) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

export type SignInResponseData = {
  access_token: string
  refresh_token: string
  token_type: string
}

export type UserProfileResponseData = {
  name: string
  email: string
  role: string
}

export type ExamListItem = {
  id: string
  name: string
  general_subject: string | null
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  documents_count: number
  created_at: string
  updated_at: string
}

export type UploadExamResponseData = {
  exam_id: string
  message: string
}

export type DeleteExamResponseData = {
  exam_id: string
  message: string
}

function isValidationStatus(status: number) {
  return status === 400 || status === 409 || status === 422
}

function createApiError(message: string, status: number) {
  return new ApiError(message, status, isValidationStatus(status) ? 'validation' : 'global')
}

function handleUnauthorizedSession() {
  clearAuthSession()

  if (window.location.pathname !== '/login') {
    showErrorToast('Sua sessão expirou. Faça login novamente.')
    navigateTo('/login', { replace: true })
  }
}

function extractApiErrorMessage(payload: ApiErrorPayload) {
  if (payload.errors?.[0]) {
    return payload.errors[0]
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  if (Array.isArray(payload.detail)) {
    const firstDetail = payload.detail[0]
    const detailMessage = firstDetail?.msg ?? firstDetail?.message

    if (detailMessage) {
      return detailMessage
    }
  }

  return payload.message ?? 'Não foi possível concluir a requisição.'
}

async function fetchApi(input: RequestInfo | URL, init?: RequestInit) {
  try {
    return await fetch(input, init)
  } catch {
    const message = 'Não foi possível conectar à API.'
    showErrorToast(message)
    throw new ApiError(message, 0, 'global')
  }
}

async function parseApiResponse<TData>(
  response: Response,
  options: ParseApiResponseOptions = {},
) {
  const { redirectOnUnauthorized = true, showGlobalErrors = true } = options
  let payload: ApiEnvelope<TData> & ApiErrorPayload

  try {
    payload = (await response.json()) as ApiEnvelope<TData> & ApiErrorPayload
  } catch {
    if (response.status === 401 && redirectOnUnauthorized) {
      handleUnauthorizedSession()
      throw new ApiError('Sessão expirada.', response.status, 'global')
    }

    const message = 'A API retornou uma resposta inválida.'
    showErrorToast(message)
    throw new ApiError(message, response.status || 500, 'global')
  }

  if (response.status === 401 && redirectOnUnauthorized) {
    handleUnauthorizedSession()
    throw new ApiError(extractApiErrorMessage(payload), response.status, 'global')
  }

  if (!response.ok || !payload.success || payload.data === null) {
    const message = extractApiErrorMessage(payload)
    const error = createApiError(message, response.status)

    if (error.kind === 'global' && showGlobalErrors) {
      showErrorToast(message)
    }

    throw error
  }

  return payload.data
}

export async function signIn(email: string, password: string) {
  const response = await fetchApi(`${API_BASE_URL}/auth/sign-in`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })

  return parseApiResponse<SignInResponseData>(response, { redirectOnUnauthorized: false })
}

export async function getProfile() {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/auth/profile`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<UserProfileResponseData>(response)
}

export async function getExams() {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ExamListItem[]>(response)
}

export async function uploadExam(
  name: string,
  generalSubject: string,
  files: OrderedExamUploadFile[],
) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const formData = new FormData()
  formData.append('name', name)

  if (generalSubject.trim()) {
    formData.append('general_subject', generalSubject.trim())
  }

  formData.append(
    'file_order',
    JSON.stringify(
      files.map((item, index) => ({
        client_id: item.id,
        file_name: item.file.name,
        page_order: index + 1,
      })),
    ),
  )

  files.forEach((item) => {
    formData.append('files', item.file, `${item.id}__${item.file.name}`)
  })

  const response = await fetchApi(`${API_BASE_URL}/exams/upload`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
    body: formData,
  })

  return parseApiResponse<UploadExamResponseData>(response)
}

export async function deleteExam(examId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams/${examId}`, {
    method: 'DELETE',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<DeleteExamResponseData>(response)
}

export async function getExamQuestions(examId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams/${examId}/questions`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<Question[]>(response)
}

export async function getActiveExamResolution(examId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams/${examId}/resolutions/active`, {
    headers: {
      Authorization: authorization,
    },
  })

  if (response.status === 404) {
    return null
  }

  return parseApiResponse<ResolutionSummary>(response)
}

export async function getExamResolutions(examId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams/${examId}/resolutions`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ResolutionSummary[]>(response)
}

export async function createExamResolution(examId: string, mode: ResolutionMode) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/exams/${examId}/resolutions`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mode }),
  })

  return parseApiResponse<ResolutionSummary>(response)
}

export async function getResolution(resolutionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ResolutionDetail>(response)
}

export type UpsertQuestionResponseItem = {
  option_id?: string
  text_answer?: string
}

export async function upsertQuestionResponse(
  resolutionId: string,
  questionId: string,
  items: UpsertQuestionResponseItem[],
) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/questions/${questionId}/response`, {
    method: 'PUT',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ items }),
  })

  return parseApiResponse<QuestionResponse>(response)
}

export async function evaluateResolutionQuestion(resolutionId: string, questionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/questions/${questionId}/evaluate`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<QuestionResponse>(response)
}

export async function evaluateResolution(resolutionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/evaluate`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ResolutionEvaluationTask>(response)
}

export async function pauseResolution(resolutionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/pause`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ResolutionSummary>(response)
}

export async function resumeResolution(resolutionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/resume`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<ResolutionSummary>(response)
}

export async function submitResolution(resolutionId: string) {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  const response = await fetchApi(`${API_BASE_URL}/resolutions/${resolutionId}/submit`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<{ resolution: ResolutionSummary }>(response)
}

function requireAuth() {
  const authorization = getAuthorizationHeader()

  if (!authorization) {
    handleUnauthorizedSession()
    throw new ApiError('Sessão não encontrada.', 401, 'global')
  }

  return authorization
}

export async function listCategories() {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/categories`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<Category[]>(response)
}

export async function createCategory(name: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/categories`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  })

  return parseApiResponse<Category>(response)
}

export async function updateCategory(categoryId: string, name: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/categories/${categoryId}`, {
    method: 'PATCH',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  })

  return parseApiResponse<Category>(response)
}

export type DeleteCategoryResponseData = {
  category_id: string
  message: string
}

export async function deleteCategory(categoryId: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/categories/${categoryId}`, {
    method: 'DELETE',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<DeleteCategoryResponseData>(response)
}

export async function listLectures() {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<LectureSummary[]>(response)
}

export async function getLecture(lectureId: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures/${lectureId}`, {
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<LectureDetail>(response)
}

export async function startLecture(payload: StartLecturePayload) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return parseApiResponse<LectureSummary>(response)
}

export async function pauseLecture(lectureId: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures/${lectureId}/pause`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<LectureSummary>(response)
}

export async function resumeLecture(lectureId: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures/${lectureId}/resume`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<LectureSummary>(response)
}

export async function finishLecture(lectureId: string) {
  const authorization = requireAuth()

  const response = await fetchApi(`${API_BASE_URL}/lectures/${lectureId}/finish`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
  })

  return parseApiResponse<LectureSummary>(response)
}

export async function processLectureSegment(
  lectureId: string,
  audio: Blob,
  sequence: number,
  duration: number,
  filename = `segment_${sequence}.webm`,
) {
  const authorization = requireAuth()

  const formData = new FormData()
  formData.append('audio', audio, filename)
  formData.append('sequence', String(sequence))
  formData.append('duration', String(duration))

  const response = await fetchApi(`${API_BASE_URL}/lectures/${lectureId}/segments`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
    },
    body: formData,
  })

  return parseApiResponse<ProcessSegmentResponse>(response)
}
