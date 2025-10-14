import { useQuery } from '@tanstack/react-query';
import { samOpportunitiesAPI } from '../services/api';
import OpportunityGridCard from '../components/OpportunityGridCard';
import { Link } from 'react-router-dom';

export default function HighScoring() {
  const { data: opportunities, isLoading, error } = useQuery({
    queryKey: ['high-scoring-opportunities'],
    queryFn: () => samOpportunitiesAPI.listHighScoring(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card max-w-md mx-auto mt-12">
        <div className="text-red-600 mb-2">⚠️ Error Loading</div>
        <p className="text-gray-600">{error instanceof Error ? error.message : 'Failed to load'}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">High-Scoring Opportunities</h1>
        <p className="text-gray-600 mt-1">
          Opportunities with fit score ≥ 6.0 • Showing {opportunities?.length || 0} opportunities
        </p>
      </div>

      {/* Empty State */}
      {opportunities && opportunities.length === 0 && (
        <div className="card text-center py-12">
          <div className="text-6xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No High-Scoring Opportunities</h3>
          <p className="text-gray-600 mb-4">
            No opportunities with fit score ≥ 6.0 found.
          </p>
          <Link to="/" className="btn btn-primary">
            View All Opportunities
          </Link>
        </div>
      )}

      {/* Grid View */}
      {opportunities && opportunities.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {opportunities.map((opp) => (
            <OpportunityGridCard key={opp.id} opportunity={opp} />
          ))}
        </div>
      )}
    </div>
  );
}
