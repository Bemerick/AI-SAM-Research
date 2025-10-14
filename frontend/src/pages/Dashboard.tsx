import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { samOpportunitiesAPI } from '../services/api';
import type { SAMOpportunity, SAMOpportunityFilters } from '../types';
import { OpportunityDataGrid } from '../components/OpportunityDataGrid';
import FilterBar from '../components/FilterBar';

export default function Dashboard() {
  const [filters, setFilters] = useState<SAMOpportunityFilters>({});
  const navigate = useNavigate();

  const { data: opportunities, isLoading, error } = useQuery({
    queryKey: ['sam-opportunities', filters],
    queryFn: () => samOpportunitiesAPI.list(filters),
  });

  const handleRowClick = (opportunity: SAMOpportunity) => {
    navigate(`/opportunities/${opportunity.id}`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading opportunities...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-white rounded-lg shadow p-6 max-w-md">
          <div className="text-red-600 mb-2 font-semibold">⚠️ Error Loading Opportunities</div>
          <p className="text-gray-600">
            {error instanceof Error ? error.message : 'Failed to load opportunities'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 bg-white border-b">
        <h1 className="text-2xl font-bold text-gray-900">SAM.gov Opportunities</h1>
        <p className="text-gray-600 text-sm mt-1">
          Showing {opportunities?.length || 0} opportunities
        </p>
      </div>

      {/* Filters */}
      <div className="px-4 py-2 bg-gray-50 border-b">
        <FilterBar onFilterChange={setFilters} />
      </div>

      {/* Empty State */}
      {opportunities && opportunities.length === 0 && (
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow p-12 text-center max-w-md">
            <div className="text-6xl mb-4">📋</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Opportunities Found</h3>
            <p className="text-gray-600 mb-4">
              {Object.keys(filters).length > 0
                ? 'Try adjusting your filters to see more results.'
                : 'No opportunities have been added yet.'}
            </p>
            {Object.keys(filters).length > 0 && (
              <button
                onClick={() => setFilters({})}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* AG Grid Data Table - Maximum Width */}
      {opportunities && opportunities.length > 0 && (
        <div className="flex-1 overflow-hidden">
          <div className="h-full px-[5%] py-2">
            <div className="bg-white rounded shadow h-full">
              <OpportunityDataGrid
                opportunities={opportunities}
                onRowClicked={handleRowClick}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
