"""
Step 5: Topic Clustering - Cluster similar content into collections
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import dependencies
from ..utils.llm_client import LLMClient
from ..core.shared_config import PROMPT_FILES, METADATA_DIR, MAX_CLIPS_PER_COLLECTION

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """Topic Clustering Engine"""
    
    def __init__(self, metadata_dir: Optional[Path] = None, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        
        # Load prompts
        prompt_files_to_use = prompt_files if prompt_files is not None else PROMPT_FILES
        with open(prompt_files_to_use['clustering'], 'r', encoding='utf-8') as f:
            self.clustering_prompt = f.read()
        
        # Use passed metadata_dir or default value
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        self.metadata_dir = metadata_dir
    
    def cluster_clips(self, clips_with_titles: List[Dict]) -> List[Dict]:
        """
        Perform topic clustering on clips
        
        Args:
            clips_with_titles: List of clips with titles
            
        Returns:
            List of collection data
        """
        logger.info("Starting topic clustering...")
        
        # Prepare clustering data
        clips_for_clustering = []
        for clip in clips_with_titles:
            clips_for_clustering.append({
                'id': clip['id'],
                'title': clip.get('generated_title', clip['outline']),
                'summary': clip.get('recommend_reason', ''),
                'score': clip.get('final_score', 0)
            })
        
        # First perform keyword-based pre-clustering
        pre_clusters = self._pre_cluster_by_keywords(clips_for_clustering)
        
        # Build complete prompt
        full_prompt = self.clustering_prompt + "\n\nThe following is a list of video clips:\n"
        for i, clip in enumerate(clips_for_clustering, 1):
            full_prompt += f"{i}. Title: {clip['title']}\n   Summary: {clip['summary']}\n   Score: {clip['score']:.2f}\n\n"
        
        # Add pre-clustering results as reference
        if pre_clusters:
            full_prompt += "\n\nKeyword-based pre-clustering results (for reference only):\n"
            for theme, clip_ids in pre_clusters.items():
                full_prompt += f"{theme}: {', '.join(clip_ids)}\n"
        
        try:
            # Call LLM for clustering
            response = self.llm_client.call_with_retry(full_prompt)
            
            # Parse JSON response
            collections_data = self.llm_client.parse_json_response(response)
            
            # Validate and clean collection data
            validated_collections = self._validate_collections(collections_data, clips_with_titles)
            
            # If LLM clustering results are not ideal, use pre-clustering results
            if len(validated_collections) < 3:
                logger.warning("LLM clustering results not ideal, using pre-clustering results")
                validated_collections = self._create_collections_from_pre_clusters(pre_clusters, clips_with_titles)
            
            logger.info(f"Topic clustering completed, total {len(validated_collections)} collections")
            return validated_collections
            
        except Exception as e:
            logger.error(f"Topic clustering failed: {str(e)}")
            # Use pre-clustering results as fallback
            if pre_clusters:
                logger.info("Using pre-clustering results as fallback")
                return self._create_collections_from_pre_clusters(pre_clusters, clips_with_titles)
            # Return default clustering results
            return self._create_default_collections(clips_with_titles)
    
    def _pre_cluster_by_keywords(self, clips: List[Dict]) -> Dict[str, List[str]]:
        """
        Perform keyword-based pre-clustering
        
        Args:
            clips: List of clips
            
        Returns:
            Pre-clustering results
        """
        # Define theme keywords
        theme_keywords = {
            'Investment & Finance': ['Investment', 'Finance', 'Stocks', 'Funds', 'Trading', 'Profit', 'Returns', 'Market', 'Retail investors'],
            'Career Growth': ['Career', 'Work', 'Skills', 'Learning', 'Education', 'College', 'Financial literacy'],
            'Social Commentary': ['Society', 'Phenomenon', 'Internet', 'Platform', 'Industry', 'Streamers'],
            'Cultural Differences': ['Culture', 'Differences', 'Western', 'Japanese', 'Korean', 'Diet', 'Language', 'Cruise'],
            'Live Streaming': ['Live stream', 'Interaction', 'Comments', 'Fans', 'Donations', 'PK', 'Lottery'],
            'Relationships': ['Dating', 'Emotions', 'Social', 'Relationship', 'Psychology'],
            'Healthy Living': ['Health', 'Exercise', 'Running', 'Diet', 'Milk', 'Lifestyle', 'Fitness'],
            'Content Creation': ['Creation', 'Platform', 'Photography', 'Content', 'Operations', 'Self-media']
        }
        
        pre_clusters = {theme: [] for theme in theme_keywords.keys()}
        
        for clip in clips:
            # Combine title and summary for keyword matching
            text = f"{clip['title']} {clip['summary']}".lower()
            
            # Calculate match score for each theme
            theme_scores = {}
            for theme, keywords in theme_keywords.items():
                score = sum(1 for keyword in keywords if keyword.lower() in text)
                if score > 0:
                    theme_scores[theme] = score
            
            # Select theme with highest match score
            if theme_scores:
                best_theme = max(theme_scores.keys(), key=lambda k: theme_scores[k])
                pre_clusters[best_theme].append(clip['id'])
        
        # Filter out empty themes
        return {theme: clip_ids for theme, clip_ids in pre_clusters.items() if len(clip_ids) >= 2}
    
    def _create_collections_from_pre_clusters(self, pre_clusters: Dict[str, List[str]], clips_with_titles: List[Dict]) -> List[Dict]:
        """
        Create collections from pre-clustering results
        
        Args:
            pre_clusters: Pre-clustering results
            clips_with_titles: Clip data
            
        Returns:
            List of collection data
        """
        collections = []
        collection_id = 1
        
        # Theme title mapping
        theme_titles = {
            'Investment & Finance': 'Investment & Finance Insights',
            'Career Growth': 'Career Growth Stories', 
            'Social Commentary': 'Social Commentary Notes',
            'Cultural Differences': 'Cultural Differences & Fun',
            'Live Streaming': 'Live Streaming Moments',
            'Relationships': 'Emotions & Relationships',
            'Healthy Living': 'Healthy Lifestyle',
            'Content Creation': 'Content Creation & Platform Ecosystem'
        }
        
        # Theme summary mapping
        theme_summaries = {
            'Investment & Finance': 'Sharing investment philosophy through relatable life examples, both practical and resonant.',
            'Career Growth': 'Exploring career development, skill improvement, and workplace mindset changes.',
            'Social Commentary': 'Rational commentary on social phenomena and internet trends with clear viewpoints.',
            'Cultural Differences': 'From diet to language, showcasing interesting perspectives on cross-cultural exchange.',
            'Live Streaming': 'Recreating authentic live streaming interaction scenes, showcasing streamer reactions.',
            'Relationships': 'Analyzing dating psychology, social confusion, and emotional resonance topics.',
            'Healthy Living': 'Sharing health management experiences including exercise, diet, and mental wellness.',
            'Content Creation': 'Analyzing content creation challenges and platform mechanisms, ideal for creators.'
        }
        
        for theme, clip_ids in pre_clusters.items():
            # Limit number of clips per collection
            if len(clip_ids) > MAX_CLIPS_PER_COLLECTION:
                clip_ids = clip_ids[:MAX_CLIPS_PER_COLLECTION]
            
            collections.append({
                'id': str(collection_id),
                'collection_title': theme_titles.get(theme, theme),
                'collection_summary': theme_summaries.get(theme, f'Exciting clips collection related to {theme}'),
                'clip_ids': clip_ids
            })
            collection_id += 1
        
        return collections
    
    def _validate_collections(self, collections_data: List[Dict], clips_with_titles: List[Dict]) -> List[Dict]:
        """
        Validate and clean collection data
        
        Args:
            collections_data: Raw collection data
            clips_with_titles: Clip data
            
        Returns:
            Validated collection data
        """
        validated_collections = []
        
        for i, collection in enumerate(collections_data):
            try:
                # Validate required fields
                if not all(key in collection for key in ['collection_title', 'collection_summary', 'clips']):
                    logger.warning(f"Collection {i} missing required fields, skipping")
                    continue
                
                # Validate clip list
                clip_titles = collection['clips']
                valid_clip_ids = []
                
                for clip_title in clip_titles:
                    # Find corresponding clip ID by title
                    for clip in clips_with_titles:
                        if (clip.get('generated_title', clip['outline']) == clip_title or 
                            clip['outline'] == clip_title):
                            valid_clip_ids.append(clip['id'])
                            break
                
                if len(valid_clip_ids) < 2:
                    logger.warning(f"Collection {i} has fewer than 2 valid clips, skipping")
                    continue
                
                # Limit number of clips per collection
                if len(valid_clip_ids) > MAX_CLIPS_PER_COLLECTION:
                    valid_clip_ids = valid_clip_ids[:MAX_CLIPS_PER_COLLECTION]
                
                validated_collection = {
                    'id': str(i + 1),
                    'collection_title': collection['collection_title'],
                    'collection_summary': collection['collection_summary'],
                    'clip_ids': valid_clip_ids
                }
                
                validated_collections.append(validated_collection)
                
            except Exception as e:
                logger.error(f"Failed to validate collection {i}: {str(e)}")
                continue
        
        return validated_collections
    
    def _create_default_collections(self, clips_with_titles: List[Dict]) -> List[Dict]:
        """
        Create default collections (when clustering fails)
        
        Args:
            clips_with_titles: Clip data
            
        Returns:
            Default collection data
        """
        logger.info("Creating default collections...")
        
        # Group by score
        high_score = []
        medium_score = []
        
        for clip in clips_with_titles:
            score = clip.get('final_score', 0)
            if score >= 0.8:
                high_score.append(clip)
            elif score >= 0.6:
                medium_score.append(clip)
        
        collections = []
        
        # Create high-score collection
        if len(high_score) >= 2:
            collections.append({
                'id': '1',
                'collection_title': 'Top High-Scoring Clips',
                'collection_summary': 'Collection of highest-rated exciting clips',
                'clip_ids': [clip['id'] for clip in high_score[:MAX_CLIPS_PER_COLLECTION]]
            })
        
        # Create medium-score collection
        if len(medium_score) >= 2:
            collections.append({
                'id': '2',
                'collection_title': 'Quality Content Recommendations',
                'collection_summary': 'Curated quality content clips',
                'clip_ids': [clip['id'] for clip in medium_score[:MAX_CLIPS_PER_COLLECTION]]
            })
        
        return collections
    
    def save_collections(self, collections_data: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        Save collection data
        
        Args:
            collections_data: Collection data
            output_path: Output path
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = self.metadata_dir / "collections.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collections_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Collection data saved to: {output_path}")
        return output_path
    
    def load_collections(self, input_path: Path) -> List[Dict]:
        """
        Load collection data from file
        
        Args:
            input_path: Input file path
            
        Returns:
            Collection data
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)

def run_step5_clustering(clips_with_titles_path: Path, output_path: Optional[Path] = None, metadata_dir: Optional[str] = None, prompt_files: Dict = None) -> List[Dict]:
    """
    Run Step 5: Topic Clustering
    
    Args:
        clips_with_titles_path: Clips with titles file path
        output_path: Output file path
        prompt_files: Custom prompt files
        
    Returns:
        Collection data
    """
    # Load data
    with open(clips_with_titles_path, 'r', encoding='utf-8') as f:
        clips_with_titles = json.load(f)
    
    # Create clustering engine
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    clusterer = ClusteringEngine(metadata_dir=Path(metadata_dir), prompt_files=prompt_files)
    
    # Perform clustering
    collections_data = clusterer.cluster_clips(clips_with_titles)
    
    # Save results
    if output_path is None:
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        output_path = Path(metadata_dir) / "step5_collections.json"
    
    clusterer.save_collections(collections_data, output_path)
    
    return collections_data
