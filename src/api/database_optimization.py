"""Advanced database optimization with connection pooling and query caching."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

import structlog
from sqlalchemy import text, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.sql import ClauseElement

from .config import settings
from .cache import cache, CacheKey, get_cache
from .exceptions import DatabaseError

logger = structlog.get_logger(__name__)


@dataclass
class QueryStats:
    """Query execution statistics."""
    query_hash: str
    execution_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    max_duration: float = 0.0
    min_duration: float = float('inf')
    last_executed: Optional[datetime] = None
    
    def add_execution(self, duration: float):
        """Add execution statistics."""
        self.execution_count += 1
        self.total_duration += duration
        self.avg_duration = self.total_duration / self.execution_count
        self.max_duration = max(self.max_duration, duration)
        self.min_duration = min(self.min_duration, duration)
        self.last_executed = datetime.now()


class QueryOptimizer:
    """Query optimization and monitoring."""
    
    def __init__(self):
        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_query_threshold = 1.0  # 1 second
        self.query_cache_ttl = 300  # 5 minutes
    
    def get_query_hash(self, query: Union[str, ClauseElement]) -> str:
        """Generate consistent hash for query."""
        if isinstance(query, str):
            query_text = query
        else:
            query_text = str(query.compile(compile_kwargs={"literal_binds": True}))
        
        import hashlib
        return hashlib.md5(query_text.encode()).hexdigest()
    
    def record_query_execution(self, query: Union[str, ClauseElement], duration: float):
        """Record query execution for monitoring."""
        query_hash = self.get_query_hash(query)
        
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = QueryStats(query_hash=query_hash)
        
        self.query_stats[query_hash].add_execution(duration)
        
        # Log slow queries
        if duration > self.slow_query_threshold:
            logger.warning(
                "Slow query detected",
                query_hash=query_hash,
                duration=duration,
                query_preview=str(query)[:200]
            )
    
    def get_query_recommendations(self) -> List[Dict[str, Any]]:
        """Get query optimization recommendations."""
        recommendations = []
        
        for stats in self.query_stats.values():
            if stats.execution_count > 10 and stats.avg_duration > 0.5:
                recommendations.append({
                    "query_hash": stats.query_hash,
                    "issue": "frequent_slow_query",
                    "description": f"Query executed {stats.execution_count} times with avg duration {stats.avg_duration:.3f}s",
                    "suggestion": "Consider adding indexes or caching this query"
                })
            
            if stats.execution_count > 100:
                recommendations.append({
                    "query_hash": stats.query_hash,
                    "issue": "high_frequency_query",
                    "description": f"Query executed {stats.execution_count} times",
                    "suggestion": "Consider caching this query result"
                })
        
        return recommendations


class ConnectionPoolManager:
    """Advanced connection pool management."""
    
    def __init__(self):
        self.engines: Dict[str, AsyncEngine] = {}
        self.query_optimizer = QueryOptimizer()
    
    def create_optimized_engine(
        self,
        database_url: str,
        pool_name: str = "default",
        read_only: bool = False
    ) -> AsyncEngine:
        """Create optimized database engine."""
        
        # Determine pool settings based on usage
        if read_only:
            pool_size = 20
            max_overflow = 5
            pool_recycle = 3600  # 1 hour for read-only
        else:
            pool_size = settings.DATABASE_POOL_SIZE
            max_overflow = settings.DATABASE_MAX_OVERFLOW
            pool_recycle = 300  # 5 minutes for write connections
        
        engine = create_async_engine(
            database_url,
            # Connection pool settings
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            pool_timeout=30,
            
            # Query execution settings
            echo=settings.DEBUG,
            echo_pool=settings.DEBUG,
            
            # Performance optimizations
            connect_args={
                "server_settings": {
                    "application_name": f"fundcast_{pool_name}",
                    "jit": "off",  # Disable JIT for faster startup
                    "statement_timeout": "30s",
                    "idle_in_transaction_session_timeout": "5min",
                }
            }
        )
        
        # Add query monitoring
        self._setup_query_monitoring(engine, pool_name)
        
        self.engines[pool_name] = engine
        return engine
    
    def _setup_query_monitoring(self, engine: AsyncEngine, pool_name: str):
        """Setup query execution monitoring."""
        
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                self.query_optimizer.record_query_execution(statement, duration)
    
    def get_engine(self, pool_name: str = "default") -> AsyncEngine:
        """Get engine by pool name."""
        if pool_name not in self.engines:
            raise DatabaseError(f"Database pool '{pool_name}' not found")
        return self.engines[pool_name]
    
    async def close_all_engines(self):
        """Close all database engines."""
        for engine in self.engines.values():
            await engine.dispose()
        self.engines.clear()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {}
        for name, engine in self.engines.items():
            pool = engine.pool
            stats[name] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
        return stats


# Global connection pool manager
pool_manager = ConnectionPoolManager()


class QueryCache:
    """Intelligent query result caching."""
    
    def __init__(self):
        self.cache_key = CacheKey("db_query")
        self.default_ttl = 300  # 5 minutes
        
        # Tables that should not be cached (frequently changing data)
        self.no_cache_tables = {
            'market_positions',  # Real-time market data
            'audit_logs',        # Always fresh
            'rate_limits',       # Rate limiting state
        }
        
        # Tables with longer cache TTL
        self.long_cache_tables = {
            'users': 1800,      # 30 minutes
            'companies': 3600,   # 1 hour
            'markets': 900,      # 15 minutes
        }
    
    def should_cache_query(self, query: str) -> bool:
        """Determine if query should be cached."""
        query_lower = query.lower()
        
        # Don't cache writes
        if any(keyword in query_lower for keyword in ['insert', 'update', 'delete']):
            return False
        
        # Don't cache queries on no-cache tables
        for table in self.no_cache_tables:
            if table in query_lower:
                return False
        
        # Cache SELECT queries
        return 'select' in query_lower
    
    def get_cache_ttl(self, query: str) -> int:
        """Get appropriate cache TTL for query."""
        query_lower = query.lower()
        
        for table, ttl in self.long_cache_tables.items():
            if table in query_lower:
                return ttl
        
        return self.default_ttl
    
    @cache(ttl=300)
    async def execute_cached_query(
        self,
        session: AsyncSession,
        query: Union[str, ClauseElement],
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute query with intelligent caching."""
        if isinstance(query, str):
            result = await session.execute(text(query), parameters or {})
        else:
            result = await session.execute(query)
        
        # Convert to serializable format
        rows = []
        for row in result:
            if hasattr(row, '_asdict'):
                rows.append(row._asdict())
            else:
                rows.append(dict(row))
        
        return rows


