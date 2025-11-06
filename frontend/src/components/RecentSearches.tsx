import React, { useEffect, useMemo, useState } from 'react';
import { Box, Typography, Chip, Stack, IconButton, Tooltip, Button } from '@mui/material';
import { Restore as HistoryIcon, ClearAll as ClearIcon } from '@mui/icons-material';
import { apiHelpers } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface HistoryItem {
  id: string;
  query: string;
  created_at: string;
  params?: any;
  results_count?: string;
}

interface RecentSearchesProps {
  limit?: number;
  onSelect?: (query: string) => void;
  variant?: 'default' | 'compact';
}

const RecentSearches: React.FC<RecentSearchesProps> = ({ limit = 10, onSelect, variant = 'default' }) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pinned, setPinned] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem('pinned_queries');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    const res = await apiHelpers.listHistory(limit);
    if (res.success) setItems(res.items || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, [limit]);

  const clear = async () => {
    const res = await apiHelpers.clearHistory();
    if (res.success) setItems([]);
  };

  const setPinnedPersist = (next: string[]) => {
    setPinned(next);
    try { localStorage.setItem('pinned_queries', JSON.stringify(next)); } catch {}
  };
  const togglePin = (q: string) => {
    setPinnedPersist(pinned.includes(q) ? pinned.filter(x => x !== q) : [q, ...pinned].slice(0, 50));
  };

  const pinnedSet = useMemo(() => new Set(pinned), [pinned]);
  const pinnedItems = items.filter(i => pinnedSet.has(i.query));
  const otherItems = items.filter(i => !pinnedSet.has(i.query));

  const renderChip = (it: HistoryItem) => {
    const when = it.created_at ? new Date(it.created_at) : null;
    const top = Array.isArray(it.params?.top_sources) ? it.params.top_sources.slice(0, 3) : [];
    const tip = `${when ? when.toLocaleString() : ''}${it.results_count !== undefined && it.results_count !== null ? ` · ${it.results_count} results` : ''}${top.length ? `\nTop: ${top.join(' · ')}` : ''}`;
    const firstTitle = top.length ? String(top[0]) : '';
    const shortFirst = firstTitle && firstTitle.length > 40 ? `${firstTitle.slice(0, 37)}…` : firstTitle;
    const countStr = it.results_count !== undefined && it.results_count !== null ? ` · ${it.results_count}${variant === 'compact' ? ` ${Number(it.results_count) === 1 ? 'paper' : 'papers'}` : ''}` : '';
    const label = variant === 'compact'
      ? `${it.query}${countStr}`
      : `${it.query}${it.results_count !== undefined && it.results_count !== null ? ` · ${it.results_count}` : ''}${shortFirst ? ` · ${shortFirst}` : ''}`;
    const chatId = it.params?.chat_id as string | undefined;
    const handleClick = () => {
      if (onSelect) return onSelect(it.query);
      if (chatId) return navigate(`/research/${encodeURIComponent(chatId)}?q=${encodeURIComponent(it.query)}`);
      return navigate(`/research?q=${encodeURIComponent(it.query)}`);
    };
    return (
      <Tooltip key={it.id} title={tip} arrow>
        <span>
          <Chip
            size="small"
            label={label}
            onClick={handleClick}
            onDelete={() => togglePin(it.query)}
            deleteIcon={<span style={{ fontSize: 10, fontWeight: 700 }}>★</span>}
            variant={pinnedSet.has(it.query) ? 'filled' : 'outlined'}
            color={pinnedSet.has(it.query) ? 'primary' : 'default'}
          />
        </span>
      </Tooltip>
    );
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
      <HistoryIcon fontSize="small" sx={{ color: 'text.secondary' }} />
      <Typography variant="caption" sx={{ color: 'text.secondary', mr: 1 }}>Recent searches:</Typography>
      {pinnedItems.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          {pinnedItems.map(renderChip)}
        </Stack>
      )}
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
        {otherItems.map(renderChip)}
      </Stack>
      <Tooltip title="Clear history">
        <IconButton size="small" onClick={clear} sx={{ ml: 'auto' }}>
          <ClearIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Button size="small" variant="text" onClick={load}>Refresh</Button>
    </Box>
  );
};

export default RecentSearches;
