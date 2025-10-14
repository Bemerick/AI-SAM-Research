"""
Configuration module for SAM.gov API client.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SAM.gov API configuration
SAM_API_KEY = os.getenv("SAM_API_KEY")
SAM_API_URL_V2 = "https://api.sam.gov/prod/opportunities/v2/search"
SAM_API_ALPHA_URL_V2 = "https://api-alpha.sam.gov/prod/opportunities/v2/search"

# Default to production URL unless specified otherwise
SAM_API_BASE_URL = SAM_API_URL_V2

# API rate limits and defaults
DEFAULT_LIMIT = 10
MAX_LIMIT = 100
DEFAULT_OFFSET = 0

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# GovWin API configuration
GOVWIN_USERNAME = os.getenv("GOVWIN_USERNAME")
GOVWIN_PASSWORD = os.getenv("GOVWIN_PASSWORD")

# Teams Webhook configuration
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")

# Microsoft Graph API for SharePoint List configuration
MS_TENANT_ID = os.getenv("MS_TENANT_ID")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
SHAREPOINT_LIST_NAME = os.getenv("SHAREPOINT_LIST_NAME")

# Company practice areas with detailed descriptions
PRACTICE_AREAS = {
    "Acquisition Lifecycle Management": "We help federal agencies buy goods and services more efficiently through their entire procurement process - from initial market research and cost estimates to contract closeout. Our services include building procurement packages, administering contracts and modifications, supporting evaluation panels, and managing contract closeout activities. We use automation and AI tools along with integrated tracking and reporting systems to help agencies manage the process more effectively.",
    "Program Management & Delivery": "We help federal agencies successfully execute their programs and build organizational capabilities. Our services include program management, performance evaluation using data analytics, process improvement through automation, and comprehensive management support to ensure missions are accomplished effectively.",
    "Business Transformation & Change Management": "We help federal agencies improve their operations by analyzing current processes, redesigning workflows, and managing organizational change. Our services include process diagnostics, optimization strategies, change management, and strategic communications to ensure successful transformation initiatives.",
    "Grant Program Management": "Providing targeted technical assistance through research and data analytics, policy evaluation, and strategic alignment—supported by expert peer review management, event coordination, and grants operations oversight.",
    "Risk, Safety & Mission Assurance": "Our Safety and Risk Management services ensure organizations remain secure, resilient, and compliant. We provide expert support in program planning, cybersecurity compliance, and mission assurance. Our team specializes in risk assessment, incident preparedness, and continuity planning to safeguard critical assets and operations. Through compliance auditing, monitoring, and training programs, we help organizations mitigate risks and enhance resilience.",
    "Business & Technology Services": "We help federal agencies modernize their technology systems and operations. Our services include custom software development, automation using RPA and AI, user experience design, application support, and quality assurance testing. We also provide data analytics and insights to support better decision-making. Our teams integrate these solutions into complex government environments to deliver long-term results.",
    "Human Capital & Workforce Innovation": "We help federal agencies build and develop their workforce through strategic HR consulting, workforce planning, and talent acquisition. Our services include designing and executing training and development programs, improving organizational structure, and enhancing operational efficiency. We use research, analytics, and industry insights to ensure our workforce solutions meet each agency's specific needs."
}

# NAICS codes for company capabilities
COMPANY_NAICS_CODES = [
    "519190", "518210", "541430", "541490", "541511", "541512", "541519", 
    "541611", "541618", "541690", "541990", "92119", "921190", "541715", 
    "611430", "561110", "541990"
]

# Procurement types of interest
PROCUREMENT_TYPES = ["p", "r", "o", "k"]

# Preferred agencies that should receive higher scoring weights
PREFERRED_AGENCIES = [
    "Department of Agriculture",
    "Department of Transportation",
    "Department of Veterans Affairs",
    "Department of Education",
    "Department of Interior",
    "Department of Homeland Security"
]

# Validate essential configurations
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set in the .env file.")
if not SAM_API_KEY:
    print("Warning: SAM_API_KEY is not set in the .env file.")
if not TEAMS_WEBHOOK_URL:
    print("Warning: TEAMS_WEBHOOK_URL is not set in the .env file.")

# Validate Microsoft Graph configurations (optional, but good practice)
if not MS_TENANT_ID:
    print("Warning: MS_TENANT_ID is not set in the .env file for Microsoft List integration.")
if not MS_CLIENT_ID:
    print("Warning: MS_CLIENT_ID is not set in the .env file for Microsoft List integration.")
if not MS_CLIENT_SECRET:
    print("Warning: MS_CLIENT_SECRET is not set in the .env file for Microsoft List integration.")
if not SHAREPOINT_SITE_URL:
    print("Warning: SHAREPOINT_SITE_URL is not set in the .env file for Microsoft List integration.")
if not SHAREPOINT_LIST_NAME:
    print("Warning: SHAREPOINT_LIST_NAME is not set in the .env file for Microsoft List integration.")
