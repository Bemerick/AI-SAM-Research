import { Link } from 'react-router-dom';
import type { SAMOpportunity } from '../types';
import FitScoreBadge from './FitScoreBadge';
import { formatDate, truncateText, daysUntilDeadline, getUrgencyClass } from '../utils/formatters';

interface OpportunityCardProps {
  opportunity: SAMOpportunity;
}

export default function OpportunityCard({ opportunity }: OpportunityCardProps) {
  const days = daysUntilDeadline(opportunity.response_deadline);
  const urgencyClass = getUrgencyClass(opportunity.response_deadline);

  return (
    <Link to={`/opportunities/${opportunity.id}`}>
      <div className="card card-hover cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              {opportunity.title || 'Untitled Opportunity'}
            </h3>
            <p className="text-sm text-gray-500">{opportunity.notice_id}</p>
          </div>
          <FitScoreBadge score={opportunity.fit_score} />
        </div>

        <div className="space-y-2 mb-3">
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Department:</span>
            <span className="text-gray-900 font-medium">
              {truncateText(opportunity.department, 50)}
            </span>
          </div>

          {opportunity.assigned_practice_area && (
            <div className="flex items-center text-sm">
              <span className="text-gray-500 w-24">Practice:</span>
              <span className="text-gray-900">{opportunity.assigned_practice_area}</span>
            </div>
          )}

          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">NAICS:</span>
            <span className="text-gray-900">{opportunity.naics_code || 'N/A'}</span>
          </div>

          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Posted:</span>
            <span className="text-gray-900">{formatDate(opportunity.posted_date)}</span>
          </div>

          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Deadline:</span>
            <span className={`text-gray-900 ${urgencyClass}`}>
              {formatDate(opportunity.response_deadline)}
              {days !== null && days >= 0 && (
                <span className="ml-2">({days} days)</span>
              )}
            </span>
          </div>
        </div>

        {opportunity.summary_description && (
          <p className="text-sm text-gray-600 mb-3">
            {truncateText(opportunity.summary_description, 150)}
          </p>
        )}

        <div className="flex gap-2 flex-wrap">
          {opportunity.set_aside && (
            <span className="badge badge-gray">{opportunity.set_aside}</span>
          )}
          {opportunity.ptype && (
            <span className="badge badge-gray">{opportunity.ptype}</span>
          )}
          {opportunity.review_for_bid !== 'Pending' && (
            <span className={`badge ${opportunity.review_for_bid === 'Yes' ? 'badge-high' : 'badge-low'}`}>
              Review: {opportunity.review_for_bid}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
