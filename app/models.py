"""
Pydantic models for the SAM.gov API client.
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class OpportunitySearchParams(BaseModel):
    """Parameters for searching opportunities."""
    p_type: Optional[List[str]] = Field(None, description="List of procurement types")
    notice_id: Optional[str] = Field(None, description="Notice ID")
    sol_num: Optional[str] = Field(None, description="Solicitation number")
    title: Optional[str] = Field(None, description="Title of the opportunity")
    state: Optional[str] = Field(None, description="Place of performance state")
    zip_code: Optional[str] = Field(None, description="Place of performance ZIP code")
    set_aside_type: Optional[str] = Field(None, description="Type of set-aside code")
    naics_code: Optional[str] = Field(None, description="NAICS code")
    classification_code: Optional[str] = Field(None, description="Classification code")
    posted_from: Optional[str] = Field(None, description="Posted from date (mm/dd/yyyy)")
    posted_to: Optional[str] = Field(None, description="Posted to date (mm/dd/yyyy)")
    response_deadline_from: Optional[str] = Field(None, description="Response deadline from date (mm/dd/yyyy)")
    response_deadline_to: Optional[str] = Field(None, description="Response deadline to date (mm/dd/yyyy)")
    limit: int = Field(10, description="Number of records to fetch")
    offset: int = Field(0, description="Offset value for pagination")


class Address(BaseModel):
    """Address model."""
    street_address: Optional[str] = None
    city: Optional[Dict[str, str]] = None
    state: Optional[Dict[str, str]] = None
    zip: Optional[str] = None
    country: Optional[Dict[str, str]] = None


class Awardee(BaseModel):
    """Awardee model."""
    name: Optional[str] = None
    location: Optional[Address] = None
    uei_sam: Optional[str] = None


class Award(BaseModel):
    """Award model."""
    date: Optional[str] = None
    number: Optional[str] = None
    amount: Optional[str] = None
    awardee: Optional[Awardee] = None


class PointOfContact(BaseModel):
    """Point of contact model."""
    fax: Optional[str] = None
    type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    full_name: Optional[str] = Field(None, alias="fullName")


class OfficeAddress(BaseModel):
    """Office address model."""
    zipcode: Optional[str] = None
    city: Optional[str] = None
    country_code: Optional[str] = Field(None, alias="countryCode")
    state: Optional[str] = None


class Link(BaseModel):
    """Link model."""
    rel: Optional[str] = None
    href: Optional[str] = None
    hreflang: Optional[str] = None
    media: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    deprecation: Optional[str] = None


class Opportunity(BaseModel):
    """Opportunity model."""
    notice_id: str = Field(alias="noticeId")
    title: Optional[str] = None
    solicitation_number: Optional[str] = Field(None, alias="solicitationNumber")
    department: Optional[str] = None
    sub_tier: Optional[str] = Field(None, alias="subTier")
    office: Optional[str] = None
    posted_date: Optional[str] = Field(None, alias="postedDate")
    type: Optional[str] = None
    base_type: Optional[str] = Field(None, alias="baseType")
    archive_type: Optional[str] = Field(None, alias="archiveType")
    archive_date: Optional[str] = Field(None, alias="archiveDate")
    type_of_set_aside_description: Optional[str] = Field(None, alias="typeOfSetAsideDescription")
    type_of_set_aside: Optional[str] = Field(None, alias="typeOfSetAside")
    response_deadline: Optional[str] = Field(None, alias="responseDeadLine")
    naics_code: Optional[str] = Field(None, alias="naicsCode")
    classification_code: Optional[str] = Field(None, alias="classificationCode")
    active: Optional[str] = None
    award: Optional[Award] = None
    point_of_contact: Optional[List[PointOfContact]] = Field(None, alias="pointOfContact")
    description: Optional[str] = None
    description_text: Optional[str] = None
    organization_type: Optional[str] = Field(None, alias="organizationType")
    office_address: Optional[OfficeAddress] = Field(None, alias="officeAddress")
    place_of_performance: Optional[Address] = Field(None, alias="placeOfPerformance")
    additional_info_link: Optional[str] = Field(None, alias="additionalInfoLink")
    ui_link: Optional[str] = Field(None, alias="uiLink")
    links: Optional[List[Link]] = None
    resource_links: Optional[Any] = Field(None, alias="resourceLinks")


class OpportunityResponse(BaseModel):
    """Response model for opportunities search."""
    total_records: int
    limit: int
    offset: int
    opportunities_data: List[Opportunity]
    links: List[Link]
