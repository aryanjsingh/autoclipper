"""
Bilibili service class - Refactored version
Removed bilitool dependency, using direct API calls
"""

import asyncio
import json
import logging
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

import aiofiles
import aiohttp
from sqlalchemy.orm import Session

from ..models.bilibili import BilibiliAccount, UploadRecord
from ..schemas.bilibili import BilibiliAccountCreate, UploadRequest
from ..utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class BilibiliAccountService:
    """Bilibili account service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def verify_cookie(self, cookie: str) -> Tuple[bool, Optional[Dict]]:
        """Verify if Bilibili Cookie is valid"""
        try:
            headers = {
                "Cookie": cookie,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/"
            }
            
            async with aiohttp.ClientSession() as session:
                # First check login status
                async with session.get(
                    "https://api.bilibili.com/x/web-interface/nav",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    
                    if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
                        user_info = data["data"]
                        
                        return True, {
                            "uid": user_info.get("mid"),
                            "username": user_info.get("uname"),
                            "face": user_info.get("face"),
                            "level": user_info.get("level_info", {}).get("current_level", 0),
                            "can_upload": True,  # Temporarily set to True to avoid extra API calls
                            "vip_status": user_info.get("vipStatus", 0),
                            "verified_at": datetime.now().isoformat()
                        }
                    else:
                        logger.warning(f"Cookie verification failed: code={data.get('code')}, message={data.get('message')}")
                        return False, None
                        
        except asyncio.TimeoutError:
            logger.error("Cookie verification timed out")
            return False, None
        except Exception as e:
            logger.error(f"Cookie verification failed: {e}")
            return False, None
    
    async def create_account(self, account_data: BilibiliAccountCreate) -> BilibiliAccount:
        """Create a Bilibili account"""
        try:
            # Verify Cookie
            is_valid, user_info = await self.verify_cookie(account_data.cookie_content)
            if not is_valid:
                raise ValueError("Invalid Cookie, please check if the Cookie is correct or has expired")
            
            # Check if account already exists
            existing_account = self.db.query(BilibiliAccount).filter(
                BilibiliAccount.username == user_info.get("username")
            ).first()
            
            if existing_account:
                # Update existing account info
                existing_account.cookies = encrypt_data(account_data.cookie_content)
                existing_account.nickname = account_data.nickname or user_info.get("username")
                existing_account.status = "active"
                existing_account.updated_at = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing_account)
                
                logger.info(f"Updated existing Bilibili account: {existing_account.username}")
                return existing_account
            
            # Encrypt and store cookies
            encrypted_cookies = encrypt_data(account_data.cookie_content)
            
            # Create new account record
            account = BilibiliAccount(
                username=user_info.get("username", account_data.username),
                nickname=account_data.nickname or user_info.get("username", "Bilibili User"),
                cookies=encrypted_cookies,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"Bilibili account created successfully: {account.username} (UID: {user_info.get('uid')})")
            return account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create Bilibili account: {e}")
            raise
    
    async def check_account_health(self, account_id: int) -> Dict[str, Any]:
        """Check account health status"""
        try:
            account = self.db.query(BilibiliAccount).filter(
                BilibiliAccount.id == account_id
            ).first()
            
            if not account:
                raise ValueError("Account does not exist")
            
            # Decrypt Cookie
            decrypted_cookies = decrypt_data(account.cookies)
            
            # Verify Cookie validity
            is_valid, user_info = await self.verify_cookie(decrypted_cookies)
            
            health_status = {
                "account_id": account_id,
                "username": account.username,
                "is_valid": is_valid,
                "checked_at": datetime.now().isoformat(),
                "last_verified": account.updated_at.isoformat() if account.updated_at else None
            }
            
            if is_valid and user_info:
                health_status.update({
                    "user_info": user_info,
                    "can_upload": user_info.get("can_upload", False),
                    "level": user_info.get("level", 0),
                    "vip_status": user_info.get("vip_status", 0)
                })
                
                # Update account status
                account.status = "active"
                account.updated_at = datetime.now()
            else:
                health_status["error"] = "Cookie has expired or account is abnormal"
                account.status = "inactive"
            
            self.db.commit()
            return health_status
            
        except Exception as e:
            logger.error(f"Failed to check account health status: {e}")
            return {
                "account_id": account_id,
                "is_valid": False,
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    async def batch_check_accounts_health(self) -> List[Dict[str, Any]]:
        """Batch check health status of all accounts"""
        try:
            accounts = self.db.query(BilibiliAccount).all()
            results = []
            
            for account in accounts:
                health_status = await self.check_account_health(account.id)
                results.append(health_status)
                
                # Avoid too frequent requests
                await asyncio.sleep(1)
            
            logger.info(f"Batch check completed, checked {len(results)} accounts")
            return results
            
        except Exception as e:
            logger.error(f"Failed to batch check account health status: {e}")
            raise
    
    def get_active_accounts(self) -> List[BilibiliAccount]:
        """Get all active accounts"""
        try:
            accounts = self.db.query(BilibiliAccount).filter(
                BilibiliAccount.status == "active"
            ).order_by(BilibiliAccount.updated_at.desc()).all()
            
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to get active accounts: {e}")
            return []
    
    def get_account_by_id(self, account_id: int) -> Optional[BilibiliAccount]:
        """Get account by ID"""
        try:
            return self.db.query(BilibiliAccount).filter(
                BilibiliAccount.id == account_id
            ).first()
            
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return None
    
    def select_best_account(self, exclude_ids: List[int] = None) -> Optional[BilibiliAccount]:
        """Intelligently select the best upload account"""
        try:
            query = self.db.query(BilibiliAccount).filter(
                BilibiliAccount.status == "active"
            )
            
            if exclude_ids:
                query = query.filter(~BilibiliAccount.id.in_(exclude_ids))
            
            accounts = query.all()
            
            if not accounts:
                return None
            
            # Sort by priority: VIP > Level > Last used time
            def account_priority(account):
                # VIP accounts get priority
                vip_score = account.vip_status * 1000 if hasattr(account, 'vip_status') else 0
                # Level score
                level_score = getattr(account, 'level', 0) * 100
                # Last used time (longer unused = higher priority)
                last_used = account.updated_at or account.created_at
                time_score = (datetime.now() - last_used).total_seconds() / 3600  # Hours
                
                return vip_score + level_score + time_score
            
            best_account = max(accounts, key=account_priority)
            logger.info(f"Selected account for upload: {best_account.username} (ID: {best_account.id})")
            
            return best_account
            
        except Exception as e:
            logger.error(f"Failed to select best account: {e}")
            return None
    
    def get_account_upload_stats(self, account_id: int, days: int = 7) -> Dict[str, Any]:
        """Get account upload statistics"""
        try:
            from datetime import timedelta
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Query upload records
            upload_records = self.db.query(UploadRecord).filter(
                UploadRecord.account_id == account_id,
                UploadRecord.created_at >= start_date
            ).all()
            
            total_uploads = len(upload_records)
            successful_uploads = len([r for r in upload_records if r.status == 'success'])
            failed_uploads = len([r for r in upload_records if r.status == 'failed'])
            
            success_rate = (successful_uploads / total_uploads * 100) if total_uploads > 0 else 0
            
            return {
                "account_id": account_id,
                "days": days,
                "total_uploads": total_uploads,
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "success_rate": round(success_rate, 2),
                "last_upload": upload_records[-1].created_at.isoformat() if upload_records else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get account upload stats: {e}")
            return {
                "account_id": account_id,
                "error": str(e)
            }
    
    def rotate_accounts_for_batch_upload(self, video_count: int) -> List[BilibiliAccount]:
        """Allocate accounts for batch upload (load balancing)"""
        try:
            active_accounts = self.get_active_accounts()
            
            if not active_accounts:
                return []
            
            # If video count is less than account count, allocate directly
            if video_count <= len(active_accounts):
                return active_accounts[:video_count]
            
            # Otherwise rotate allocation
            allocated_accounts = []
            for i in range(video_count):
                account_index = i % len(active_accounts)
                allocated_accounts.append(active_accounts[account_index])
            
            logger.info(f"Allocated {len(set(allocated_accounts))} accounts for {video_count} videos")
            return allocated_accounts
            
        except Exception as e:
            logger.error(f"Account rotation allocation failed: {e}")
            return []
    
    def update_account_usage(self, account_id: int):
        """Update account last usage time"""
        try:
            account = self.get_account_by_id(account_id)
            if account:
                account.updated_at = datetime.now()
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update account usage time: {e}")
    
    def get_accounts(self) -> List[BilibiliAccount]:
        """Get all accounts"""
        return self.db.query(BilibiliAccount).all()
    
    def get_account(self, account_id: UUID) -> Optional[BilibiliAccount]:
        """Get specified account"""
        return self.db.query(BilibiliAccount).filter(BilibiliAccount.id == account_id).first()
    
    def delete_account(self, account_id: UUID) -> bool:
        """Delete account"""
        account = self.get_account(account_id)
        if not account:
            return False
        
        try:
            # First delete all related upload records
            from ..models.bilibili import UploadRecord
            upload_records = self.db.query(UploadRecord).filter(UploadRecord.account_id == account_id).all()
            
            for record in upload_records:
                logger.info(f"Deleting related upload record: {record.id}")
                self.db.delete(record)
            
            # Delete account
            self.db.delete(account)
            self.db.commit()
            
            logger.info(f"Bilibili account deleted successfully: {account.username}, also deleted {len(upload_records)} related upload records")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete account: {str(e)}")
            return False
    
    def check_account_status(self, account_id: UUID) -> bool:
        """Check account status"""
        account = self.get_account(account_id)
        if not account:
            return False
        
        try:
            # Try to decrypt cookies
            try:
                cookies_data_str = decrypt_data(account.cookies)
                # Verify cookie string format
                if not cookies_data_str or not isinstance(cookies_data_str, str):
                    return False
                return True
            except Exception as e:
                logger.warning(f"Failed to decrypt cookies: {str(e)}")
                return False
                    
        except Exception as e:
            logger.error(f"Failed to check account status: {str(e)}")
            return False


class BilibiliUploadService:
    """Bilibili upload service - using direct API calls"""
    
    def __init__(self, db: Session):
        self.db = db
        self.account_service = BilibiliAccountService(db)
    
    def create_upload_record(self, project_id: UUID, upload_data: UploadRequest) -> UploadRecord:
        """Create upload record"""
        # Verify account
        account = self.account_service.get_account(upload_data.account_id)
        if not account:
            raise ValueError("Account does not exist")
        
        # Create upload record
        record = UploadRecord(
            project_id=project_id,
            account_id=upload_data.account_id,
            clip_id=",".join(upload_data.clip_ids),  # Temporarily stored as comma-separated
            title=upload_data.title,
            description=upload_data.description,
            tags=json.dumps(upload_data.tags),
            partition_id=upload_data.partition_id,
            status="pending"
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"Upload record created successfully: {record.id}")
        return record
    
    async def upload_clip(self, record_id: int, video_path: str, max_retries: int = 3) -> bool:
        """Upload a single clip - using built-in upload implementation"""
        try:
            # Get upload record
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                logger.error(f"Upload record does not exist: {record_id}")
                return False
            
            # Get account info
            account = self.db.query(BilibiliAccount).filter(BilibiliAccount.id == record.account_id).first()
            if not account:
                logger.error(f"Account does not exist: {record.account_id}")
                return False
            
            # Decrypt Cookie
            cookies = decrypt_data(account.cookies)
            if not cookies:
                logger.error("Cookie decryption failed")
                return False
            
            # Use direct uploader
            uploader = BilibiliDirectUploader(cookies)
            success = await uploader.upload_video(
                video_path=video_path,
                metadata={
                    'title': record.title,
                    'desc': record.description or '',
                    'tid': record.tid,
                    'tag': record.tags or '',
                    'source': record.source or '',
                    'copyright': record.copyright or 1
                },
                max_retries=max_retries
            )
            
            if success:
                record.status = 'completed'
                record.bv_id = uploader.bv_id
                record.completed_at = datetime.utcnow()
            else:
                record.status = 'failed'
                record.error_message = uploader.error_message
                record.failed_at = datetime.utcnow()
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Failed to upload clip: {e}")
            # Update record status
            try:
                record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
                if record:
                    record.status = 'failed'
                    record.error_message = str(e)
                    record.failed_at = datetime.utcnow()
                    self.db.commit()
            except:
                pass
            return False
    
    def update_upload_status(self, record_id, status: str, error_message: str = None) -> bool:
        """Update upload status"""
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                return False
            
            record.status = status
            if error_message:
                record.error_message = error_message
            record.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update upload status: {str(e)}")
            self.db.rollback()
            return False

    def retry_upload_task(self, record_id: int) -> bool:
        """Retry a failed upload task"""
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                raise ValueError("Upload record does not exist")
            
            if record.status != "failed":
                raise ValueError("Only failed tasks can be retried")
            
            # Reset status to pending
            record.status = "pending"
            record.error_message = None
            record.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Restart upload task
            clip_ids = record.clip_id.split(",") if record.clip_id else []
            for clip_id in clip_ids:
                clip_id = clip_id.strip()
                if clip_id:
                    from ..tasks.upload import upload_clip_task
                    upload_clip_task.delay(str(record.id), clip_id)
            
            logger.info(f"Upload task retry initiated: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry upload task: {str(e)}")
            self.db.rollback()
            return False

    def cancel_upload_task(self, record_id: int) -> bool:
        """Cancel an in-progress upload task"""
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                raise ValueError("Upload record does not exist")
            
            if record.status not in ["pending", "processing"]:
                raise ValueError("Only pending or processing tasks can be cancelled")
            
            # Update status to cancelled
            record.status = "cancelled"
            record.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Upload task cancelled: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel upload task: {str(e)}")
            self.db.rollback()
            return False
    
    def delete_upload_task(self, record_id: int) -> bool:
        """Delete an upload task"""
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                raise ValueError("Upload record does not exist")
            
            # Only completed, failed, or cancelled tasks can be deleted
            if record.status in ["pending", "processing"]:
                raise ValueError("In-progress tasks cannot be deleted, please cancel first")
            
            # Delete record
            self.db.delete(record)
            self.db.commit()
            
            logger.info(f"Upload task deleted: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete upload task: {str(e)}")
            self.db.rollback()
            return False
    
    def get_upload_records(self, project_id: Optional[UUID] = None) -> List[dict]:
        """Get upload records with related info"""
        from ..models.project import Project
        
        query = self.db.query(
            UploadRecord,
            BilibiliAccount.username.label('account_username'),
            BilibiliAccount.nickname.label('account_nickname'),
            Project.name.label('project_name')
        ).join(
            BilibiliAccount, UploadRecord.account_id == BilibiliAccount.id
        ).outerjoin(
            Project, UploadRecord.project_id == Project.id
        )
        
        if project_id:
            query = query.filter(UploadRecord.project_id == project_id)
        
        results = query.order_by(UploadRecord.created_at.desc()).all()
        
        # Convert to dictionary format with related info
        records = []
        for record, account_username, account_nickname, project_name in results:
            record_dict = {
                'id': record.id,
                'task_id': record.task_id,
                'project_id': record.project_id,
                'account_id': record.account_id,
                'clip_id': record.clip_id,
                'title': record.title,
                'description': record.description,
                'tags': record.tags,
                'partition_id': record.partition_id,
                'video_path': record.video_path,
                'bv_id': record.bv_id,
                'av_id': record.av_id,
                'status': record.status,
                'error_message': record.error_message,
                'progress': record.progress or 0,
                'file_size': record.file_size,
                'upload_duration': record.upload_duration,
                'created_at': record.created_at,
                'updated_at': record.updated_at,
                'account_username': account_username,
                'account_nickname': account_nickname,
                'project_name': project_name
            }
            records.append(record_dict)
        
        return records
    
    def get_upload_record(self, record_id: UUID) -> Optional[UploadRecord]:
        """Get specified upload record"""
        return self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
    
    def get_upload_record_by_id(self, record_id: int) -> Optional[UploadRecord]:
        """Get specified upload record by integer ID"""
        return self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
    
    def upload_clip_sync(self, record_id: int, video_path: str, max_retries: int = 3) -> bool:
        """Synchronous version of single clip upload"""
        try:
            # Get upload record
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                logger.error(f"Upload record does not exist: {record_id}")
                return False
            
            # Get account info
            account = self.db.query(BilibiliAccount).filter(BilibiliAccount.id == record.account_id).first()
            if not account:
                logger.error(f"Account does not exist: {record.account_id}")
                return False
            
            # Decrypt Cookie
            cookies = decrypt_data(account.cookies)
            if not cookies:
                logger.error("Cookie decryption failed")
                return False
            
            # Use direct uploader (sync version)
            uploader = BilibiliDirectUploader(cookies)
            success = uploader.upload_video_sync(
                video_path=video_path,
                metadata={
                    'title': record.title,
                    'desc': record.description or '',
                    'tid': record.tid,
                    'tag': record.tags or '',
                    'source': record.source or '',
                    'copyright': record.copyright or 1
                },
                max_retries=max_retries
            )
            
            if success:
                record.status = 'completed'
                record.bv_id = uploader.bv_id
                record.completed_at = datetime.utcnow()
            else:
                record.status = 'failed'
                record.error_message = uploader.error_message
                record.failed_at = datetime.utcnow()
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Failed to upload clip: {e}")
            # Update record status
            try:
                record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
                if record:
                    record.status = 'failed'
                    record.error_message = str(e)
                    record.failed_at = datetime.utcnow()
                    self.db.commit()
            except:
                pass
            return False


class BilibiliDirectUploader:
    """Bilibili direct API uploader"""
    
    def __init__(self, cookies: str):
        self.cookies = cookies
        self.bv_id = None
        self.error_message = None
        self.session = None
    
    async def upload_video(self, video_path: str, metadata: dict, max_retries: int = 3) -> bool:
        """Upload video - simplified version, temporarily returns failure status"""
        try:
            # Temporarily return failure as upload logic needs to be reimplemented
            self.error_message = "Upload feature is under development, please try again later"
            logger.warning("Upload feature not yet implemented, returning failure status")
            return False
                
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to upload video: {e}")
            return False
    
    def upload_video_sync(self, video_path: str, metadata: dict, max_retries: int = 3) -> bool:
        """Synchronous version of video upload"""
        try:
            # Temporarily return failure as upload logic needs to be reimplemented
            self.error_message = "Upload feature is under development, please try again later"
            logger.warning("Upload feature not yet implemented, returning failure status")
            return False
                
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to upload video: {e}")
            return False
    
    async def _pre_upload(self, video_path: str) -> Optional[str]:
        """Pre-upload to get upload_id"""
        try:
            file_size = os.path.getsize(video_path)
            file_name = os.path.basename(video_path)
            
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://member.bilibili.com/"
            }
            
            data = {
                "name": file_name,
                "size": str(file_size)
            }
            
            async with self.session.post(
                "https://member.bilibili.com/x/vu/web/add",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                
                if result.get("code") == 0:
                    upload_id = result.get("data", {}).get("id")
                    logger.info(f"Pre-upload successful, upload_id: {upload_id}")
                    return upload_id
                else:
                    self.error_message = f"Pre-upload failed: {result.get('message', 'Unknown error')}"
                    logger.error(self.error_message)
                    return None
                    
        except Exception as e:
            self.error_message = f"Pre-upload exception: {str(e)}"
            logger.error(self.error_message)
            return None
    
    async def _chunk_upload(self, video_path: str, upload_id: str, max_retries: int = 3) -> bool:
        """Chunk upload"""
        try:
            chunk_size = 2 * 1024 * 1024  # 2MB per chunk
            file_size = os.path.getsize(video_path)
            
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://member.bilibili.com/"
            }
            
            with open(video_path, 'rb') as f:
                chunk_index = 0
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Retry logic
                    for attempt in range(max_retries):
                        try:
                            form_data = aiohttp.FormData()
                            form_data.add_field('chunk', chunk_data, filename=f'chunk_{chunk_index}')
                            form_data.add_field('id', upload_id)
                            form_data.add_field('chunk_index', str(chunk_index))
                            
                            async with self.session.post(
                                "https://member.bilibili.com/x/vu/web/upload",
                                headers=headers,
                                data=form_data,
                                timeout=aiohttp.ClientTimeout(total=60)
                            ) as response:
                                result = await response.json()
                                
                                if result.get("code") == 0:
                                    logger.info(f"Chunk {chunk_index} uploaded successfully")
                                    break
                                else:
                                    if attempt == max_retries - 1:
                                        self.error_message = f"Chunk {chunk_index} upload failed: {result.get('message', 'Unknown error')}"
                                        logger.error(self.error_message)
                                        return False
                                    else:
                                        await asyncio.sleep(2 ** attempt)
                                        
                        except Exception as e:
                            if attempt == max_retries - 1:
                                self.error_message = f"Chunk {chunk_index} upload exception: {str(e)}"
                                logger.error(self.error_message)
                                return False
                            else:
                                await asyncio.sleep(2 ** attempt)
                    
                    chunk_index += 1
            
            logger.info(f"All chunks uploaded successfully, total {chunk_index} chunks")
            return True
            
        except Exception as e:
            self.error_message = f"Chunk upload exception: {str(e)}"
            logger.error(self.error_message)
            return False
    
    async def _merge_chunks(self, upload_id: str) -> bool:
        """Merge chunks"""
        try:
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://member.bilibili.com/"
            }
            
            data = {
                "id": upload_id
            }
            
            async with self.session.post(
                "https://member.bilibili.com/x/vu/web/merge",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                result = await response.json()
                
                if result.get("code") == 0:
                    logger.info("Chunk merge successful")
                    return True
                else:
                    self.error_message = f"Chunk merge failed: {result.get('message', 'Unknown error')}"
                    logger.error(self.error_message)
                    return False
                    
        except Exception as e:
            self.error_message = f"Chunk merge exception: {str(e)}"
            logger.error(self.error_message)
            return False
    
    async def _submit_video(self, upload_id: str, metadata: dict) -> bool:
        """Submit upload"""
        try:
            headers = {
                "Cookie": self.cookies,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://member.bilibili.com/",
                "Content-Type": "application/json"
            }
            
            # Build upload data
            submit_data = {
                "copyright": 1,  # Self-made
                "videos": [{
                    "filename": upload_id,
                    "title": metadata.get('title', ''),
                    "desc": metadata.get('description', '')
                }],
                "source": "",
                "tid": metadata.get('partition_id', 17),
                "cover": "",
                "title": metadata.get('title', ''),
                "tag": ",".join(metadata.get('tags', [])),
                "desc_format_id": 0,
                "desc": metadata.get('description', ''),
                "dynamic": "",
                "subtitle": {
                    "open": 0,
                    "lan": ""
                },
                "open_elec": 0,
                "no_reprint": 0,
                "up_selection_reply": False,
                "up_close_reply": False,
                "up_close_danmu": False
            }
            
            async with self.session.post(
                "https://member.bilibili.com/x/vu/web/add",
                headers=headers,
                json=submit_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                
                if result.get("code") == 0:
                    self.bv_id = result.get("data", {}).get("bvid")
                    logger.info(f"Upload submission successful, BV number: {self.bv_id}")
                    return True
                else:
                    self.error_message = f"Upload submission failed: {result.get('message', 'Unknown error')}"
                    logger.error(self.error_message)
                    return False
                    
        except Exception as e:
            self.error_message = f"Upload submission exception: {str(e)}"
            logger.error(self.error_message)
            return False
    
    def get_bv_id(self) -> Optional[str]:
        """Get BV number"""
        return self.bv_id
    
    def get_error_message(self) -> Optional[str]:
        """Get error message"""
        return self.error_message
