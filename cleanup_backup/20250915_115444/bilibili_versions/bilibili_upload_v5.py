"""
Bilibili Upload Submission Service v5.0
Correct implementation based on the official bilibili-api library
"""

import asyncio
import aiohttp
import json
import os
import time
import hashlib
import random
import string
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import logging

from ..core.database import SessionLocal
from ..models.bilibili import BilibiliAccount, BilibiliUploadRecord
from ..utils.crypto import decrypt_data
import uuid

# Import the official bilibili-api library
from bilibili_api import Credential, user

logger = logging.getLogger(__name__)

class BilibiliUploaderV5:
    """Bilibili Upload Submission Uploader v5.0 - Based on the official bilibili-api library"""
    
    def __init__(self, cookies: str):
        self.cookies = cookies
        self.session = None
        self.upload_id = None
        self.bv_id = None
        self.error_message = None
        self.credential = None
        
    def _create_credential(self) -> Optional[Credential]:
        """Create Credential object"""
        try:
            # Parse cookies
            cookie_dict = {}
            for cookie in self.cookies.split(';'):
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    cookie_dict[key.strip()] = value.strip()
            
            # Extract key fields
            sessdata = cookie_dict.get('SESSDATA', '')
            bili_jct = cookie_dict.get('bili_jct', '')
            buvid3 = cookie_dict.get('buvid3', '')
            dede_user_id = cookie_dict.get('DedeUserID', '')
            
            if not all([sessdata, bili_jct, buvid3, dede_user_id]):
                self.error_message = "Cookie missing required authentication fields"
                return None
            
            # Create Credential object
            credential = Credential(
                sessdata=sessdata,
                bili_jct=bili_jct,
                buvid3=buvid3,
                dedeuserid=dede_user_id
            )
            
            return credential
            
        except Exception as e:
            self.error_message = f"Failed to create Credential object: {str(e)}"
            return None
    
    async def upload_video(self, video_path: str, metadata: dict, max_retries: int = 3) -> bool:
        """Main upload video flow - Based on the official bilibili-api library"""
        try:
            # Create Credential object
            self.credential = self._create_credential()
            if not self.credential:
                return False
            
            async with aiohttp.ClientSession() as session:
                self.session = session
                
                # 1. Verify login status
                if not await self._check_login_status():
                    return False
                
                # 2. Get pre-upload info
                pre_upload_info = await self._get_pre_upload_info(video_path)
                if not pre_upload_info:
                    return False
                
                # 3. Chunk upload - Using the correct implementation
                success = await self._chunk_upload_correct(video_path, pre_upload_info, max_retries)
                if not success:
                    return False
                
                # 4. Merge chunks
                success = await self._merge_chunks_correct(pre_upload_info)
                if not success:
                    return False
                
                # 5. Submit upload
                success = await self._submit_video_correct(pre_upload_info, metadata)
                if not success:
                    return False
                
                return True
                
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to upload video: {e}")
            return False
    
    async def _check_login_status(self) -> bool:
        """Check login status - Using the official bilibili-api library"""
        try:
            # Check login status using the official library
            u = user.User(uid=int(self.credential.dedeuserid), credential=self.credential)
            user_info = await u.get_user_info()
            
            if user_info and user_info.get('mid'):
                logger.info(f"Login status normal, user: {user_info.get('name', 'unknown')}")
                return True
            else:
                self.error_message = "User not logged in or login status abnormal"
                logger.error(self.error_message)
                return False
                
        except Exception as e:
            self.error_message = f"Exception checking login status: {str(e)}"
            logger.error(self.error_message)
            return False
    
    async def _get_pre_upload_info(self, video_path: str) -> Optional[dict]:
        """Get pre-upload info - Using the correct implementation"""
        try:
            file_size = os.path.getsize(video_path)
            file_name = os.path.basename(video_path)
            
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://member.bilibili.com/",
                "Origin": "https://member.bilibili.com",
                "X-CSRF-Token": self.credential.bili_jct
            }
            
            # Using the correct parameters
            params = {
                "name": file_name,
                "size": str(file_size),
                "r": "upos",
                "profile": "ugcupos/bup",
                "ssl": "0",
                "version": "2.10.4",
                "build": "2100400",
                "upcdn": "bda2,bldsa",
                "probe_version": "20200709"
            }
            
            async with self.session.get(
                "https://member.bilibili.com/preupload",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Pre-upload API response: {result}")
                    if result.get("OK") == 1:
                        upload_info = {
                            "upload_id": result.get("biz_id"),
                            "endpoint": result.get("endpoint"),
                            "auth": result.get("auth"),
                            "chunk_size": result.get("chunk_size", 10485760),
                            "upos_uri": result.get("upos_uri"),
                            "put_query": result.get("put_query")
                        }
                        logger.info(f"Pre-upload info obtained successfully: {upload_info}")
                        return upload_info
                    else:
                        self.error_message = f"Pre-upload failed: {result.get('message', 'Unknown error')}"
                        logger.error(self.error_message)
                        return None
                else:
                    self.error_message = f"Pre-upload request failed, HTTP status code: {response.status}"
                    logger.error(self.error_message)
                    return None
                    
        except Exception as e:
            self.error_message = f"Exception getting pre-upload info: {str(e)}"
            logger.error(self.error_message)
            return None
    
    async def _chunk_upload_correct(self, video_path: str, upload_info: dict, max_retries: int = 3) -> bool:
        """Chunk upload - Using the correct implementation"""
        try:
            file_size = os.path.getsize(video_path)
            chunk_size = 2 * 1024 * 1024  # 2MB chunks
            total_chunks = (file_size + chunk_size - 1) // chunk_size
            
            endpoint = upload_info.get("endpoint", "//upos-cs-upcdnbda2.bilivideo.com")
            auth = upload_info.get("auth", "")
            upos_uri = upload_info.get("upos_uri", "")
            
            # Handle endpoint format
            if "," in endpoint:
                endpoint = endpoint.split(",")[0]
            if not endpoint.endswith('.bilivideo.com'):
                endpoint = endpoint.replace('//upos-cs-upcdnbda2', '//upos-cs-upcdnbda2.bilivideo.com')
            
            # Handle upos_uri format
            if upos_uri.startswith("upos://"):
                upos_path = upos_uri[7:]
            else:
                upos_path = upos_uri
            
            # Build upload URL
            upload_url = f"https:{endpoint}/{upos_path}"
            if auth:
                upload_url += f"?{auth}"
            
            logger.info(f"Constructed upload URL: {upload_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://member.bilibili.com/",
                "Origin": "https://member.bilibili.com"
            }
            
            with open(video_path, 'rb') as f:
                for chunk_index in range(total_chunks):
                    # Read chunk data
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Retry logic
                    for attempt in range(max_retries):
                        try:
                            # Build chunk upload URL - Using the correct parameter format
                            chunk_url = f"{upload_url}&partNumber={chunk_index + 1}"
                            
                            logger.debug(f"Chunk {chunk_index + 1} upload URL: {chunk_url}")
                            
                            # Upload chunk using PUT method - This is the key!
                            headers['Content-Type'] = 'application/octet-stream'
                            headers['Content-Length'] = str(len(chunk_data))
                            
                            async with self.session.put(
                                chunk_url,
                                headers=headers,
                                data=chunk_data,
                                timeout=aiohttp.ClientTimeout(total=60)
                            ) as response:
                                if response.status in [200, 201, 204]:
                                    logger.debug(f"Chunk {chunk_index + 1}/{total_chunks} uploaded successfully")
                                    break
                                else:
                                    if attempt < max_retries - 1:
                                        logger.warning(f"Chunk {chunk_index + 1} upload failed, retrying {attempt + 1}/{max_retries}: HTTP {response.status}")
                                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    else:
                                        logger.error(f"Chunk {chunk_index + 1} upload failed: HTTP {response.status}")
                                        response_text = await response.text()
                                        logger.error(f"Response content: {response_text}")
                                        return False
                                        
                        except Exception as e:
                            if attempt < max_retries - 1:
                                logger.warning(f"Chunk {chunk_index + 1} upload exception, retrying {attempt + 1}/{max_retries}: {str(e)}")
                                await asyncio.sleep(2 ** attempt)
                            else:
                                logger.error(f"Chunk {chunk_index + 1} upload exception: {str(e)}")
                                return False
            
            logger.info("All chunks uploaded successfully")
            return True
            
        except Exception as e:
            self.error_message = f"Chunk upload exception: {str(e)}"
            logger.error(self.error_message)
            return False
    
    async def _merge_chunks_correct(self, upload_info: dict) -> bool:
        """Merge chunks - Using the correct implementation"""
        try:
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://member.bilibili.com/",
                "Origin": "https://member.bilibili.com",
                "X-CSRF-Token": self.credential.bili_jct,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "biz_id": upload_info.get("upload_id"),
                "csrf": self.credential.bili_jct
            }
            
            async with self.session.post(
                "https://member.bilibili.com/x/vu/web/complete",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Merge chunks response: {result}")
                    if result.get("code") == 0:
                        logger.info("Chunks merged successfully")
                        return True
                    else:
                        self.error_message = f"Merge chunks failed: {result.get('message', 'Unknown error')}"
                        logger.error(self.error_message)
                        return False
                else:
                    self.error_message = f"Merge chunks request failed, HTTP status code: {response.status}"
                    logger.error(self.error_message)
                    return False
                    
        except Exception as e:
            self.error_message = f"Merge chunks exception: {str(e)}"
            logger.error(self.error_message)
            return False
    
    async def _submit_video_correct(self, upload_info: dict, metadata: dict) -> bool:
        """Submit upload - Using the correct implementation"""
        try:
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://member.bilibili.com/",
                "Origin": "https://member.bilibili.com",
                "X-CSRF-Token": self.credential.bili_jct,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Build upload submission data
            upos_uri = upload_info.get("upos_uri", "")
            filename = upos_uri.split("/")[-1] if "/" in upos_uri else upos_uri
            
            data = {
                "copyright": "1",  # Original
                "videos": json.dumps([{
                    "filename": filename,
                    "title": metadata.get("title", ""),
                    "desc": metadata.get("description", "")
                }]),
                "source": "",
                "tid": str(metadata.get("partition_id", 1)),
                "cover": "",
                "title": metadata.get("title", ""),
                "tag": ",".join(metadata.get("tags", [])),
                "desc_format_id": "0",
                "desc": metadata.get("description", ""),
                "open_elec": "1",
                "no_reprint": "0",
                "subtitles": json.dumps({
                    "lan": "",
                    "open": "0"
                }),
                "csrf": self.credential.bili_jct
            }
            
            async with self.session.post(
                "https://member.bilibili.com/x/vu/web/add",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Submit upload response: {result}")
                    if result.get("code") == 0:
                        self.bv_id = result.get("data", {}).get("bvid")
                        logger.info(f"Upload submitted successfully, BV ID: {self.bv_id}")
                        return True
                    else:
                        self.error_message = f"Upload submission failed: {result.get('message', 'Unknown error')}"
                        logger.error(self.error_message)
                        return False
                else:
                    self.error_message = f"Upload submission request failed, HTTP status code: {response.status}"
                    logger.error(self.error_message)
                    return False
                    
        except Exception as e:
            self.error_message = f"Upload submission exception: {str(e)}"
            logger.error(self.error_message)
            return False


class BilibiliUploadServiceV5:
    """Bilibili Upload Submission Service v5.0"""
    
    def __init__(self, db):
        self.db = db
    
    async def upload_clip(self, record_id: int, video_path: str, max_retries: int = 3) -> bool:
        """Upload a single clip"""
        try:
            # Get upload record
            record = self.db.query(BilibiliUploadRecord).filter(BilibiliUploadRecord.id == record_id).first()
            if not record:
                logger.error(f"Upload record does not exist: {record_id}")
                return False
            
            # Get account info
            account = self.db.query(BilibiliAccount).filter(BilibiliAccount.id == record.account_id).first()
            if not account:
                logger.error(f"Account does not exist: {record.account_id}")
                return False
            
            # Decrypt Cookie
            try:
                cookies = decrypt_data(account.cookies)
            except Exception as e:
                logger.error(f"Failed to decrypt Cookie: {e}")
                return False
            
            # Build upload submission metadata
            metadata = {
                "title": record.title,
                "description": record.description or "",
                "tags": json.loads(record.tags) if record.tags else [],
                "partition_id": record.partition_id
            }
            
            # Use v5.0 uploader
            uploader = BilibiliUploaderV5(cookies)
            success = await uploader.upload_video(video_path, metadata, max_retries)
            
            if success:
                # Update record status
                record.status = "success"
                record.bv_id = uploader.bv_id
                record.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Clip uploaded successfully: {record_id}, BV ID: {uploader.bv_id}")
                return True
            else:
                # Update record status
                record.status = "failed"
                record.error_message = uploader.error_message
                record.updated_at = datetime.utcnow()
                self.db.commit()
                logger.error(f"Clip upload failed: {record_id}, error: {uploader.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Upload clip exception: {e}")
            return False
