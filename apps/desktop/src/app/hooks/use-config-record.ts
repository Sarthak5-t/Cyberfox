import { useQuery } from '@tanstack/react-query'

import { getCyberfoxConfigRecord } from '@/cyberfox'
import { queryClient, writeCache } from '@/lib/query-client'
import type { CyberfoxConfigRecord } from '@/types/cyberfox'

// One shared cache for the whole profile config record (`GET /api/config`).
// Every settings surface (MCP, model, config) reads and writes through this key
// so a save in one shows in the others, and revisiting a tab paints the cache
// instead of blanking on a fresh fetch.
//
// Distinct from session/hooks/use-cyberfox-config.ts, which is side-effecting —
// it pushes personality/cwd/voice/… into the session stores for live chat.
export const CYBERFOX_CONFIG_KEY = ['cyberfox-config-record'] as const

// staleTime 0 → serve cache instantly, background-revalidate on every mount.
export const useCyberfoxConfigRecord = () =>
  useQuery({ queryKey: CYBERFOX_CONFIG_KEY, queryFn: getCyberfoxConfigRecord, staleTime: 0 })

export const setCyberfoxConfigCache = writeCache<CyberfoxConfigRecord>(CYBERFOX_CONFIG_KEY)

export const invalidateCyberfoxConfig = () => queryClient.invalidateQueries({ queryKey: CYBERFOX_CONFIG_KEY })
