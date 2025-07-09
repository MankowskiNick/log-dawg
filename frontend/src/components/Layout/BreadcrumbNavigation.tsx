import React from 'react';
import {
  Breadcrumbs,
  Link,
  Typography,
  Box,
} from '@mui/material';
import {
  Home as HomeIcon,
  NavigateNext as NavigateNextIcon,
} from '@mui/icons-material';
import { useLocation, Link as RouterLink } from 'react-router-dom';

interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: React.ReactElement;
}

const getBreadcrumbs = (pathname: string): BreadcrumbItem[] => {
  const pathSegments = pathname.split('/').filter(Boolean);
  
  // Always start with home
  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Dashboard', path: '/', icon: <HomeIcon sx={{ mr: 0.5 }} fontSize="inherit" /> }
  ];

  // Handle specific routes
  if (pathSegments.length === 0) {
    // We're at home, return just the home breadcrumb
    return breadcrumbs;
  }

  if (pathSegments[0] === 'reports') {
    breadcrumbs.push({ label: 'Reports', path: '/reports' });
    
    if (pathSegments.length > 1) {
      // Individual report
      const reportFilename = decodeURIComponent(pathSegments[1]);
      breadcrumbs.push({ label: reportFilename });
    }
  } else if (pathSegments[0] === 'system') {
    breadcrumbs.push({ label: 'System Status', path: '/system' });
  } else {
    // Generic handling for unknown routes
    pathSegments.forEach((segment, index) => {
      const path = '/' + pathSegments.slice(0, index + 1).join('/');
      const isLast = index === pathSegments.length - 1;
      
      breadcrumbs.push({
        label: segment.charAt(0).toUpperCase() + segment.slice(1),
        path: isLast ? undefined : path,
      });
    });
  }

  return breadcrumbs;
};

export const BreadcrumbNavigation: React.FC = () => {
  const location = useLocation();
  const breadcrumbs = getBreadcrumbs(location.pathname);

  if (breadcrumbs.length <= 1) {
    return null; // Don't show breadcrumbs on home page
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Breadcrumbs
        separator={<NavigateNextIcon fontSize="small" />}
        aria-label="breadcrumb"
      >
        {breadcrumbs.map((breadcrumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          if (isLast || !breadcrumb.path) {
            return (
              <Typography
                key={breadcrumb.label}
                color="text.primary"
                sx={{ display: 'flex', alignItems: 'center' }}
              >
                {breadcrumb.icon}
                {breadcrumb.label}
              </Typography>
            );
          }

          return (
            <Link
              key={breadcrumb.label}
              component={RouterLink}
              to={breadcrumb.path}
              underline="hover"
              color="inherit"
              sx={{ display: 'flex', alignItems: 'center' }}
            >
              {breadcrumb.icon}
              {breadcrumb.label}
            </Link>
          );
        })}
      </Breadcrumbs>
    </Box>
  );
};
