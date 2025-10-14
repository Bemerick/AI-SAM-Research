#!/usr/bin/env python
"""
Script to search for SAM.gov opportunities matching company NAICS codes and procurement types,
then analyze them using OpenAI to evaluate fit with company practice areas.
"""
import json
import os
import argparse
from datetime import datetime, timedelta
import time
import pytz

from app.sam_client import SAMClient, SAMApiError
from app.openai_analyzer import OpportunityAnalyzer
from app.teams_notifier import TeamsNotifier
from app.microsoft_list_poster import post_opportunities_to_list # Added for MS List posting
from app.config import COMPANY_NAICS_CODES, PROCUREMENT_TYPES, PRACTICE_AREAS, OPENAI_API_KEY, TEAMS_WEBHOOK_URL

MAX_OPPS_PER_MESSAGE = 15

def main():
    """
    Main function to search for and analyze opportunities.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SAM.gov Opportunity Analyzer')
    parser.add_argument('--format', choices=['markdown', 'html', 'json'], default='markdown',
                        help='Output format (markdown, html, or json)')
    parser.add_argument('--days', type=int, default=1,
                        help='Number of days to search back from today')
    parser.add_argument('--use_cached', action='store_true',
                        help='Use cached opportunities from raw_opportunities.json instead of making API calls')
    parser.add_argument('--send-to-teams', action='store_true',
                        help='Send the markdown report to a configured Microsoft Teams channel via webhook.')
    parser.add_argument('--output-file', type=str, default=None,
                        help='Base filename for output files (default: opportunity_analysis)')
    parser.add_argument('--post-to-list', action='store_true',
                        help='Post the analyzed opportunities to the configured Microsoft List.')
    args = parser.parse_args()
    print("SAM.gov Opportunity Analyzer")
    print("============================")
    
    output_file_base = args.output_file if args.output_file else "opportunity_analysis"
    output_filename_json = f"{output_file_base}.json"
    output_filename_md = f"{output_file_base}.md"
    output_filename_html = f"{output_file_base}.html"

    # Initialize the SAM client
    try:
        sam_client = SAMClient()
    except ValueError as e:
        print(f"Error initializing SAM client: {str(e)}")
        return
    
    # Initialize the OpenAI analyzer
    try:
        analyzer = OpportunityAnalyzer(openai_api_key=OPENAI_API_KEY)
    except ValueError as e:
        print(f"Error initializing OpenAI analyzer: {str(e)}")
        return
    
    # Set date range
    days_to_search = args.days
    today = datetime.now()
    yesterday = today - timedelta(days=days_to_search)
    posted_from = yesterday.strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")
    
    print(f"\nSearching for opportunities with:")
    print(f"- NAICS codes: {', '.join(COMPANY_NAICS_CODES)}")
    print(f"- Procurement types: {', '.join(PROCUREMENT_TYPES)}")
    print(f"- Date range: {posted_from} to {posted_to} ({days_to_search} days)")
    print(f"- Practice areas: {', '.join(PRACTICE_AREAS.keys())}")
    print("\nPractice Area Descriptions:")
    for area, description in PRACTICE_AREAS.items():
        print(f"- {area}: {description[:100]}...")
    
    
    # Collect all opportunities matching our criteria
    all_opportunities = []
    seen_opportunity_ids = set() # To keep track of unique opportunities

    if args.use_cached:
        print("\nUsing cached raw opportunities from raw_opportunities.json...")
        try:
            with open('raw_opportunities.json', 'r') as f:
                cached_data = json.load(f)
                # Ensure cached_data is a list of opportunities
                if isinstance(cached_data, list):
                    all_opportunities = cached_data
                elif isinstance(cached_data, dict) and 'opportunities' in cached_data:
                    # Handle if raw_opportunities.json was saved as a dict with an 'opportunities' key
                    all_opportunities = cached_data['opportunities']
                else:
                    print("Error: raw_opportunities.json is not in the expected format (list of opportunities or dict with 'opportunities' key).")
                    return
            print(f"Loaded {len(all_opportunities)} opportunities from raw_opportunities.json")
        except FileNotFoundError:
            print("Error: raw_opportunities.json not found. Run the script without --use_cached first to generate it.")
            return
        except json.JSONDecodeError:
            print("Error: raw_opportunities.json is not a valid JSON file.")
            return
    else:
        # Search for each NAICS code separately
        for naics_code in COMPANY_NAICS_CODES:
            print(f"\nSearching for opportunities with NAICS code {naics_code}...")
            
            try:
                # Search for opportunities with this NAICS code
                result = sam_client.search_opportunities(
                    p_type=PROCUREMENT_TYPES,
                    naics_code=naics_code,
                    posted_from=posted_from,
                    posted_to=posted_to,
                    limit=20,  # Limit per NAICS code
                    include_description=True  # Include descriptions for analysis
                )
                time.sleep(1) # Added delay
                
                # Get the opportunities for this NAICS code
                opportunities = result.get("opportunitiesData", [])
                count = len(opportunities)
                
                print(f"Found {count} opportunities for NAICS code {naics_code}")
                
                # Ensure unique opportunities
                current_opportunities_count = len(all_opportunities)
                for opp in opportunities:
                    if opp['noticeId'] not in seen_opportunity_ids:
                        all_opportunities.append(opp)
                        seen_opportunity_ids.add(opp['noticeId'])
                
                added_count = len(all_opportunities) - current_opportunities_count
                if added_count > 0:
                    print(f"Added {added_count} new unique opportunities for NAICS code {naics_code}.")

            except SAMApiError as e:
                print(f"Error searching for NAICS code {naics_code}: {str(e)}")

    # Save raw opportunities to a file if fetched from API
    if not args.use_cached and all_opportunities:
        print(f"\nFound {len(all_opportunities)} unique opportunities across all NAICS codes")
        with open('raw_opportunities.json', 'w') as f:
            json.dump(all_opportunities, f, indent=4)
        print("Raw opportunities saved to raw_opportunities.json")
    elif not all_opportunities:
        print("\nNo opportunities found or loaded. Exiting.")
        return

    print("\nAnalyzing opportunities with OpenAI...")
    # Always get the full JSON data first for internal use and JSON output
    analysis_result = analyzer.analyze_opportunities(all_opportunities, output_format='json') 
    
    if isinstance(analysis_result, dict) and "error" in analysis_result:
        print(f"Error during analysis: {analysis_result['error']}")
        return # Exit if analysis itself failed
    
    # Save JSON output - this should always happen if analysis was successful
    with open(output_filename_json, "w") as f_json: 
        json.dump(analysis_result, f_json, indent=2)
    print(f"JSON analysis saved to {output_filename_json}")

    # Post to Microsoft List if requested
    if args.post_to_list:
        ranked_ops_for_list = analysis_result.get("ranked_opportunities", [])
        if ranked_ops_for_list:
            print("\nPosting ranked opportunities to Microsoft List...")
            try:
                post_opportunities_to_list(ranked_ops_for_list)
                print("Successfully initiated posting to Microsoft List. Check logs for details.")
            except Exception as e:
                print(f"Error during posting to Microsoft List: {e}")
        else:
            print("\nNo ranked opportunities to post to Microsoft List.")

    # If only JSON was requested and not sending to teams and not posting to list, then exit.
    if args.format.lower() == "json" and not args.send_to_teams and not args.post_to_list:
        print("JSON output generated. Exiting as only JSON was requested and no other actions (Teams, List) were specified.")
        return

    # Proceed with Markdown/Teams if requested
    ranked_opportunities = analysis_result.get("ranked_opportunities", [])
    unranked_opportunities = analysis_result.get("unranked_opportunities", [])
    
    # Generate a single, consistent timestamp for all parts of the report and the full file
    if pytz:
        generated_on_timestamp = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        generated_on_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC (pytz not available)")

    report_agent = analyzer.report_agent # Get the ReportAgent instance

    if args.send_to_teams:
        if TEAMS_WEBHOOK_URL:
            print("\nSending report to Microsoft Teams in parts...")
            notifier = TeamsNotifier(webhook_url=TEAMS_WEBHOOK_URL)
            report_date_str_title = datetime.now().strftime("%Y-%m-%d") # For the main title part
            
            # Batch and send ranked opportunities
            if ranked_opportunities:
                num_ranked_parts = (len(ranked_opportunities) + MAX_OPPS_PER_MESSAGE - 1) // MAX_OPPS_PER_MESSAGE
                for i in range(num_ranked_parts):
                    batch_start = i * MAX_OPPS_PER_MESSAGE
                    batch_end = batch_start + MAX_OPPS_PER_MESSAGE
                    current_batch_ranked = ranked_opportunities[batch_start:batch_end]
                    
                    part_info_str = f"(Ranked - Part {i + 1} of {num_ranked_parts})"
                    teams_title = f"SAM Opportunity Analysis - {report_date_str_title} {part_info_str}"
                    
                    markdown_part = report_agent.generate_markdown_report(
                        ranked_opportunities_batch=current_batch_ranked,
                        unranked_opportunities_batch=[],
                        report_title_prefix="SAM.gov Opportunity Analysis",
                        part_info=part_info_str,
                        generated_on_timestamp=generated_on_timestamp # Use consistent timestamp
                    )
                    print(f"Sending {part_info_str} to Teams ({len(current_batch_ranked)} ranked opps)...")
                    if notifier.send_message(markdown_part, title=teams_title):
                        print(f"{part_info_str} successfully sent to Teams.")
                    else:
                        print(f"Failed to send {part_info_str} to Teams.")
                    time.sleep(2) # Delay between messages

            # Batch and send unranked opportunities
            if unranked_opportunities:
                num_unranked_parts = (len(unranked_opportunities) + MAX_OPPS_PER_MESSAGE - 1) // MAX_OPPS_PER_MESSAGE
                for i in range(num_unranked_parts):
                    batch_start = i * MAX_OPPS_PER_MESSAGE
                    batch_end = batch_start + MAX_OPPS_PER_MESSAGE
                    current_batch_unranked = unranked_opportunities[batch_start:batch_end]

                    part_info_str = f"(Unranked - Part {i + 1} of {num_unranked_parts})"
                    teams_title = f"SAM Opportunity Analysis - {report_date_str_title} {part_info_str}"

                    markdown_part = report_agent.generate_markdown_report(
                        ranked_opportunities_batch=[],
                        unranked_opportunities_batch=current_batch_unranked,
                        report_title_prefix="SAM.gov Opportunity Analysis",
                        part_info=part_info_str,
                        generated_on_timestamp=generated_on_timestamp # Use consistent timestamp
                    )
                    print(f"Sending {part_info_str} to Teams ({len(current_batch_unranked)} unranked opps)...")
                    if notifier.send_message(markdown_part, title=teams_title):
                        print(f"{part_info_str} successfully sent to Teams.")
                    else:
                        print(f"Failed to send {part_info_str} to Teams.")
                    time.sleep(2) # Delay between messages
        else:
            print("\n--send-to-teams was specified, but TEAMS_WEBHOOK_URL is not configured. Skipping Teams notification.")

    # Save full Markdown report to file if format is markdown
    if args.format.lower() == "markdown":
        print(f"\nGenerating full Markdown report for file {output_filename_md}...")
        full_markdown_report = report_agent.generate_markdown_report(
            ranked_opportunities_batch=ranked_opportunities, # All ranked
            unranked_opportunities_batch=unranked_opportunities, # All unranked
            report_title_prefix="SAM.gov Opportunity Analysis (Full Report)",
            part_info=None, # No part info for the full report file
            generated_on_timestamp=generated_on_timestamp # Use consistent timestamp
        )
        with open(output_filename_md, "w") as f: 
            f.write(full_markdown_report)
        print(f"Full Markdown analysis saved to {output_filename_md}")

    elif args.format.lower() == "html":
        # This section remains largely as it was, ensure it uses 'analysis_result' (the JSON data)
        # and 'output_filename_html' correctly.
        print("\nHTML output generation...")
        if isinstance(analysis_result, dict):
            template_path = os.path.join(os.path.dirname(__file__), "app", "templates", "opportunity_template.html")
            try:
                with open(template_path, "r") as template_file:
                    template_content = template_file.read()
                
                # This is a placeholder. Actual HTML generation might be more complex
                # and require parsing 'analysis_result' (JSON) to populate the template.
                html_to_insert = "<!-- HTML content generated from JSON data would be inserted here. -->"
                # Example: html_to_insert = convert_json_to_html_for_template(analysis_result)

                html_content = template_content.replace("<!-- Content will be inserted here by the OpenAI model -->", html_to_insert)
                
                with open(output_filename_html, "w") as f: 
                    f.write(html_content)
                print(f"HTML analysis saved to {output_filename_html}")

            except FileNotFoundError:
                print(f"Error: HTML template not found at {template_path}")
            except Exception as e:
                print(f"Error processing HTML output: {e}")
        else:
            print(f"Error: Expected dictionary for HTML processing, but got: {type(analysis_result)}")
    
    print("\nScript finished.")
    
if __name__ == "__main__":
    main()
