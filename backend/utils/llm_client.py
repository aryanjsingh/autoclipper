"""
LLM client - Compatibility wrapper using new LLM manager
"""
import json
import logging
import os
import re
from typing import Dict, Any, List
from collections.abc import Generator

# Fix import issues
try:
    from ..core.shared_config import MODEL_NAME
except ImportError:
    # If relative import fails, try absolute import
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from core.shared_config import MODEL_NAME

# Import new LLM manager
try:
    from ..core.llm_manager import get_llm_manager
except ImportError:
    # If relative import fails, try absolute import
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from core.llm_manager import get_llm_manager

logger = logging.getLogger(__name__)

class LLMClient:
    """LLM client - Compatibility wrapper"""
    
    def __init__(self):
        self.model = MODEL_NAME
        self.llm_manager = get_llm_manager()
    
    def call(
        self,
        prompt: str,
        input_data: Any = None,
        pipeline_step: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        Call LLM API - Uses new LLM manager
        
        Args:
            prompt: Prompt
            input_data: Input data
            pipeline_step: e.g. step1, step2, step3, step4, caption — picks Opus vs Sonnet
            model: Override model id (Kiro API name)
            
        Returns:
            Model response text
        """
        if model is None and pipeline_step:
            model = self.llm_manager.model_for_pipeline_step(pipeline_step)
        try:
            return self.llm_manager.call(prompt, input_data, model=model)
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def call_with_retry(
        self,
        prompt: str,
        input_data: Any = None,
        max_retries: int = 3,
        pipeline_step: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        API call with retry mechanism
        
        Args:
            prompt: Prompt
            input_data: Input data
            max_retries: Maximum retry count
            pipeline_step: e.g. step1, step2, step3, step4, caption
            model: Override model id
            
        Returns:
            Model response text
        """
        if model is None and pipeline_step:
            model = self.llm_manager.model_for_pipeline_step(pipeline_step)
        try:
            return self.llm_manager.call_with_retry(
                prompt, input_data, max_retries, model=model
            )
        except Exception as e:
            logger.error(f"LLM retry call failed: {str(e)}")
            raise
    
    def _preprocess_llm_response(self, response: str) -> str:
        """
        Preprocess LLM response, remove common non-JSON content
        """
        # Remove leading titles and explanatory text
        lines = response.split('\n')
        json_start = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('[') or stripped.startswith('{'):
                json_start = i
                break
        
        if json_start >= 0:
            response = '\n'.join(lines[json_start:])
        
        # Remove trailing non-JSON content
        if '```' in response:
            # If there are multiple ```, take content before the first one
            parts = response.split('```')
            if len(parts) > 1:
                response = parts[0]
        
        return response.strip()
    
    def _auto_fix_response(self, response: str) -> str:
        """
        Automatically fix common response issues
        """
        # Remove BOM and special characters
        response = response.lstrip('\ufeff')
        response = response.strip()
        
        # Fix Chinese quotes
        response = response.replace('"', '\"').replace('"', '\"')
        
        return response
    
    def _validate_json_structure(self, parsed_data: Any) -> bool:
        """
        Validate JSON structure
        """
        try:
            if not isinstance(parsed_data, list):
                logger.error(f"Response is not an array format, actual type: {type(parsed_data)}")
                return False
            
            for i, item in enumerate(parsed_data):
                if not isinstance(item, dict):
                    logger.error(f"Element {i} is not an object format, actual type: {type(item)}")
                    return False
                    
                # Check basic fields (can be adjusted based on specific requirements)
                if 'outline' in item or 'start_time' in item or 'end_time' in item:
                    required_fields = ['outline', 'start_time', 'end_time']
                    for field in required_fields:
                        if field not in item:
                            logger.error(f"Element {i} is missing required field: {field}")
                            return False
        except Exception as e:
            logger.error(f"Error validating JSON structure: {e}")
            return False
        
        return True
    
    def _try_close_truncated_json(self, text: str) -> str:
        """Best-effort close arrays/objects cut off by output token limits."""
        s = text.strip()
        if not s or s[0] not in "[{":
            return s
        for suffix in ("", "]", "}]", "\"}]", "\"}]\n}", "}"):
            candidate = s + suffix
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue
        return s

    def parse_json_response(self, response: str) -> Any:
        """
        Parse JSON objects from text that may contain Markdown formatting.
        This function has multi-layer error tolerance:
        1. Preprocess response, remove non-JSON content
        2. Direct json.loads (models usually return clean JSON)
        3. Close truncated arrays/objects when output was cut off
        4. Markdown extraction, regex extraction, and light repairs as fallback
        """
        
        def sanitize_string(s: str) -> str:
            """Enhanced sanitization function, remove characters that may cause JSON parsing failure"""
            # Remove BOM marker
            s = s.lstrip('\ufeff')
            # Remove leading and trailing whitespace
            s = s.strip()
            # Remove possible control characters (keep necessary newlines and tabs)
            s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
            return s
        
        def fix_common_json_errors(json_str: str) -> str:
            """Fix common JSON format errors"""
            # Record original string for debugging
            original_str = json_str
            
            # 1. Fix missing commas
            json_str = re.sub(r'}\s*{', '},{', json_str)
            json_str = re.sub(r']\s*\[', '],[', json_str)
            
            # 2. Fix missing commas between objects (more precise pattern)
            json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)
            
            # 3. Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # 4. Fix single quotes to double quotes
            json_str = re.sub(r"'([^']*?)'\s*:", r'"\1":', json_str)
            json_str = re.sub(r":\s*'([^']*?)'", r': "\1"', json_str)
            
            # 5. Fix field names without quotes
            json_str = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', json_str)
            
            # 6. Fix possible newline issues
            json_str = re.sub(r'\n\s*\n', '\n', json_str)
            
            # 7. Ensure proper closing of arrays and objects
            # Count braces and brackets
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            
            # If braces don't match, try to fix
            if open_braces > close_braces:
                json_str += '}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                json_str += ']' * (open_brackets - close_brackets)
            
            # Log fix process
            if json_str != original_str:
                logger.debug(f"JSON before fix: {original_str[:100]}...")
                logger.debug(f"JSON after fix: {json_str[:100]}...")
            
            return json_str

        response = response.strip()
        
        # 0. Preprocess response, remove non-JSON content
        response = self._preprocess_llm_response(response)
        logger.debug(f"Preprocessed response: {response[:200]}...")

        # 1. Fast path — avoid aggressive "fixers" that can break valid JSON
        try:
            return json.loads(sanitize_string(response))
        except json.JSONDecodeError:
            pass

        try:
            return json.loads(sanitize_string(self._try_close_truncated_json(response)))
        except json.JSONDecodeError:
            pass
        
        # 2. Prioritize extracting from Markdown code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.DOTALL)
        if match:
            json_str = sanitize_string(match.group(1))
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                # Log specific error location and context
                error_pos = e.pos if hasattr(e, 'pos') else 0
                context_start = max(0, error_pos - 50)
                context_end = min(len(json_str), error_pos + 50)
                context = json_str[context_start:context_end]
                logger.error(f"JSON parsing failed at position {error_pos}, context: ...{context}...")
                logger.warning(f"Content extracted from Markdown failed to parse: {e}. Will try to fix and parse.")
                
                # Try to fix common errors and parse again
                try:
                    fixed_json = fix_common_json_errors(json_str)
                    return json.loads(fixed_json)
                except json.JSONDecodeError:
                    logger.warning("Still failed to parse after fix, will try parsing the entire response.")
        
        # 3. If no Markdown or Markdown parsing failed, try the entire response
        try:
            sanitized_response = sanitize_string(response)
            return json.loads(sanitized_response)
        except json.JSONDecodeError:
            # 4. If direct parsing of entire response also failed, make one last attempt with generic regex
            logger.warning("Direct response parsing failed, trying generic regex to find JSON...")
            json_match = re.search(r'\[[\s\S]*\]|\{[\s\S]*\}', response, re.DOTALL)
            if json_match:
                json_str = sanitize_string(json_match.group())
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    # 5. Final attempt to fix common errors
                    try:
                        fixed_json = fix_common_json_errors(json_str)
                        return json.loads(fixed_json)
                    except json.JSONDecodeError as final_e:
                        logger.error(f"Final parsing attempt failed: {final_e}")
                        # Save original response for debugging
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                            f.write(response)
                            logger.error(f"Original response saved to {f.name} for debugging")
                        raise ValueError(f"Unable to parse valid JSON from response: {response[:200]}...") from final_e
            
            # If even generic regex can't find anything, complete failure
            raise ValueError(f"Unable to parse valid JSON from response: {response[:200]}...")
    
    def get_current_provider_info(self) -> Dict[str, Any]:
        """Get current provider information"""
        return self.llm_manager.get_current_provider_info()
