"""
YouTube-related API routes
Handles YouTube video parsing and download functionality
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ...core.config import get_data_directory
import uuid
import asyncio
from datetime import datetime
import yt_dlp

logger = logging.getLogger(__name__)
router = APIRouter()

# Store download task status
download_tasks = {}

class YouTubeParseRequest(BaseModel):
    url: str
    browser: Optional[str] = None

class YouTubeDownloadRequest(BaseModel):
    url: str
    project_name: str
    video_category: Optional[str] = "default"
    browser: Optional[str] = None

class YouTubeVideoInfo(BaseModel):
    title: str
    description: str
    duration: int
    uploader: str
    upload_date: str
    view_count: int
    like_count: int
    thumbnail: str

class YouTubeDownloadTask(BaseModel):
    id: str
    url: str
    project_name: str
    video_category: str
    status: str  # pending, processing, completed, failed
    progress: float
    error_message: Optional[str] = None
    project_id: Optional[str] = None
    created_at: str
    updated_at: str

@router.post("/parse")
async def parse_youtube_video(
    url: str = Form(...),
    browser: Optional[str] = Form(None)
):
    """Parse YouTube video information"""
    try:
        logger.info(f"Starting YouTube video parsing: {url}")
        
        # Simple URL validation
        if "youtube.com" not in url and "youtu.be" not in url:
            raise HTTPException(status_code=400, detail="Invalid YouTube video link")
        
        # Use yt-dlp to get video information
        import yt_dlp
        import asyncio
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        if browser:
            ydl_opts['cookiesfrombrowser'] = (browser.lower(),)
        
        def extract_info_sync(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(None, extract_info_sync, url, ydl_opts)
        
        logger.info(f"YouTube video info parsed successfully: {info_dict.get('title', 'Unknown')}")
        
        return {
            "success": True,
            "video_info": {
                "title": info_dict.get('title', 'Unknown'),
                "description": info_dict.get('description', ''),
                "duration": info_dict.get('duration', 0),
                "uploader": info_dict.get('uploader', 'Unknown'),
                "upload_date": info_dict.get('upload_date', ''),
                "view_count": info_dict.get('view_count', 0),
                "like_count": info_dict.get('like_count', 0),
                "thumbnail": info_dict.get('thumbnail', '')
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to parse YouTube video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")

@router.post("/download")
async def create_youtube_download_task(request: YouTubeDownloadRequest):
    """Create YouTube video download task - create project immediately"""
    try:
        logger.info(f"Creating YouTube download task: {request.url}")
        
        # First get video info to obtain thumbnail
        import yt_dlp
        import asyncio
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        if request.browser:
            ydl_opts['cookiesfrombrowser'] = (request.browser.lower(),)
        
        def extract_info_sync(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        loop = asyncio.get_event_loop()
        video_info = await loop.run_in_executor(None, extract_info_sync, request.url, ydl_opts)
        
        # Create project record immediately
        from ...core.database import SessionLocal
        from ...services.project_service import ProjectService
        from ...schemas.project import ProjectCreate, ProjectType, ProjectStatus
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            
            # Process thumbnail - use parsed cover image directly
            thumbnail_data = None
            thumbnail_url = video_info.get('thumbnail', '')
            if thumbnail_url:
                try:
                    import requests
                    import base64
                    
                    # Download thumbnail
                    response = requests.get(thumbnail_url, timeout=10)
                    if response.status_code == 200:
                        # Convert to base64
                        thumbnail_base64 = base64.b64encode(response.content).decode('utf-8')
                        thumbnail_data = f"data:image/jpeg;base64,{thumbnail_base64}"
                        logger.info(f"YouTube thumbnail retrieved successfully: {video_info.get('title', 'Unknown')}")
                    else:
                        logger.warning(f"Failed to download YouTube thumbnail: {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to process YouTube thumbnail: {e}")
                    # Thumbnail processing failure does not affect main flow
            
            # Create project data
            project_data = ProjectCreate(
                name=request.project_name,
                description=f"Downloaded from YouTube: {video_info.get('title', 'Unknown')}",
                project_type=ProjectType(request.video_category),
                status=ProjectStatus.PENDING,  # Initial status is pending
                source_url=request.url,
                source_file=None,  # Will be updated after download
                settings={
                    "download_status": "downloading",
                    "download_progress": 0.0,
                    "youtube_info": {
                        "url": request.url,
                        "browser": request.browser,
                        "title": video_info.get('title', 'Unknown'),
                        "uploader": video_info.get('uploader', 'Unknown'),
                        "duration": video_info.get('duration', 0),
                        "view_count": video_info.get('view_count', 0),
                        "thumbnail_url": thumbnail_url
                    }
                }
            )
            
            project = project_service.create_project(project_data)
            project_id = str(project.id)
            
            # Set thumbnail
            if thumbnail_data:
                project.thumbnail = thumbnail_data
                db.commit()
                logger.info(f"Thumbnail set for project {project_id}")
            
            # Create project directory
            from ...core.path_utils import get_project_directory
            project_dir = get_project_directory(project_id)
            raw_dir = project_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Project created: {project_id}")
            
            # Generate download task ID
            task_id = str(uuid.uuid4())
            
            # Create task record
            task = YouTubeDownloadTask(
                id=task_id,
                url=request.url,
                project_name=request.project_name,
                video_category=request.video_category,
                status="pending",
                progress=0.0,
                project_id=project_id,  # Associate project ID
                created_at=str(uuid.uuid1().time),
                updated_at=str(uuid.uuid1().time)
            )
            
            # Store task
            download_tasks[task_id] = task
            
            # Async launch download task - use safe task manager
            from .async_task_manager import task_manager
            await task_manager.create_safe_task(
                f"youtube_download_{task_id}", 
                process_youtube_download_task, 
                task_id, 
                request, 
                project_id
            )
            
            # Return project info instead of task info
            return {
                "project_id": project_id,
                "task_id": task_id,
                "status": "created",
                "message": "Project created, downloading..."
            }
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Failed to create YouTube download task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/tasks/{task_id}")
async def get_youtube_task_status(task_id: str):
    """Get YouTube download task status"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Task does not exist")
    
    return download_tasks[task_id]

