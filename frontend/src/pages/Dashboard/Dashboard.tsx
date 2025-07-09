import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  ButtonBase,
  Link,
} from '@mui/material';
import {
  Assessment as ReportsIcon,
  Speed as PerformanceIcon,
  CheckCircle as HealthIcon,
  TrendingUp as TrendIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useReports, useHealth, useStats } from '../../hooks/useApi';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactElement;
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning';
  subtitle?: string;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  icon, 
  color = 'primary',
  subtitle 
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Box sx={{ color: `${color}.main`, mr: 2 }}>
          {icon}
        </Box>
        <Typography variant="h6" component="div">
          {title}
        </Typography>
      </Box>
      <Typography variant="h4" component="div" sx={{ mb: 1 }}>
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </CardContent>
  </Card>
);

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: reports, isLoading: reportsLoading, error: reportsError } = useReports();
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: stats, isLoading: statsLoading } = useStats();

  const isLoading = reportsLoading || healthLoading || statsLoading;

  const handleReportClick = (reportId: string) => {
    navigate(`/reports/${encodeURIComponent(reportId)}`);
  };

  const handleViewAllReports = () => {
    navigate('/reports');
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard Overview
      </Typography>
      
      {reportsError && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Unable to connect to backend service. Some data may be unavailable.
        </Alert>
      )}

      {/* Stats Cards Row */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { 
          xs: '1fr', 
          sm: 'repeat(2, 1fr)', 
          md: 'repeat(4, 1fr)' 
        }, 
        gap: 3, 
        mb: 3 
      }}>
        {/* System Health Status */}
        <StatCard
          title="System Status"
          value={health?.status === 'healthy' ? 'Online' : 'Issues'}
          icon={<HealthIcon />}
          color={health?.status === 'healthy' ? 'success' : 'error'}
          subtitle={health?.timestamp ? `Last check: ${new Date(health.timestamp).toLocaleTimeString()}` : undefined}
        />

        {/* Total Reports */}
        <StatCard
          title="Total Reports"
          value={stats?.reports?.total_reports || reports?.length || 0}
          icon={<ReportsIcon />}
          color="primary"
          subtitle="All diagnostic reports"
        />

        {/* Reports Today */}
        <StatCard
          title="Reports Today"
          value={stats?.reports?.reports_today || 0}
          icon={<TrendIcon />}
          color="secondary"
          subtitle="Generated today"
        />

        {/* Average Confidence */}
        <StatCard
          title="Avg Confidence"
          value={stats?.reports?.average_confidence_score ? `${stats.reports.average_confidence_score}%` : 'N/A'}
          icon={<PerformanceIcon />}
          color="warning"
          subtitle="Analysis confidence"
        />
      </Box>

      {/* Main Content Row */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { 
          xs: '1fr', 
          md: '2fr 1fr' 
        }, 
        gap: 3 
      }}>
        {/* Recent Reports */}
        <Card>
          <CardContent>
            <Typography variant="h6" component="h2" gutterBottom>
              Recent Reports
            </Typography>
            {reports && reports.length > 0 ? (
              <Box>
                {reports.slice(0, 5).map((report) => (
                  <ButtonBase
                    key={report.report_id || report.filename}
                    onClick={() => handleReportClick(report.report_id || report.filename)}
                    sx={{
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      py: 1.5,
                      px: 1,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                      '&:last-child': { borderBottom: 'none' },
                      '&:hover': {
                        backgroundColor: 'action.hover',
                      },
                      transition: 'background-color 0.2s ease',
                    }}
                  >
                    <Box sx={{ flex: 1, textAlign: 'left' }}>
                      <Typography variant="body1" component="div" sx={{ fontWeight: 500 }}>
                        {report.display_title || report.filename}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(report.created).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={`${(report.size_bytes / 1024).toFixed(1)} KB`}
                        size="small"
                        variant="outlined"
                      />
                      <ChevronRightIcon color="action" fontSize="small" />
                    </Box>
                  </ButtonBase>
                ))}
                {reports.length > 5 && (
                  <Box sx={{ mt: 2 }}>
                    <Link
                      component="button"
                      variant="body2"
                      onClick={handleViewAllReports}
                      sx={{
                        textDecoration: 'none',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5,
                      }}
                    >
                      ... and {reports.length - 5} more reports
                      <ChevronRightIcon fontSize="small" />
                    </Link>
                  </Box>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No reports available
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* System Information */}
        <Card>
          <CardContent>
            <Typography variant="h6" component="h2" gutterBottom>
              System Information
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {stats?.git && (
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Git Branch
                  </Typography>
                  <Typography variant="body1">
                    {stats.git.branch}
                  </Typography>
                </Box>
              )}
              
              {stats?.version && (
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Version
                  </Typography>
                  <Typography variant="body1">
                    {stats.version}
                  </Typography>
                </Box>
              )}

              <Box>
                <Typography variant="body2" color="text.secondary">
                  Backend Status
                </Typography>
                <Chip
                  label={health ? 'Connected' : 'Disconnected'}
                  color={health ? 'success' : 'error'}
                  size="small"
                />
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};
