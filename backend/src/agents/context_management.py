"""
Intelligent context management for ResearchMind agents.

Implements both trimming and summarization strategies based on OpenAI Agents SDK recommendations
for managing long-running, multi-turn conversations while maintaining coherence and efficiency.
"""
import asyncio
import json
from abc import ABC, abstractmethod
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import asyncio
import json
from openai import AsyncOpenAI

from src.config import get_settings
from src.core import logger

TResponseInputItem = Dict[str, Any]
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


def _is_user_msg(item: TResponseInputItem) -> bool:
    """Return True if the item represents a user message."""
    if isinstance(item, dict):
        role = item.get("role")
        if role is not None:
            return role == ROLE_USER
        if item.get("type") == "message":
            return item.get("role") == ROLE_USER
    return getattr(item, "role", None) == ROLE_USER


class SessionABC(ABC):
    """Abstract base class for session management."""
    
    @abstractmethod
    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return conversation history items."""
        pass
    
    @abstractmethod
    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Add new items to the conversation history."""
        pass
    
    @abstractmethod
    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Remove and return the most recent item."""
        pass
    
    @abstractmethod
    async def clear_session(self) -> None:
        """Clear all items from the session."""
        pass


class TrimmingSession(SessionABC):
    """
    Keep only the last N *user turns* in memory.

    A turn = a user message and all subsequent items (assistant/tool calls/results)
    up to (but not including) the next user message.
    
    Pros:
    - Deterministic & simple: No summarizer variability
    - Zero added latency: No extra model calls
    - Fidelity for recent work: Latest tool results stay verbatim
    - Lower risk of "summary drift"
    
    Cons:
    - Forgets long-range context abruptly
    - User experience "amnesia"
    - Wasted signal from older turns
    
    Best for: Independent tasks with non-overlapping context
    """

    def __init__(self, session_id: str, max_turns: int = 8):
        self.session_id = session_id
        self.max_turns = max(1, int(max_turns))
        self._items: Deque[TResponseInputItem] = deque()
        self._lock = asyncio.Lock()

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return history trimmed to the last N user turns."""
        async with self._lock:
            trimmed = self._trim_to_last_turns(list(self._items))
            return trimmed[-limit:] if (limit is not None and limit >= 0) else trimmed

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Append new items, then trim to last N user turns."""
        if not items:
            return
        async with self._lock:
            self._items.extend(items)
            trimmed = self._trim_to_last_turns(list(self._items))
            self._items.clear()
            self._items.extend(trimmed)

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Remove and return the most recent item (post-trim)."""
        async with self._lock:
            return self._items.pop() if self._items else None

    async def clear_session(self) -> None:
        """Remove all items for this session."""
        async with self._lock:
            self._items.clear()

    def _trim_to_last_turns(self, items: List[TResponseInputItem]) -> List[TResponseInputItem]:
        """
        Keep only the suffix containing the last `max_turns` user messages and everything after
        the earliest of those user messages.
        """
        if not items:
            return items

        count = 0
        start_idx = 0

        for i in range(len(items) - 1, -1, -1):
            if _is_user_msg(items[i]):
                count += 1
                if count == self.max_turns:
                    start_idx = i
                    break

        return items[start_idx:]

    async def set_max_turns(self, max_turns: int) -> None:
        """Update max_turns and re-trim if necessary."""
        async with self._lock:
            self.max_turns = max(1, int(max_turns))
            trimmed = self._trim_to_last_turns(list(self._items))
            self._items.clear()
            self._items.extend(trimmed)

    async def raw_items(self) -> List[TResponseInputItem]:
        """Return the untrimmed in-memory log (for debugging)."""
        async with self._lock:
            return list(self._items)


