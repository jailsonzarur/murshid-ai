import { listSubjectOptions } from './api'
import type { OptionPage } from '../components/ui/searchable-select'

export async function fetchSubjectOptions(search: string, page: number): Promise<OptionPage> {
  const { meta, data } = await listSubjectOptions(page, search)
  return { options: data, hasMore: meta.page < meta.total_pages }
}
