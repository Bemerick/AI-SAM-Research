#!/usr/bin/env python
"""
Command-line utility for searching opportunities on SAM.gov.

Usage:
    python sam_cli.py search --posted-from "05/01/2023" --posted-to "05/21/2025" --limit 5
    python sam_cli.py get-opportunity --notice-id "123456789abcdef"
"""
import argparse
import json
import sys
from datetime import datetime

from app.sam_client import SAMClient, SAMApiError
from app.config import SAM_API_KEY


def format_json(data):
    """Format JSON data for display."""
    return json.dumps(data, indent=2)


def search_opportunities(args):
    """Search for opportunities based on command-line arguments."""
    if not SAM_API_KEY:
        print("Error: SAM_API_KEY is not set. Please set it in your .env file.")
        sys.exit(1)
    
    try:
        client = SAMClient()
        result = client.search_opportunities(
            p_type=args.p_type,
            notice_id=args.notice_id,
            sol_num=args.sol_num,
            title=args.title,
            state=args.state,
            zip_code=args.zip_code,
            set_aside_type=args.set_aside_type,
            naics_code=args.naics_code,
            classification_code=args.classification_code,
            posted_from=args.posted_from,
            posted_to=args.posted_to,
            response_deadline_from=args.response_deadline_from,
            response_deadline_to=args.response_deadline_to,
            limit=args.limit,
            offset=args.offset
        )
        
        print(f"Found {result.get('totalRecords', 0)} opportunities")
        print(format_json(result))
        
    except SAMApiError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def get_opportunity(args):
    """Get a specific opportunity by notice ID."""
    if not SAM_API_KEY:
        print("Error: SAM_API_KEY is not set. Please set it in your .env file.")
        sys.exit(1)
    
    try:
        client = SAMClient()
        result = client.get_opportunity_by_id(args.notice_id)
        
        opportunities = result.get("opportunitiesData", [])
        if not opportunities:
            print(f"No opportunity found with notice ID: {args.notice_id}")
            sys.exit(1)
        
        print(format_json(opportunities[0]))
        
    except SAMApiError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for the command-line utility."""
    parser = argparse.ArgumentParser(description="Command-line utility for searching opportunities on SAM.gov")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for opportunities")
    search_parser.add_argument("--p-type", nargs="+", help="List of procurement types")
    search_parser.add_argument("--notice-id", help="Notice ID")
    search_parser.add_argument("--sol-num", help="Solicitation number")
    search_parser.add_argument("--title", help="Title of the opportunity")
    search_parser.add_argument("--state", help="Place of performance state")
    search_parser.add_argument("--zip-code", help="Place of performance ZIP code")
    search_parser.add_argument("--set-aside-type", help="Type of set-aside code")
    search_parser.add_argument("--naics-code", nargs="+", help="NAICS codes - can provide multiple")
    search_parser.add_argument("--classification-code", help="Classification code")
    search_parser.add_argument("--posted-from", help="Posted from date (mm/dd/yyyy)")
    search_parser.add_argument("--posted-to", help="Posted to date (mm/dd/yyyy)")
    search_parser.add_argument("--response-deadline-from", help="Response deadline from date (mm/dd/yyyy)")
    search_parser.add_argument("--response-deadline-to", help="Response deadline to date (mm/dd/yyyy)")
    search_parser.add_argument("--limit", type=int, default=10, help="Number of records to fetch")
    search_parser.add_argument("--offset", type=int, default=0, help="Offset value for pagination")
    
    # Get opportunity command
    get_parser = subparsers.add_parser("get-opportunity", help="Get a specific opportunity by notice ID")
    get_parser.add_argument("--notice-id", required=True, help="Notice ID of the opportunity to retrieve")
    
    args = parser.parse_args()
    
    if args.command == "search":
        search_opportunities(args)
    elif args.command == "get-opportunity":
        get_opportunity(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
