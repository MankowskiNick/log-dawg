import React, { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  Button,
  LinearProgress,
  Snackbar,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Schedule as TimeIcon,
} from '@mui/icons-material';
import { useReports, useDownloadMarkdown, useDeleteReport } from '../../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { DeleteConfirmationDialog } from '../../components/Common/DeleteConfirmationDialog';

export const ReportsList: React.FC = () => {
  const { data: reports, isLoading, error } = useReports();
  const downloadMarkdown = useDownloadMarkdown();
  const deleteReport = useDeleteReport();
  const navigate = useNavigate();

  // Delete confirmation dialog state
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    reportId: string;
    reportName: string;
  }>({
    open: false,
    reportId: '',
    reportName: '',
  });

  // Success/error feedback state
  const [feedback, setFeedback] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load reports: {error.message}
      </Alert>
    );
  }

  const handleViewReport = (reportId: string) => {
    navigate(`/reports/${encodeURIComponent(reportId)}`);
  };

  const handleDownloadReport = async (reportId: string) => {
    try {
      await downloadMarkdown.mutateAsync(reportId);
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const handleDeleteClick = (reportId: string, reportName: string) => {
    setDeleteDialog({
      open: true,
      reportId,
      reportName,
    });
  };

  const handleDeleteConfirm = async () => {
    try {
      await deleteReport.mutateAsync(deleteDialog.reportId);
      setFeedback({
        open: true,
        message: 'Report deleted successfully',
        severity: 'success',
      });
      setDeleteDialog({ open: false, reportId: '', reportName: '' });
    } catch (error) {
      setFeedback({
        open: true,
        message: 'Failed to delete report',
        severity: 'error',
      });
      console.error('Failed to delete report:', error);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialog({ open: false, reportId: '', reportName: '' });
  };

  const handleFeedbackClose = () => {
    setFeedback({ open: false, message: '', severity: 'success' });
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Diagnostic Reports
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {reports?.length || 0} reports found
      </Typography>

      {reports && reports.length > 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {reports.map((report) => {
            // Helper functions for display
            const getConfidenceColor = (confidence: number) => {
              if (confidence >= 0.8) return 'success';
              if (confidence >= 0.6) return 'warning';
              return 'error';
            };

            const getErrorIcon = (errorType: string) => {
              if (errorType?.toLowerCase().includes('error')) return <ErrorIcon fontSize="small" />;
              if (errorType?.toLowerCase().includes('warning')) return <WarningIcon fontSize="small" />;
              return <ErrorIcon fontSize="small" />;
            };

            const formatDateTime = (dateStr: string) => {
              const date = new Date(dateStr);
              return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
              });
            };

            return (
              <Card key={report.report_id || report.filename} sx={{ '&:hover': { boxShadow: 3 } }}>
                <CardContent>
                  <Box sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: 2
                  }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      {/* Error Type Icon & Title */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        {report.error_type && getErrorIcon(report.error_type)}
                        <Typography variant="h6" component="h2" sx={{ 
                          color: 'text.primary',
                          fontWeight: 600
                        }}>
                          {report.display_title || 'Diagnostic Report'}
                        </Typography>
                      </Box>

                      {/* Error Type Badge */}
                      {report.error_type && (
                        <Box sx={{ mb: 1 }}>
                          <Chip
                            label={report.error_type}
                            size="small"
                            variant="outlined"
                            color={getConfidenceColor(report.confidence_score || 0)}
                            sx={{ fontWeight: 500 }}
                          />
                        </Box>
                      )}

                      {/* Summary Preview */}
                      {report.summary_preview && (
                        <Box sx={{ 
                          mb: 2,
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          '& p': {
                            margin: 0,
                            fontSize: '0.875rem',
                            color: 'text.secondary',
                            lineHeight: 1.43
                          },
                          '& strong': {
                            fontWeight: 600,
                            color: 'text.primary'
                          },
                          '& code': {
                            backgroundColor: 'grey.100',
                            px: 0.5,
                            py: 0.25,
                            borderRadius: 0.5,
                            fontSize: '0.8125rem',
                            fontFamily: 'monospace'
                          }
                        }}>
                          <ReactMarkdown>{report.summary_preview}</ReactMarkdown>
                        </Box>
                      )}

                      {/* Metadata Row */}
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                        {/* Confidence Score */}
                        {report.confidence_score !== undefined && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              Confidence:
                            </Typography>
                            <Box sx={{ width: 60, mr: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={report.confidence_score * 100}
                                color={getConfidenceColor(report.confidence_score)}
                                sx={{ height: 4, borderRadius: 2 }}
                              />
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                              {Math.round(report.confidence_score * 100)}%
                            </Typography>
                          </Box>
                        )}

                        {/* Processing Time */}
                        {/* {report.processing_time !== undefined && (
                          <Chip
                            icon={<TimeIcon />}
                            label={`${report.processing_time.toFixed(1)}s`}
                            size="small"
                            variant="outlined"
                          />
                        )} */}

                        {/* Created Date/Time */}
                        <Typography variant="caption" color="text.secondary">
                          {formatDateTime(report.created)}
                        </Typography>

                        {/* File Size */}
                        {/* <Chip
                          label={`${(report.size_bytes / 1024).toFixed(1)} KB`}
                          size="small"
                          variant="outlined"
                        /> */}

                        {/* Report ID */}
                        {/* {report.report_id && (
                          <Chip
                            label={`ID: ${report.report_id.slice(0, 8)}...`}
                            size="small"
                            variant="outlined"
                          />
                        )} */}
                      </Box>
                    </Box>
                    
                    <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<ViewIcon />}
                        onClick={() => handleViewReport(report.report_id || report.filename)}
                      >
                        View
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => handleDownloadReport(report.report_id || report.filename)}
                        disabled={downloadMarkdown.isPending}
                      >
                        {downloadMarkdown.isPending ? 'Downloading...' : 'Download'}
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        color="error"
                        startIcon={<DeleteIcon />}
                        onClick={() => handleDeleteClick(
                          report.report_id || report.filename,
                          report.display_title || 'Diagnostic Report'
                        )}
                        disabled={deleteReport.isPending}
                      >
                        Delete
                      </Button>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      ) : (
        <Card>
          <CardContent>
            <Typography variant="body1" color="text.secondary" align="center">
              No reports available. Reports will appear here once the backend generates diagnostic analyses.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={deleteDialog.open}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Report"
        itemName={deleteDialog.reportName}
        itemId={deleteDialog.reportId}
        isDeleting={deleteReport.isPending}
      />

      {/* Success/Error Feedback */}
      <Snackbar
        open={feedback.open}
        autoHideDuration={6000}
        onClose={handleFeedbackClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleFeedbackClose}
          severity={feedback.severity}
          sx={{ width: '100%' }}
        >
          {feedback.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