@router.get("/tasks")
async def get_all_youtube_tasks():
    """Get all YouTube download tasks"""
    return list(download_tasks.values())

async def update_project_download_progress(project_id: str, progress: float, message: str):
    """Update project download progress"""
    try:
        from ...core.database import SessionLocal
        from ...services.project_service import ProjectService
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            project = project_service.get(project_id)
            
            if project:
                # Update download progress in project settings
                if not project.processing_config:
                    project.processing_config = {}
                
                project.processing_config.update({
                    "download_progress": progress,
                    "download_message": message
                })
                
                # If progress reaches 100%, update status to pending
                if progress >= 100.0:
                    from ...schemas.project import ProjectStatus
                    project.status = ProjectStatus.PENDING
                
                db.commit()
                logger.info(f"Project {project_id} download progress updated: {progress}% - {message}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to update project download progress: {e}")

async def process_youtube_download_task(task_id: str, request: YouTubeDownloadRequest, project_id: str):
    """Process YouTube download task"""
    try:
        # Update task status to processing
        download_tasks[task_id].status = "processing"
        download_tasks[task_id].progress = 10.0
        
        # Update project status and progress
        await update_project_download_progress(project_id, 10.0, "Retrieving video information...")
        
        # Use yt-dlp to download video
        import yt_dlp
        import asyncio
        from ...core.config import get_data_directory
        
        data_dir = get_data_directory()
        download_dir = data_dir / "temp"
        download_dir.mkdir(exist_ok=True)
        
        # Update project progress
        await update_project_download_progress(project_id, 30.0, "Downloading video...")
        
        # Set download options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'writesubtitles': True,
            'writeautomaticsub': True,  # Download auto-generated subtitles
            'subtitleslangs': ['en', 'zh-Hans', 'zh', 'en-US', 'auto'],  # English and Chinese subtitles, including auto-detect
            'subtitlesformat': 'srt',
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': False,  # Show warnings for debugging
        }
        
        if request.browser:
            ydl_opts['cookiesfrombrowser'] = (request.browser.lower(),)
        
        def download_sync(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.download([url])
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_sync, request.url, ydl_opts)
        
        # Find downloaded files
        video_files = list(download_dir.glob("*.mp4"))
        subtitle_files = list(download_dir.glob("*.srt"))
        
        if not video_files:
            raise Exception("Downloaded video file not found")
        
        video_path = str(video_files[0])
        subtitle_path = str(subtitle_files[0]) if subtitle_files else ""
        
        download_tasks[task_id].progress = 80.0
        
        # Update project progress
        await update_project_download_progress(project_id, 60.0, "Video download completed, processing subtitles...")
        
        # If no subtitle file, use Whisper to generate subtitles first
        if not subtitle_path:
            logger.info("Using Whisper to generate high-quality subtitles")
            # Update project progress
            await update_project_download_progress(project_id, 70.0, "Generating subtitles with Whisper...")
            
            try:
                from ...utils.speech_recognizer import generate_subtitle_for_video, SpeechRecognitionError
                video_file_path = Path(video_path)
                
                # Select appropriate model based on video info
                model = "base"  # Default to balanced model
                language = "auto"  # Default to auto-detect language
                
                # Can determine content type based on video title
                # More intelligent content type detection logic can be added here
                
                logger.info(f"Generating subtitles with Whisper - language: {language}, model: {model}")
                
                generated_subtitle = generate_subtitle_for_video(
                    video_file_path,
                    language=language,
                    model=model
                )
                subtitle_path = str(generated_subtitle)
                logger.info(f"Whisper subtitle generation successful: {subtitle_path}")
                
                # Update project progress
                await update_project_download_progress(project_id, 90.0, "Subtitle generation completed, preparing for processing...")
                
            except SpeechRecognitionError as e:
                logger.error(f"Whisper subtitle generation failed: {e}")
                # When Whisper fails, try multiple strategies to get platform subtitles as backup
                logger.info("Trying to download platform subtitles as backup")
                try:
                    subtitle_path = await _try_youtube_subtitle_strategies(request.url, download_dir, request.browser)
                    if subtitle_path:
                        logger.info(f"Backup subtitle retrieval successful: {subtitle_path}")
                    else:
                        logger.warning("All subtitle retrieval strategies failed")
                        subtitle_path = None  # Ensure subtitle path is empty, project will be marked as failed later
                except Exception as backup_error:
                    logger.error(f"Backup subtitle retrieval also failed: {backup_error}")
                    subtitle_path = None  # Ensure subtitle path is empty, project will be marked as failed later
            except Exception as e:
                logger.error(f"Unknown error occurred during subtitle generation: {e}")
                subtitle_path = None  # Ensure subtitle path is empty, project will be marked as failed later
        
        logger.info(f"Download completed - video file: {video_path}, subtitle file: {subtitle_path}")
        
        # Update project info (project was created at the beginning)
        from ...services.project_service import ProjectService
        from ...core.database import SessionLocal
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            
            # Get the created project
            project = project_service.get(project_id)
            if not project:
                raise Exception(f"Project {project_id} does not exist")
            
            # Update project info
            project.description = f"Downloaded from YouTube: {request.project_name}"
            # Note: Do not set video_path here, wait until file move is complete
            
            # Update project settings
            if not project.processing_config:
                project.processing_config = {}
            
            project.processing_config.update({
                "youtube_info": {
                    "title": request.project_name,
                    "uploader": "YouTube",
                    "duration": 0,
                    "view_count": 0,
                    "like_count": 0
                },
                "subtitle_path": subtitle_path,
                "download_status": "completed",
                "download_progress": 100.0
            })
            
            # Move files to project directory
            from ...core.path_utils import get_project_directory
            project_dir = get_project_directory(project_id)
            raw_dir = project_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            # Move video file to project directory
            import shutil
            from pathlib import Path
            
            if video_path:
                video_file_path = Path(video_path)
                if video_file_path.exists():
                    # Rename video file to input.mp4
                    new_video_path = raw_dir / "input.mp4"
                    shutil.move(str(video_file_path), str(new_video_path))
                    logger.info(f"Video file moved to: {new_video_path}")
                    
                    # Update video path in project
                    project.video_path = str(new_video_path)
            
            # Move subtitle file to project directory
            if subtitle_path:
                subtitle_file_path = Path(subtitle_path)
                if subtitle_file_path.exists():
                    # Rename subtitle file to input.srt
                    new_subtitle_path = raw_dir / "input.srt"
                    shutil.move(str(subtitle_file_path), str(new_subtitle_path))
                    logger.info(f"Subtitle file moved to: {new_subtitle_path}")
                    
                    # Update subtitle path in project processing config
                    if not project.processing_config:
                        project.processing_config = {}
                    project.processing_config["subtitle_path"] = str(new_subtitle_path)
            
            # Save project updates
            db.commit()
            
            # Check if subtitle file exists, mark project as failed if not
            srt_file_path = raw_dir / "input.srt"
            if not srt_file_path.exists():
                logger.error(f"Subtitle file does not exist: {srt_file_path}, project will be marked as failed")
                from ...schemas.project import ProjectStatus
                project.status = ProjectStatus.FAILED
                if not project.processing_config:
                    project.processing_config = {}
                project.processing_config["error_message"] = "Subtitle file does not exist and Whisper generation failed"
                db.commit()
                
                # Update task status to failed
                download_tasks[task_id].status = "failed"
                download_tasks[task_id].error_message = "Subtitle file does not exist and Whisper generation failed"
                download_tasks[task_id].progress = 0.0
                download_tasks[task_id].project_id = str(project.id)
                download_tasks[task_id].updated_at = datetime.now().isoformat()
                
                # Update project download progress to failed
                await update_project_download_progress(project_id, 0.0, "Download failed: subtitle file does not exist")
                
                logger.info(f"YouTube download task failed: {task_id}, project ID: {project.id}, reason: subtitle file does not exist")
                return
            
            # Update project download progress to completed
            await update_project_download_progress(project_id, 100.0, "Download completed, preparing to start processing")
            
            # Update task status
            download_tasks[task_id].status = "completed"
            download_tasks[task_id].progress = 100.0
            download_tasks[task_id].project_id = str(project.id)
            download_tasks[task_id].updated_at = datetime.now().isoformat()
            
            logger.info(f"YouTube download task completed: {task_id}, project ID: {project.id}")
            
            # Auto-start processing pipeline
            try:
                # Update project status to pending
                from ...schemas.project import ProjectStatus
                project.status = ProjectStatus.PENDING  # Change to PENDING to let automation service start
                db.commit()
                
                logger.info(f"YouTube project {project.id} download completed, waiting for automation pipeline to start")
                
                # Async start automation pipeline
                import asyncio
                from ...services.auto_pipeline_service import auto_pipeline_service
                
                # Use create_task in running event loop
                try:
                    loop = asyncio.get_running_loop()
                    # Create task in running event loop
                    task = loop.create_task(
                        auto_pipeline_service.auto_start_pipeline(str(project.id))
                    )
                    # Wait for task to complete
                    pipeline_result = await task
                except RuntimeError:
                    # If no running event loop, create new one
                    pipeline_result = await auto_pipeline_service.auto_start_pipeline(str(project.id))
                
                if pipeline_result['status'] == 'started':
                    logger.info(f"YouTube project {project.id} automation pipeline started: {pipeline_result}")
                else:
                    logger.warning(f"YouTube project {project.id} automation pipeline start result: {pipeline_result}")
                
            except Exception as e:
                logger.error(f"Failed to start YouTube project {project.id} automation pipeline: {str(e)}")
                # Even if processing fails to start, return download success
                # User can restart processing via retry button
            
        except Exception as e:
            logger.error(f"Failed to create project: {str(e)}")
            # Even if processing fails to start, return download success
            # User can restart processing via retry button
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to process download task: {str(e)}")
        download_tasks[task_id].status = "failed"
        download_tasks[task_id].error_message = str(e)
        download_tasks[task_id].progress = 0.0
        download_tasks[task_id].updated_at = datetime.now().isoformat()


