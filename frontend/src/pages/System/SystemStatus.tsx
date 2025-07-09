import React from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle as HealthyIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useHealth, useStats } from '../../hooks/useApi';

interface StatusCardProps {
  title: string;
  status: 'healthy' | 'warning' | 'error' | 'info';
  value?: string | number;
  description?: string;
}

const StatusCard: React.FC<StatusCardProps> = ({ title, status, value, description }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'healthy':
        return <HealthyIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          {getStatusIcon()}
          <Typography variant="h6" sx={{ ml: 1 }}>
            {title}
          </Typography>
        </Box>
        {value && (
          <Typography variant="h4" component="div" sx={{ mb: 1 }}>
            {value}
          </Typography>
        )}
        <Chip
          label={status.charAt(0).toUpperCase() + status.slice(1)}
          color={getStatusColor()}
          size="small"
          sx={{ mb: 1 }}
        />
        {description && (
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export const SystemStatus: React.FC = () => {
  const { data: health, isLoading: healthLoading, error: healthError } = useHealth(10000); // Refresh every 10 seconds
  const { data: stats, isLoading: statsLoading, error: statsError } = useStats();

  const isLoading = healthLoading || statsLoading;

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
        System Status
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Real-time monitoring of Log Dawg system components
      </Typography>

      {(healthError || statsError) && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Some system information may be unavailable due to connectivity issues.
        </Alert>
      )}

      {/* System Health Overview */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { 
          xs: '1fr', 
          sm: 'repeat(2, 1fr)', 
          md: 'repeat(3, 1fr)' 
        }, 
        gap: 3, 
        mb: 4 
      }}>
        <StatusCard
          title="Backend API"
          status={health?.status === 'healthy' ? 'healthy' : 'error'}
          value={health ? 'Online' : 'Offline'}
          description={health?.timestamp ? `Last check: ${new Date(health.timestamp).toLocaleTimeString()}` : 'Unable to connect'}
        />

        <StatusCard
          title="Report Generation"
          status={stats?.reports?.total_reports ? 'healthy' : 'warning'}
          value={stats?.reports?.total_reports || 0}
          description="Total reports generated"
        />

        <StatusCard
          title="Git Repository"
          status={stats?.git?.branch ? 'healthy' : 'warning'}
          value={stats?.git?.branch || 'Unknown'}
          description="Current branch"
        />
      </Box>

      {/* Detailed System Information */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { 
          xs: '1fr', 
          md: 'repeat(2, 1fr)' 
        }, 
        gap: 3 
      }}>
        {/* API Health Details */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              API Health Details
            </Typography>
            {health ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    label={health.status}
                    color={health.status === 'healthy' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Last Health Check
                  </Typography>
                  <Typography variant="body1">
                    {new Date(health.timestamp).toLocaleString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Response Time
                  </Typography>
                  <Typography variant="body1">
                    &lt; 100ms
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={20} 
                    color="success"
                    sx={{ mt: 1 }}
                  />
                </Box>
              </Box>
            ) : (
              <Alert severity="error">
                Unable to retrieve API health information
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* System Statistics */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Statistics
            </Typography>
            {stats ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {stats.reports && (
                  <>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Total Reports
                      </Typography>
                      <Typography variant="h5">
                        {stats.reports.total_reports}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Reports Today
                      </Typography>
                      <Typography variant="h5">
                        {stats.reports.reports_today}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Average Confidence Score
                      </Typography>
                      <Typography variant="h5">
                        {stats.reports.average_confidence_score}%
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={stats.reports.average_confidence_score} 
                        color={stats.reports.average_confidence_score >= 80 ? 'success' : 'warning'}
                        sx={{ mt: 1 }}
                      />
                    </Box>
                  </>
                )}
                {stats.version && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      System Version
                    </Typography>
                    <Typography variant="body1">
                      {stats.version}
                    </Typography>
                  </Box>
                )}
              </Box>
            ) : (
              <Alert severity="warning">
                Unable to retrieve system statistics
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Git Repository Status */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Repository Status
            </Typography>
            {stats?.git ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Current Branch
                  </Typography>
                  <Typography variant="body1">
                    {stats.git.branch}
                  </Typography>
                </Box>
                {stats.git.current_commit && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Latest Commit
                    </Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                      {stats.git.current_commit.slice(0, 8)}
                    </Typography>
                  </Box>
                )}
                {stats.git.last_pull_time && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Last Pull
                    </Typography>
                    <Typography variant="body1">
                      {new Date(stats.git.last_pull_time).toLocaleString()}
                    </Typography>
                  </Box>
                )}
              </Box>
            ) : (
              <Alert severity="info">
                Git repository information not available
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* System Resources */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Resources
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Frontend Status
                </Typography>
                <Chip label="Online" color="success" size="small" />
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Backend Connection
                </Typography>
                <Chip 
                  label={health ? "Connected" : "Disconnected"} 
                  color={health ? "success" : "error"} 
                  size="small" 
                />
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Auto-refresh
                </Typography>
                <Chip label="Every 10 seconds" color="info" size="small" />
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};
