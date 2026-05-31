"""
Step 1: Outline Extraction - Extract structural outline from transcription text
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import dependencies
from ..utils.llm_client import LLMClient
from ..utils.text_processor import TextProcessor
from ..core.shared_config import PROMPT_FILES, METADATA_DIR

logger = logging.getLogger(__name__)

class OutlineExtractor:
    """Outline Extractor (Refactored)"""
    
    def __init__(self, metadata_dir: Path = None, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        self.text_processor = TextProcessor()
        
        # Use passed metadata_dir or default value
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        self.metadata_dir = metadata_dir
        
        # Use passed prompt_files or default value
        if prompt_files is None:
            prompt_files = PROMPT_FILES
        
        # Load prompts
        with open(prompt_files['outline'], 'r', encoding='utf-8') as f:
            self.outline_prompt = f.read()
            
        # Create directory for intermediate text chunks
        self.chunks_dir = self.metadata_dir / "step1_chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        # Create directory for intermediate SRT chunks
        self.srt_chunks_dir = self.metadata_dir / "step1_srt_chunks"
        self.srt_chunks_dir.mkdir(parents=True, exist_ok=True)

    def extract_outline(self, srt_path: Path) -> List[Dict]:
        """
        Extract video outline from SRT file
        
        Args:
            srt_path: Path to the SRT file
            
        Returns:
            List of video outlines
        """
        logger.info("Starting video outline extraction...")
        
        # 1. Parse SRT file
        try:
            srt_data = self.text_processor.parse_srt(srt_path)
            if not srt_data:
                logger.warning("SRT file is empty or parsing failed")
                return []
        except Exception as e:
            logger.error(f"Failed to parse SRT file: {e}")
            return []
            
        # 2. Intelligent time-based chunking
        chunks = self.text_processor.chunk_srt_data(srt_data, interval_minutes=30)
        logger.info(f"Text divided into ~30min/chunk, total {len(chunks)} chunks")
        
        # 3. Save text chunks and SRT chunks to intermediate files
        chunk_files = self._save_chunks_to_files(chunks)
        self._save_srt_chunks(chunks)
        
        all_outlines = []
        
        # 4. Process each text chunk file individually
        for i, chunk_file in enumerate(chunk_files):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}: {chunk_file.name}")
            try:
                # Read text chunk content
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_text = f.read()
                
                # Call LLM for each chunk
                input_data = {"text": chunk_text}
                response = self.llm_client.call_with_retry(
                    self.outline_prompt, input_data, pipeline_step="step1"
                )
                
                if response:
                    # Parse response and attach chunk index
                    # Note: chunk_index here directly uses i, corresponding to filename and original chunk
                    parsed_outlines = self._parse_outline_response(response, i)
                    all_outlines.extend(parsed_outlines)
                else:
                    logger.warning(f"Empty response when processing chunk {i+1}")
            except Exception as e:
                logger.error(f"Failed to process chunk {i+1}: {e}")
                continue
        
        # 5. Merge and deduplicate
        final_outlines = self._merge_outlines(all_outlines)
        
        logger.info(f"Outline extraction completed, total {len(final_outlines)} topics")
        return final_outlines

    def _save_chunks_to_files(self, chunks: List[Dict]) -> List[Path]:
        """Save text chunks as individual .txt files"""
        chunk_files = []
        for chunk in chunks:
            chunk_index = chunk['chunk_index']
            text_content = chunk['text']
            file_path = self.chunks_dir / f"chunk_{chunk_index}.txt"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            chunk_files.append(file_path)
        
        logger.info(f"All text chunks saved to: {self.chunks_dir}")
        return chunk_files

    def _save_srt_chunks(self, chunks: List[Dict]):
        """Save SRT data chunks as individual .json files"""
        for chunk in chunks:
            chunk_index = chunk['chunk_index']
            srt_entries = chunk['srt_entries']
            file_path = self.srt_chunks_dir / f"chunk_{chunk_index}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(srt_entries, f, ensure_ascii=False, indent=2)
        
        logger.info(f"All SRT chunks saved to: {self.srt_chunks_dir}")

    def _parse_outline_response(self, response: str, chunk_index: int) -> List[Dict]:
        """
        Parse the LLM's outline response.

        The outline prompt returns a JSON array of clip moments:
            [{"title": "...", "subtopics": ["...", "..."]}, ...]
        We parse it robustly and attach the chunk_index to each moment.

        Args:
            response: LLM response
            chunk_index: Index of the currently processed chunk

        Returns:
            Parsed outline structure (list of {title, subtopics, chunk_index})
        """
        outlines: List[Dict] = []

        try:
            parsed = self.llm_client.parse_json_response(response)
        except Exception as e:
            logger.warning(f"Failed to parse outline JSON for chunk {chunk_index}: {e}")
            return outlines

        if isinstance(parsed, dict):
            # Tolerate a wrapper object such as {"moments": [...]} or {"topics": [...]}
            for key in ("moments", "topics", "outline", "outlines", "clips", "items"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                parsed = [parsed]

        if not isinstance(parsed, list):
            logger.warning(f"Outline response for chunk {chunk_index} is not a list: {type(parsed)}")
            return outlines

        for item in parsed:
            if not isinstance(item, dict):
                continue
            title = item.get('title') or item.get('outline') or item.get('name')
            if not title or not isinstance(title, str):
                continue
            subtopics = item.get('subtopics') or item.get('content') or []
            if isinstance(subtopics, str):
                subtopics = [subtopics]
            if not isinstance(subtopics, list):
                subtopics = []
            subtopics = [str(s).strip() for s in subtopics if str(s).strip()]
            outlines.append({
                'title': title.strip(),
                'subtopics': subtopics,
                'chunk_index': chunk_index,
            })

        return outlines
    
    def _merge_outlines(self, outlines: List[Dict]) -> List[Dict]:
        """
        Deduplicate moments while preserving order. The same title may legitimately
        recur in different chunks, so we key on (chunk_index, normalized title).
        """
        unique_outlines = {}
        result = []
        for outline in outlines:
            key = (outline.get('chunk_index'), outline['title'].strip().lower())
            if key not in unique_outlines:
                unique_outlines[key] = True
                result.append(outline)
        return result
    
    def save_outline(self, outlines: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        Save outline to file
        """
        if output_path is None:
            output_path = self.metadata_dir / "step1_outline.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(outlines, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Outline saved to: {output_path}")
        return output_path
    
    def load_outline(self, input_path: Path) -> List[Dict]:
        """
        Load outline from file
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)

def run_step1_outline(srt_path: Path, metadata_dir: Path = None, output_path: Optional[Path] = None, prompt_files: Dict = None) -> List[Dict]:
    """
    Run Step 1: Outline Extraction
    """
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
        
    extractor = OutlineExtractor(metadata_dir, prompt_files)
    outlines = extractor.extract_outline(srt_path)
    
    if output_path is None:
        output_path = metadata_dir / "step1_outline.json"
        
    extractor.save_outline(outlines, output_path)
    
    return outlines
