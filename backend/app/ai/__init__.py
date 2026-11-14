"""BusReserve 2.0 Phase 4 Gemini AI & Deterministic Local Fallback package."""

from app.ai.assistant_service import (
    clear_ai_history,
    get_ai_history,
    run_admin_ai_assistant,
    run_passenger_assistant,
    run_recommendations_engine,
)
from app.ai.nlp import extract_travel_preferences, sanitize_user_input
from app.ai.providers import (
    AIProviderError,
    AIProviderManager,
    BaseAIProvider,
    GeminiProvider,
    LocalFallbackProvider,
    ProviderResult,
    get_ai_manager,
)
from app.ai.recommendations import RecommendationEngine

__all__ = [
    "AIProviderError",
    "AIProviderManager",
    "BaseAIProvider",
    "GeminiProvider",
    "LocalFallbackProvider",
    "ProviderResult",
    "RecommendationEngine",
    "clear_ai_history",
    "extract_travel_preferences",
    "get_ai_history",
    "get_ai_manager",
    "run_admin_ai_assistant",
    "run_passenger_assistant",
    "run_recommendations_engine",
    "sanitize_user_input",
]
