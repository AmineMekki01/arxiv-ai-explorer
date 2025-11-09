import React, { useEffect, useState } from 'react';
import { Box, Typography, List, ListItem, ListItemText, IconButton, Button, Stack, Paper, Divider } from '@mui/material';
import { Delete as DeleteIcon, OpenInNew as OpenIcon } from '@mui/icons-material';
import { apiEndpoints } from '../services/api';

interface BookmarkItem {
  id: string;
  arxiv_id: string;
  title?: string;
  paper_id?: number;
}

const LikedPapers: React.FC = () => {
  const [items, setItems] = useState<BookmarkItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const res = await apiEndpoints.listLikedPapers();
    console.log("liked papers : ", res.data)
    setItems(res.data || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const remove = async (arxiv_id: string) => {
    const res = await apiEndpoints.unlikePaper(arxiv_id);
    if (res.status === 200) {
      load();
    }
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>Liked Papers</Typography>
      {loading ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography color="text.secondary">Loading...</Typography>
        </Paper>
      ) : items.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography color="text.secondary">No papers liked yet. Use the Like button on a paper to save it.</Typography>
        </Paper>
      ) : (
        <Paper variant="outlined">
          <List>
            {items.map((b, idx) => (
              <React.Fragment key={b.id}>
                <ListItem
                  secondaryAction={
                    <Stack direction="row" spacing={1}>
                      <IconButton edge="end" aria-label="open" href={`https://arxiv.org/abs/${b.arxiv_id}`} target="_blank" rel="noopener noreferrer">
                        <OpenIcon />
                      </IconButton>
                      <IconButton edge="end" aria-label="delete" onClick={() => remove(b.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  }
                >
                  <ListItemText
                    primary={b.title || b.arxiv_id}
                    secondary={`arXiv: ${b.arxiv_id}`}
                  />
                </ListItem>
                {idx < items.length - 1 && <Divider component="li" />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}
      <Box sx={{ mt: 2 }}>
        <Button variant="outlined" onClick={load} disabled={loading}>Refresh</Button>
      </Box>
    </Box>
  );
};

export default LikedPapers;
