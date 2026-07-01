"""Advanced async task management with priority queues and retry logic."""

import asyncio
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from .exceptions import TaskError

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskDefinition:
    """Task definition with execution parameters."""

    task_id: str
    function_name: str
    args: tuple
    kwargs: dict
    priority: TaskPriority
    max_retries: int
    retry_delay: float
    timeout: Optional[float]
    created_at: datetime
    scheduled_at: Optional[datetime]
    metadata: Dict[str, Any]

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RetryPolicy:
    """Configurable retry policy for tasks."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if attempt >= self.max_retries:
            return 0

        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5  # Add jitter

        return delay

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if task should be retried."""
        if attempt >= self.max_retries:
            return False

        # Don't retry certain types of errors
        non_retryable_errors = (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        )

        return not isinstance(error, non_retryable_errors)


class TaskQueue:
    """Priority-based async task queue."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.queues: Dict[TaskPriority, asyncio.Queue] = {
            TaskPriority.CRITICAL: asyncio.Queue(),
            TaskPriority.HIGH: asyncio.Queue(),
            TaskPriority.NORMAL: asyncio.Queue(),
            TaskPriority.LOW: asyncio.Queue(),
        }
        self.size = 0

    async def put(self, task: TaskDefinition) -> bool:
        """Add task to appropriate priority queue."""
        if self.size >= self.max_size:
            logger.warning("Task queue full, rejecting task", task_id=task.task_id)
            return False

        await self.queues[task.priority].put(task)
        self.size += 1
        return True

    async def get(self) -> TaskDefinition:
        """Get next task from highest priority queue."""
        # Check queues in priority order
        for priority in [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]:
            try:
                task = self.queues[priority].get_nowait()
                self.size -= 1
                return task
            except asyncio.QueueEmpty:
                continue

        # If all queues empty, wait on normal priority
        task = await self.queues[TaskPriority.NORMAL].get()
        self.size -= 1
        return task

    def qsize(self) -> Dict[TaskPriority, int]:
        """Get queue sizes by priority."""
        return {priority: queue.qsize() for priority, queue in self.queues.items()}


class TaskExecutor:
    """Execute tasks with monitoring and error handling."""

    def __init__(
        self,
        max_workers: int = 10,
        max_concurrent_tasks: int = 100,
        default_timeout: float = 300.0,  # 5 minutes
    ):
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.registered_functions: Dict[str, Callable] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.default_retry_policy = RetryPolicy()

    def register_function(self, name: str, func: Callable):
        """Register a function for task execution."""
        self.registered_functions[name] = func
        logger.debug("Function registered for task execution", function_name=name)

    async def execute_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a single task with error handling."""
        result = TaskResult(
            task_id=task.task_id, status=TaskStatus.PENDING, started_at=datetime.now()
        )

        try:
            # Check if function is registered
            if task.function_name not in self.registered_functions:
                raise TaskError(f"Function {task.function_name} not registered")

            func = self.registered_functions[task.function_name]
            result.status = TaskStatus.RUNNING

            # Execute with timeout
            timeout = task.timeout or self.default_timeout

            if asyncio.iscoroutinefunction(func):
                # Async function
                task_result = await asyncio.wait_for(
                    func(*task.args, **task.kwargs), timeout=timeout
                )
            else:
                # Sync function - run in thread pool
                task_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        self.thread_pool, func, *task.args, **task.kwargs
                    ),
                    timeout=timeout,
                )

            result.result = task_result
            result.status = TaskStatus.COMPLETED
            result.completed_at = datetime.now()
            result.duration = (result.completed_at - result.started_at).total_seconds()

            logger.info(
                "Task completed successfully",
                task_id=task.task_id,
                function=task.function_name,
                duration=result.duration,
            )

        except asyncio.TimeoutError:
            result.status = TaskStatus.FAILED
            result.error = f"Task timed out after {timeout}s"
            result.completed_at = datetime.now()
            logger.error("Task timeout", task_id=task.task_id, timeout=timeout)

        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
            result.duration = (result.completed_at - result.started_at).total_seconds()

            logger.error(
                "Task execution failed",
                task_id=task.task_id,
                function=task.function_name,
                error=str(e),
                traceback=traceback.format_exc(),
            )

        # Store result
        self.task_results[task.task_id] = result
        return result

    async def retry_task(
        self, task: TaskDefinition, error: Exception
    ) -> Optional[TaskDefinition]:
        """Create retry task if retry policy allows."""
        retry_policy = self.default_retry_policy
        current_retry = task.metadata.get("retry_count", 0)

        if retry_policy.should_retry(current_retry, error):
            delay = retry_policy.get_delay(current_retry)

            # Create new task for retry
            retry_task = TaskDefinition(
                task_id=f"{task.task_id}_retry_{current_retry + 1}",
                function_name=task.function_name,
                args=task.args,
                kwargs=task.kwargs,
                priority=task.priority,
                max_retries=task.max_retries,
                retry_delay=delay,
                timeout=task.timeout,
                created_at=datetime.now(),
                scheduled_at=datetime.now() + timedelta(seconds=delay),
                metadata={
                    **task.metadata,
                    "retry_count": current_retry + 1,
                    "original_task_id": task.task_id,
                },
            )

            logger.info(
                "Task scheduled for retry",
                task_id=task.task_id,
                retry_task_id=retry_task.task_id,
                retry_count=current_retry + 1,
                delay=delay,
            )

            return retry_task

        return None

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task execution result."""
        return self.task_results.get(task_id)

    def cleanup_old_results(self, max_age_hours: int = 24):
        """Clean up old task results."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for task_id, result in self.task_results.items():
            if result.completed_at and result.completed_at < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.task_results[task_id]

        logger.info("Old task results cleaned up", removed_count=len(to_remove))


