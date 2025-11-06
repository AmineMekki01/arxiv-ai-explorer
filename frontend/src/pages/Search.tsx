import React, { useEffect, useMemo, useState } from 'react';
import { Box, Typography, Paper, Stack, IconButton, Button, Chip, Divider } from '@mui/material';
import { PushPin as PinIcon, PushPinOutlined as PinOutlineIcon, PlayArrow as RunIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { apiHelpers } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface HistoryItem {
  id: string;
  query: string;
  created_at: string;
  params?: any;
  results_count?: string;
}

const SearchPage: React.FC = () => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [pinned, setPinned] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('pinned_queries') || '[]'); } catch { return []; }
  });
  const setPinnedPersist = (next: string[]) => {
    setPinned(next);
    try { localStorage.setItem('pinned_queries', JSON.stringify(next)); } catch {}
  };
  const togglePin = (q: string) => setPinnedPersist(pinned.includes(q) ? pinned.filter(x => x !== q) : [q, ...pinned].slice(0, 50));

  const load = async () => {
    setLoading(true);
    const res = await apiHelpers.listHistory(50);
    if (res.success) setItems(res.items || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const pinnedSet = useMemo(() => new Set(pinned), [pinned]);
  const pinnedItems = items.filter(i => pinnedSet.has(i.query));
  const otherItems = items.filter(i => !pinnedSet.has(i.query));

  const renderCard = (it: HistoryItem) => {
    const when = it.created_at ? new Date(it.created_at) : null;
    const topFull = Array.isArray(it.params?.top_sources_full) ? (it.params.top_sources_full as Array<{ title: string; arxiv_id?: string }>).slice(0, 3) : [];
    const top = topFull.length > 0
      ? topFull.map(t => t.title)
      : (Array.isArray(it.params?.top_sources) ? (it.params.top_sources as string[]).slice(0, 3) : []);
    const chatId = typeof it.params?.chat_id === 'string' ? it.params.chat_id : undefined;
    const resultsCount = it.results_count !== undefined && it.results_count !== null ? Number(it.results_count) : undefined;
    return (
      <Paper key={it.id} variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" alignItems="flex-start" spacing={1}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
              {it.query}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1, mb: top.length ? 1 : 0 }}>
              {resultsCount !== undefined && (
                <Chip size="small" label={`${resultsCount} ${resultsCount === 1 ? 'paper' : 'papers'}`} />
              )}
              {when && (
                <Chip size="small" label={when.toLocaleString()} variant="outlined" />
              )}
            </Stack>
            {top.length > 0 && (
              <>
                <Typography variant="caption" color="text.secondary">Top sources</Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
                  {(topFull.length > 0 ? topFull : top.map(t => ({ title: t } as any))).map((t: any, idx: number) => (
                    <Chip
                      key={idx}
                      size="small"
                      variant="outlined"
                      label={
                        t.arxiv_id ? (
                          <span>
                            {t.title}
                            {' '}
                            <a href={`https://arxiv.org/abs/${t.arxiv_id}`} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                              ↗
                            </a>
                          </span>
                        ) : t.title
                      }
                    />
                  ))}
                </Stack>
              </>
            )}
          </Box>
          <Stack direction="row" spacing={1} sx={{ ml: 'auto' }}>
            <Button size="small" variant="contained" startIcon={<RunIcon />} onClick={() => navigate(chatId ? `/research/${encodeURIComponent(chatId)}?q=${encodeURIComponent(it.query)}` : `/research?q=${encodeURIComponent(it.query)}`)}>
              {chatId ? 'Open Chat' : 'Rerun'}
            </Button>
            <IconButton onClick={() => togglePin(it.query)} color={pinnedSet.has(it.query) ? 'primary' : 'default'}>
              {pinnedSet.has(it.query) ? <PinIcon /> : <PinOutlineIcon />}
            </IconButton>
          </Stack>
        </Stack>
      </Paper>
    );
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>Search</Typography>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>Refresh</Button>
      </Stack>

      {loading && (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography color="text.secondary">Loading...</Typography>
        </Paper>
      )}

      {pinnedItems.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary' }}>Pinned</Typography>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            {pinnedItems.map(renderCard)}
          </Stack>
        </Box>
      )}

      <Typography variant="overline" sx={{ color: 'text.secondary' }}>Recent</Typography>
      <Stack spacing={1.5} sx={{ mt: 1 }}>
        {otherItems.map(renderCard)}
        {!loading && items.length === 0 && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography color="text.secondary">No history yet. Run a search in the Research Workspace.</Typography>
          </Paper>
        )}
      </Stack>
    </Box>
  );
};

export default SearchPage;
