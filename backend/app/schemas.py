"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# SAM Opportunity Schemas
class SAMOpportunityBase(BaseModel):
    """Base schema for SAM opportunity."""
    notice_id: str
    title: Optional[str] = None
    department: Optional[str] = None
    standardized_department: Optional[str] = None
    sub_tier: Optional[str] = None
    office: Optional[str] = None
    naics_code: Optional[str] = None
    full_parent_path: Optional[str] = None
    fit_score: Optional[float] = None
    posted_date: Optional[str] = None
    response_deadline: Optional[str] = None
    solicitation_number: Optional[str] = None
    description: Optional[str] = None
    summary_description: Optional[str] = None
    type: Optional[str] = None
    ptype: Optional[str] = None
    classification_code: Optional[str] = None
    set_aside: Optional[str] = None
    place_of_performance_city: Optional[str] = None
    place_of_performance_state: Optional[str] = None
    place_of_performance_zip: Optional[str] = None
    point_of_contact_email: Optional[str] = None
    point_of_contact_name: Optional[str] = None
    sam_link: Optional[str] = None
    assigned_practice_area: Optional[str] = None
    justification: Optional[str] = None
    is_amendment: Optional[int] = 0
    original_notice_id: Optional[str] = None
    superseded_by_notice_id: Optional[str] = None
    review_for_bid: Optional[str] = "Pending"
    recommend_bid: Optional[str] = "Pending"
    review_comments: Optional[str] = None
    is_followed: Optional[int] = 0


class SAMOpportunityCreate(SAMOpportunityBase):
    """Schema for creating SAM opportunity."""
    analysis_data: Optional[str] = None  # JSON string


class SAMOpportunityUpdate(BaseModel):
    """Schema for updating SAM opportunity."""
    fit_score: Optional[float] = None
    assigned_practice_area: Optional[str] = None
    justification: Optional[str] = None
    summary_description: Optional[str] = None
    analysis_data: Optional[str] = None
    review_for_bid: Optional[str] = None
    recommend_bid: Optional[str] = None
    review_comments: Optional[str] = None
    reviewed_by: Optional[str] = None
    is_followed: Optional[int] = None


class SAMOpportunity(SAMOpportunityBase):
    """Schema for SAM opportunity response."""
    id: int
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    match_count: Optional[int] = None  # Number of GovWin matches

    model_config = ConfigDict(from_attributes=True)


# GovWin Opportunity Schemas
class GovWinOpportunityBase(BaseModel):
    """Base schema for GovWin opportunity."""
    govwin_id: str
    title: Optional[str] = None
    type: Optional[str] = None
    gov_entity: Optional[str] = None
    gov_entity_id: Optional[str] = None
    primary_naics: Optional[str] = None
    description: Optional[str] = None
    value: Optional[float] = None
    post_date: Optional[str] = None
    close_date: Optional[str] = None
    award_date: Optional[str] = None
    stage: Optional[str] = None


class GovWinOpportunityCreate(GovWinOpportunityBase):
    """Schema for creating GovWin opportunity."""
    raw_data: Optional[str] = None  # JSON string


class GovWinOpportunity(GovWinOpportunityBase):
    """Schema for GovWin opportunity response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# GovWin Contract Schemas
class GovWinContractBase(BaseModel):
    """Base schema for GovWin contract."""
    govwin_opportunity_id: int
    contract_id: Optional[str] = None
    contract_number: Optional[str] = None
    title: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    contract_value: Optional[float] = None
    award_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    contract_type: Optional[str] = None
    description: Optional[str] = None


class GovWinContractCreate(GovWinContractBase):
    """Schema for creating GovWin contract."""
    raw_data: Optional[str] = None  # JSON string


class GovWinContract(GovWinContractBase):
    """Schema for GovWin contract response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Match Schemas
class MatchBase(BaseModel):
    """Base schema for match."""
    sam_opportunity_id: int
    govwin_opportunity_id: int
    search_strategy: str
    ai_match_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    status: str = "pending_review"
    user_notes: Optional[str] = None


class MatchCreate(MatchBase):
    """Schema for creating match."""
    pass


class MatchCreateFromExternalIDs(BaseModel):
    """Schema for creating match using external IDs (SAM notice ID and GovWin ID string)."""
    sam_notice_id: str
    govwin_id: str
    search_strategy: str = "ai_matching"
    match_score: float
    match_notes: Optional[str] = None
    status: str = "pending_review"


class MatchUpdate(BaseModel):
    """Schema for updating match."""
    ai_match_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    status: Optional[str] = None
    user_notes: Optional[str] = None
    reviewed_by: Optional[str] = None


class Match(MatchBase):
    """Schema for match response."""
    id: int
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MatchWithDetails(Match):
    """Schema for match with full opportunity details."""
    sam_opportunity: SAMOpportunity
    govwin_opportunity: GovWinOpportunity

    model_config = ConfigDict(from_attributes=True)


# Search Log Schemas
class SearchLogBase(BaseModel):
    """Base schema for search log."""
    sam_opportunity_id: int
    search_params: str  # JSON string
    results_count: Optional[int] = None
    search_strategy: str
    execution_time: Optional[float] = None
    error_message: Optional[str] = None


class SearchLogCreate(SearchLogBase):
    """Schema for creating search log."""
    pass


class SearchLog(SearchLogBase):
    """Schema for search log response."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Filter and Pagination Schemas
class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Number of records to return")


class MatchFilters(BaseModel):
    """Schema for filtering matches."""
    status: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    search_strategy: Optional[str] = None
    sam_notice_id: Optional[str] = None


class SAMOpportunityFilters(BaseModel):
    """Schema for filtering SAM opportunities."""
    min_fit_score: Optional[float] = Field(None, ge=0, le=10)
    department: Optional[str] = None
    naics_code: Optional[str] = None


# Analytics Schemas
class MatchStatistics(BaseModel):
    """Schema for match statistics."""
    total_matches: int
    pending_review: int
    confirmed: int
    rejected: int
    needs_info: int
    average_ai_score: Optional[float] = None
    top_search_strategy: Optional[str] = None


class OpportunityStatistics(BaseModel):
    """Schema for opportunity statistics."""
    total_sam_opportunities: int
    total_govwin_opportunities: int
    high_scoring_sam_opps: int  # fit_score > 6
    avg_fit_score: Optional[float] = None
    total_searches_performed: int
