import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { 
  Box, 
  Stack, 
  Typography, 
  Card, 
  Chip, 
  Button, 
  IconButton, 
  Tooltip, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel,
  Grid,
  Divider 
} from '@mui/material';
import { OpenInNew as ExternalIcon, Refresh as RefreshIcon, ArrowBack as BackIcon } from '@mui/icons-material';
import { apiHelpers } from '../services/api';

interface PaperNode {
  arxiv_id?: string;
  s2_paper_id?: string;
  doi?: string;
  title: string;
  citation_count?: number;
  is_seminal?: boolean;
  external_url?: string;
}

interface CitationNetworkResponse {
  center_paper: string;
  depth: number;
  cited_papers: PaperNode[];
  citing_papers: PaperNode[];
}

const CitationNetwork: React.FC = () => {
  const { arxivId } = useParams<{ arxivId?: string }>();
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

  const getTruncatedLabel = (title: string, id: string) => {
    return title && title.length > 50 ? `${title.substring(0, 50)}...` : (title || id);
  };

  const getFullTitle = (title: string, id: string) => title || id;

  const renderPaperItem = (paper: PaperNode, key: string) => {
    const baseId = paper.arxiv_id || paper.s2_paper_id || paper.doi || 'unknown';
    const fullTitle = getFullTitle(paper.title, baseId);
    const truncatedLabel = getTruncatedLabel(paper.title, baseId);
    const isTruncated = !!(paper.title && paper.title.length > 50);
    const externalUrl = paper.external_url || (paper.arxiv_id
      ? `https://arxiv.org/abs/${paper.arxiv_id}`
      : paper.doi
        ? `https://doi.org/${paper.doi}`
        : paper.s2_paper_id
          ? `https://www.semanticscholar.org/paper/${paper.s2_paper_id}`
          : undefined);

    return (
      <Stack key={key} direction="row" alignItems="center" spacing={1} sx={{ py: 1 }}>
        <Tooltip title={isTruncated ? fullTitle : ''} placement="top" arrow>
          {paper.arxiv_id ? (
            <Chip
              size="small"
              variant="outlined"
              label={truncatedLabel}
              component={RouterLink}
              to={`/paper/${encodeURIComponent(paper.arxiv_id)}`}
              clickable
              sx={{ 
                flex: 1, 
                minWidth: 0,
                overflow: 'hidden',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis'
              }}
            />
          ) : (
            <Chip
              size="small"
              variant="outlined"
              label={truncatedLabel}
              sx={{ 
                flex: 1, 
                minWidth: 0,
                overflow: 'hidden',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis'
              }}
            />
          )}
        </Tooltip>
        {externalUrl && (
          <Tooltip title="Open external">
            <IconButton size="small" component="a" href={externalUrl} target="_blank" rel="noopener noreferrer">
              <ExternalIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        {paper.citation_count && <Chip size="small" label={`${paper.citation_count} citations`} color="info" />}
        {paper.is_seminal && <Chip size="small" color="secondary" label="Seminal" />}
      </Stack>
    );
  };

  const renderCenterPaper = () => {
    if (!data?.center_paper) return null;
    // Assuming center_paper is arxiv_id; if it has a title, adjust accordingly
    return (
      <Stack direction="row" justifyContent="center" alignItems="center" spacing={1}>
        <Chip
          color="primary"
          label={data.center_paper}
          component={RouterLink}
          to={`/paper/${encodeURIComponent(data.center_paper)}`}
          clickable
          sx={{ fontSize: '0.875rem' }}
        />
        <Tooltip title="View on arXiv">
          <IconButton size="small" component="a" href={`https://arxiv.org/abs/${data.center_paper}`} target="_blank" rel="noopener noreferrer">
            <ExternalIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
    );
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', p: { xs: 2, md: 3 } }}>
      {/* Header */}
      <Card elevation={1} sx={{ mb: 3, borderRadius: 2 }}>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ p: 2 }}>
          <IconButton onClick={() => navigate(-1)} size="small">
            <BackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ fontWeight: 500, flex: 1 }}>Citation Network</Typography>
          <FormControl size="small" sx={{ minWidth: 80 }}>
            <InputLabel>Depth</InputLabel>
            <Select value={depth} label="Depth" onChange={(e) => onChangeDepth(Number(e.target.value))}>
              <MenuItem value={1}>1</MenuItem>
              <MenuItem value={2}>2</MenuItem>
              <MenuItem value={3}>3</MenuItem>
            </Select>
          </FormControl>
          <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading} variant="outlined">
            Refresh
          </Button>
        </Stack>
      </Card>

      {/* Loading/Error States */}
      {loading && (
        <Card elevation={1} sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">Loading citations...</Typography>
        </Card>
      )}
      {error && (
        <Card elevation={1} sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="error">{error}</Typography>
        </Card>
      )}

      {/* Main Content */}
      {data && (
        <Card elevation={1} sx={{ borderRadius: 2, overflow: 'hidden' }}>
          <Box sx={{ p: { xs: 2, md: 3 } }}>
            {/* Center Paper */}
            <Box sx={{ mb: 4, textAlign: 'center' }}>
              <Typography variant="overline" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                Center Paper
              </Typography>
              {renderCenterPaper()}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Cited and Citing Sections */}
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 500 }}>Citing Papers</Typography>
                <Stack spacing={1.5}>
                  {data.citing_papers.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No citing papers found.</Typography>
                  ) : (
                    data.citing_papers.map((p) => {
                      const key = p.arxiv_id || p.s2_paper_id || p.doi || Math.random().toString(36);
                      return renderPaperItem(p, `citing-${key}`);
                    })
                  )}
                </Stack>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 500 }}>Cited Papers</Typography>
                <Stack spacing={1.5}>
                  {data.cited_papers.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No cited papers found.</Typography>
                  ) : (
                    data.cited_papers.map((p) => {
                      const key = p.arxiv_id || p.s2_paper_id || p.doi || Math.random().toString(36);
                      return renderPaperItem(p, `cited-${key}`);
                    })
                  )}
                </Stack>
              </Grid>
            </Grid>
          </Box>
        </Card>
      )}

      {!loading && !data && !error && (
        <Card elevation={1} sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">Select a paper to view its network.</Typography>
        </Card>
      )}
    </Box>
  );
};

export default CitationNetwork;
