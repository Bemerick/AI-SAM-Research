"""
OpenAI integration module for analyzing SAM.gov opportunities.
"""
import json
import os
from typing import Any, Dict, List, Tuple, Union
from openai import OpenAI
import logging
from .config import OPENAI_API_KEY, PRACTICE_AREAS, PREFERRED_AGENCIES
import datetime
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    import pytz
except ImportError:
    pytz = None # type: ignore

# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BusinessDevelopmentAgent:
    """
    Agent responsible for analyzing opportunities, standardizing them, 
    and preparing them for ranking.
    """
    BATCH_SIZE = 3 # Class attribute for batch size (reduced from 5 to save tokens/time)

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model # Will be used in get_ranked_opportunities_json
        if not self.api_key:
            raise ValueError("OpenAI API key is required for BusinessDevelopmentAgent.")
        # self.client will be initialized here but used in get_ranked_opportunities_json
        # Set timeout to 5 minutes (300 seconds) to prevent hanging
        import httpx
        self.client = OpenAI(
            api_key=self.api_key,
            timeout=httpx.Timeout(300.0, read=300.0, write=300.0, connect=30.0)
        )
        
    def _empty_usage(self) -> Dict[str, int]:
           """Returns an empty usage dictionary."""
           return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _standardize_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize an opportunity's data to ensure consistent processing.
        """
        # IMPORTANT: This is a simplified version based on what was visible.
        # You might have a more detailed _standardize_opportunity method.
        # Please ensure you use YOUR version of _standardize_opportunity if it's more complex.
        opp = opportunity.copy()

        # Ensure notice_id is populated (SAM.gov uses 'noticeId')
        # The .get() method will return None if 'noticeId' is not in opportunity, 
        # which is handled by the calling code in OpportunityAnalyzer.
        opp['notice_id'] = opportunity.get('noticeId')
    
        # Standardize department (extract from fullParentPathName)
        if 'fullParentPathName' in opp and opp['fullParentPathName']:
            dept_path = opp['fullParentPathName'].split('.')
            if dept_path:
                dept = dept_path[0].strip().upper()
                opp['standardized_department'] = dept
                opp['department'] = dept  # Also set 'department' field for consistency
            else:
                opp['standardized_department'] = 'N/A'
                opp['department'] = 'N/A'
        else:
            opp['standardized_department'] = 'N/A'
            opp['department'] = 'N/A'
        
        # Standardize type
        opp['standardized_type'] = opp.get('type', 'N/A').lower()

        # NAICS Code
        opp['naics_code'] = opportunity.get('naicsCode', 'N/A')
        
        # Set Aside Information
        # The actual text description of the set-aside
        opp['set_aside'] = opportunity.get('typeOfSetAsideDescription', opportunity.get('setAside', 'N/A'))

        # Small business flag (can be derived from set_aside or kept if distinct logic applies)
        opp['is_small_business'] = False
        if opp['set_aside'] and isinstance(opp['set_aside'], str):
            opp['is_small_business'] = 'small business' in opp['set_aside'].lower()

        # Procurement Type (ptype)
        opp['ptype'] = opportunity.get('type', 'N/A').lower() # Use 'type' from SAM.gov and convert to lowercase
    
        # Dates
        raw_response_deadline = opp.get('responseDeadLine') # Get the raw value from the opportunity copy
        if raw_response_deadline and isinstance(raw_response_deadline, str) and len(raw_response_deadline) >= 10:
            opp['response_date'] = raw_response_deadline[:10]  # Extract YYYY-MM-DD
        else:
            opp['response_date'] = 'N/A' # Default if not present, not a string, or too short
        
        opp['posted_date'] = opp.get('postedDate', 'N/A')

        # Solicitation Number and Classification Code (not for AI, but for SharePoint)
        opp['solicitationNumber'] = opportunity.get('solicitationNumber', 'N/A')
        opp['classificationCode'] = opportunity.get('classificationCode', 'N/A')

        # Description
        opp['descriptionText'] = opp.get('descriptionText', opp.get('description', 'No description available'))
        
        # Link
        raw_ui_link = opportunity.get('uiLink')
        if not raw_ui_link:
            try:
                logger.warning(f"Raw opportunity (Title: {opportunity.get('title', 'N/A')}) is missing 'uiLink' or it's empty. Value: '{raw_ui_link}'. Available keys: {list(opportunity.keys())}")
            except NameError: # Fallback if logger is not defined
                print(f"WARNING: Raw opportunity (Title: {opportunity.get('title', 'N/A')}) is missing 'uiLink' or it's empty. Value: '{raw_ui_link}'. Available keys: {list(opportunity.keys())}")
            
        opp['uiLink'] = raw_ui_link if raw_ui_link else 'N/A'
        print(f"DEBUG_STANDARDIZE: notice_id={opp.get('notice_id', 'N/A')}, opp['uiLink'] set to: '{opp['uiLink']}'") # DEBUG

        return opp

    def _prepare_input_for_ranking_model(self, opportunities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Prepare opportunities data. Rankable opportunities are returned as a list of dicts.
        Unrankable opportunities (due to insufficient data) are also returned as a list of dicts.
        """
        standardized_opportunities = [self._standardize_opportunity(opp) for opp in opportunities]
        rankable_prepared_data = []
        unrankable_opportunities_data = []
        
        # Keep track of noticeIds to process each unique opportunity once for ranking
        processed_notice_ids_for_ranking = set()

        rankable_id_counter = 1 # This is used for the 'id' field sent to AI

        for opp in standardized_opportunities:
            notice_id = opp.get('noticeId', f"MISSING_NOTICE_ID_{rankable_id_counter}") # Fallback if noticeId is missing

            # Skip if this notice_id has already been processed for ranking
            if notice_id in processed_notice_ids_for_ranking and notice_id != f"MISSING_NOTICE_ID_{rankable_id_counter}": # only skip if it's a real ID
                logger.debug(f"Skipping duplicate noticeId '{notice_id}' for AI ranking preparation.")
                continue
            
            title = opp.get('title', 'N/A')
            # department, posted_date, response_date, etc. should come from _standardize_opportunity
            department = opp.get('standardized_department', 'N/A')
            posted_date = opp.get('posted_date', 'N/A')
            response_date = opp.get('response_date', 'N/A') # Ensure this is the correct response date field
            opp_type = opp.get('standardized_type', 'N/A')
            naics = opp.get('naicsCode', 'N/A')
            set_aside = opp.get('typeOfSetAsideDescription', 'None')
            is_sb = opp.get('is_small_business', False)
            description = opp.get('descriptionText', 'No description available') # From standardization
            link = opp.get('uiLink', 'N/A') # From standardization
            sol_num = opp.get('solicitationNumber', 'N/A')

            # Criteria for unrankable (use constants from class if defined, e.g., self.MIN_TITLE_LEN)
            # Using placeholder values here, adjust to your actual criteria.
            MIN_TITLE_LEN = getattr(self, 'MIN_TITLE_LEN', 5) 
            MIN_DESC_LEN = getattr(self, 'MIN_DESC_LEN', 20)

            is_title_poor = title == 'N/A' or len(title) < MIN_TITLE_LEN
            is_desc_poor = description == 'No description available' or len(description) < MIN_DESC_LEN

            if is_title_poor or is_desc_poor:
                unrankable_opportunities_data.append({
                    "title": title,
                    "notice_id": notice_id,
                    "department": department,
                    "set_aside": set_aside,
                    "response_date": response_date,
                    "link": link,
                    "reason_unranked": f"Title too short (len: {len(title)}) or description too short (len: {len(description)})."
                })
            else:
                # Add to processed set only if it's going to be rankable
                if notice_id != f"MISSING_NOTICE_ID_{rankable_id_counter}": # only add real IDs
                    processed_notice_ids_for_ranking.add(notice_id)

                # For AI, provide a shorter summary if full description is very long, else full description.
                # Truncate more aggressively to save tokens (1500 chars is ~300-400 words)
                ai_description_input = description[:1500] + "...[truncated]" if len(description) > 1500 else description # For AI to read
                summary_desc_for_output = description  # Keep full description for database storage

                rankable_prepared_data.append({
                    "id": rankable_id_counter, # Internal ID for this batch for AI, AI returns as original_opportunity_id
                    "title": title,
                    "notice_id": notice_id, # Actual notice_id
                    "solicitation_number": sol_num,
                    "department": department,
                    "posted_date": posted_date,
                    "response_date": response_date,
                    "type": opp_type,
                    "naics_code": naics,
                    "set_aside": set_aside,
                    "is_small_business_set_aside": is_sb,
                    "description_for_ai_processing": ai_description_input, 
                    "summary_description_for_output": summary_desc_for_output,
                    "link": link
                })
                rankable_id_counter += 1
        
        logger.info(f"Prepared {len(rankable_prepared_data)} unique opportunities for AI ranking after duplicate check.")
        logger.info(f"Categorized {len(unrankable_opportunities_data)} as unrankable (before sending to AI).")
        
        # Ensure this returns the list directly, NOT json.dumps()
        return rankable_prepared_data, unrankable_opportunities_data
    

    def get_ranked_opportunities_json(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Uses OpenAI to rank opportunities in batches and returns the result as JSON,
        including both ranked and unranked items, and aggregated token usage.
        """
        logger.info(f"BusinessDevelopmentAgent received {len(opportunities)} opportunities for processing.")
        if not opportunities:
            logger.info("No opportunities data provided to BusinessDevelopmentAgent.")
            return {"ranked_opportunities": [], "unranked_opportunities": [], "usage": self._empty_usage(), "error": "No opportunities provided."}

        rankable_opportunities_list, unrankable_opportunities_data = self._prepare_input_for_ranking_model(opportunities)
        
        num_rankable_for_ai = len(rankable_opportunities_list)
        
        logger.info(f"Prepared {num_rankable_for_ai} opportunities for AI ranking.")
        logger.info(f"Categorized {len(unrankable_opportunities_data)} opportunities as unrankable (will not be sent to AI).")

        total_categorized = num_rankable_for_ai + len(unrankable_opportunities_data)
        # (Your existing logging for count mismatches can remain here if desired)
        if total_categorized != len(opportunities):
             logger.warning(
                f"Count mismatch: Received {len(opportunities)}, "
                f"categorized {total_categorized} (Rankable: {num_rankable_for_ai}, Unrankable: {len(unrankable_opportunities_data)}). "
                "This might be due to duplicate handling or filtering in _prepare_input_for_ranking_model."
            )
        else:
            logger.info(f"All {len(opportunities)} received opportunities have been accounted for.")

        if num_rankable_for_ai == 0:
            logger.info("No opportunities were deemed suitable for AI ranking. Returning unranked items only.")
            return {"ranked_opportunities": [], "unranked_opportunities": unrankable_opportunities_data, "usage": self._empty_usage()}

        system_message_content = f'''
You are a Business Development Professional. Your task is to analyze a list of government contract opportunities and evaluate their fit with our company's capabilities.
Our company has the following practice areas:
{json.dumps(PRACTICE_AREAS, indent=2)}

Our preferred agencies are: {', '.join(PREFERRED_AGENCIES)}. Opportunities from these agencies should be given a slightly higher preference (e.g., +1 to fit score if relevant and all other factors are equal).

Instructions:
1. For each opportunity provided in the JSON input string (which is a list of opportunity objects, each having a 'description_for_ai_processing' field for your analysis), assess its relevance to our practice areas.
2. Assign a 'fit_score' from 1 (poor fit) to 10 (excellent fit).
   - 1-3: Poor fit
   - 4-5: Moderate fit
   - 6-7: Good fit
   - 8-10: Excellent fit
3. Assign each opportunity to ONLY ONE 'assigned_practice_area' - the most relevant one where it scores highest.
4. If there's a tie in fit score between practice areas, use this priority order to break ties:
   1. Business & Technology Services
   2. Program Management & Delivery
   3. Human Capital & Workforce Innovation
   4. Business Transformation & Change Management
   5. Risk, Safety & Mission Assurance
   6. Acquisition Lifecycle Management
   7. Grant Program Management
5. Provide a CONCISE 'justification' (1 sentence maximum, 15 words or less) for the score and practice area assignment.
6. Structure your output as a single JSON object. This object must have a key "ranked_opportunities", whose value is a list of objects. Each object in this list represents an analyzed opportunity and must include:
   - 'original_opportunity_id': The 'id' from the input JSON for that opportunity.
   - 'title': The opportunity title (from input).
   - 'notice_id': The notice ID (from input).
   - 'assigned_practice_area': The practice area you assigned. If no specific practice area clearly fits, assign the value 'Uncategorized'. This field must always be present.
   - 'fit_score': Your calculated fit score (integer 1-10).
   - 'justification': Your brief justification (string, 15 words max).

   DO NOT include: department, posted_date, response_date, set_aside, summary_description, or link in your response. We already have these fields.

7. **Irrelevant Terms:** The following terms generally indicate a poor fit for our company: *Membership Renewal, Medical Services, Fire Alarm, Trauma, Injury, Expert Witness, Data Entry, Culinary, Geospatial, Heritage Resource, Chemical, Surface Power, Laptops, Hardware, Helpdesk, Geophysical, Subscription, Network Support, Targeting, Commercial Solutions, Indian, Specimen, Sensors, Software Licensing, Licensing, Enterprise License, Battlefield, Warfighter*, Fire Suppression, Fire Alarm. If an opportunity's primary focus clearly revolves around one or more of these terms, assign a 'fit_score' between 1 and 2 and explicitly state the presence of these irrelevant terms as a key reason in your 'justification'.

Example of an item in the output 'ranked_opportunities' list:
{{ "original_opportunity_id": 1, "title": "Example Title", "notice_id": "EX123", "assigned_practice_area": "Business & Technology Services", "fit_score": 8, "justification": "Strong alignment with tech services capabilities." }}

Ensure the entire output is a valid JSON object adhering to this structure.
'''
        BATCH_SIZE = self.BATCH_SIZE # Class attribute for batch size

        all_ranked_opportunities_from_ai = []
        aggregated_usage = self._empty_usage()

        logger.info(f"Starting batch processing for {num_rankable_for_ai} rankable opportunities in batches of {BATCH_SIZE}.")

        for i in range(0, num_rankable_for_ai, BATCH_SIZE):
            current_batch_list = rankable_opportunities_list[i:i + BATCH_SIZE]
            current_batch_input_str = json.dumps(current_batch_list) # Convert current batch to JSON string
            
            batch_number = (i // BATCH_SIZE) + 1
            total_batches = (num_rankable_for_ai + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"Processing batch {batch_number}/{total_batches} with {len(current_batch_list)} opportunities.")

            user_message_content = f"Please analyze the following opportunities based on the instructions:\n{current_batch_input_str}"

            try:
                logger.info(f"Sending batch {batch_number} to OpenAI for analysis (Model: {self.model})...")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message_content},
                        {"role": "user", "content": user_message_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                
                ai_response_content_batch = response.choices[0].message.content
                logger.info(f"Raw AI response for batch {batch_number} received (length: {len(ai_response_content_batch)} chars). First 100 chars: {ai_response_content_batch[:100]}")

                if response.usage:
                    usage_data_batch = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                    logger.info(f"OpenAI API usage for batch {batch_number}: {usage_data_batch}")
                    aggregated_usage["prompt_tokens"] += usage_data_batch.get("prompt_tokens", 0)
                    aggregated_usage["completion_tokens"] += usage_data_batch.get("completion_tokens", 0)
                    aggregated_usage["total_tokens"] += usage_data_batch.get("total_tokens", 0)
                else:
                    logger.warning(f"No usage data in response for batch {batch_number}.")


                try:
                    parsed_ai_response_batch = json.loads(ai_response_content_batch)
                    logger.info(f"Successfully parsed AI response for batch {batch_number}. Type: {type(parsed_ai_response_batch)}")
                    
                    if isinstance(parsed_ai_response_batch, dict):
                        raw_ranked_list_batch = parsed_ai_response_batch.get("ranked_opportunities")
                        
                        if raw_ranked_list_batch is None:
                            logger.warning(f"'ranked_opportunities' key not found in AI response for batch {batch_number}.")
                        elif not isinstance(raw_ranked_list_batch, list):
                            logger.warning(f"'ranked_opportunities' in AI response for batch {batch_number} is not a list. Type: {type(raw_ranked_list_batch)}. Content (first 100 chars): {str(raw_ranked_list_batch)[:100]}")
                        else:
                            logger.info(f"Extracted {len(raw_ranked_list_batch)} items from 'ranked_opportunities' in batch {batch_number}.")
                            for item in raw_ranked_list_batch:
                                if isinstance(item, dict):
                                    all_ranked_opportunities_from_ai.append(item)
                                else:
                                    logger.warning(f"Item in 'ranked_opportunities' from batch {batch_number} is not a dict: {str(item)[:100]}")
                    else:
                        logger.warning(f"Parsed AI response for batch {batch_number} is not a dictionary. Type: {type(parsed_ai_response_batch)}. Content (first 100 chars): {str(parsed_ai_response_batch)[:100]}")

                except json.JSONDecodeError as e_json:
                    logger.error(f"Failed to decode AI JSON response for batch {batch_number}: {e_json}. Response (first 200 chars): {ai_response_content_batch[:200]}")
                
            except Exception as e_batch_call:
                logger.error(f"An error occurred during OpenAI API call or processing for batch {batch_number}: {str(e_batch_call)}", exc_info=True)

        logger.info(f"Finished all batches. Total ranked opportunities aggregated before validation: {len(all_ranked_opportunities_from_ai)}")
        logger.info(f"Aggregated OpenAI API usage: {aggregated_usage}")

        final_ranked_opportunities = []
        if all_ranked_opportunities_from_ai:
            for item in all_ranked_opportunities_from_ai:
                if isinstance(item, dict):
                    if 'original_opportunity_id' in item and 'notice_id' in item: 
                        final_ranked_opportunities.append(item)
                    else:
                        logger.warning(f"Skipping ranked item due to missing 'original_opportunity_id' or 'notice_id': {str(item)[:100]}")
                else:
                    logger.warning(f"Skipping non-dictionary item in ranked_opportunities from AI: {str(item)[:100]}")
        
        logger.info(f"Number of valid ranked opportunities after filtering all batches: {len(final_ranked_opportunities)}")

        return {
            "ranked_opportunities": final_ranked_opportunities,
            "unranked_opportunities": unrankable_opportunities_data,
            "usage": aggregated_usage
        }

class ReportAgent:
    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini"):
        # Assuming existing __init__ structure.
        # self.openai_client = OpenAI(api_key=openai_api_key) # Example, if client is initialized here
        self.model = model

    def generate_markdown_report(self,
                                 ranked_opportunities_batch: List[Dict[str, Any]],
                                 unranked_opportunities_batch: List[Dict[str, Any]],
                                 report_title_prefix: str = "Opportunity Analysis Report",
                                 part_info: Optional[str] = None,
                                 generated_on_timestamp: Optional[str] = None):
        lines = []

        if generated_on_timestamp:
            gen_time_str = generated_on_timestamp
        else:
            # Generate a timestamp if not provided
            if pytz:
                gen_time_str = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                gen_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC (pytz not available)")
        
        title_line = f"# {report_title_prefix}"
        if part_info:
            title_line += f" {part_info}" # e.g., " (Part 1 of 3)"
        lines.append(title_line)
        lines.append(f"\n_Generated on: {gen_time_str}_\n")

        first_item_in_report = True # Tracks if any item has been added to add HR correctly

        if ranked_opportunities_batch:
            lines.append("## Ranked Opportunities by Practice Area")
            
            grouped_batch = {}
            for opp in ranked_opportunities_batch:
                pa = opp.get('assigned_practice_area', 'Uncategorized')
                if not pa: pa = 'Uncategorized'
                if pa not in grouped_batch:
                    grouped_batch[pa] = []
                grouped_batch[pa].append(opp)
            
            sorted_practice_areas = sorted(grouped_batch.keys())

            for pa_idx, pa in enumerate(sorted_practice_areas):
                lines.append(f"\n### {pa}")
                sorted_opps = sorted(grouped_batch[pa], key=lambda x: x.get('fit_score_numeric', 0), reverse=True)

                for opp_idx, opp in enumerate(sorted_opps):
                    if not first_item_in_report:
                        lines.append("\n---\n")
                    else:
                        first_item_in_report = False
                    
                    lines.append(f"\n#### {opp.get('title', 'N/A')}")
                    lines.append(f"- **Notice ID:** {opp.get('notice_id', opp.get('noticeId', 'N/A'))}")
                    lines.append(f"- **Department/Agency:** {opp.get('department', opp.get('agency', 'N/A'))}")
                    lines.append(f"- **Posted Date:** {opp.get('posted_date', opp.get('postedDate', 'N/A'))}")
                    lines.append(f"- **Response Date:** {opp.get('response_date', opp.get('responseDate', 'N/A'))}")
                    lines.append(f"- **Set Aside:** {opp.get('set_aside', opp.get('setAside', 'N/A'))}")
                    lines.append(f"- **Fit Score:** {opp.get('fit_score', 'N/A')}")
                    lines.append(f"- **Justification:** {opp.get('justification', 'N/A')}")
                    
                    summary_desc_text = opp.get('summary_description', opp.get('summaryDescription', 'N/A'))
                    lines.append(f"- **Summary Description:** {summary_desc_text if summary_desc_text else 'N/A'}")
                    link_url = opp.get('link', opp.get('uiLink', '#'))
                    link_text = opp.get('link', opp.get('uiLink', 'N/A'))
                    lines.append(f"- **Link:** [{link_text}]({link_url})")

        if unranked_opportunities_batch:
            lines.append("\n## Unranked Opportunities")
            for opp_idx, opp in enumerate(unranked_opportunities_batch):
                # Logic to add HR if it's not the very first item in the entire message part
                if not first_item_in_report: # An item (ranked or unranked) has already been printed
                    lines.append("\n---\n")
                else: # This is the first item overall in this part of the report
                    first_item_in_report = False
                
                lines.append(f"\n### {opp.get('title', 'N/A')}")
                lines.append(f"- **Notice ID:** {opp.get('notice_id', opp.get('noticeId', 'N/A'))}")
                lines.append(f"- **Department/Agency:** {opp.get('department', opp.get('agency', 'N/A'))}")
                lines.append(f"- **Set Aside:** {opp.get('set_aside', opp.get('setAside', 'N/A'))}")
                lines.append(f"- **Response Date:** {opp.get('response_date', opp.get('responseDate', 'N/A'))}")
                link_url = opp.get('link', opp.get('uiLink', '#'))
                link_text = opp.get('link', opp.get('uiLink', 'N/A'))
                lines.append(f"- **Link:** [{link_text}]({link_url})")
                lines.append(f"  - _This opportunity was not ranked due to limited information or other factors._")
        
        return "\n".join(lines)

class OpportunityAnalyzer:
    """
    Orchestrates the BusinessDevelopmentAgent and ReportAgent to analyze opportunities.
    """
    def __init__(self, openai_api_key: str):
        if not openai_api_key:
            # This should ideally be caught by the script calling this, 
            # but good to have a check.
            logger.error("OpenAI API key is REQUIRED for OpportunityAnalyzer and its agents.")
            raise ValueError("OpenAI API key is required for OpportunityAnalyzer.")
        
        # Default models are set in the respective agents' __init__ methods
        self.business_dev_agent = BusinessDevelopmentAgent(api_key=openai_api_key)
        self.report_agent = ReportAgent(openai_api_key=openai_api_key)

        logger.info("OpportunityAnalyzer initialized with BusinessDevelopmentAgent and ReportAgent.")

    def analyze_opportunities(self, opportunities: List[Dict[str, Any]], output_format: str = "json") -> Union[Dict[str, Any], str]:
        """
        Analyzes a list of opportunities and returns the result in the specified format.

        Args:
            opportunities: A list of opportunity dictionaries.
            output_format: Desired output format ('json' or 'markdown').

        Returns:
            A dictionary (for 'json') or a string (for 'markdown') containing the analysis.
            
        Raises:
            ValueError: If an unsupported output_format is provided.
        """
        logger.info(f"Starting analysis for {len(opportunities)} opportunities. Output format: {output_format}")
        
        # Step 1: Get ranked and unranked data from BusinessDevelopmentAgent
        # This step involves API calls to OpenAI for ranking if rankable opportunities exist.
        ranked_data_json = self.business_dev_agent.get_ranked_opportunities_json(opportunities)
        
        # Step 2: Format the output
        if output_format.lower() == "markdown":
            logger.info("Generating Markdown report...")
            # The report agent can directly use the AI's output structure
            markdown_report = self.report_agent.generate_markdown_report(
                ranked_data_json.get("ranked_opportunities", []),
                ranked_data_json.get("unranked_opportunities", [])
            )
            logger.info("Markdown report generated.")
            return markdown_report
        elif output_format.lower() == "json":
            logger.info("Preparing final JSON data with merged AI insights...")

            # 1. Create a map of standardized versions of the original opportunities.
            #    The _standardize_opportunity method ensures fields like 'notice_id', 'department',
            #    'posted_date', 'response_date', 'set_aside', 'summary_description' (from original), 'link' are present.
            standardized_opportunities_map = {}
            for opp in opportunities:
                std_opp = self.business_dev_agent._standardize_opportunity(opp.copy()) # Standardize a copy
                notice_id = std_opp.get('notice_id') # _standardize_opportunity should create 'notice_id'
                if notice_id: # Ensure notice_id exists after standardization
                    standardized_opportunities_map[notice_id] = std_opp
                else:
                    logger.warning(f"Opportunity missing notice_id after standardization, cannot be reliably merged: {std_opp.get('title', 'N/A')}")

            # 2. Get AI ranked data (this was already done)
            # ranked_data_json = self.business_dev_agent.get_ranked_opportunities_json(opportunities)
            # ai_ranked_opps_map now contains items from AI, keyed by 'notice_id'.
            # These items have: original_opportunity_id (internal batch id), title, notice_id, department, 
            # posted_date, response_date, set_aside, summary_description (AI version), 
            # assigned_practice_area, fit_score, justification, link.
            ai_analyzed_items_map = {item['notice_id']: item for item in ranked_data_json.get("ranked_opportunities", []) if 'notice_id' in item}

            final_enriched_opportunities = []
            processed_notice_ids_for_final_list = set()

            # 3. Merge AI data into the standardized opportunities
            for notice_id, ai_item in ai_analyzed_items_map.items():
                if notice_id in standardized_opportunities_map:
                    # Start with the fully standardized opportunity
                    enriched_opp = standardized_opportunities_map[notice_id].copy()
                    
                    # Add/overwrite with AI-generated fields
                    enriched_opp['assigned_practice_area'] = ai_item.get('assigned_practice_area')
                    enriched_opp['fit_score'] = ai_item.get('fit_score')
                    enriched_opp['justification'] = ai_item.get('justification')
                    # Use AI's summary_description as it's crafted for output
                    enriched_opp['summary_description'] = ai_item.get('summary_description', enriched_opp.get('summary_description'))
                    
                    # Fields like title, department, dates, set_aside, link should already be in enriched_opp
                    # from the initial standardization. The AI returns them too, mostly for reference or if the prompt
                    # asked it to modify them. We are prioritizing the initially standardized values for these,
                    # unless the AI's version is explicitly preferred (like summary_description).

                    final_enriched_opportunities.append(enriched_opp)
                    processed_notice_ids_for_final_list.add(notice_id)
                else:
                    logger.warning(f"AI analyzed item with notice_id '{notice_id}' not found in original standardized set. Skipping.")

            # 4. Add any standardized opportunities that were not analyzed by AI (e.g., unrankable by pre-filter)
            for notice_id, std_opp in standardized_opportunities_map.items():
                if notice_id not in processed_notice_ids_for_final_list:
                    # This opportunity was standardized but not found in AI's ranked output.
                    # It might be in ranked_data_json["unranked_opportunities"], or filtered before AI.
                    # We add it here without AI fields to ensure it's in the final list if it was processed at all.
                    final_enriched_opportunities.append(std_opp)
            
            logger.info(f"Returning {len(final_enriched_opportunities)} merged and enriched opportunities in JSON format.")
            return {
                "ranked_opportunities": final_enriched_opportunities, 
                "unranked_opportunities": ranked_data_json.get("unranked_opportunities", []), 
                "usage": ranked_data_json.get("usage", self.business_dev_agent._empty_usage())
            }
        else:
            logger.error(f"Invalid output format: {output_format}. Supported formats are 'json' and 'markdown'.")
            raise ValueError(f"Invalid output format: '{output_format}'. Supported formats are 'json' and 'markdown'.")
