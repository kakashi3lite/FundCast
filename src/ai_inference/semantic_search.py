"""Semantic search implementation for codebase context with Red Team security."""

import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import asyncio
from dataclasses import dataclass
import logging

import numpy as np
from sentence_transformers import SentenceTransformer
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..api.config import settings
from ..api.exceptions import InferenceError, ValidationError

logger = structlog.get_logger(__name__)

# Security: Whitelist of allowed file extensions to prevent code injection
SAFE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.txt', '.json', 
    '.yaml', '.yml', '.toml', '.cfg', '.ini', '.sql'
}

# Security: Blacklist patterns to prevent information leakage
SECURITY_BLACKLIST_PATTERNS = [
    r'password\s*[=:]\s*["\'][^"\']+["\']',
    r'secret\s*[=:]\s*["\'][^"\']+["\']',
    r'api_?key\s*[=:]\s*["\'][^"\']+["\']',
    r'token\s*[=:]\s*["\'][^"\']+["\']',
    r'private_?key',
    r'-----BEGIN.*PRIVATE KEY-----',
    r'ssh-rsa\s+[A-Za-z0-9+/=]+',
    r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IP addresses
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
]

# Security: Maximum file size to prevent resource exhaustion
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MAX_SEARCH_RESULTS = 50
MAX_CONTEXT_LENGTH = 10000


@dataclass
class SearchResult:
    """Search result with security metadata."""
    file_path: str
    content: str
    similarity_score: float
    last_modified: datetime
    file_hash: str
    is_safe: bool
    redacted_content: Optional[str] = None


class SecurityFilter:
    """Red Team security filter for code content."""
    
    def __init__(self):
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in SECURITY_BLACKLIST_PATTERNS
        ]
    
    def is_safe_file(self, file_path: Path) -> bool:
        """Check if file is safe to process."""
        # Check file extension
        if file_path.suffix.lower() not in SAFE_EXTENSIONS:
            logger.warning("Unsafe file extension", file_path=str(file_path))
            return False
        
        # Check file size
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                logger.warning("File too large", file_path=str(file_path), size=file_path.stat().st_size)
                return False
        except OSError:
            return False
        
        # Check for hidden files or system files
        if any(part.startswith('.') and part not in {'.env.example', '.gitignore'} 
               for part in file_path.parts):
            return False
        
        return True
    
    def sanitize_content(self, content: str) -> Tuple[str, bool]:
        """Sanitize content by removing sensitive information."""
        is_safe = True
        sanitized = content
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(content)
            if matches:
                is_safe = False
                # Redact sensitive content
                sanitized = pattern.sub('[REDACTED]', sanitized)
                logger.warning("Sensitive content detected and redacted", pattern=pattern.pattern)
        
        return sanitized, is_safe
    
    def validate_search_query(self, query: str) -> bool:
        """Validate search query for potential injection attacks."""
        # Prevent SQL injection attempts
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 'EXEC']
        if any(keyword.lower() in query.lower() for keyword in sql_keywords):
            logger.warning("Potential SQL injection in search query", query=query)
            return False
        
        # Prevent path traversal
        if '../' in query or '..\\' in query:
            logger.warning("Path traversal attempt in search query", query=query)
            return False
        
        # Check query length
        if len(query) > 1000:
            logger.warning("Search query too long", query_length=len(query))
            return False
        
        return True


