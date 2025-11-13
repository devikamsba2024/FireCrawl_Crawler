"""Storage management for scraped content."""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


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
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load metadata about previously scraped pages.
        
        Returns:
            Metadata dictionary
        """
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text())
            except Exception:
                return {"pages": {}, "last_crawl": None}
        return {"pages": {}, "last_crawl": None}
    
    def _save_metadata(self) -> None:
        """Save metadata to file."""
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2))
    
    def _update_page_metadata(self, url: str, filepath: str) -> None:
        """
        Update metadata for a scraped page.
        
        Args:
            url: Page URL
            filepath: Path to saved file
        """
        self.metadata["pages"][url] = {
            "file": filepath,
            "scraped_at": datetime.now().isoformat(),
            "file_size": Path(filepath).stat().st_size if Path(filepath).exists() else 0
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
        
        # Generate filename
        if custom_filename:
            filename = custom_filename if custom_filename.endswith('.md') else f"{custom_filename}.md"
        else:
            filename = self._generate_filename(url, title)
        
        filepath = self._ensure_unique_filename(self.output_dir / filename)
        
        # Create content with metadata header
        content = f"# {title or 'Untitled'}\n\n"
        content += f"**Source:** {url}\n\n"
        content += "---\n\n"
        content += markdown_content
        
        # Save file
        filepath.write_text(content, encoding='utf-8')
        print(f"✓ Saved: {filepath}")
        
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
        
        for i, page in enumerate(pages, 1):
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
            except Exception as e:
                print(f"✗ Error saving page: {str(e)}")
        
        # Create index file
        if create_index and index_entries:
            self._create_index_file(index_entries)
        
        return saved_files
    
    def _create_index_file(self, entries: List[Dict[str, str]]) -> None:
        """
        Create an index file listing all saved pages.
        
        Args:
            entries: List of page entries with title, url, and file
        """
        index_path = self.output_dir / "INDEX.md"
        
        content = "# Crawled Pages Index\n\n"
        content += f"Total pages: {len(entries)}\n\n"
        content += "---\n\n"
        
        for entry in entries:
            content += f"## {entry['title']}\n\n"
            content += f"- **URL:** {entry['url']}\n"
            content += f"- **File:** [{entry['file']}](./{entry['file']})\n\n"
        
        index_path.write_text(content, encoding='utf-8')
        print(f"✓ Created index: {index_path}")

