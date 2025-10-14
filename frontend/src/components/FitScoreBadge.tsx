import { getFitScoreBadgeClass } from '../utils/formatters';

interface FitScoreBadgeProps {
  score: number | null;
  showLabel?: boolean;
}

export default function FitScoreBadge({ score, showLabel = true }: FitScoreBadgeProps) {
  if (score === null) {
    return <span className="badge badge-gray">N/A</span>;
  }

  return (
    <span className={getFitScoreBadgeClass(score)}>
      {showLabel && 'Fit: '}
      {score.toFixed(1)}
    </span>
  );
}
