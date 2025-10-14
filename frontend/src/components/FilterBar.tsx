import { useState } from 'react';
import type { SAMOpportunityFilters } from '../types';
import { REVIEW_STATUSES } from '../types';

interface FilterBarProps {
  onFilterChange: (filters: SAMOpportunityFilters) => void;
}

export default function FilterBar({ onFilterChange }: FilterBarProps) {
  const [minFitScore, setMinFitScore] = useState<string>('');
  const [department, setDepartment] = useState<string>('');
  const [naicsCode, setNaicsCode] = useState<string>('');
  const [reviewForBid, setReviewForBid] = useState<string>('');
  const [recommendBid, setRecommendBid] = useState<string>('');

  const handleApplyFilters = () => {
    const filters: SAMOpportunityFilters = {};

    if (minFitScore) filters.min_fit_score = parseFloat(minFitScore);
    if (department) filters.department = department;
    if (naicsCode) filters.naics_code = naicsCode;
    if (reviewForBid && reviewForBid !== 'All') filters.review_for_bid = reviewForBid;
    if (recommendBid && recommendBid !== 'All') filters.recommend_bid = recommendBid;

    onFilterChange(filters);
  };

  const handleClearFilters = () => {
    setMinFitScore('');
    setDepartment('');
    setNaicsCode('');
    setReviewForBid('');
    setRecommendBid('');
    onFilterChange({});
  };

  return (
    <div className="card mb-6">
      <h3 className="text-lg font-semibold mb-4">Filters</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div>
          <label className="label">Min Fit Score</label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            className="input"
            value={minFitScore}
            onChange={(e) => setMinFitScore(e.target.value)}
            placeholder="e.g., 6"
          />
        </div>

        <div>
          <label className="label">Department</label>
          <input
            type="text"
            className="input"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            placeholder="Enter department"
          />
        </div>

        <div>
          <label className="label">NAICS Code</label>
          <input
            type="text"
            className="input"
            value={naicsCode}
            onChange={(e) => setNaicsCode(e.target.value)}
            placeholder="e.g., 541512"
          />
        </div>

        <div>
          <label className="label">Review For Bid</label>
          <select
            className="select"
            value={reviewForBid}
            onChange={(e) => setReviewForBid(e.target.value)}
          >
            <option value="">All</option>
            {REVIEW_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Recommend Bid</label>
          <select
            className="select"
            value={recommendBid}
            onChange={(e) => setRecommendBid(e.target.value)}
          >
            <option value="">All</option>
            {REVIEW_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button onClick={handleApplyFilters} className="btn btn-primary">
          Apply Filters
        </button>
        <button onClick={handleClearFilters} className="btn btn-secondary">
          Clear Filters
        </button>
      </div>
    </div>
  );
}
