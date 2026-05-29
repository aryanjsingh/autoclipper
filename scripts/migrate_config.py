#!/usr/bin/env python3
"""
Configuration Migration Script
Migrates from the old scattered configuration system to the new unified configuration system
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.unified_config import UnifiedConfig, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_old_configs():
    """Analyze old configuration files"""
    logger.info("Analyzing old configuration files...")
    
    old_configs = {}
    
    # Check data/settings.json
    settings_file = project_root / "data" / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                old_configs['settings.json'] = json.load(f)
            logger.info(f"Found config file: {settings_file}")
        except Exception as e:
            logger.warning(f"Failed to read config file: {e}")
    
    # Check .env file
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
                old_configs['.env'] = parse_env_file(env_content)
            logger.info(f"Found environment variable file: {env_file}")
        except Exception as e:
            logger.warning(f"Failed to read environment variable file: {e}")
    
    # Check default values in backend/core/config.py
    old_configs['config.py_defaults'] = {
        "database_url": "sqlite:///./data/autoclip.db",
        "redis_url": "redis://localhost:6379/0",
        "api_dashscope_api_key": "",
        "api_model_name": "qwen-plus",
        "processing_chunk_size": 5000,
        "processing_min_score_threshold": 0.7,
        "log_level": "INFO"
    }
    
    return old_configs


def parse_env_file(env_content: str) -> dict:
    """Parse .env file content"""
    env_vars = {}
    for line in env_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip().strip('"\'')
    return env_vars


def migrate_configs(old_configs: dict, dry_run: bool = True):
    """Migrate configuration to the new unified configuration system"""
    logger.info(f"Starting configuration migration (dry_run={dry_run})")
    
    migration_log = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "migrated_settings": {},
        "issues": []
    }
    
    try:
        # Create new config instance
        new_config = UnifiedConfig()
        
        # Migrate settings.json configuration
        if 'settings.json' in old_configs:
            settings = old_configs['settings.json']
            migrated_settings = migrate_settings_json(settings, new_config)
            migration_log['migrated_settings']['settings.json'] = migrated_settings
        
        # Migrate .env file configuration
        if '.env' in old_configs:
            env_vars = old_configs['.env']
            migrated_env = migrate_env_vars(env_vars, new_config)
            migration_log['migrated_settings']['.env'] = migrated_env
        
        # Validate new configuration
        validation_result = new_config.validate_config()
        if not validation_result['valid']:
            migration_log['issues'].extend(validation_result['issues'])
        
        if dry_run:
            logger.info("Migration simulation complete")
            return {
                "success": True,
                "dry_run": True,
                "migration_log": migration_log,
                "new_config_summary": new_config.get_config_summary()
            }
        
        # Actual migration
        if not migration_log['issues']:
            # Backup old configuration
            backup_old_configs(old_configs)
            
            # Save new configuration
            new_config.save_to_file()
            
            logger.info("Configuration migration complete")
            return {
                "success": True,
                "migration_log": migration_log,
                "new_config_summary": new_config.get_config_summary()
            }
        else:
            logger.error("Configuration validation failed, cannot migrate")
            return {
                "success": False,
                "migration_log": migration_log
            }
            
    except Exception as e:
        logger.error(f"Configuration migration failed: {e}")
        migration_log['issues'].append(f"Error during migration: {str(e)}")
        return {
            "success": False,
            "migration_log": migration_log
        }


def migrate_settings_json(settings: dict, new_config: UnifiedConfig) -> dict:
    """Migrate settings.json configuration"""
    migrated = {}
    
    # API configuration
    if 'dashscope_api_key' in settings:
        new_config.api.dashscope_api_key = settings['dashscope_api_key']
        migrated['dashscope_api_key'] = 'migrated'
    
    if 'model_name' in settings:
        new_config.api.model_name = settings['model_name']
        migrated['model_name'] = 'migrated'
    
    # Processing configuration
    if 'chunk_size' in settings:
        new_config.processing.chunk_size = settings['chunk_size']
        migrated['chunk_size'] = 'migrated'
    
    if 'min_score_threshold' in settings:
        new_config.processing.min_score_threshold = settings['min_score_threshold']
        migrated['min_score_threshold'] = 'migrated'
    
    if 'max_clips_per_collection' in settings:
        new_config.processing.max_clips_per_collection = settings['max_clips_per_collection']
        migrated['max_clips_per_collection'] = 'migrated'
    
    # Speech recognition configuration
    if 'speech_recognition_method' in settings:
        new_config.speech_recognition.method = settings['speech_recognition_method']
        migrated['speech_recognition_method'] = 'migrated'
    
    if 'speech_recognition_language' in settings:
        new_config.speech_recognition.language = settings['speech_recognition_language']
        migrated['speech_recognition_language'] = 'migrated'
    
    # Bilibili configuration
    if 'bilibili_auto_upload' in settings:
        new_config.bilibili.auto_upload = settings['bilibili_auto_upload']
        migrated['bilibili_auto_upload'] = 'migrated'
    
    if 'bilibili_default_tid' in settings:
        new_config.bilibili.default_tid = settings['bilibili_default_tid']
        migrated['bilibili_default_tid'] = 'migrated'
    
    return migrated


def migrate_env_vars(env_vars: dict, new_config: UnifiedConfig) -> dict:
    """Migrate environment variables"""
    migrated = {}
    
    # Database configuration
    if 'DATABASE_URL' in env_vars:
        new_config.database.url = env_vars['DATABASE_URL']
        migrated['DATABASE_URL'] = 'migrated'
    
    # Redis configuration
    if 'REDIS_URL' in env_vars:
        new_config.redis.url = env_vars['REDIS_URL']
        migrated['REDIS_URL'] = 'migrated'
    
    # API configuration
    if 'DASHSCOPE_API_KEY' in env_vars:
        new_config.api.dashscope_api_key = env_vars['DASHSCOPE_API_KEY']
        migrated['DASHSCOPE_API_KEY'] = 'migrated'
    
    if 'API_MODEL_NAME' in env_vars:
        new_config.api.model_name = env_vars['API_MODEL_NAME']
        migrated['API_MODEL_NAME'] = 'migrated'
    
    # Processing configuration
    if 'PROCESSING_CHUNK_SIZE' in env_vars:
        new_config.processing.chunk_size = int(env_vars['PROCESSING_CHUNK_SIZE'])
        migrated['PROCESSING_CHUNK_SIZE'] = 'migrated'
    
    if 'PROCESSING_MIN_SCORE_THRESHOLD' in env_vars:
        new_config.processing.min_score_threshold = float(env_vars['PROCESSING_MIN_SCORE_THRESHOLD'])
        migrated['PROCESSING_MIN_SCORE_THRESHOLD'] = 'migrated'
    
    # Logging configuration
    if 'LOG_LEVEL' in env_vars:
        new_config.logging.level = env_vars['LOG_LEVEL']
        migrated['LOG_LEVEL'] = 'migrated'
    
    if 'LOG_FILE' in env_vars:
        new_config.logging.file = env_vars['LOG_FILE']
        migrated['LOG_FILE'] = 'migrated'
    
    return migrated


def backup_old_configs(old_configs: dict):
    """Backup old configuration files"""
    backup_dir = project_root / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(exist_ok=True)
    
    logger.info(f"Creating config backup: {backup_dir}")
    
    # Backup settings.json
    if 'settings.json' in old_configs:
        settings_file = project_root / "data" / "settings.json"
        if settings_file.exists():
            backup_file = backup_dir / "settings.json"
            with open(settings_file, 'r', encoding='utf-8') as src, \
                 open(backup_file, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # Backup .env file
    env_file = project_root / ".env"
    if env_file.exists():
        backup_file = backup_dir / ".env"
        with open(env_file, 'r', encoding='utf-8') as src, \
             open(backup_file, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    # Save migration log
    migration_log_file = backup_dir / "migration_log.json"
    with open(migration_log_file, 'w', encoding='utf-8') as f:
        json.dump(old_configs, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Config backup complete: {backup_dir}")


def display_config_comparison(old_configs: dict, new_config_summary: dict):
    """Display configuration comparison"""
    print("\n" + "=" * 80)
    print("Configuration Comparison")
    print("=" * 80)
    
    print("\nAPI Configuration:")
    print(f"  Model name: {new_config_summary['api']['model_name']}")
    print(f"  Max tokens: {new_config_summary['api']['max_tokens']}")
    print(f"  Timeout: {new_config_summary['api']['timeout']}s")
    print(f"  API key: {'Configured' if new_config_summary['api']['has_api_key'] else 'Not configured'}")
    
    print("\nProcessing Configuration:")
    print(f"  Chunk size: {new_config_summary['processing']['chunk_size']}")
    print(f"  Min score threshold: {new_config_summary['processing']['min_score_threshold']}")
    print(f"  Max clips per collection: {new_config_summary['processing']['max_clips_per_collection']}")
    
    print("\nDatabase Configuration:")
    print(f"  Database URL: {new_config_summary['database']['url']}")
    print(f"  Redis URL: {new_config_summary['redis']['url']}")
    
    print("\nPath Configuration:")
    print(f"  Data directory: {new_config_summary['paths']['data_dir']}")
    print(f"  Uploads directory: {new_config_summary['paths']['uploads_dir']}")
    print(f"  Output directory: {new_config_summary['paths']['output_dir']}")
    
    print("\nLogging Configuration:")
    print(f"  Log level: {new_config_summary['logging']['level']}")
    print(f"  Log file: {new_config_summary['logging']['file']}")


def main():
    """Main function"""
    logger.info("Starting configuration migration...")
    
    # Analyze old configuration
    old_configs = analyze_old_configs()
    
    if not old_configs:
        logger.info("No configuration files found to migrate")
        return
    
    print("\nDiscovered configuration files:")
    for config_name in old_configs.keys():
        print(f"  * {config_name}")
    
    # Ask whether to continue
    print("\n" + "=" * 60)
    print("Migration Options:")
    print("1. Dry run - Preview migration effects without executing")
    print("2. Execute migration - Actually migrate configuration and backup old files")
    print("3. Exit")
    
    while True:
        choice = input("\nSelect operation (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice, please enter 1, 2, or 3")
    
    if choice == '3':
        logger.info("User cancelled migration")
        return
    
    dry_run = (choice == '1')
    
    # Execute migration
    result = migrate_configs(old_configs, dry_run)
    
    if result['success']:
        if dry_run:
            print("\nMigration Simulation Results:")
        else:
            print("\nMigration complete:")
        
        # Display configuration comparison
        if 'new_config_summary' in result:
            display_config_comparison(old_configs, result['new_config_summary'])
        
        # Display migration log
        migration_log = result['migration_log']
        if migration_log['migrated_settings']:
            print("\nMigration Statistics:")
            for config_name, migrated in migration_log['migrated_settings'].items():
                print(f"  {config_name}: {len(migrated)} settings")
        
        # Display issues
        if migration_log['issues']:
            print("\nIssues found:")
            for issue in migration_log['issues']:
                print(f"  * {issue}")
        
        if not dry_run:
            print(f"\nBackup location: config_backup_*")
            print("Recommendations:")
            print("1. Test system functionality")
            print("2. Delete backup files after confirming everything works")
            print("3. Check the new configuration file format")
    
    else:
        print("\nMigration failed:")
        migration_log = result['migration_log']
        if migration_log['issues']:
            for issue in migration_log['issues']:
                print(f"  * {issue}")
    
    logger.info("Configuration migration complete!")


if __name__ == "__main__":
    main()
