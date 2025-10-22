/**
 * API client for backend communication
 */
import axios from 'axios';
import type {
  SAMOpportunity,
  SAMOpportunityCreate,
  SAMOpportunityUpdate,
  SAMOpportunityFilters,
  GovWinOpportunity,
  GovWinContract,
  Match,
  MatchWithDetails,
  MatchCreate,
  MatchUpdate,
  MatchFilters,
  OpportunityStatistics,
  MatchStatistics,
} from '../types';

// Base URL for API - use environment variable or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// SAM Opportunities API
export const samOpportunitiesAPI = {
  list: async (filters?: SAMOpportunityFilters): Promise<SAMOpportunity[]> => {
    const response = await apiClient.get<SAMOpportunity[]>('/sam-opportunities/', {
      params: { ...filters, limit: 1000 }
    });
    return response.data;
  },

  listHighScoring: async (skip = 0, limit = 100): Promise<SAMOpportunity[]> => {
    const response = await apiClient.get<SAMOpportunity[]>('/sam-opportunities/high-scoring/', {
      params: { skip, limit },
    });
    return response.data;
  },

  getById: async (id: number): Promise<SAMOpportunity> => {
    const response = await apiClient.get<SAMOpportunity>(`/sam-opportunities/${id}/`);
    return response.data;
  },

  getByNoticeId: async (noticeId: string): Promise<SAMOpportunity> => {
    const response = await apiClient.get<SAMOpportunity>(`/sam-opportunities/notice/${noticeId}/`);
    return response.data;
  },

  create: async (opportunity: SAMOpportunityCreate): Promise<SAMOpportunity> => {
    const response = await apiClient.post<SAMOpportunity>('/sam-opportunities/', opportunity);
    return response.data;
  },

  update: async (id: number, updates: SAMOpportunityUpdate): Promise<SAMOpportunity> => {
    const response = await apiClient.patch<SAMOpportunity>(`/sam-opportunities/${id}/`, updates);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/sam-opportunities/${id}/`);
  },

  getMatches: async (id: number): Promise<MatchWithDetails[]> => {
    const response = await apiClient.get<MatchWithDetails[]>(`/sam-opportunities/${id}/matches/`);
    return response.data;
  },

  getMatchContracts: async (opportunityId: number, matchId: number): Promise<GovWinContract[]> => {
    const response = await apiClient.get<GovWinContract[]>(`/sam-opportunities/${opportunityId}/matches/${matchId}/contracts/`);
    return response.data;
  },

  shareViaEmail: async (id: number, toEmails: string[], senderName?: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/sam-opportunities/${id}/share/`, {
      to_emails: toEmails,
      sender_name: senderName,
    });
    return response.data;
  },
};

// GovWin Opportunities API
export const govwinOpportunitiesAPI = {
  list: async (skip = 0, limit = 100): Promise<GovWinOpportunity[]> => {
    const response = await apiClient.get<GovWinOpportunity[]>('/govwin-opportunities/', {
      params: { skip, limit },
    });
    return response.data;
  },

  getById: async (id: number): Promise<GovWinOpportunity> => {
    const response = await apiClient.get<GovWinOpportunity>(`/govwin-opportunities/${id}/`);
    return response.data;
  },

  getByGovWinId: async (govwinId: string): Promise<GovWinOpportunity> => {
    const response = await apiClient.get<GovWinOpportunity>(`/govwin-opportunities/govwin-id/${govwinId}/`);
    return response.data;
  },
};

// Matches API
export const matchesAPI = {
  list: async (filters?: MatchFilters): Promise<MatchWithDetails[]> => {
    const response = await apiClient.get<MatchWithDetails[]>('/matches/', { params: filters });
    return response.data;
  },

  listPending: async (skip = 0, limit = 100): Promise<MatchWithDetails[]> => {
    const response = await apiClient.get<MatchWithDetails[]>('/matches/pending/', {
      params: { skip, limit },
    });
    return response.data;
  },

  getById: async (id: number): Promise<MatchWithDetails> => {
    const response = await apiClient.get<MatchWithDetails>(`/matches/${id}/`);
    return response.data;
  },

  create: async (match: MatchCreate): Promise<Match> => {
    const response = await apiClient.post<Match>('/matches/', match);
    return response.data;
  },

  update: async (id: number, updates: MatchUpdate): Promise<Match> => {
    const response = await apiClient.patch<Match>(`/matches/${id}/`, updates);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/matches/${id}/`);
  },
};

// Analytics API
export const analyticsAPI = {
  getOpportunityStats: async (): Promise<OpportunityStatistics> => {
    const response = await apiClient.get<OpportunityStatistics>('/analytics/summary/');
    return response.data;
  },

  getMatchStats: async (): Promise<MatchStatistics> => {
    const response = await apiClient.get<MatchStatistics>('/analytics/match-quality/');
    return response.data;
  },
};

// Admin API
export interface FetchByDateResponse {
  message: string;
  fetched_count: number;
  stored_count: number;
  duplicate_count: number;
  error_count: number;
}

export const fetchSAMOpportunitiesByDate = async (
  postedDate: string,
  naicsCodes?: string[]
): Promise<FetchByDateResponse> => {
  const response = await apiClient.post<FetchByDateResponse>(
    '/sam-opportunities/fetch-by-date',
    {
      posted_date: postedDate,
      naics_codes: naicsCodes,
    }
  );
  return response.data;
};

// CRM Integration API
export const crmAPI = {
  sendToCRM: async (opportunityId: number): Promise<any> => {
    const response = await apiClient.post(`/crm/opportunities/${opportunityId}/send`);
    return response.data;
  },

  getSyncStatus: async (opportunityId: number): Promise<any> => {
    const response = await apiClient.get(`/crm/opportunities/${opportunityId}/status`);
    return response.data;
  },
};

export default apiClient;
