import msal
import requests
import json
import logging
import re
import time
from . import config

logger = logging.getLogger(__name__)

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

def get_access_token():
    """Acquires an access token from Azure AD."""
    authority = f"https://login.microsoftonline.com/{config.MS_TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        config.MS_CLIENT_ID,
        authority=authority,
        client_credential=config.MS_CLIENT_SECRET,
    )

    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

    if "access_token" in result:
        return result['access_token']
    else:
        logger.error(f"Failed to acquire token: {result.get('error_description')}")
        raise Exception(f"Error acquiring token: {result.get('error')}\nDescription: {result.get('error_description')}")

def get_site_id(access_token, site_url):
    """Gets the SharePoint site ID using the site URL."""
    # Example site_url: https://yourtenant.sharepoint.com/sites/yoursite
    if not site_url.startswith('https://'):
        raise ValueError("SHAREPOINT_SITE_URL must start with https://")
    
    try:
        # Split URL into hostname and path part
        # e.g., 'yourtenant.sharepoint.com' and '/sites/yoursite'
        parts = site_url.replace('https://', '', 1).split('/', 1)
        hostname = parts[0]
        if not hostname.endswith('.sharepoint.com'):
            raise ValueError("Site URL does not appear to be a valid SharePoint Online URL.")
        
        # The server-relative path needs a leading slash if it's not empty
        relative_path = ""
        if len(parts) > 1 and parts[1]:
            relative_path = "/" + parts[1]
        else: # Handle case like https://tenant.sharepoint.com (root site)
            relative_path = ""
            
        # Construct the site identifier for Graph API: hostname:/server-relative-path
        # For root site, it would be hostname:/
        # For a specific site, it would be hostname:/sites/sitename
        graph_site_identifier = f"{hostname}:{relative_path}"
        logger.info(f"Constructed Graph API site identifier: {graph_site_identifier}")

    except Exception as e:
        logger.error(f"Error parsing SHAREPOINT_SITE_URL '{site_url}': {e}")
        raise ValueError(f"Could not parse SHAREPOINT_SITE_URL: {site_url}. Ensure it's a valid SharePoint site URL.")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    response = requests.get(f"{GRAPH_API_ENDPOINT}/sites/{graph_site_identifier}", headers=headers)
    response.raise_for_status() # Raise an exception for HTTP errors
    return response.json().get('id')