async def _try_youtube_subtitle_strategies(url: str, download_dir: Path, browser: Optional[str] = None) -> str:
    """Try multiple YouTube subtitle retrieval strategies"""
    strategies = [
        lambda: _try_download_with_different_formats(url, download_dir, browser),
        lambda: _try_download_with_different_langs(url, download_dir, browser),
        lambda: _try_extract_from_metadata(url, download_dir, browser)
    ]
    
    for strategy in strategies:
        try:
            subtitle_path = await strategy()
            if subtitle_path:
                logger.info(f"YouTube backup subtitle strategy succeeded")
                return subtitle_path
        except Exception as e:
            logger.warning(f"YouTube backup subtitle strategy failed: {e}")
            continue
    
    logger.warning("All YouTube subtitle retrieval strategies failed")
    return ""


async def _try_download_with_different_formats(url: str, download_dir: Path, browser: Optional[str] = None) -> str:
    """Try downloading subtitles in different formats"""
    import asyncio
    logger.info("Trying to download YouTube subtitles in different formats...")
    
    formats = ['srt', 'vtt', 'json3']
    
    for fmt in formats:
        try:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'zh-Hans', 'zh'],
                'subtitlesformat': fmt,
                'outtmpl': str(download_dir / f'subtitle_%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
            }
            
            if browser:
                ydl_opts['cookiesfrombrowser'] = (browser.lower(),)
            
            def download_sync(url, ydl_opts):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.download([url])
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, download_sync, url, ydl_opts)
            
            # Find downloaded subtitle files
            subtitle_files = list(download_dir.glob(f"*.{fmt}"))
            if subtitle_files:
                subtitle_path = str(subtitle_files[0])
                
                # If VTT format, convert to SRT
                if fmt == 'vtt':
                    srt_path = subtitle_path.replace('.vtt', '.srt')
                    await _convert_vtt_to_srt(subtitle_path, srt_path)
                    return srt_path
                
                return subtitle_path
                
        except Exception as e:
            logger.debug(f"Format {fmt} attempt failed: {e}")
            continue
    
    return ""


