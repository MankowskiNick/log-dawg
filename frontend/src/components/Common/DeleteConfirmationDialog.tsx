import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { Warning as WarningIcon } from '@mui/icons-material';

interface DeleteConfirmationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  itemName: string;
  itemId?: string;
  isDeleting?: boolean;
}

export const DeleteConfirmationDialog: React.FC<DeleteConfirmationDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  itemName,
  itemId,
  isDeleting = false,
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <WarningIcon color="warning" />
        {title}
      </DialogTitle>
      
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          This action cannot be undone.
        </Alert>
        
        <Typography variant="body1" gutterBottom>
          Are you sure you want to delete this report?
        </Typography>
        
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" color="text.secondary">
            Report Name:
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
            {itemName}
          </Typography>
          
          {itemId && (
            <>
              <Typography variant="subtitle2" color="text.secondary">
                Report ID:
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {itemId}
              </Typography>
            </>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          disabled={isDeleting}
        >
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="error"
          disabled={isDeleting}
        >
          {isDeleting ? 'Deleting...' : 'Delete Report'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
