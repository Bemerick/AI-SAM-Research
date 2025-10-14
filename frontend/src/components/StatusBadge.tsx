import { formatMatchStatus, getMatchStatusColor } from '../utils/formatters';

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`badge ${getMatchStatusColor(status)}`}>
      {formatMatchStatus(status)}
    </span>
  );
}
