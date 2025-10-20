/**
 * AG Grid component for displaying SAM.gov opportunities
 */
import React, { useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import type { ColDef, GridReadyEvent } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import type { SAMOpportunity } from '../types';
import { formatDate } from '../utils/formatters';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

interface OpportunityDataGridProps {
  opportunities: SAMOpportunity[];
  onRowClicked?: (opportunity: SAMOpportunity) => void;
}

// Custom cell renderer for fit score with color coding
const FitScoreCellRenderer = (params: any) => {
  const score = params.value;
  let colorClass = 'bg-gray-100 text-gray-800';

  if (score >= 6) {
    colorClass = 'bg-green-100 text-green-800';
  } else if (score >= 4) {
    colorClass = 'bg-yellow-100 text-yellow-800';
  } else if (score >= 1) {
    colorClass = 'bg-red-100 text-red-800';
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colorClass}`}>
      {score ? score.toFixed(1) : 'N/A'}
    </span>
  );
};

// Custom cell renderer for deadline with urgency indicator
const DeadlineCellRenderer = (params: any) => {
  const deadline = params.value;
  if (!deadline || deadline === 'N/A') {
    return <span className="text-gray-400">No deadline</span>;
  }

  const deadlineDate = new Date(deadline);
  const now = new Date();
  const daysUntil = Math.ceil((deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const formattedDate = formatDate(deadline);

  if (daysUntil < 0) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-gray-400 line-through">{formattedDate}</span>
        <span className="text-xs text-gray-400">(Expired)</span>
      </div>
    );
  } else if (daysUntil <= 7) {
    // Urgent - show date with red indicator
    return (
      <div className="flex items-center gap-2">
        <span className="text-red-700 font-semibold">{formattedDate}</span>
        <span className="px-1.5 py-0.5 text-xs font-semibold bg-red-100 text-red-800 rounded">
          {daysUntil}d
        </span>
      </div>
    );
  } else if (daysUntil <= 14) {
    // Warning - show date with orange indicator
    return (
      <div className="flex items-center gap-2">
        <span className="text-orange-700">{formattedDate}</span>
        <span className="px-1.5 py-0.5 text-xs bg-orange-100 text-orange-800 rounded">
          {daysUntil}d
        </span>
      </div>
    );
  } else {
    // Normal - just show the date
    return <span className="text-gray-700">{formattedDate}</span>;
  }
};

// Custom cell renderer for review status
const ReviewStatusCellRenderer = (params: any) => {
  const reviewForBid = params.data.review_for_bid;
  const recommendBid = params.data.recommend_bid;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Yes':
        return 'bg-green-100 text-green-800';
      case 'No':
        return 'bg-red-100 text-red-800';
      case 'Pending':
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="flex gap-1">
      <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(reviewForBid)}`}>
        {reviewForBid}
      </span>
      {recommendBid !== 'Pending' && (
        <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(recommendBid)}`}>
          Rec: {recommendBid}
        </span>
      )}
    </div>
  );
};

export const OpportunityDataGrid: React.FC<OpportunityDataGridProps> = ({
  opportunities,
  onRowClicked,
}) => {
  // Debug: Log opportunities data
  React.useEffect(() => {
    console.log('AG Grid - Opportunities count:', opportunities?.length);
    console.log('AG Grid - First opportunity:', opportunities?.[0]);
  }, [opportunities]);

  // Column definitions
  const columnDefs = useMemo<ColDef[]>(() => [
    {
      field: 'fit_score',
      headerName: 'Fit Score',
      width: 110,
      cellRenderer: FitScoreCellRenderer,
      sortable: true,
      filter: 'agNumberColumnFilter',
      sort: 'desc',
      sortIndex: 1,
      pinned: 'left',
    },
    {
      field: 'match_count',
      headerName: 'GovWin',
      width: 90,
      sortable: true,
      filter: 'agNumberColumnFilter',
      cellRenderer: (params: any) => {
        const count = params.value;
        if (!count || count === 0) {
          return <span className="text-gray-400">-</span>;
        }
        return (
          <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            {count} {count === 1 ? 'match' : 'matches'}
          </span>
        );
      },
      pinned: 'left',
    },
    {
      field: 'title',
      headerName: 'Title',
      flex: 2,
      minWidth: 300,
      sortable: true,
      filter: 'agTextColumnFilter',
      cellStyle: { fontWeight: '500' },
      wrapText: true,
      autoHeight: true,
    },
    {
      field: 'department',
      headerName: 'Department',
      flex: 1,
      minWidth: 180,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'assigned_practice_area',
      headerName: 'Practice Area',
      flex: 1,
      minWidth: 180,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'naics_code',
      headerName: 'NAICS',
      width: 100,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'ptype',
      headerName: 'Type',
      width: 130,
      sortable: true,
      filter: 'agTextColumnFilter',
      valueFormatter: (params) => {
        const type = params.value;
        if (!type) return 'N/A';
        return type.charAt(0).toUpperCase() + type.slice(1);
      },
    },
    {
      field: 'posted_date',
      headerName: 'Posted',
      width: 120,
      sortable: true,
      filter: 'agDateColumnFilter',
      sort: 'desc',
      sortIndex: 0,
      valueFormatter: (params) => formatDate(params.value),
    },
    {
      field: 'response_deadline',
      headerName: 'Deadline',
      width: 160,
      sortable: true,
      filter: 'agDateColumnFilter',
      cellRenderer: DeadlineCellRenderer,
      comparator: (valueA: any, valueB: any) => {
        // Custom comparator for date sorting
        // Handle N/A values - put them at the end
        if (valueA === 'N/A' && valueB === 'N/A') return 0;
        if (valueA === 'N/A') return 1;
        if (valueB === 'N/A') return -1;

        // Parse dates and compare
        const dateA = new Date(valueA).getTime();
        const dateB = new Date(valueB).getTime();
        return dateA - dateB;
      },
      valueGetter: (params: any) => {
        // Return the raw date value for filtering and sorting
        return params.data.response_deadline;
      },
    },
    {
      field: 'set_aside',
      headerName: 'Set Aside',
      width: 140,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'review_for_bid',
      headerName: 'Review Status',
      width: 150,
      sortable: true,
      filter: 'agTextColumnFilter',
      cellRenderer: ReviewStatusCellRenderer,
    },
    {
      field: 'solicitation_number',
      headerName: 'Solicitation #',
      width: 150,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
  ], []);

  // Default column settings
  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    floatingFilter: true,
  }), []);

  // Handle row click
  const onRowClick = useCallback((event: any) => {
    if (onRowClicked && event.data) {
      onRowClicked(event.data);
    }
  }, [onRowClicked]);

  // Handle grid ready
  const onGridReady = useCallback((params: GridReadyEvent) => {
    // Auto-size columns to fit content
    params.api.sizeColumnsToFit();
  }, []);

  // Debug empty data
  if (!opportunities || opportunities.length === 0) {
    console.warn('AG Grid - No opportunities data to display');
  }

  return (
    <div className="ag-theme-alpine" style={{ height: '100%', width: '100%' }}>
      <AgGridReact
        rowData={opportunities}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        onRowClicked={onRowClick}
        rowSelection="single"
        animateRows={true}
        pagination={true}
        paginationPageSize={50}
        paginationPageSizeSelector={[10, 25, 50, 100]}
        onGridReady={onGridReady}
        suppressCellFocus={true}
        domLayout="normal"
      />
    </div>
  );
};