async def _try_download_with_different_langs(url: str, download_dir: Path, browser: Optional[str] = None) -> str:
    """Try downloading subtitles in different languages"""
    import asyncio
    logger.info("Trying to download YouTube subtitles in different languages...")
    
    lang_combinations = [
        ['en', 'en-US'],      # English
        ['zh-Hans', 'zh'],    # Chinese
        ['ja', 'ja-JP'],      # Japanese
        ['ko', 'ko-KR'],      # Korean
        ['auto']              # Auto-detect
    ]
    
    for langs in lang_combinations:
        try:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': langs,
                'subtitlesformat': 'srt',
                'outtmpl': str(download_dir / f'lang_%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
            }
            
            if browser:
                ydl_opts['cookiesfrombrowser'] = (browser.lower(),)
            
            def download_sync(url, ydl_opts):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.download([url])
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, download_sync, url, ydl_opts)
            
            # Find downloaded subtitle files
            subtitle_files = list(download_dir.glob("*.srt"))
            if subtitle_files:
                return str(subtitle_files[0])
                
        except Exception as e:
            logger.debug(f"Language {langs} attempt failed: {e}")
            continue
    
    return ""


async def _try_extract_from_metadata(url: str, download_dir: Path, browser: Optional[str] = None) -> str:
    """Try extracting subtitle information from video metadata"""
    import asyncio
    logger.info("Trying to extract subtitle info from YouTube video metadata...")
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        if browser:
            ydl_opts['cookiesfrombrowser'] = (browser.lower(),)
        
        def extract_info_sync(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(None, extract_info_sync, url, ydl_opts)
        
        # Check for subtitle information
        subtitles = info_dict.get('subtitles', {})
        auto_subtitles = info_dict.get('automatic_captions', {})
        
        if subtitles or auto_subtitles:
            logger.info(f"Found YouTube subtitle info: {list(subtitles.keys()) + list(auto_subtitles.keys())}")
            # Can further process subtitle info here, but currently return empty string
            return ""
        
        return ""
        
    except Exception as e:
        logger.debug(f"Failed to extract YouTube video metadata: {e}")
        return ""


async def _convert_vtt_to_srt(vtt_path: str, srt_path: str):
    """Convert VTT subtitle file to SRT format"""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as vtt_file:
            vtt_content = vtt_file.read()
        
        # Simple VTT to SRT conversion
        lines = vtt_content.split('\n')
        srt_lines = []
        subtitle_count = 1
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip VTT header info
            if line.startswith('WEBVTT') or line.startswith('NOTE') or not line:
                i += 1
                continue
            
            # Find timestamp line
            if '-->' in line:
                # Convert time format (VTT uses dots, SRT uses commas)
                time_line = line.replace('.', ',')
                srt_lines.append(str(subtitle_count))
                srt_lines.append(time_line)
                
                # Get subtitle text
                i += 1
                subtitle_text = []
                while i < len(lines) and lines[i].strip():
                    subtitle_text.append(lines[i].strip())
                    i += 1
                
                srt_lines.extend(subtitle_text)
                srt_lines.append('')  # Empty line separator
                subtitle_count += 1
            
            i += 1
        
        # Write SRT file
        with open(srt_path, 'w', encoding='utf-8') as srt_file:
            srt_file.write('\n'.join(srt_lines))
            
        logger.info(f"VTT to SRT conversion successful: {vtt_path} -> {srt_path}")
        
    except Exception as e:
        logger.error(f"VTT to SRT conversion failed: {e}")
        raise