class OptimizedSession:
    """Database session with advanced features."""
    
    def __init__(self, session: AsyncSession, pool_name: str = "default"):
        self.session = session
        self.pool_name = pool_name
        self.query_cache = QueryCache()
        self._transaction_start_time = None
    
    async def execute_optimized(
        self,
        query: Union[str, ClauseElement],
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Any:
        """Execute query with optimization features."""
        
        # Use cache for eligible queries
        if use_cache and isinstance(query, str) and self.query_cache.should_cache_query(query):
            return await self.query_cache.execute_cached_query(
                self.session, query, parameters
            )
        
        # Execute directly
        if isinstance(query, str):
            result = await self.session.execute(text(query), parameters or {})
        else:
            result = await self.session.execute(query, parameters or {})
        
        return result
    
    async def bulk_insert_optimized(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """Optimized bulk insert with batching."""
        if not data:
            return 0
        
        total_inserted = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            # Build bulk insert query
            columns = list(batch[0].keys())
            placeholders = ', '.join([f':{col}' for col in columns])
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            await self.session.execute(text(query), batch)
            total_inserted += len(batch)
            
            # Commit batch to avoid long transactions
            if i % (batch_size * 10) == 0:
                await self.session.commit()
        
        logger.info(
            "Bulk insert completed",
            table=table_name,
            total_rows=total_inserted,
            batch_size=batch_size
        )
        
        return total_inserted
    
    async def __aenter__(self):
        self._transaction_start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            # Log transaction duration
            if self._transaction_start_time:
                duration = time.time() - self._transaction_start_time
                if duration > 5.0:  # Log long transactions
                    logger.warning(
                        "Long database transaction",
                        duration=duration,
                        pool=self.pool_name
                    )
            
            await self.session.close()


@asynccontextmanager
async def get_optimized_db_session(
    pool_name: str = "default",
    read_only: bool = False
) -> OptimizedSession:
    """Get optimized database session."""
    engine = pool_manager.get_engine(pool_name)
    
    async with AsyncSession(
        engine,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False
    ) as session:
        
        # Set read-only mode if requested
        if read_only:
            await session.execute(text("SET TRANSACTION READ ONLY"))
        
        optimized_session = OptimizedSession(session, pool_name)
        
        try:
            yield optimized_session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Database maintenance utilities
class DatabaseMaintenance:
    """Database maintenance and optimization utilities."""
    
    @staticmethod
    async def analyze_table_stats(session: AsyncSession) -> Dict[str, Any]:
        """Analyze table statistics for optimization."""
        stats_query = """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC;
        """
        
        result = await session.execute(text(stats_query))
        return [dict(row) for row in result]
    
    @staticmethod
    async def get_index_usage_stats(session: AsyncSession) -> Dict[str, Any]:
        """Get index usage statistics."""
        index_query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_tup_read,
                idx_tup_fetch,
                idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            ORDER BY schemaname, tablename;
        """
        
        result = await session.execute(text(index_query))
        return [dict(row) for row in result]
    
    @staticmethod
    async def suggest_maintenance(session: AsyncSession) -> List[Dict[str, str]]:
        """Suggest database maintenance actions."""
        suggestions = []
        
        # Check for tables needing vacuum
        table_stats = await DatabaseMaintenance.analyze_table_stats(session)
        for stat in table_stats:
            dead_ratio = stat['dead_tuples'] / max(stat['live_tuples'], 1)
            if dead_ratio > 0.1:  # More than 10% dead tuples
                suggestions.append({
                    "type": "vacuum",
                    "table": f"{stat['schemaname']}.{stat['tablename']}",
                    "reason": f"High dead tuple ratio: {dead_ratio:.2%}",
                    "action": f"VACUUM {stat['schemaname']}.{stat['tablename']}"
                })
        
        # Check for unused indexes
        unused_indexes = await DatabaseMaintenance.get_index_usage_stats(session)
        for idx in unused_indexes:
            suggestions.append({
                "type": "index_cleanup",
                "table": f"{idx['schemaname']}.{idx['tablename']}",
                "index": idx['indexname'],
                "reason": "Unused index detected",
                "action": f"Consider dropping index {idx['indexname']}"
            })
        
        return suggestions


# Initialize database pools
async def initialize_database_pools():
    """Initialize optimized database connection pools."""
    
    # Main read-write pool
    pool_manager.create_optimized_engine(
        settings.DATABASE_URL,
        pool_name="default",
        read_only=False
    )
    
    # Read-only pool for analytics queries
    if hasattr(settings, 'DATABASE_READ_URL'):
        pool_manager.create_optimized_engine(
            settings.DATABASE_READ_URL,
            pool_name="readonly",
            read_only=True
        )
    
    logger.info("Database pools initialized")


# Cleanup function
async def cleanup_database_pools():
    """Clean up database connection pools."""
    await pool_manager.close_all_engines()
    logger.info("Database pools closed")