import React from 'react';
import {
  Toolbar,
  Typography,
  IconButton,
  Box,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
} from '@mui/icons-material';
import { useHealth } from '../../hooks/useApi';

interface TopNavigationProps {
  onMenuClick: () => void;
  showMenuButton: boolean;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({
  onMenuClick,
  showMenuButton,
}) => {
  const { data: health } = useHealth();

  return (
    <Toolbar>
      {showMenuButton && (
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
      )}
      
      <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
        Log Dawg Dashboard
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {/* System Status Indicator */}
        {health && (
          <Chip
            label={health.status === 'healthy' ? 'System Online' : 'System Issues'}
            color={health.status === 'healthy' ? 'success' : 'error'}
            size="small"
            variant="outlined"
          />
        )}

        {/* Theme Toggle - Placeholder for future implementation */}
        <IconButton color="inherit" aria-label="toggle theme">
          <LightModeIcon />
        </IconButton>
      </Box>
    </Toolbar>
  );
};
