import { clearAuthSession, getAuthorizationHeader } from './auth'
import { navigateTo } from './navigation'
import { showErrorToast } from './toast'
import type { Question } from '../types/exam'

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
  const { redirectOnUnauthorized = true } = options
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

    if (error.kind === 'global') {
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

export async function uploadExam(name: string, generalSubject: string, files: File[]) {
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

  files.forEach((file) => {
    formData.append('files', file)
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
