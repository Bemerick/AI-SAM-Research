/**
 * Utility functions for formatting data
 */

/**
 * Get fit score color class based on score value
 */
export function getFitScoreColor(score: number | null): string {
  if (score === null) return 'gray';
  if (score >= 6) return 'high';
  if (score >= 4) return 'medium';
  return 'low';
}

/**
 * Get fit score badge class
 */
export function getFitScoreBadgeClass(score: number | null): string {
  const color = getFitScoreColor(score);
  return `badge badge-${color}`;
}

/**
 * Get match status color
 */
export function getMatchStatusColor(status: string): string {
  switch (status) {
    case 'confirmed':
      return 'text-green-600 bg-green-100';
    case 'rejected':
      return 'text-red-600 bg-red-100';
    case 'needs_info':
      return 'text-yellow-600 bg-yellow-100';
    case 'pending_review':
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/**
 * Format match status for display
 */
export function formatMatchStatus(status: string): string {
  switch (status) {
    case 'pending_review':
      return 'Pending Review';
    case 'needs_info':
      return 'Needs Info';
    case 'confirmed':
      return 'Confirmed';
    case 'rejected':
      return 'Rejected';
    default:
      return status;
  }
}

/**
 * Format date string for display
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A';

  try {
    // Parse date string as UTC to avoid timezone conversion issues
    // If the date is in format YYYY-MM-DD, append 'T00:00:00Z' to ensure UTC parsing
    let dateToFormat = dateString;
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
      // Date-only format, treat as UTC date
      dateToFormat = dateString + 'T12:00:00Z'; // Use noon UTC to avoid any timezone edge cases
    }
    const date = new Date(dateToFormat);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC', // Format in UTC to match the date we stored
    });
  } catch {
    return dateString;
  }
}

/**
 * Format date for datetime display
 */
export function formatDateTime(dateString: string | null): string {
  if (!dateString) return 'N/A';

  try {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

/**
 * Truncate text to specified length
 */
export function truncateText(text: string | null, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Format currency
 */
export function formatCurrency(value: number | null): string {
  if (value === null) return 'N/A';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Calculate days until deadline
 */
export function daysUntilDeadline(deadline: string | null): number | null {
  if (!deadline) return null;

  try {
    const deadlineDate = new Date(deadline);
    const today = new Date();
    const diffTime = deadlineDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  } catch {
    return null;
  }
}

/**
 * Get urgency class based on days until deadline
 */
export function getUrgencyClass(deadline: string | null): string {
  const days = daysUntilDeadline(deadline);
  if (days === null) return '';

  if (days < 0) return 'text-red-600 font-semibold'; // Expired
  if (days <= 7) return 'text-red-600 font-medium';  // Critical
  if (days <= 14) return 'text-yellow-600';          // Warning
  return '';                                          // Normal
}
