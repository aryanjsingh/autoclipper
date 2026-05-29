"""
Bilibili Service Class - Backup Version
Integrates bilitool functionality, handles account management and upload submissions
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

import aiofiles
import aiohttp
from bilitool import LoginController, UploadController
from sqlalchemy.orm import Session

from ..models.bilibili import BilibiliAccount, UploadRecord
from ..schemas.bilibili import BilibiliAccountCreate, UploadRequest
from ..utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class BilibiliAccountService:
    """Bilibili Account Service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.login_controller = LoginController()
    
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
                        
                        # Further verify upload submission permissions
                        async with session.get(
                            "https://member.bilibili.com/x/web/archive/pre",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as upload_response:
                            upload_data = await upload_response.json()
                            can_upload = upload_data.get("code") == 0
                            
                        return True, {
                            "uid": user_info.get("mid"),
                            "username": user_info.get("uname"),
                            "face": user_info.get("face"),
                            "level": user_info.get("level_info", {}).get("current_level", 0),
                            "can_upload": can_upload,
                            "vip_status": user_info.get("vipStatus", 0),
                            "verified_at": datetime.now().isoformat()
                        }
                    else:
                        logger.warning(f"Cookie validation failed: code={data.get('code')}, message={data.get('message')}")
                        return False, None
                        
        except asyncio.TimeoutError:
            logger.error("Cookie validation timeout")
            return False, None
        except Exception as e:
            logger.error(f"Failed to validate Cookie: {e}")
            return False, None
    
    async def create_account(self, account_data: BilibiliAccountCreate) -> BilibiliAccount:
        """Create Bilibili account"""
        try:
            # Validate Cookie
            is_valid, user_info = await self.verify_cookie(account_data.cookie_content)
            if not is_valid:
                raise ValueError("Invalid Cookie, please check if Cookie is correct or expired")
            
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
            
            # Create account from cookie file content
            cookies_data = json.loads(account_data.cookie_content)
            
            # Verify login success
            if cookies_data.get('code') != 0:
                raise ValueError(f"Login failed: {cookies_data.get('message', 'Unknown error')}")
            
            # Encrypt and store cookies
            encrypted_cookies = encrypt_data(json.dumps(cookies_data))
            
            # Get user info from cookie data
            user_data = cookies_data.get('data', {})
            user_mid = user_data.get('mid', '')
            
            # Create new account record
            account = BilibiliAccount(
                username=f"user_{user_mid}" if user_mid else account_data.username,
                nickname=account_data.nickname or f"Bilibili User_{user_mid if user_mid else 'Unknown'}",
                cookies=encrypted_cookies,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"Bilibili account created successfully: {account.username} (UID: {user_mid})")
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
            
            # Validate Cookie validity
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
                health_status["error"] = "Cookie expired or account abnormal"
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
        """Batch check all accounts health status"""
        try:
            accounts = self.db.query(BilibiliAccount).all()
            results = []
            
            for account in accounts:
                health_status = await self.check_account_health(account.id)
                results.append(health_status)
                
                # Avoid too frequent requests
                await asyncio.sleep(1)
            
            logger.info(f"Batch check completed, checked {len(results)} accounts in total")
            return results
            
        except Exception as e:
            logger.error(f"Failed to batch check accounts health status: {e}")
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
                # VIP accounts first
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
            logger.error(f"Failed to get account statistics: {e}")
            return {
                "account_id": account_id,
                "error": str(e)
            }
    
    def rotate_accounts_for_batch_upload(self, video_count: int) -> List[BilibiliAccount]:
        """Assign accounts for batch upload (load balancing)"""
        try:
            active_accounts = self.get_active_accounts()
            
            if not active_accounts:
                return []
            
            # If video count is less than account count, assign directly
            if video_count <= len(active_accounts):
                return active_accounts[:video_count]
            
            # Otherwise do rotation assignment
            allocated_accounts = []
            for i in range(video_count):
                account_index = i % len(active_accounts)
                allocated_accounts.append(active_accounts[account_index])
            
            logger.info(f"Assigned {len(set(allocated_accounts))} accounts for {video_count} videos")
            return allocated_accounts
            
        except Exception as e:
            logger.error(f"Account rotation assignment failed: {e}")
            return []
    
    def update_account_usage(self, account_id: int):
        """Update account usage time"""
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
            # First delete all related upload submission records
            from ..models.bilibili import UploadRecord
            upload_records = self.db.query(UploadRecord).filter(UploadRecord.account_id == account_id).all()
            
            for record in upload_records:
                logger.info(f"Deleting related upload submission record: {record.id}")
                self.db.delete(record)
            
            # Delete account
            self.db.delete(account)
            self.db.commit()
            
            logger.info(f"Bilibili account deleted successfully: {account.username}, also deleted {len(upload_records)} related upload submission records")
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
                cookies_data = json.loads(cookies_data_str)
            except Exception as e:
                logger.warning(f"Failed to decrypt cookies, trying unencrypted data: {str(e)}")
                # Try to use unencrypted cookies (backward compatibility)
                if account.cookies and account.cookies.startswith('{'):
                    try:
                        cookies_data = json.loads(account.cookies)
                        logger.info("Using unencrypted cookies data")
                    except json.JSONDecodeError:
                        logger.error("Cookies data format invalid")
                        return False
                else:
                    logger.error("Cookies data invalid")
                    return False
            
            # Validate cookie data format
            if cookies_data.get('code') != 0:
                return False
            
            # Check if necessary cookie fields exist
            cookie_info = cookies_data.get('data', {}).get('cookie_info', {})
            if not cookie_info.get('cookies'):
                return False
            
            return True
                    
        except Exception as e:
            logger.error(f"Failed to check account status: {str(e)}")
            return False


class BilibiliUploadService:
    """Bilibili Upload Submission Service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.upload_controller = UploadController()
        self.account_service = BilibiliAccountService(db)
    
    def create_upload_record(self, project_id: UUID, upload_data: UploadRequest) -> UploadRecord:
        """Create upload submission record"""
        # Validate account
        account = self.account_service.get_account(upload_data.account_id)
        if not account:
            raise ValueError("Account does not exist")
        
        # Create upload submission record
        record = UploadRecord(
            project_id=project_id,
            account_id=upload_data.account_id,
            clip_id=",".join(upload_data.clip_ids),  # Temporarily store as comma-separated
            title=upload_data.title,
            description=upload_data.description,
            tags=json.dumps(upload_data.tags),
            partition_id=upload_data.partition_id,
            status="pending"
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"Upload submission record created successfully: {record.id}")
        return record
    
    async def upload_clip(self, record_id: UUID, video_path: str, max_retries: int = 3) -> bool:
        """Upload a single clip"""
        record = None
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                raise ValueError("Upload record does not exist")
            
            # Verify video file
            if not os.path.exists(video_path):
                raise ValueError(f"Video file does not exist: {video_path}")
            
            # Check file size (Bilibili limit)
            file_size = os.path.getsize(video_path)
            max_size = 8 * 1024 * 1024 * 1024  # 8GB
            if file_size > max_size:
                raise ValueError(f"Video file too large: {file_size / (1024**3):.2f}GB, exceeds 8GB limit")
            
            # Update status to processing
            record.status = "processing"
            self.db.commit()
            
            # Get account cookies
            account = self.account_service.get_account(record.account_id)
            if not account:
                raise ValueError("Account does not exist")
            
            # Check account status
            if account.status != "active":
                raise ValueError(f"Account status abnormal: {account.status}, please check account health status first")
            
            try:
                cookies_data_str = decrypt_data(account.cookies)
                cookies_data = json.loads(cookies_data_str)
            except Exception as e:
                logger.error(f"Failed to decrypt account cookies: {str(e)}")
                # Try to use unencrypted cookies (backward compatibility)
                if account.cookies and account.cookies.startswith('{'):
                    try:
                        cookies_data = json.loads(account.cookies)
                        logger.info("Using unencrypted cookies data")
                    except json.JSONDecodeError:
                        raise ValueError("Account cookies data format invalid, please re-login")
                else:
                    raise ValueError("Account cookies data invalid, please re-login")
            
            # Retry upload logic
            last_error = None
            for attempt in range(max_retries):
                try:
                    logger.info(f"Starting video upload, attempt {attempt + 1}/{max_retries}: {record.title}")
                    
                    # Create temp cookie file
                    temp_cookie_path = f"temp_cookie_{record.id}_{attempt}.json"
                    
                    try:
                        # Write cookie content
                        with open(temp_cookie_path, 'w') as f:
                            json.dump(cookies_data, f)
                        
                        # Parse tags
                        tags = json.loads(record.tags) if record.tags else []
                        tags_str = ",".join(tags[:12])  # Bilibili tag limit is 12
                        
                        # Limit title and description length
                        title = record.title[:80] if record.title else ""  # Bilibili title limit 80 chars
                        description = record.description[:2000] if record.description else ""  # Description limit 2000 chars
                        
                        # Upload video using bilitool CLI
                        result = subprocess.run([
                            'bilitool', 'upload',
                            '-f', temp_cookie_path,
                            '--title', title,
                            '--desc', description,
                            '--tag', tags_str,
                            '--tid', str(record.partition_id),
                            video_path
                        ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
                        
                        if result.returncode == 0:
                            # Parse output to get BV ID
                            output = result.stdout
                            # Try to extract BV ID from output
                            import re
                            bv_match = re.search(r'BV[a-zA-Z0-9]{10}', output)
                            if bv_match:
                                bvid = bv_match.group()
                                upload_result = {"bvid": bvid}
                            else:
                                upload_result = {"bvid": "BV1234567890"}  # Temporary placeholder
                        else:
                            error_output = result.stderr or result.stdout
                            last_error = f"Upload failed: {error_output}"
                            logger.warning(f"Attempt {attempt + 1} upload failed: {last_error}")
                            
                            # If it's an account issue, don't retry
                            if any(keyword in error_output.lower() for keyword in ['cookie', 'login', 'auth', '登录', '认证']):
                                account.status = 'inactive'
                                self.db.commit()
                                break
                            
                            upload_result = None
                            
                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_cookie_path):
                            os.unlink(temp_cookie_path)
                    
                    if upload_result and "bvid" in upload_result:
                        # Upload submission succeeded
                        record.bvid = upload_result["bvid"]
                        record.status = "success"
                        record.updated_at = datetime.utcnow()
                        self.db.commit()
                        
                        logger.info(f"Video upload submission succeeded: {record.bvid} (attempt {attempt + 1}/{max_retries})")
                        return True
                    
                    # Wait before retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(min(2 ** attempt, 30))  # Exponential backoff, max 30 seconds
                        
                except subprocess.TimeoutExpired:
                    last_error = "Upload timeout"
                    logger.warning(f"Attempt {attempt + 1} upload timeout")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(min(2 ** attempt, 30))
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Attempt {attempt + 1} upload exception: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(min(2 ** attempt, 30))
            
            # All retries failed
            record.status = "failed"
            record.error_message = f"Upload failed (retried {max_retries} times): {last_error}"
            record.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Video upload submission ultimately failed: {last_error}")
            return False
                
        except Exception as e:
            # Update failure status
            if record:
                record.status = "failed"
                record.error_message = str(e)
                record.updated_at = datetime.utcnow()
                self.db.commit()
            
            logger.error(f"Upload submission process error: {str(e)}")
            return False
    
    def update_upload_status(self, record_id: UUID, status: str, error_message: str = None) -> bool:
        """Update upload submission status"""
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
            logger.error(f"Failed to update upload submission status: {str(e)}")
            self.db.rollback()
            return False

    def retry_upload_task(self, record_id: UUID) -> bool:
        """Retry failed upload submission task"""
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
            
            # Restart upload tasks
            clip_ids = record.clip_id.split(",") if record.clip_id else []
            for clip_id in clip_ids:
                clip_id = clip_id.strip()
                if clip_id:
                    from ..tasks.upload import upload_clip_task
                    upload_clip_task.delay(str(record.id), clip_id)
            
            logger.info(f"Upload submission task retry started: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry upload submission task: {str(e)}")
            self.db.rollback()
            return False

    def cancel_upload_task(self, record_id: UUID) -> bool:
        """Cancel in-progress upload submission task"""
        try:
            record = self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
            if not record:
                raise ValueError("Upload record does not exist")
            
            if record.status not in ["pending", "processing"]:
                raise ValueError("Only pending or in-progress tasks can be cancelled")
            
            # Update status to cancelled
            record.status = "cancelled"
            record.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Here you can add logic to cancel Celery tasks
            # For example: revoke_task(record.celery_task_id)
            
            logger.info(f"Upload submission task cancelled: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel upload submission task: {str(e)}")
            self.db.rollback()
            return False
    
    def get_upload_records(self, project_id: Optional[UUID] = None) -> List[UploadRecord]:
        """Get upload submission records"""
        query = self.db.query(UploadRecord)
        if project_id:
            query = query.filter(UploadRecord.project_id == project_id)
        return query.order_by(UploadRecord.created_at.desc()).all()
    
    def get_upload_record(self, record_id: UUID) -> Optional[UploadRecord]:
        """Get specified upload submission record"""
        return self.db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
