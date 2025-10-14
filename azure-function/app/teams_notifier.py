import requests
import json
import logging

logger = logging.getLogger(__name__)

# Microsoft Teams has a message limit of approximately 28KB.
# We'll use a slightly lower limit to be safe and account for JSON overhead.
MAX_MESSAGE_SIZE_BYTES = 27 * 1024  # 27KB

class TeamsNotifier:
    def __init__(self, webhook_url):
        if not webhook_url:
            raise ValueError("Teams webhook URL is required.")
        self.webhook_url = webhook_url

    def _post_chunk(self, chunk_content: str, part_num: int = 0, total_parts: int = 1) -> bool:
        """Posts a single chunk of content to Teams."""
        headers = {'Content-Type': 'application/json'}
        message_body = {"text": chunk_content}
        
        log_prefix = f"[Part {part_num}/{total_parts}] " if total_parts > 1 else ""

        try:
            response = requests.post(self.webhook_url, data=json.dumps(message_body), headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            logger.info(f"{log_prefix}Successfully sent message chunk to Teams.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"{log_prefix}Error sending message chunk to Teams: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Teams API Response Status: {e.response.status_code}")
                logger.error(f"Teams API Response Body: {e.response.text}")
            return False

    def send_message(self, markdown_content: str, title: str = "Opportunity Analysis Report") -> bool:
        """Sends a markdown message to Teams, splitting it if necessary."""
        if not markdown_content.strip():
            logger.warning("Markdown content is empty. Nothing to send to Teams.")
            return False

        # Add a title to the overall message if provided
        full_message = f"## {title}\n\n{markdown_content}"
        
        content_bytes = full_message.encode('utf-8')
        total_size = len(content_bytes)

        if total_size <= MAX_MESSAGE_SIZE_BYTES:
            logger.info(f"Message size ({total_size} bytes) is within limits. Sending as a single post.")
            return self._post_chunk(full_message)
        else:
            logger.info(f"Message size ({total_size} bytes) exceeds limit. Splitting into multiple posts.")
            chunks = []
            current_chunk = ""
            lines = full_message.splitlines(keepends=True)
            
            for line in lines:
                # If adding the next line exceeds the limit, finalize the current chunk
                if len(current_chunk.encode('utf-8')) + len(line.encode('utf-8')) > MAX_MESSAGE_SIZE_BYTES:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""
                    
                    # If a single line itself is too long, it must be split
                    # This is a basic split; for very long unbreakable lines, this might still be an issue
                    # or might break markdown. A more sophisticated split would be needed for perfect markdown preservation.
                    while len(line.encode('utf-8')) > MAX_MESSAGE_SIZE_BYTES:
                        # Find a split point within the line (e.g., at MAX_MESSAGE_SIZE_BYTES)
                        # This is a character-based split, not ideal for UTF-8, but a starting point.
                        # A better way would be to decode, slice, and re-encode, ensuring valid char boundaries.
                        split_point = MAX_MESSAGE_SIZE_BYTES // 2 # Heuristic to find a point
                        # Attempt to split at a space if possible for better readability
                        safe_split_point = line[:split_point].rfind(' ')
                        if safe_split_point == -1 or safe_split_point < split_point // 2: # if no space or too early
                            safe_split_point = split_point
                        else:
                            safe_split_point += 1 # include the space in the first part or split after it
                        
                        chunks.append(line[:safe_split_point])
                        line = line[safe_split_point:]
                current_chunk += line
            
            if current_chunk: # Add the last chunk
                chunks.append(current_chunk)

            if not chunks:
                logger.error("Failed to split the message into manageable chunks.")
                return False

            total_parts = len(chunks)
            logger.info(f"Message split into {total_parts} parts.")
            all_sent_successfully = True
            for i, chunk in enumerate(chunks):
                # Add continuation notice for multi-part messages
                chunk_to_send = chunk
                if total_parts > 1:
                    continuation_notice = f"\n*(Message part {i+1} of {total_parts})*"
                    if len(chunk.encode('utf-8')) + len(continuation_notice.encode('utf-8')) <= MAX_MESSAGE_SIZE_BYTES:
                        chunk_to_send += continuation_notice
                    else:
                        # If notice makes it too long, send notice as separate small message if first part, or just send chunk
                        if i == 0:
                             self._post_chunk(f"*(Report is split into {total_parts} parts due to size limits.)*")
                
                if not self._post_chunk(chunk_to_send, part_num=i+1, total_parts=total_parts):
                    all_sent_successfully = False
                    # Optionally, decide if you want to stop on first failure or try all chunks
                    # For now, it tries all chunks and reports overall success/failure.
            
            return all_sent_successfully
