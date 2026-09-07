export type LectureStatus = 'ACTIVE' | 'PAUSED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export type Subject = {
  id: string
  name: string
}

export type SubjectDocumentStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED'

export type SubjectDocument = {
  id: string
  subject_id: string
  title: string
  original_name: string
  mime_type: string
  size_bytes: number
  page_count: number | null
  status: SubjectDocumentStatus
  thumbnail_url: string | null
  icon_url: string | null
  created_at: string
}

export type SubjectDetail = Subject & {
  documents: SubjectDocument[]
}

export type PaginationMeta = {
  page: number
  items_per_page: number
  total_items: number
  total_pages: number
}

export type PaginatedSubjects = {
  meta: PaginationMeta
  subjects: SubjectDetail[]
}

export type LectureNode = {
  id: string
  parent_id: string | null
  label: string
  summary: string | null
}

export type LectureSegment = {
  id: string
  sequence: number
  transcript: string
  duration_seconds: number
  offset_seconds: number
  created_at: string
}

export type LectureSummary = {
  id: string
  user_id: string
  subject: Subject | null
  title: string | null
  status: LectureStatus
  duration_seconds: number
  nodes_count: number
  created_at: string
  updated_at: string
}

export type LectureDetail = {
  id: string
  user_id: string
  subject: Subject | null
  title: string | null
  status: LectureStatus
  duration_seconds: number
  summary: string | null
  nodes: LectureNode[]
  segments: LectureSegment[]
  created_at: string
  updated_at: string
}

export type ProcessSegmentResponse = {
  segment: LectureSegment
  insight_message: string | null
}

export type StartLecturePayload = {
  title?: string | null
  subject_id?: string | null
}
