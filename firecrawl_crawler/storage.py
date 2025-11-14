"""Storage management for scraped content."""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from .logger import get_logger
from .exceptions import StorageError

logger = get_logger(__name__)


class MarkdownStorage:
    """Handle saving scraped content as markdown files."""
    
    def __init__(self, output_dir: str = "./output"):
        """
        Initialize storage.
        
        Args:
            output_dir: Directory to save markdown files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.output_dir / ".scrape_metadata.json"
        self.metadata = self._load_metadata()
        logger.debug(f"Initialized MarkdownStorage: {self.output_dir}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load metadata about previously scraped pages.
        
        Returns:
            Metadata dictionary
        """
        if self.metadata_file.exists():
            try:
                content = self.metadata_file.read_text()
                metadata = json.loads(content)
                logger.debug(f"Loaded metadata: {len(metadata.get('pages', {}))} pages")
                return metadata
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted metadata file, starting fresh: {e}")
                print(f"⚠️  Warning: Corrupted metadata file, starting fresh. Error: {e}")
                return {"pages": {}, "last_crawl": None}
            except Exception as e:
                logger.warning(f"Cannot read metadata file: {e}")
                print(f"⚠️  Warning: Cannot read metadata file: {e}")
                return {"pages": {}, "last_crawl": None}
        logger.debug("No existing metadata file, starting fresh")
        return {"pages": {}, "last_crawl": None}
    
    def _save_metadata(self) -> None:
        """Save metadata to file."""
        try:
            self.metadata_file.write_text(json.dumps(self.metadata, indent=2))
            logger.debug(f"Saved metadata: {len(self.metadata.get('pages', {}))} pages")
        except (IOError, OSError) as e:
            logger.error(f"Failed to save metadata: {e}")
            raise StorageError(f"Cannot save metadata to {self.metadata_file}: {e}")
    
    def _update_page_metadata(self, url: str, filepath: str) -> None:
        """
        Update metadata for a scraped page.
        
        Args:
            url: Page URL
            filepath: Path to saved file (can be str or Path)
        """
        filepath_obj = Path(filepath)
        
        # Store path relative to output_dir for portability
        try:
            relative_path = filepath_obj.relative_to(self.output_dir)
            stored_path = str(relative_path)
        except ValueError:
            # If not relative to output_dir, store as-is but try to make relative
            if filepath_obj.is_absolute():
                try:
                    stored_path = str(filepath_obj.relative_to(Path.cwd()))
                except ValueError:
                    stored_path = str(filepath_obj)
            else:
                stored_path = str(filepath_obj)
        
        self.metadata["pages"][url] = {
            "file": stored_path,
            "scraped_at": datetime.now().isoformat(),
            "file_size": filepath_obj.stat().st_size if filepath_obj.exists() else 0
        }
        self.metadata["last_crawl"] = datetime.now().isoformat()
        self._save_metadata()
    
    def get_scraped_urls(self) -> List[str]:
        """
        Get list of previously scraped URLs.
        
        Returns:
            List of URLs
        """
        return list(self.metadata.get("pages", {}).keys())
    
    def get_page_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a specific page.
        
        Args:
            url: Page URL
            
        Returns:
            Page metadata or None
        """
        return self.metadata.get("pages", {}).get(url)
    
    def _sanitize_filename(self, text: str) -> str:
        """
        Convert text to safe filename.
        
        Args:
            text: Input text
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        text = re.sub(r'[<>:"/\\|?*]', '-', text)
        # Remove leading/trailing spaces and dots
        text = text.strip('. ')
        # Limit length
        text = text[:200]
        # Replace multiple spaces/dashes with single dash
        text = re.sub(r'[-\s]+', '-', text)
        return text or "untitled"
    
    def _generate_filename(self, url: str, title: Optional[str] = None) -> str:
        """
        Generate filename from URL and title.
        
        Args:
            url: Source URL
            title: Page title (optional)
            
        Returns:
            Generated filename
        """
        if title:
            base_name = self._sanitize_filename(title)
        else:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                base_name = self._sanitize_filename(path_parts[-1])
            else:
                base_name = self._sanitize_filename(parsed.netloc)
        
        # Ensure .md extension
        if not base_name.endswith('.md'):
            base_name += '.md'
        
        return base_name
    
    def _ensure_unique_filename(self, filepath: Path) -> Path:
        """
        Ensure filename is unique by adding counter if needed.
        
        Args:
            filepath: Proposed filepath
            
        Returns:
            Unique filepath
        """
        if not filepath.exists():
            return filepath
        
        base = filepath.stem
        ext = filepath.suffix
        counter = 1
        
        while filepath.exists():
            filepath = filepath.parent / f"{base}_{counter}{ext}"
            counter += 1
        
        return filepath
    
    def save_single_page(
        self,
        data: Dict[str, Any],
        custom_filename: Optional[str] = None
    ) -> str:
        """
        Save a single scraped page.
        
        Args:
            data: Scraped data from Firecrawl
            custom_filename: Optional custom filename
            
        Returns:
            Path to saved file
        """
        # Extract data
        url = data.get("metadata", {}).get("url") or data.get("url", "unknown")
        title = data.get("metadata", {}).get("title")
        markdown_content = data.get("markdown", "")
        
        # Check if this URL was already scraped (for updates)
        existing_file = None
        if url in self.metadata.get("pages", {}):
            existing_file_path = self.metadata["pages"][url].get("file")
            if existing_file_path:
                # Resolve path - could be absolute, relative to cwd, or relative to output_dir
                existing_path = Path(existing_file_path)
                filepath = None
                
                if existing_path.is_absolute():
                    # Absolute path
                    if existing_path.exists():
                        filepath = existing_path
                else:
                    # Relative path - try multiple locations
                    # 1. Try relative to output_dir (most common case)
                    candidate = self.output_dir / existing_path
                    if candidate.exists():
                        filepath = candidate
                    else:
                        # 2. Try relative to current working directory
                        candidate = Path.cwd() / existing_path
                        if candidate.exists():
                            filepath = candidate
                        else:
                            # 3. Try just the filename in output_dir
                            filename_only = existing_path.name
                            candidate = self.output_dir / filename_only
                            if candidate.exists():
                                filepath = candidate
                            else:
                                # 4. If path contains "output/", try resolving from cwd
                                if "output" in str(existing_path):
                                    candidate = Path.cwd() / existing_path
                                    if candidate.exists():
                                        filepath = candidate
                
                if filepath and filepath.exists():
                    logger.debug(f"Updating existing file for {url}: {filepath}")
                    existing_file = str(filepath)
                else:
                    logger.debug(f"Existing file path not found: {existing_file_path}, will create new file")
                    existing_file = None
            else:
                existing_file = None
        
        # Generate new filename if no existing file
        if not existing_file:
            if custom_filename:
                filename = custom_filename if custom_filename.endswith('.md') else f"{custom_filename}.md"
            else:
                filename = self._generate_filename(url, title)
            
            filepath = self.output_dir / filename
            # Only ensure unique filename for truly new pages
            if filepath.exists() and url not in self.metadata.get("pages", {}):
                filepath = self._ensure_unique_filename(filepath)
        
        # Create content with metadata header
        content = f"# {title or 'Untitled'}\n\n"
        content += f"**Source:** {url}\n\n"
        content += "---\n\n"
        content += markdown_content
        
        # Save file
        try:
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Saved: {url} -> {filepath.name}")
            logger.debug(f"File size: {filepath.stat().st_size} bytes")
            print(f"✓ Saved: {filepath}")
        except (IOError, OSError) as e:
            logger.error(f"Cannot write file {filepath}: {e}")
            raise StorageError(f"Cannot write file {filepath}: {e}")
        
        # Update metadata
        self._update_page_metadata(url, str(filepath))
        
        return str(filepath)
    
    def save_multiple_pages(
        self,
        pages: List[Dict[str, Any]],
        create_index: bool = True
    ) -> List[str]:
        """
        Save multiple scraped pages.
        
        Args:
            pages: List of scraped pages from Firecrawl
            create_index: Whether to create an index file
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        index_entries = []
        logger.info(f"Saving {len(pages)} pages")
        
        for i, page in enumerate(pages, 1):
            url = page.get("metadata", {}).get("url") or page.get("url", "unknown")
            print(f"Saving page {i}/{len(pages)}...")
            try:
                filepath = self.save_single_page(page)
                saved_files.append(filepath)
                
                # Collect info for index
                title = page.get("metadata", {}).get("title", "Untitled")
                url = page.get("metadata", {}).get("url") or page.get("url", "")
                index_entries.append({
                    "title": title,
                    "url": url,
                    "file": Path(filepath).name
                })
            except StorageError as e:
                logger.error(f"Storage error saving {url}: {e}")
                print(f"✗ Storage error saving page: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error saving {url}: {e}")
                print(f"✗ Unexpected error saving page: {str(e)}")
        
        # Create index file
        if create_index and index_entries:
            self._create_index_file(index_entries)
        
        logger.info(f"Saved {len(saved_files)} pages successfully")
        return saved_files
    
    def _create_index_file(self, entries: List[Dict[str, str]]) -> None:
        """
        Create an index file listing all saved pages.
        
        Args:
            entries: List of page entries with title, url, and file
        """
        index_path = self.output_dir / "INDEX.md"
        logger.debug(f"Creating index file with {len(entries)} entries")
        
        content = "# Crawled Pages Index\n\n"
        content += f"Total pages: {len(entries)}\n\n"
        content += "---\n\n"
        
        for entry in entries:
            content += f"## {entry['title']}\n\n"
            content += f"- **URL:** {entry['url']}\n"
            content += f"- **File:** [{entry['file']}](./{entry['file']})\n\n"
        
        index_path.write_text(content, encoding='utf-8')
        logger.info(f"Created index file: {index_path}")
        print(f"✓ Created index: {index_path}")

