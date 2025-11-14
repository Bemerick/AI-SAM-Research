/**
 * TypeScript types matching the backend API models
 */

export interface SAMOpportunity {
  id: number;
  notice_id: string;
  title: string | null;
  department: string | null;
  standardized_department: string | null;
  sub_tier: string | null;
  office: string | null;
  naics_code: string | null;
  full_parent_path: string | null;
  fit_score: number | null;
  posted_date: string | null;
  response_deadline: string | null;
  solicitation_number: string | null;
  description: string | null;
  summary_description: string | null;
  type: string | null;
  ptype: string | null;
  classification_code: string | null;
  set_aside: string | null;
  place_of_performance_city: string | null;
  place_of_performance_state: string | null;
  place_of_performance_zip: string | null;
  point_of_contact_email: string | null;
  point_of_contact_name: string | null;
  sam_link: string | null;
  assigned_practice_area: string | null;
  justification: string | null;

  // Amendment tracking fields
  is_amendment: number | null;
  original_notice_id: string | null;
  superseded_by_notice_id: string | null;

  // Workflow fields
  review_for_bid: string;
  recommend_bid: string;
  review_comments: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;

  // GovWin matching
  match_count?: number | null;

  created_at: string;
  updated_at: string | null;
}

export interface SAMOpportunityCreate extends Omit<SAMOpportunity, 'id' | 'created_at' | 'updated_at' | 'reviewed_at'> {
  analysis_data?: string;
}

export interface SAMOpportunityUpdate {
  fit_score?: number;
  analysis_data?: string;
  review_for_bid?: string;
  recommend_bid?: string;
  review_comments?: string;
  reviewed_by?: string;
}

export interface GovWinOpportunity {
  id: number;
  govwin_id: string;
  title: string | null;
  type: string | null;
  gov_entity: string | null;
  gov_entity_id: string | null;
  primary_naics: string | null;
  description: string | null;
  value: number | null;
  post_date: string | null;
  close_date: string | null;
  award_date: string | null;
  stage: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface GovWinContract {
  id: number;
  govwin_opportunity_id: number;
  contract_id: string | null;
  contract_number: string | null;
  title: string | null;
  vendor_name: string | null;
  vendor_id: string | null;
  contract_value: number | null;
  award_date: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string | null;
  contract_type: string | null;
  description: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Match {
  id: number;
  sam_opportunity_id: number;
  govwin_opportunity_id: number;
  search_strategy: string;
  ai_match_score: number | null;
  ai_reasoning: string | null;
  status: MatchStatus;
  user_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface MatchWithDetails extends Match {
  sam_opportunity: SAMOpportunity;
  govwin_opportunity: GovWinOpportunity;
}

export interface MatchCreate {
  sam_opportunity_id: number;
  govwin_opportunity_id: number;
  search_strategy: string;
  ai_match_score?: number;
  ai_reasoning?: string;
  status?: MatchStatus;
  user_notes?: string;
}

export interface MatchUpdate {
  ai_match_score?: number;
  ai_reasoning?: string;
  status?: MatchStatus;
  user_notes?: string;
  reviewed_by?: string;
}

export interface OpportunityStatistics {
  total_sam_opportunities: number;
  total_govwin_opportunities: number;
  high_scoring_sam_opps: number;
  avg_fit_score: number | null;
  total_searches_performed: number;
}

export interface MatchStatistics {
  total_matches: number;
  pending_review: number;
  confirmed: number;
  rejected: number;
  needs_info: number;
  average_ai_score: number | null;
  top_search_strategy: string | null;
}

// Enums and constants
export type MatchStatus = 'pending_review' | 'confirmed' | 'rejected' | 'needs_info';
export type ReviewStatus = 'Pending' | 'Yes' | 'No';

export const MATCH_STATUSES: MatchStatus[] = ['pending_review', 'confirmed', 'rejected', 'needs_info'];
export const REVIEW_STATUSES: ReviewStatus[] = ['Pending', 'Yes', 'No'];

// Filter interfaces
export interface SAMOpportunityFilters {
  skip?: number;
  limit?: number;
  min_fit_score?: number;
  department?: string;
  naics_code?: string;
  review_for_bid?: string;
  recommend_bid?: string;
}

export interface MatchFilters {
  skip?: number;
  limit?: number;
  status?: MatchStatus;
  min_score?: number;
  max_score?: number;
  search_strategy?: string;
}
