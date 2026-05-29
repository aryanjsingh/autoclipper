#!/usr/bin/env python3
"""Translate Chinese text in markdown files with aggressive rate limiting."""

import os
import re
import time
import sys
from pathlib import Path
from deep_translator import GoogleTranslator

def contains_chinese(text):
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def translate_with_retry(translator, text, max_retries=5):
    """Translate text with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            result = translator.translate(text)
            if result:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2  # 2, 4, 8, 16 seconds
                print(f"    Retry {attempt+1} after {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                raise
    return None

def translate_file(filepath, translator):
    """Translate a markdown file."""
    print(f"\nProcessing: {filepath.name}", flush=True)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not contains_chinese(content):
        print(f"  No Chinese text found, skipping", flush=True)
        return 0
    
    lines = content.split('\n')
    translated_lines = []
    in_code_block = False
    translated_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            translated_lines.append(line)
            continue
        
        # Skip code blocks and lines without Chinese
        if in_code_block or not contains_chinese(line):
            translated_lines.append(line)
            continue
        
        # Preserve leading whitespace
        leading_space = len(line) - len(line.lstrip())
        indent = line[:leading_space]
        content_part = line[leading_space:]
        
        # Preserve markdown headers
        header_match = re.match(r'^(#{1,6}\s*)', content_part)
        header_prefix = header_match.group(1) if header_match else ''
        if header_prefix:
            content_part = content_part[len(header_prefix):]
        
        # Preserve list markers
        list_match = re.match(r'^(\s*[-*+]\s*|\s*\d+\.\s*)', content_part)
        list_prefix = list_match.group(1) if list_match else ''
        if list_prefix:
            content_part = content_part[len(list_prefix):]
        
        # Preserve blockquote markers
        quote_match = re.match(r'^(>\s*)', content_part)
        quote_prefix = quote_match.group(1) if quote_match else ''
        if quote_prefix:
            content_part = content_part[len(quote_prefix):]
        
        # Skip if no Chinese after removing prefixes
        if not contains_chinese(content_part):
            translated_lines.append(line)
            continue
        
        try:
            # Translate with retry
            translated = translate_with_retry(translator, content_part)
            if translated:
                new_line = indent + header_prefix + list_prefix + quote_prefix + translated
                translated_lines.append(new_line)
                translated_count += 1
            else:
                translated_lines.append(line)
        except Exception as e:
            print(f"  Warning: Line {i+1} failed: {str(e)[:50]}", flush=True)
            translated_lines.append(line)
        
        # Aggressive rate limiting
        time.sleep(0.5)  # 500ms between each translation
        if translated_count % 3 == 0 and translated_count > 0:
            time.sleep(1.0)  # Extra delay every 3 translations
            print(f"  Translated {translated_count} lines...", flush=True)
    
    # Write translated content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(translated_lines))
    
    print(f"  Completed: {translated_count} lines translated", flush=True)
    return translated_count

def main():
    docs_dir = Path(__file__).parent
    
    # Initialize translator
    translator = GoogleTranslator(source='zh-CN', target='en')
    
    # Get files that still need translation
    files_to_translate = []
    for filepath in sorted(docs_dir.glob('*.md')):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if contains_chinese(content):
            files_to_translate.append(filepath)
    
    print(f"Files needing translation: {len(files_to_translate)}", flush=True)
    
    # Translate each file
    for i, filepath in enumerate(files_to_translate):
        print(f"\n[{i+1}/{len(files_to_translate)}]", end='', flush=True)
        translate_file(filepath, translator)
        time.sleep(1.0)  # 1 second delay between files
    
    print(f"\n{'='*60}")
    print("Translation complete!", flush=True)

if __name__ == '__main__':
    main()