class TaskManager:
    """Main task management system."""

    def __init__(self):
        self.task_queue = TaskQueue()
        self.executor = TaskExecutor()
        self.scheduler_task: Optional[asyncio.Task] = None
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.scheduled_tasks: Dict[str, TaskDefinition] = {}

    async def start(self, num_workers: int = 5):
        """Start the task management system."""
        if self.is_running:
            return

        self.is_running = True

        # Start scheduler
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Start workers
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker)

        logger.info("Task manager started", num_workers=num_workers)

    async def stop(self):
        """Stop the task management system."""
        if not self.is_running:
            return

        self.is_running = False

        # Stop scheduler
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        # Stop workers
        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        # Close thread pool
        self.executor.thread_pool.shutdown(wait=True)

        logger.info("Task manager stopped")

    async def submit_task(
        self,
        function_name: str,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        scheduled_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Submit a task for execution."""
        task_id = str(uuid.uuid4())

        task = TaskDefinition(
            task_id=task_id,
            function_name=function_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=1.0,
            timeout=timeout,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            metadata=metadata or {},
        )

        if scheduled_at and scheduled_at > datetime.now():
            # Schedule for later
            self.scheduled_tasks[task_id] = task
            logger.debug("Task scheduled", task_id=task_id, scheduled_at=scheduled_at)
        else:
            # Queue immediately
            success = await self.task_queue.put(task)
            if not success:
                raise TaskError(f"Failed to queue task {task_id} - queue full")
            logger.debug("Task queued", task_id=task_id, function=function_name)

        return task_id

    async def _scheduler_loop(self):
        """Scheduler loop to handle scheduled tasks."""
        while self.is_running:
            try:
                now = datetime.now()
                ready_tasks = []

                # Find tasks ready for execution
                for task_id, task in list(self.scheduled_tasks.items()):
                    if task.scheduled_at <= now:
                        ready_tasks.append(task_id)

                # Move ready tasks to queue
                for task_id in ready_tasks:
                    task = self.scheduled_tasks.pop(task_id)
                    await self.task_queue.put(task)
                    logger.debug("Scheduled task moved to queue", task_id=task_id)

                await asyncio.sleep(1)  # Check every second

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler error", error=str(e))
                await asyncio.sleep(5)

    async def _worker_loop(self, worker_name: str):
        """Worker loop to execute tasks."""
        logger.info("Task worker started", worker=worker_name)

        while self.is_running:
            try:
                # Get next task
                task = await self.task_queue.get()

                logger.debug(
                    "Worker executing task", worker=worker_name, task_id=task.task_id
                )

                # Execute task
                result = await self.executor.execute_task(task)

                # Handle retry if task failed
                if result.status == TaskStatus.FAILED:
                    retry_task = await self.executor.retry_task(
                        task, Exception(result.error)
                    )
                    if retry_task:
                        if retry_task.scheduled_at > datetime.now():
                            self.scheduled_tasks[retry_task.task_id] = retry_task
                        else:
                            await self.task_queue.put(retry_task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker error", worker=worker_name, error=str(e))
                await asyncio.sleep(1)

        logger.info("Task worker stopped", worker=worker_name)

    def register_function(self, name: str, func: Callable):
        """Register a function for task execution."""
        self.executor.register_function(name, func)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task execution result."""
        return self.executor.get_task_result(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics."""
        queue_sizes = self.task_queue.qsize()

        status_counts = {}
        for result in self.executor.task_results.values():
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        return {
            "is_running": self.is_running,
            "queue_sizes": queue_sizes,
            "total_queue_size": self.task_queue.size,
            "scheduled_tasks": len(self.scheduled_tasks),
            "running_workers": len(self.workers),
            "task_results": len(self.executor.task_results),
            "status_distribution": status_counts,
            "registered_functions": len(self.executor.registered_functions),
        }

    async def cleanup_old_results(self):
        """Clean up old task results."""
        self.executor.cleanup_old_results()


# Global task manager
_task_manager: Optional[TaskManager] = None


async def get_task_manager() -> TaskManager:
    """Get or create task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def task(
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: Optional[float] = None,
    max_retries: int = 3,
    auto_register: bool = True,
):
    """Decorator to register functions as tasks."""

    def decorator(func: Callable) -> Callable:
        if auto_register:
            # Register function when decorator is applied
            asyncio.create_task(_register_function_async(func.__name__, func))

        async def wrapper(*args, **kwargs):
            # Submit as task
            task_manager = await get_task_manager()
            task_id = await task_manager.submit_task(
                func.__name__,
                *args,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                **kwargs,
            )
            return task_id

        # Add direct execution method
        wrapper.execute = func
        wrapper.task_name = func.__name__

        return wrapper

    return decorator


async def _register_function_async(name: str, func: Callable):
    """Register function with task manager."""
    task_manager = await get_task_manager()
    task_manager.register_function(name, func)


# Utility functions for common background tasks
@task(priority=TaskPriority.LOW, timeout=600)  # 10 minutes
async def cleanup_expired_sessions():
    """Clean up expired user sessions."""
    # Implementation would go here
    logger.info("Cleaning up expired sessions")
    return {"cleaned": 0}


@task(priority=TaskPriority.HIGH, timeout=300)  # 5 minutes
async def process_kyc_verification(user_id: str, verification_data: Dict[str, Any]):
    """Process KYC verification in background."""
    # Implementation would go here
    logger.info("Processing KYC verification", user_id=user_id)
    return {"status": "verified"}


@task(priority=TaskPriority.NORMAL, timeout=120)  # 2 minutes
async def send_notification_email(recipient: str, template: str, data: Dict[str, Any]):
    """Send notification email."""
    # Implementation would go here
    logger.info("Sending notification email", recipient=recipient, template=template)
    return {"sent": True}


# Scheduled task utilities
async def schedule_recurring_task(
    function_name: str, interval_seconds: int, *args, **kwargs
) -> str:
    """Schedule a recurring task."""
    task_manager = await get_task_manager()

    # Submit first execution
    task_id = await task_manager.submit_task(function_name, *args, **kwargs)

    # Schedule next execution
    next_run = datetime.now() + timedelta(seconds=interval_seconds)
    await task_manager.submit_task(
        "schedule_recurring_task",
        function_name,
        interval_seconds,
        *args,
        scheduled_at=next_run,
        metadata={"recurring": True, "interval": interval_seconds},
        **kwargs,
    )

    return task_id
