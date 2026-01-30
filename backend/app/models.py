"""
Database models for SAM.gov and GovWin matching system.
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class SAMOpportunity(Base):
    """SAM.gov opportunity model."""
    __tablename__ = "sam_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(Text)
    department = Column(String(255))
    standardized_department = Column(String(255))  # Standardized dept name for matching
    sub_tier = Column(String(255))
    office = Column(String(255))
    naics_code = Column(String(10), index=True)
    full_parent_path = Column(Text)
    fit_score = Column(Float, index=True)
    posted_date = Column(String(50))
    response_deadline = Column(String(50))
    solicitation_number = Column(String(255))
    description = Column(Text)
    summary_description = Column(Text)  # AI-generated summary
    type = Column(String(50))
    ptype = Column(String(100))  # Procurement type (translated)
    classification_code = Column(String(10))
    set_aside = Column(String(255))
    place_of_performance_city = Column(String(100))
    place_of_performance_state = Column(String(10))  # Increased to handle international state codes (e.g., GB-SFK)
    place_of_performance_zip = Column(String(10))
    point_of_contact_email = Column(String(255))
    point_of_contact_name = Column(String(255))
    sam_link = Column(Text)  # SAM.gov UI link
    assigned_practice_area = Column(String(255))  # Assigned practice area
    justification = Column(Text)  # AI justification for fit score

    # Amendment tracking fields
    is_amendment = Column(Integer, default=0)  # 0 = original, 1+ = amendment number
    original_notice_id = Column(String(255), index=True)  # Links to original notice if this is an amendment
    superseded_by_notice_id = Column(String(255), index=True)  # Notice ID that supersedes this one

    # Workflow fields (replacing SharePoint)
    review_for_bid = Column(String(50), default="Pending")  # Pending, Yes, No
    recommend_bid = Column(String(50), default="Pending")  # Pending, Yes, No
    review_comments = Column(Text)  # User comments/notes
    reviewed_by = Column(String(255))  # User who reviewed
    reviewed_at = Column(DateTime(timezone=True))  # When reviewed
    is_followed = Column(Integer, default=0, index=True)  # 0 = not followed, 1 = followed

    analysis_data = Column(Text)  # JSON string of full SAM data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    matches = relationship("Match", back_populates="sam_opportunity", cascade="all, delete-orphan")
    search_logs = relationship("SearchLog", back_populates="sam_opportunity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SAMOpportunity(notice_id='{self.notice_id}', title='{self.title[:50]}...')>"


class GovWinOpportunity(Base):
    """GovWin opportunity model."""
    __tablename__ = "govwin_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    govwin_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(Text)
    type = Column(String(100))
    gov_entity = Column(String(255))
    gov_entity_id = Column(String(100))
    primary_naics = Column(String(10))
    description = Column(Text)
    value = Column(Float)
    post_date = Column(String(50))
    close_date = Column(String(50))
    award_date = Column(String(50))
    stage = Column(String(100))
    raw_data = Column(Text)  # JSON string of full GovWin data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    matches = relationship("Match", back_populates="govwin_opportunity", cascade="all, delete-orphan")
    contracts = relationship("GovWinContract", back_populates="govwin_opportunity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GovWinOpportunity(govwin_id='{self.govwin_id}', title='{self.title[:50]}...')>"


class GovWinContract(Base):
    """GovWin contract model - contracts related to a GovWin opportunity."""
    __tablename__ = "govwin_contracts"

    id = Column(Integer, primary_key=True, index=True)
    govwin_opportunity_id = Column(Integer, ForeignKey("govwin_opportunities.id"), nullable=False, index=True)
    contract_id = Column(String(255), index=True)  # GovWin contract ID
    contract_number = Column(String(255), index=True)  # Actual contract number
    title = Column(Text)
    vendor_name = Column(String(255), index=True)
    vendor_id = Column(String(100))
    contract_value = Column(Float)
    award_date = Column(String(50))
    start_date = Column(String(50))
    end_date = Column(String(50))
    status = Column(String(100))
    contract_type = Column(String(100))
    description = Column(Text)
    raw_data = Column(Text)  # JSON string of full contract data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    govwin_opportunity = relationship("GovWinOpportunity", back_populates="contracts")

    def __repr__(self):
        return f"<GovWinContract(id={self.id}, contract_number='{self.contract_number}', vendor='{self.vendor_name}')>"


class Match(Base):
    """Match between SAM and GovWin opportunities."""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    sam_opportunity_id = Column(Integer, ForeignKey("sam_opportunities.id"), nullable=False)
    govwin_opportunity_id = Column(Integer, ForeignKey("govwin_opportunities.id"), nullable=False)
    search_strategy = Column(String(50), nullable=False)  # agency, naics, title_keywords, combined, multi
    ai_match_score = Column(Float, index=True)  # 0-100
    ai_reasoning = Column(Text)
    status = Column(String(50), default="pending_review", index=True)  # pending_review, confirmed, rejected, needs_info
    user_notes = Column(Text)
    reviewed_by = Column(String(255))
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sam_opportunity = relationship("SAMOpportunity", back_populates="matches")
    govwin_opportunity = relationship("GovWinOpportunity", back_populates="matches")

    # Constraints
    __table_args__ = (
        UniqueConstraint('sam_opportunity_id', 'govwin_opportunity_id', name='uix_sam_govwin_match'),
        Index('idx_match_score_status', 'ai_match_score', 'status'),
    )

    def __repr__(self):
        return f"<Match(id={self.id}, sam_id={self.sam_opportunity_id}, govwin_id={self.govwin_opportunity_id}, score={self.ai_match_score})>"


class SearchLog(Base):
    """Log of GovWin searches performed."""
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, index=True)
    sam_opportunity_id = Column(Integer, ForeignKey("sam_opportunities.id"), nullable=False)
    search_params = Column(Text)  # JSON string of search parameters
    results_count = Column(Integer)
    search_strategy = Column(String(50))
    execution_time = Column(Float)  # seconds
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sam_opportunity = relationship("SAMOpportunity", back_populates="search_logs")

    def __repr__(self):
        return f"<SearchLog(id={self.id}, sam_id={self.sam_opportunity_id}, strategy='{self.search_strategy}')>"
