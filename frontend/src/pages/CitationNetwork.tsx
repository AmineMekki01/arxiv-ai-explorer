import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { Box, Stack, Typography, Paper, Chip, Button, IconButton, Tooltip, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { OpenInNew as ExternalIcon, Refresh as RefreshIcon, ArrowBack as BackIcon } from '@mui/icons-material';
import { apiHelpers } from '../services/api';

interface PaperNode {
  arxiv_id: string;
  title: string;
  citation_count?: number;
  is_seminal?: boolean;
}

interface CitationNetworkResponse {
  center_paper: string;
  depth: number;
  cited_papers: PaperNode[];
  citing_papers: PaperNode[];
}

const CitationNetwork: React.FC = () => {
  const { arxivId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [depth, setDepth] = useState<number>(() => Number(searchParams.get('depth') || 2));
  const [data, setData] = useState<CitationNetworkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!arxivId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiHelpers.getCitationNetwork(arxivId, depth);
      if (res.success) setData(res.data as CitationNetworkResponse);
      else throw new Error(res.error || 'Failed to load');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load citation network');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [arxivId, depth]);

  const onChangeDepth = (d: number) => {
    setDepth(d);
    const next = new URLSearchParams(searchParams);
    next.set('depth', String(d));
    setSearchParams(next, { replace: true });
  };

  return (
    <Box sx={{ maxWidth: 1100, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <IconButton onClick={() => navigate(-1)}><BackIcon /></IconButton>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>Citation Network</Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="depth-label">Depth</InputLabel>
          <Select labelId="depth-label" value={depth} label="Depth" onChange={(e) => onChangeDepth(Number(e.target.value))}>
            <MenuItem value={1}>1</MenuItem>
            <MenuItem value={2}>2</MenuItem>
            <MenuItem value={3}>3</MenuItem>
          </Select>
        </FormControl>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>Refresh</Button>
      </Stack>

      {error && (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography color="error">{error}</Typography>
        </Paper>
      )}

      {loading && (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography color="text.secondary">Loading…</Typography>
        </Paper>
      )}

      {data && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={2}>
            {/* Center paper */}
            <Box>
              <Typography variant="overline" sx={{ color: 'text.secondary' }}>Center paper</Typography>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5, flexWrap: 'wrap', gap: 1 }}>
                <Chip
                  color="primary"
                  label={data.center_paper}
                  component={RouterLink}
                  to={`/paper/${encodeURIComponent(data.center_paper)}`}
                  clickable
                />
                <Tooltip title="Open on arXiv"><IconButton size="small" component="a" href={`https://arxiv.org/abs/${data.center_paper}`} target="_blank" rel="noopener noreferrer"><ExternalIcon fontSize="small" /></IconButton></Tooltip>
              </Stack>
            </Box>

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="overline" sx={{ color: 'text.secondary' }}>Cited by</Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {data.citing_papers.length === 0 && (
                    <Typography variant="body2" color="text.secondary">No citing papers at this depth.</Typography>
                  )}
                  {data.citing_papers.map((p) => (
                    <Paper key={`citing-${p.arxiv_id}`} variant="outlined" sx={{ p: 1.25 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip
                          size="small"
                          variant="outlined"
                          label={p.title || p.arxiv_id}
                          component={RouterLink}
                          to={`/paper/${encodeURIComponent(p.arxiv_id)}`}
                          clickable
                        />
                        <Tooltip title="Open on arXiv"><IconButton size="small" component="a" href={`https://arxiv.org/abs/${p.arxiv_id}`} target="_blank" rel="noopener noreferrer"><ExternalIcon fontSize="small" /></IconButton></Tooltip>
                        {!!p.citation_count && (
                          <Chip size="small" label={`${p.citation_count} citations`} />
                        )}
                        {p.is_seminal && (
                          <Chip size="small" color="secondary" label="Seminal" />
                        )}
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Box>

              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="overline" sx={{ color: 'text.secondary' }}>References</Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {data.cited_papers.length === 0 && (
                    <Typography variant="body2" color="text.secondary">No references at this depth.</Typography>
                  )}
                  {data.cited_papers.map((p) => (
                    <Paper key={`cited-${p.arxiv_id}`} variant="outlined" sx={{ p: 1.25 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip
                          size="small"
                          variant="outlined"
                          label={p.title || p.arxiv_id}
                          component={RouterLink}
                          to={`/paper/${encodeURIComponent(p.arxiv_id)}`}
                          clickable
                        />
                        <Tooltip title="Open on arXiv"><IconButton size="small" component="a" href={`https://arxiv.org/abs/${p.arxiv_id}`} target="_blank" rel="noopener noreferrer"><ExternalIcon fontSize="small" /></IconButton></Tooltip>
                        {!!p.citation_count && (
                          <Chip size="small" label={`${p.citation_count} citations`} />
                        )}
                        {p.is_seminal && (
                          <Chip size="small" color="secondary" label="Seminal" />
                        )}
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Box>
            </Stack>
          </Stack>
        </Paper>
      )}

      {!loading && !data && !error && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography color="text.secondary">No data.</Typography>
        </Paper>
      )}
    </Box>
  );
};

export default CitationNetwork;