class SemanticSearch:
    """Semantic search with comprehensive security controls."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.security_filter = SecurityFilter()
        self.model = None
        self.embeddings_cache: Dict[str, np.ndarray] = {}
        self.file_cache: Dict[str, SearchResult] = {}
        self.last_scan_time = None
        self.rate_limiter = {}  # Simple rate limiting
        
        # Security: Initialize with minimal privileges
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.model.max_seq_length = 512  # Prevent excessive memory usage
        except Exception as e:
            logger.error("Failed to initialize semantic search model", error=str(e))
            raise InferenceError("Semantic search initialization failed", "sentence_transformers")
    
    def _rate_limit_check(self, client_id: str) -> bool:
        """Simple rate limiting to prevent abuse."""
        now = time.time()
        if client_id not in self.rate_limiter:
            self.rate_limiter[client_id] = []
        
        # Clean old entries
        self.rate_limiter[client_id] = [
            timestamp for timestamp in self.rate_limiter[client_id]
            if now - timestamp < 60  # 1 minute window
        ]
        
        # Check rate limit (10 searches per minute)
        if len(self.rate_limiter[client_id]) >= 10:
            return False
        
        self.rate_limiter[client_id].append(now)
        return True
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate secure hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def _scan_project_files(self) -> List[Path]:
        """Securely scan project files with safety checks."""
        safe_files = []
        
        # Security: Limit scanning to project directory
        try:
            resolved_root = self.project_root.resolve()
        except Exception:
            logger.error("Invalid project root", project_root=str(self.project_root))
            return []
        
        for file_path in resolved_root.rglob('*'):
            try:
                # Security checks
                if not file_path.is_file():
                    continue
                
                # Prevent directory traversal
                if not str(file_path.resolve()).startswith(str(resolved_root)):
                    logger.warning("Path traversal attempt detected", file_path=str(file_path))
                    continue
                
                if self.security_filter.is_safe_file(file_path):
                    safe_files.append(file_path)
                
                # Prevent resource exhaustion
                if len(safe_files) > 10000:
                    logger.warning("Too many files found, limiting scan")
                    break
                    
            except Exception as e:
                logger.warning("Error processing file", file_path=str(file_path), error=str(e))
                continue
        
        logger.info("Project scan completed", file_count=len(safe_files))
        return safe_files
    
    def _extract_file_content(self, file_path: Path) -> Optional[SearchResult]:
        """Safely extract and sanitize file content."""
        try:
            # Check file modification time for caching
            file_hash = self._calculate_file_hash(file_path)
            cache_key = str(file_path)
            
            if cache_key in self.file_cache:
                cached_result = self.file_cache[cache_key]
                if cached_result.file_hash == file_hash:
                    return cached_result
            
            # Read file content safely
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Security: Sanitize content
            sanitized_content, is_safe = self.security_filter.sanitize_content(content)
            
            # Limit content length to prevent memory issues
            if len(sanitized_content) > MAX_CONTEXT_LENGTH:
                sanitized_content = sanitized_content[:MAX_CONTEXT_LENGTH] + "... [TRUNCATED]"
            
            result = SearchResult(
                file_path=str(file_path.relative_to(self.project_root)),
                content=sanitized_content,
                similarity_score=0.0,
                last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                file_hash=file_hash,
                is_safe=is_safe,
                redacted_content=sanitized_content if not is_safe else None
            )
            
            # Cache result
            self.file_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning("Failed to extract file content", file_path=str(file_path), error=str(e))
            return None
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings with security controls."""
        try:
            # Security: Validate input
            if not texts or len(texts) > 1000:
                raise ValidationError("Invalid text input for embeddings")
            
            # Truncate texts to prevent resource exhaustion
            truncated_texts = [
                text[:512] if len(text) > 512 else text 
                for text in texts
            ]
            
            embeddings = self.model.encode(
                truncated_texts,
                batch_size=32,  # Limit batch size
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            return embeddings
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise InferenceError("Failed to generate embeddings", "sentence_transformers")
    
    async def search_context(
        self, 
        query: str, 
        client_id: str = "default",
        max_results: int = 10
    ) -> List[SearchResult]:
        """Perform semantic search with comprehensive security."""
        
        # Security: Rate limiting
        if not self._rate_limit_check(client_id):
            raise ValidationError("Rate limit exceeded for semantic search")
        
        # Security: Validate query
        if not self.security_filter.validate_search_query(query):
            raise ValidationError("Invalid search query")
        
        # Limit results
        max_results = min(max_results, MAX_SEARCH_RESULTS)
        
        try:
            # Scan project files if needed
            if self.last_scan_time is None or (
                datetime.now() - self.last_scan_time > timedelta(minutes=5)
            ):
                await self._refresh_file_index()
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search through cached files
            results = []
            for file_result in self.file_cache.values():
                if not file_result.is_safe:
                    continue  # Skip files with sensitive content
                
                # Generate embedding for file content if not cached
                cache_key = f"embedding_{file_result.file_hash}"
                if cache_key not in self.embeddings_cache:
                    content_embedding = self._generate_embeddings([file_result.content])[0]
                    self.embeddings_cache[cache_key] = content_embedding
                else:
                    content_embedding = self.embeddings_cache[cache_key]
                
                # Calculate similarity
                similarity = np.dot(query_embedding, content_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding)
                )
                
                file_result.similarity_score = float(similarity)
                results.append(file_result)
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(
                "Semantic search completed",
                query=query[:100],  # Log truncated query
                client_id=client_id,
                result_count=len(results[:max_results])
            )
            
            return results[:max_results]
            
        except Exception as e:
            logger.error("Semantic search failed", error=str(e), query=query[:100])
            raise InferenceError("Semantic search operation failed")
    
    async def _refresh_file_index(self):
        """Refresh the file index with security controls."""
        try:
            logger.info("Refreshing semantic search index")
            
            files = self._scan_project_files()
            processed_count = 0
            
            for file_path in files:
                result = self._extract_file_content(file_path)
                if result:
                    processed_count += 1
                
                # Prevent resource exhaustion
                if processed_count > 1000:
                    logger.warning("File processing limit reached")
                    break
            
            self.last_scan_time = datetime.now()
            logger.info("Index refresh completed", processed_files=processed_count)
            
        except Exception as e:
            logger.error("Index refresh failed", error=str(e))
            raise InferenceError("Failed to refresh search index")
    
    async def get_file_context(self, file_path: str) -> Optional[SearchResult]:
        """Get context for a specific file with security validation."""
        
        # Security: Validate file path
        if '../' in file_path or '..\\' in file_path:
            logger.warning("Path traversal attempt", file_path=file_path)
            return None
        
        try:
            full_path = self.project_root / file_path
            
            # Security: Ensure path is within project root
            if not str(full_path.resolve()).startswith(str(self.project_root.resolve())):
                logger.warning("File access outside project root", file_path=file_path)
                return None
            
            if self.security_filter.is_safe_file(full_path):
                return self._extract_file_content(full_path)
            
        except Exception as e:
            logger.warning("File context retrieval failed", file_path=file_path, error=str(e))
        
        return None


# Global semantic search instance with lazy initialization
_semantic_search: Optional[SemanticSearch] = None


async def get_semantic_search() -> SemanticSearch:
    """Get or create semantic search instance."""
    global _semantic_search
    
    if _semantic_search is None:
        _semantic_search = SemanticSearch()
    
    return _semantic_search


async def search_codebase_context(
    query: str, 
    client_id: str = "default",
    max_results: int = 10
) -> List[SearchResult]:
    """High-level function for secure semantic search."""
    search_engine = await get_semantic_search()
    return await search_engine.search_context(query, client_id, max_results)