class LLMSummarizer:
    """Handles conversation summarization using LLM."""
    
    def __init__(self, client: Optional[AsyncOpenAI] = None, model: str = "gpt-4o-mini", max_tokens: int = 400, tool_trim_limit: int = 600):
        self.client = client or AsyncOpenAI()
        self.model = model
        self.max_tokens = max_tokens
        self.tool_trim_limit = tool_trim_limit

    async def summarize(self, messages: List[TResponseInputItem]) -> Tuple[str, str]:
        """
        Create a compact summary from messages.

        Returns:
            Tuple[str, str]: The shadow user line to keep dialog natural,
            and the model-generated summary text.
        """
        user_shadow = "Summarize our conversation so far."
        TOOL_ROLES = {"tool", "tool_result"}

        def to_snippet(m: TResponseInputItem) -> Optional[str]:
            role = (m.get("role") or "assistant").lower()
            content = str(m.get("content") or "").strip()
            if not content:
                return None

            if role in TOOL_ROLES and len(content) > self.tool_trim_limit:
                content = content[:self.tool_trim_limit] + " …"
            return f"{role.upper()}: {content}"

        history_snippets = [s for m in messages if (s := to_snippet(m))]

        prompt_messages = [
            {"role": "system", "content": self._get_summary_prompt()},
            {"role": "user", "content": "\n".join(history_snippets)},
        ]

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=prompt_messages,
                max_tokens=self.max_tokens,
                temperature=0.1,
            )
            
            summary = resp.choices[0].message.content or "Summary unavailable."
            return user_shadow, summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return user_shadow, "Summary unavailable due to error."

    def _get_summary_prompt(self) -> str:
        """Get the summarization prompt tailored for research conversations."""
        return """
            You are an AI research assistant creating a concise summary of a research conversation.
            Compress the earlier conversation into a precise, reusable snapshot for future turns.

            Before you write (do this silently):
            - Contradiction check: compare user claims with system instructions; note any conflicts
            - Temporal ordering: sort key events by time; the most recent update wins
            - Hallucination control: if any fact is uncertain/not stated, mark it as UNVERIFIED

            Write a structured, factual summary ≤ 200 words using these sections (use exact headings):

            • Research Context:
            - Main research topics, domains, or questions being explored

            • Papers & Sources:
            - Key papers discussed, authors, or datasets mentioned

            • Search Queries & Results:
            - Important search terms used and what was found/not found

            • Key Findings:
            - Important insights, conclusions, or discoveries from the conversation

            • Current Focus:
            - What the user is currently investigating or needs help with

            • Next Steps:
            - Recommended actions or areas to explore further

            Rules:
            - Be concise, no fluff; use short bullets, verbs first
            - Do not invent new facts; quote paper titles/authors exactly when available
            - If previous info was superseded, note "Superseded:" and omit details unless critical
            - Focus on research-relevant context that helps with future queries
            """