def get_list_id(access_token, site_id, list_name):
    """Gets the ID of a list within a SharePoint site by its display name."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    # Filter by display name to find the list
    # Using f-string for query parameter encoding; ensure list_name is simple or properly encoded if complex.
    response = requests.get(f"{GRAPH_API_ENDPOINT}/sites/{site_id}/lists?$filter=displayName eq '{list_name}'", headers=headers)
    response.raise_for_status()
    lists = response.json().get('value')
    if lists and len(lists) == 1:
        return lists[0].get('id')
    elif not lists:
        raise Exception(f"List '{list_name}' not found on site ID '{site_id}'.")
    else:
        raise Exception(f"Multiple lists found with name '{list_name}'. Please use a unique name.")

def add_item_to_list(access_token, site_id, list_id, item_data, max_retries=3, initial_retry_delay=5):
    """Adds an item to the SharePoint list with retry logic for 5xx errors."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {'fields': item_data}
    logger.info(f"DEBUG_ADD_ITEM_PAYLOAD: For NoticeID {item_data.get('NoticeID', 'N/A')}, payload being sent: {json.dumps(payload, indent=2)}") # DEBUG
    
    retries = 0
    while retries <= max_retries:
        try:
            response = requests.post(
                f"{GRAPH_API_ENDPOINT}/sites/{site_id}/lists/{list_id}/items",
                headers=headers,
                json=payload
            )
            response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
            logger.info(f"Successfully added item to list. Item ID: {response.json().get('id')}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            # For 5xx errors, retry after a delay. For 4xx, raise immediately.
            if e.response.status_code >= 500 and retries < max_retries:
                retries += 1
                delay = initial_retry_delay * (2 ** (retries - 1)) # Exponential backoff
                logger.warning(f"Server error {e.response.status_code} encountered. Retrying in {delay} seconds... (Attempt {retries}/{max_retries})")
                logger.warning(f"Failed payload for {item_data.get('NoticeID', item_data.get('Title', 'Unknown Item'))}: {json.dumps(payload)}")
                time.sleep(delay)
            else:
                logger.error(f"Error adding item to list: {e.response.status_code} - {e.response.text}")
                logger.error(f"Request payload: {json.dumps(payload)}")
                raise # Reraise the exception if it's a 4xx or max retries reached for 5xx
        except requests.exceptions.RequestException as e: # Catch other request exceptions like timeouts not resulting in HTTPError
            if retries < max_retries:
                retries += 1
                delay = initial_retry_delay * (2 ** (retries - 1))
                logger.warning(f"Request exception encountered: {e}. Retrying in {delay} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(delay)
            else:
                logger.error(f"Request exception encountered after max retries: {e}")
                logger.error(f"Request payload: {json.dumps(payload)}")
                raise
    return None # Should not be reached if max_retries leads to an exception

def map_opportunity_to_list_item(opportunity):
    print(f"DEBUG_POSTER_ENTRY: notice_id={opportunity.get('notice_id', 'N/A')}, received opportunity['uiLink']: '{opportunity.get('uiLink')}'") # DEBUG
    """
    Maps an opportunity dictionary (from your analysis) to the format 
    required for SharePoint list item creation.
    
    THIS IS WHERE YOU'LL NEED TO DEFINE THE MAPPING BASED ON YOUR LIST'S COLUMN NAMES.
    The keys in the returned dictionary MUST be the *internal* names of your SharePoint list columns.
    
    Example (assuming 'opportunity' dict has keys like 'notice_id', 'title', etc.):
    return {
        'Title': opportunity.get('title', 'N/A'), # 'Title' is often a default SharePoint column
        'NoticeID': opportunity.get('notice_id'),
        'Department': opportunity.get('department'),
        'PostedDate': opportunity.get('posted_date'), 
        'ResponseDate': opportunity.get('response_date'),
        'SetAside': opportunity.get('set_aside'),
        'FitScore': opportunity.get('fit_score'),
        'Justification': opportunity.get('justification'),
        'SummaryDescription': opportunity.get('summary_description'),
        'Link': opportunity.get('link', {}).get('url') # Assuming link is a dict with a 'url' key
        # Add other fields as needed, ensuring keys match your SharePoint list's internal column names.
    }
    """
    # Placeholder - replace with actual mapping
    # You'll need to know the internal names of your SharePoint list columns.
    # For example, if your SharePoint list has a column 'OpportunityTitle' for the title:
    # 'OpportunityTitle': opportunity.get('title', 'N/A'),
    
    # Prepare date fields - convert "N/A" or empty strings to None for date fields
    posted_date_str = opportunity.get('posted_date')
    if not posted_date_str or str(posted_date_str).strip().upper() == "N/A":
        posted_date_val = None
    else:
        posted_date_val = str(posted_date_str).strip()

    raw_response_date_from_opp = opportunity.get('response_date') # Key standardized in BusinessDevelopmentAgent
    notice_id_for_log = opportunity.get('NoticeID', opportunity.get('notice_id', 'N/A')) # Get NoticeID for logging
    logger.info(f"[Debug ResponseDate] NoticeID: {notice_id_for_log} - Raw 'response_date' from opportunity: '{raw_response_date_from_opp}' (type: {type(raw_response_date_from_opp)})")

    response_date_str = raw_response_date_from_opp # Use the already fetched value
    if not response_date_str or str(response_date_str).strip().upper() == "N/A":
        response_date_val = None
    else:
        response_date_val = str(response_date_str).strip()
    logger.info(f"[Debug ResponseDate] NoticeID: {notice_id_for_log} - Processed 'response_date_val': '{response_date_val}' (type: {type(response_date_val)})")

    # Prepare SAMUrl field for Single line of text column type
    raw_link_data = opportunity.get('uiLink') # This is the direct URL string or 'N/A'
    link_val = None

    if isinstance(raw_link_data, str):
        temp_link_string = raw_link_data.strip()
        if temp_link_string.startswith('http://') or temp_link_string.startswith('https://'):
            link_val = temp_link_string
        elif temp_link_string and temp_link_string != 'N/A': # It's some other non-empty, non-N/A string that's not a URL
            logger.warning(f"Invalid SAMUrl value received: '{temp_link_string}'. Expected a URL or 'N/A'. SAMUrl will be empty for NoticeID {opportunity.get('notice_id', 'UNKNOWN')}.")
        # If temp_link_string is 'N/A' or empty, link_val remains None, which is fine.
    elif raw_link_data is not None: # It's not a string and not None (e.g. a number or bool by mistake)
        logger.warning(f"Unexpected data type for SAMUrl: {type(raw_link_data)} with value '{raw_link_data}'. SAMUrl will be empty for NoticeID {opportunity.get('notice_id', 'UNKNOWN')}.")

    print(f"DEBUG_POSTER_LINK_VAL: notice_id={opportunity.get('notice_id', 'N/A')}, final link_val before mapping: '{link_val}' (type: {type(link_val)})") # DEBUG
    
    # Ptype translation
    ptype_code = opportunity.get('ptype', 'N/A')
    ptype_map = {
        'u': "Justification (J&A)",
        'p': "Pre solicitation",
        'a': "Award Notice",
        'r': "Sources Sought",
        's': "Special Notice",
        'o': "Solicitation",
        'g': "Sale of Surplus Property",
        'k': "Combined Synopsis/Solicitation",
        'i': "Intent to Bundle Requirements (DoD-Funded)"
    }
    translated_ptype = ptype_map.get(ptype_code, ptype_code if ptype_code and ptype_code.strip() and ptype_code.upper() != 'N/A' else 'Unknown')
    mapped_item = {
        # --- ENSURE THESE KEYS ARE YOUR ACTUAL SHAREPOINT LIST INTERNAL COLUMN NAMES ---
        'Title': opportunity.get('title', opportunity.get('solicitation_title', 'N/A')),
        'NoticeID': opportunity.get('notice_id'),
        'DepartmentName': opportunity.get('standardized_department'), # Changed source key
        'PostedDate': posted_date_val,
        'ResponseDate': response_date_val,
        'SetAside': opportunity.get('set_aside'),
        'Ptype': translated_ptype, # Use translated ptype
        'FitScore': opportunity.get('fit_score'), # Ensure this is a number if SharePoint column is Number
        'Justification': opportunity.get('justification'), # Corrected field name for SharePoint
        'SummaryDescription': opportunity.get('summary_description'), # Renamed from 'SummaryDescription' to 'Summary'
        'SAMLink': link_val, # This is where the URL for SAM.gov will be placed (using new field SAMLink)
        'NAICS': opportunity.get('naics_code'), # Added NAICS code
        'PracticeArea': opportunity.get('assigned_practice_area'), # Map assigned_practice_area to SharePoint column
        'SolicitationNumber': opportunity.get('solicitationNumber', 'N/A'),
        'ClassificationCode': opportunity.get('classificationCode', 'N/A')
    }

    # Debugging PracticeArea
    practice_area_value = opportunity.get('assigned_practice_area')
    logger.info(f"DEBUG_PRACTICE_AREA: NoticeID: {opportunity.get('notice_id', 'N/A')}, AssignedPracticeArea: '{practice_area_value}' (Type: {type(practice_area_value)}) G_PRACTICE_AREA_END")

    # Filter out None values to avoid issues with SharePoint list columns that don't accept nulls
    return {k: v for k, v in mapped_item.items() if v is not None}

def post_opportunities_to_list(opportunities):
    """Posts a list of opportunities to the configured SharePoint list."""
    if not all([config.MS_TENANT_ID, config.MS_CLIENT_ID, config.MS_CLIENT_SECRET, 
                config.SHAREPOINT_SITE_URL, config.SHAREPOINT_LIST_NAME]):
        logger.error("Microsoft Graph API credentials or SharePoint details are not fully configured. Skipping post to list.")
        return

    try:
        token = get_access_token()
        site_id = get_site_id(token, config.SHAREPOINT_SITE_URL)
        list_id = get_list_id(token, site_id, config.SHAREPOINT_LIST_NAME)

        if not opportunities:
            logger.info("No opportunities to post to the list.")
            return

        for opp in opportunities:
            # Assuming 'opp' is a dictionary representing a single opportunity
            # We need to map its fields to the SharePoint list column names
            list_item_data = map_opportunity_to_list_item(opp)
            if not list_item_data:
                logger.warning(f"Skipping opportunity due to empty mapped data: {opp.get('notice_id', 'Unknown ID')}")
                continue
            
            logger.info(f"Posting opportunity {opp.get('notice_id', 'Unknown ID')} to list '{config.SHAREPOINT_LIST_NAME}'...")
            add_item_to_list(token, site_id, list_id, list_item_data)
        
        logger.info(f"Successfully posted {len(opportunities)} opportunities to the list.")

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request error during SharePoint list operation: {e}")
    except msal.MsalException as e: # Changed to a more general MSAL exception
        logger.error(f"MSAL Authentication error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while posting to Microsoft List: {e}", exc_info=True)

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    # Ensure your .env file is populated and app.config can load the variables.
    # You would typically call post_opportunities_to_list from your main script.
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing Microsoft List Poster...")
    
    # Create a dummy opportunity list for testing
    # The structure of these dummy opportunities should match what your main script produces
    dummy_opportunities = [
        {
            'notice_id': 'TEST001',
            'title': 'Test Opportunity 1 - AI Solutions',
            'department': 'Dept of Testing',
            'posted_date': '2024-05-28',
            'response_date': '2024-06-15',
            'set_aside': 'Small Business',
            'fit_score': 0.95,
            'justification': 'Excellent fit for AI capabilities.',
            'summary_description': 'This is a test summary for an AI project.',
            'link': 'http://example.com/test001'
        },
        {
            'notice_id': 'TEST002',
            'title': 'Test Opportunity 2 - Cloud Services',
            'department': 'Dept of Cloud Innovation',
            'posted_date': '2024-05-29',
            'response_date': '2024-06-20',
            'set_aside': 'N/A',
            'fit_score': 0.88,
            'justification': 'Good alignment with cloud practice.',
            'summary_description': 'Seeking cloud migration services.',
            'link': 'http://example.com/test002'
        }
    ]
    
    if not all([config.MS_TENANT_ID, config.MS_CLIENT_ID, config.MS_CLIENT_SECRET, 
                config.SHAREPOINT_SITE_URL, config.SHAREPOINT_LIST_NAME]):
        logger.error("Cannot run test: Microsoft Graph API credentials or SharePoint details are not configured in .env / config.py.")
    else:
        try:
            post_opportunities_to_list(dummy_opportunities)
            logger.info("Test completed. Check your SharePoint list.")
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
