"""
Memory Service for VAM Cognitive Persistence (Phase 3).

Enables long-term memory for the AI using vector embeddings for semantic search.
Supports both pgvector (Postgres) and fallback keyword search (SQLite).
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, text

# Logging
try:
    from app.core.logging import logger
except ImportError:
    try:
        from backend.app.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)

# Config
try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings

# Models
try:
    from app.models import Memory, MemoryType, PGVECTOR_AVAILABLE
except ImportError:
    from backend.app.models import Memory, MemoryType, PGVECTOR_AVAILABLE

# OpenAI (optional - graceful degradation)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


class MemoryService:
    """
    Service for storing and retrieving AI memories with semantic search.
    
    Uses OpenAI embeddings for vector representation and pgvector for
    efficient similarity search. Falls back to keyword matching without
    these dependencies.
    """
    
    def __init__(self):
        self._openai_client = None
        
    @property
    def openai_client(self) -> Optional["OpenAI"]:
        """Lazy-load OpenAI client."""
        if self._openai_client is None and OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client
    
    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str | MemoryType,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Memory:
        """
        Store a new memory with vector embedding.
        
        Args:
            user_id: The user this memory belongs to
            content: The text content of the memory
            memory_type: Type classification (decision, preference, etc.)
            db: Database session
            metadata: Optional additional context
            source: Where the memory came from (standup, task, chat)
        
        Returns:
            The created Memory object
        """
        # Generate embedding
        embedding = await self._get_embedding(content)
        
        # Convert memory_type if string
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type)
            except ValueError:
                memory_type = MemoryType.CONTEXT
        
        # Create memory record
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding if PGVECTOR_AVAILABLE else json.dumps(embedding) if embedding else None,
            memory_metadata=json.dumps(metadata) if metadata else None,
            source=source,
            created_at=datetime.utcnow()
        )
        
        db.add(memory)
        db.commit()
        db.refresh(memory)
        
        logger.info(f"Stored memory {memory.id} for user {user_id}: {content[:50]}...")
        
        return memory
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        db: Session,
        limit: int = 5,
        memory_types: Optional[List[str | MemoryType]] = None
    ) -> List[Memory]:
        """
        Retrieve relevant memories using semantic similarity search.
        
        Args:
            user_id: The user whose memories to search
            query: The query text to match against
            db: Database session
            limit: Maximum number of results
            memory_types: Optional filter by memory type(s)
        
        Returns:
            List of relevant Memory objects, ordered by similarity
        """
        # Get query embedding
        query_embedding = await self._get_embedding(query)
        
        if query_embedding and PGVECTOR_AVAILABLE:
            # Use pgvector cosine similarity search
            memories = await self._vector_search(
                user_id=user_id,
                query_embedding=query_embedding,
                db=db,
                limit=limit,
                memory_types=memory_types
            )
        else:
            # Fallback to keyword search
            memories = await self._keyword_search(
                user_id=user_id,
                query=query,
                db=db,
                limit=limit,
                memory_types=memory_types
            )
        
        # Update access count for retrieved memories
        for memory in memories:
            memory.access_count = (memory.access_count or 0) + 1
            memory.last_accessed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Retrieved {len(memories)} memories for user {user_id}, query: '{query[:30]}...'")
        
        return memories
    
    async def _vector_search(
        self,
        user_id: str,
        query_embedding: List[float],
        db: Session,
        limit: int,
        memory_types: Optional[List[str | MemoryType]] = None
    ) -> List[Memory]:
        """Perform vector similarity search using pgvector."""
        
        # Build base query - using raw SQL for pgvector operators
        # The <=> operator computes cosine distance
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        sql = text("""
            SELECT id, content, memory_type, memory_metadata, source, created_at, access_count,
                   1 - (embedding <=> :embedding) as similarity
            FROM memories
            WHERE user_id = :user_id
            AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """)
        
        result = db.execute(sql, {
            "user_id": user_id,
            "embedding": embedding_str,
            "limit": limit
        })
        
        # Map results back to Memory objects
        memory_ids = [row[0] for row in result]
        if not memory_ids:
            return []
        
        memories = db.query(Memory).filter(Memory.id.in_(memory_ids)).all()
        
        # Sort by the original similarity order
        memory_map = {m.id: m for m in memories}
        return [memory_map[mid] for mid in memory_ids if mid in memory_map]
    
    async def _keyword_search(
        self,
        user_id: str,
        query: str,
        db: Session,
        limit: int,
        memory_types: Optional[List[str | MemoryType]] = None
    ) -> List[Memory]:
        """Fallback keyword-based search for systems without pgvector."""
        
        base_query = db.query(Memory).filter(Memory.user_id == user_id)
        
        # Filter by memory types if specified
        if memory_types:
            type_values = []
            for mt in memory_types:
                if isinstance(mt, str):
                    try:
                        type_values.append(MemoryType(mt))
                    except ValueError:
                        pass
                else:
                    type_values.append(mt)
            if type_values:
                base_query = base_query.filter(Memory.memory_type.in_(type_values))
        
        # Simple keyword matching on content
        query_words = query.lower().split()
        memories = base_query.order_by(desc(Memory.created_at)).limit(limit * 3).all()
        
        # Score memories by keyword overlap
        scored_memories = []
        for memory in memories:
            content_lower = memory.content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored_memories.append((memory, score))
        
        # Sort by score and return top matches
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored_memories[:limit]]
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI API.
        
        Returns None if OpenAI is not available.
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available for embedding generation")
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
                dimensions=settings.EMBEDDING_DIMENSIONS
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def get_user_memories(
        self,
        user_id: str,
        db: Session,
        memory_type: Optional[str | MemoryType] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get all memories for a user, optionally filtered by type."""
        
        query = db.query(Memory).filter(Memory.user_id == user_id)
        
        if memory_type:
            if isinstance(memory_type, str):
                memory_type = MemoryType(memory_type)
            query = query.filter(Memory.memory_type == memory_type)
        
        return query.order_by(desc(Memory.created_at)).limit(limit).all()
    
    async def delete_memory(self, memory_id: str, user_id: str, db: Session) -> bool:
        """Delete a specific memory. Returns True if deleted."""
        
        memory = db.query(Memory).filter(
            Memory.id == memory_id,
            Memory.user_id == user_id
        ).first()
        
        if memory:
            db.delete(memory)
            db.commit()
            logger.info(f"Deleted memory {memory_id} for user {user_id}")
            return True
        
        return False
    
    def format_context_for_prompt(self, memories: List[Memory]) -> str:
        """
        Format retrieved memories as context for LLM prompt injection.
        
        Returns a formatted string to insert into the system prompt.
        """
        if not memories:
            return ""
        
        lines = ["RELEVANT PAST CONTEXT:"]
        for memory in memories:
            # Format based on memory type
            prefix = {
                MemoryType.DECISION: "Past decision",
                MemoryType.PREFERENCE: "User preference",
                MemoryType.MEETING_NOTE: "From meeting",
                MemoryType.STANDUP_FOCUS: "Previous focus",
                MemoryType.TASK_COMPLETION: "Completed",
                MemoryType.CONTEXT: "Context",
            }.get(memory.memory_type, "Note")
            
            date_str = memory.created_at.strftime("%b %d") if memory.created_at else ""
            lines.append(f"- [{prefix}] {date_str}: {memory.content}")
        
        return "\n".join(lines)


# Singleton instance
memory_service = MemoryService()

# Legacy compatibility - expose VectorMemory class
class VectorMemory:
    """Legacy wrapper for backward compatibility."""
    
    def __init__(self):
        self.path = settings.VECTOR_DB_PATH
        logger.info(f"VectorMemory initialized (using new MemoryService)")
    
    def add_context(self, text: str):
        """Legacy method - does nothing without user context."""
        logger.warning("VectorMemory.add_context called without user_id - use memory_service instead")
    
    def retrieve_context(self, query: str):
        """Legacy method - returns empty list without user context."""
        logger.warning("VectorMemory.retrieve_context called without user_id - use memory_service instead")
        return []


vector_memory = VectorMemory()