class SummarizingSession(SessionABC):
    """
    Session that keeps only the last N *user turns* verbatim and summarizes the rest.

    Pros:
    - Retains long-range memory compactly
    - Smoother UX: Agent "remembers" commitments across long sessions
    - Cost-controlled scale: One summary replaces hundreds of turns
    - Searchable anchor: Stable "state of the world so far"
    
    Cons:
    - Summarization loss & bias: Details can be dropped
    - Latency & cost spikes: Each refresh adds model work
    - Compounding errors: Bad facts can poison future behavior
    - Observability complexity: Must log summary prompts/outputs
    
    Best for: Tasks needing context across the flow (planning, analysis, policy Q&A)
    """

    # Only these keys are ever sent to the model
    _ALLOWED_MSG_KEYS = {"role", "content", "name", "tool_calls", "tool_call_id"}

    def __init__(
        self,
        session_id: str,
        keep_last_n_turns: int = 3,
        context_limit: int = 8,
        summarizer: Optional[LLMSummarizer] = None,
    ):
        assert context_limit >= 1
        assert keep_last_n_turns >= 0
        assert keep_last_n_turns <= context_limit, "keep_last_n_turns should not be greater than context_limit"

        self.session_id = session_id
        self.keep_last_n_turns = keep_last_n_turns
        self.context_limit = context_limit
        self.summarizer = summarizer or LLMSummarizer()

        self._records: deque[Dict[str, Dict[str, Any]]] = deque()
        self._lock = asyncio.Lock()

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return model-safe messages only (no metadata)."""
        async with self._lock:
            data = list(self._records)
        msgs = [self._sanitize_for_model(rec["msg"]) for rec in data]
        return msgs[-limit:] if limit else msgs

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Append new items and, if needed, summarize older turns."""
        async with self._lock:
            for it in items:
                msg, meta = self._split_msg_and_meta(it)
                self._records.append({"msg": msg, "meta": meta})

            need_summary, boundary = self._summarize_decision_locked()

        if not need_summary:
            async with self._lock:
                self._normalize_synthetic_flags_locked()
            return

        async with self._lock:
            snapshot = list(self._records)
            prefix_msgs = [r["msg"] for r in snapshot[:boundary]]

        user_shadow, assistant_summary = await self._summarize(prefix_msgs)

        async with self._lock:
            still_need, new_boundary = self._summarize_decision_locked()
            if not still_need:
                self._normalize_synthetic_flags_locked()
                return

            snapshot = list(self._records)
            suffix = snapshot[new_boundary:]

            self._records.clear()
            self._records.extend([
                {
                    "msg": {"role": "user", "content": user_shadow},
                    "meta": {
                        "synthetic": True,
                        "kind": "history_summary_prompt",
                        "summary_for_turns": f"< all before idx {new_boundary} >",
                        "timestamp": datetime.now().isoformat(),
                    },
                },
                {
                    "msg": {"role": "assistant", "content": assistant_summary},
                    "meta": {
                        "synthetic": True,
                        "kind": "history_summary",
                        "summary_for_turns": f"< all before idx {new_boundary} >",
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            ])
            self._records.extend(suffix)

            self._normalize_synthetic_flags_locked()

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Pop the latest message (model-safe), if any."""
        async with self._lock:
            if not self._records:
                return None
            rec = self._records.pop()
            return dict(rec["msg"])

    async def clear_session(self) -> None:
        """Remove all records."""
        async with self._lock:
            self._records.clear()

    async def get_full_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Return combined history entries for debugging/analytics:
        {"message": {role, content[, name]}, "metadata": {...}}
        """
        async with self._lock:
            data = list(self._records)
        out = [{"message": dict(rec["msg"]), "metadata": dict(rec["meta"])} for rec in data]
        return out[-limit:] if limit else out

    def _split_msg_and_meta(self, it: TResponseInputItem) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Split input into (msg, meta)."""
        msg = {k: v for k, v in it.items() if k in self._ALLOWED_MSG_KEYS}
        extra = {k: v for k, v in it.items() if k not in self._ALLOWED_MSG_KEYS}
        meta = dict(extra.pop("metadata", {}))
        meta.update(extra)

        msg.setdefault("role", "user")
        msg.setdefault("content", str(it))

        role = msg.get("role")
        if role in ("user", "assistant") and "synthetic" not in meta:
            meta["synthetic"] = False
        
        if "timestamp" not in meta:
            meta["timestamp"] = datetime.now().isoformat()
            
        return msg, meta

    @staticmethod
    def _sanitize_for_model(msg: Dict[str, Any]) -> Dict[str, Any]:
        """Drop anything not allowed in model calls."""
        return {k: v for k, v in msg.items() if k in SummarizingSession._ALLOWED_MSG_KEYS}

    @staticmethod
    def _is_real_user_turn_start(rec: Dict[str, Dict[str, Any]]) -> bool:
        """True if record starts a *real* user turn (role=='user' and not synthetic)."""
        return (
            rec["msg"].get("role") == "user"
            and not rec["meta"].get("synthetic", False)
        )

    def _summarize_decision_locked(self) -> Tuple[bool, int]:
        """Decide whether to summarize and compute the boundary index."""
        user_starts: List[int] = [
            i for i, rec in enumerate(self._records) if self._is_real_user_turn_start(rec)
        ]
        real_turns = len(user_starts)

        if real_turns <= self.context_limit:
            return False, -1

        if self.keep_last_n_turns == 0:
            return True, len(self._records)

        if len(user_starts) < self.keep_last_n_turns:
            return False, -1 

        boundary = user_starts[-self.keep_last_n_turns]

        if boundary <= 0:
            return False, -1

        return True, boundary

    def _normalize_synthetic_flags_locked(self) -> None:
        """Ensure all real user/assistant records explicitly carry synthetic=False."""
        for rec in self._records:
            role = rec["msg"].get("role")
            if role in ("user", "assistant") and "synthetic" not in rec["meta"]:
                rec["meta"]["synthetic"] = False

    async def _summarize(self, prefix_msgs: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Ask the configured summarizer to compress the given prefix."""
        if not self.summarizer:
            return ("Summarize our conversation so far.", "Summary unavailable.")
        clean_prefix = [self._sanitize_for_model(m) for m in prefix_msgs]
        return await self.summarizer.summarize(clean_prefix)


class HybridSession(SessionABC):
    """
    Hybrid session that combines trimming and summarization strategies.
    
    Uses trimming for short conversations and switches to summarization
    when conversations become longer and more complex.
    """
    
    def __init__(
        self,
        session_id: str,
        trim_threshold: int = 5,
        summary_threshold: int = 12,
        keep_last_n_turns: int = 4,
        summarizer: Optional[LLMSummarizer] = None,
    ):
        self.session_id = session_id
        self.trim_threshold = trim_threshold
        self.summary_threshold = summary_threshold
        
        self._current_session: SessionABC = TrimmingSession(session_id, trim_threshold)
        self._strategy = "trimming"
        
        self.keep_last_n_turns = keep_last_n_turns
        self.summarizer = summarizer or LLMSummarizer()
        
        self._lock = asyncio.Lock()

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return items from current session strategy."""
        return await self._current_session.get_items(limit)

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Add items and potentially switch strategies."""
        await self._current_session.add_items(items)
        
        async with self._lock:
            await self._maybe_switch_strategy()

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Pop item from current session."""
        return await self._current_session.pop_item()

    async def clear_session(self) -> None:
        """Clear current session."""
        await self._current_session.clear_session()

    async def _maybe_switch_strategy(self) -> None:
        """Switch between trimming and summarization based on conversation length."""
        current_items = await self._current_session.get_items()
        user_turns = len([item for item in current_items if _is_user_msg(item)])
        
        if self._strategy == "trimming" and user_turns >= self.summary_threshold:
            print(f"Switching to summarization strategy for session {self.session_id}")
            
            new_session = SummarizingSession(
                session_id=self.session_id,
                keep_last_n_turns=self.keep_last_n_turns,
                context_limit=self.summary_threshold,
                summarizer=self.summarizer,
            )
            
            await new_session.add_items(current_items)
            
            self._current_session = new_session
            self._strategy = "summarization"

    async def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about current strategy and session state."""
        items = await self._current_session.get_items()
        user_turns = len([item for item in items if _is_user_msg(item)])
        
        info = {
            "session_id": self.session_id,
            "current_strategy": self._strategy,
            "total_items": len(items),
            "user_turns": user_turns,
            "trim_threshold": self.trim_threshold,
            "summary_threshold": self.summary_threshold,
        }
        
        if hasattr(self._current_session, 'get_full_history'):
            full_history = await self._current_session.get_full_history()
            synthetic_items = len([h for h in full_history if h.get("metadata", {}).get("synthetic", False)])
            info["synthetic_items"] = synthetic_items
            
        return info


class FileBackedSession(SessionABC):
    """
    Session that persists conversation history to disk while using
    intelligent context management in memory.
    """
    
    def __init__(
        self,
        session_id: str,
        storage_dir: Union[str, Path] = "conversations",
        context_strategy: str = "hybrid",
        **strategy_kwargs
    ):
        self.session_id = session_id
        self.context_strategy = context_strategy
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.file_path = self.storage_dir / f"{session_id}.json"
        
        if context_strategy == "trimming":
            self._memory_session = TrimmingSession(session_id, **strategy_kwargs)
        elif context_strategy == "summarization":
            self._memory_session = SummarizingSession(session_id, **strategy_kwargs)
        elif context_strategy == "hybrid":
            self._memory_session = HybridSession(session_id, **strategy_kwargs)
        else:
            raise ValueError(f"Unknown context strategy: {context_strategy}")
        
        self._lock = asyncio.Lock()
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Load conversation history from disk if not already loaded."""
        if self._loaded:
            return
            
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data.get("items", [])
                    if items:
                        await self._memory_session.add_items(items)
                        print(f"Loaded {len(items)} items from {self.file_path}")
            except Exception as e:
                print(f"Error loading conversation history: {e}")
        
        self._loaded = True

    async def _save_to_disk(self) -> None:
        """Save current conversation state to disk."""
        try:
            if hasattr(self._memory_session, 'get_full_history'):
                full_history = await self._memory_session.get_full_history()
                items = [h["message"] for h in full_history]
                metadata = [h["metadata"] for h in full_history]
            else:
                items = await self._memory_session.get_items()
                metadata = [{}] * len(items)
            
            data = {
                "session_id": self.session_id,
                "last_updated": datetime.now().isoformat(),
                "total_items": len(items),
                "items": items,
                "metadata": metadata,
            }
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving conversation history: {e}")

    async def get_items(self, limit: Optional[int] = None) -> List[TResponseInputItem]:
        """Return items from memory session."""
        async with self._lock:
            await self._ensure_loaded()
            return await self._memory_session.get_items(limit)

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """Add items to memory session and save to disk."""
        async with self._lock:
            await self._ensure_loaded()
            await self._memory_session.add_items(items)
            await self._save_to_disk()

    async def pop_item(self) -> Optional[TResponseInputItem]:
        """Pop item from memory session and save to disk."""
        async with self._lock:
            await self._ensure_loaded()
            result = await self._memory_session.pop_item()
            if result:
                await self._save_to_disk()
            return result

    async def clear_session(self) -> None:
        """Clear memory session and remove disk file."""
        async with self._lock:
            await self._memory_session.clear_session()
            if self.file_path.exists():
                self.file_path.unlink()
            self._loaded = False

    async def get_session_info(self) -> Dict[str, Any]:
        """Get information about the session."""
        info = {
            "session_id": self.session_id,
            "file_path": str(self.file_path),
            "file_exists": self.file_path.exists(),
            "loaded": self._loaded,
            "current_strategy": self.context_strategy,
        }
        
        if hasattr(self._memory_session, 'get_strategy_info'):
            strategy_info = await self._memory_session.get_strategy_info()
            info.update(strategy_info)
        
        return info
