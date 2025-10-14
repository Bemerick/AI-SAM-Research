import { Link } from 'react-router-dom';
import type { SAMOpportunity } from '../types';
import FitScoreBadge from './FitScoreBadge';
import { formatDate, truncateText, daysUntilDeadline, getUrgencyClass } from '../utils/formatters';

interface OpportunityGridCardProps {
  opportunity: SAMOpportunity;
}

export default function OpportunityGridCard({ opportunity }: OpportunityGridCardProps) {
  const days = daysUntilDeadline(opportunity.response_deadline);
  const urgencyClass = getUrgencyClass(opportunity.response_deadline);

  return (
    <Link to={`/opportunities/${opportunity.id}`} className="block">
      <div className="card card-hover h-full cursor-pointer flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start mb-3">
          <FitScoreBadge score={opportunity.fit_score} />
          {opportunity.review_for_bid !== 'Pending' && (
            <span className={`badge ${opportunity.review_for_bid === 'Yes' ? 'badge-high' : 'badge-low'}`}>
              {opportunity.review_for_bid}
            </span>
          )}
        </div>

        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
          {opportunity.title || 'Untitled Opportunity'}
        </h3>

        {/* Notice ID */}
        <p className="text-xs text-gray-500 mb-3">{opportunity.notice_id}</p>

        {/* Key Info */}
        <div className="space-y-1.5 mb-3 flex-1">
          <div className="text-sm">
            <span className="text-gray-500">Agency:</span>
            <span className="ml-2 text-gray-900 font-medium">{truncateText(opportunity.department, 30)}</span>
          </div>

          {opportunity.assigned_practice_area && (
            <div className="text-sm">
              <span className="text-gray-500">Practice:</span>
              <span className="ml-2 text-gray-900">{truncateText(opportunity.assigned_practice_area, 25)}</span>
            </div>
          )}

          <div className="text-sm">
            <span className="text-gray-500">NAICS:</span>
            <span className="ml-2 text-gray-900">{opportunity.naics_code || 'N/A'}</span>
          </div>

          <div className="text-sm">
            <span className="text-gray-500">Posted:</span>
            <span className="ml-2 text-gray-900">{formatDate(opportunity.posted_date)}</span>
          </div>

          <div className="text-sm">
            <span className="text-gray-500">Deadline:</span>
            <span className={`ml-2 text-gray-900 ${urgencyClass}`}>
              {formatDate(opportunity.response_deadline)}
              {days !== null && days >= 0 && <span className="ml-1 text-xs">({days}d)</span>}
            </span>
          </div>
        </div>

        {/* Summary */}
        {opportunity.summary_description && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {opportunity.summary_description}
          </p>
        )}

        {/* Tags */}
        <div className="flex gap-1.5 flex-wrap mt-auto pt-3 border-t">
          {opportunity.set_aside && (
            <span className="badge badge-gray text-xs">{opportunity.set_aside}</span>
          )}
          {opportunity.ptype && (
            <span className="badge badge-gray text-xs">{opportunity.ptype}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
