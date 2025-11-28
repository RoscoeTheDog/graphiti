"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from .availability import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    HealthCheckConfig,
    HealthCheckResult,
    LLMAvailabilityConfig,
    LLMAvailabilityManager,
    LLMError,
    LLMErrorClassifier,
    LLMErrorType,
    LLMHealthMonitor,
)
from .client import LLMClient
from .config import LLMConfig
from .errors import (
    EmptyResponseError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMUnavailableError,
    RateLimitError,
    RefusalError,
)
from .openai_client import OpenAIClient

__all__ = [
    # Client
    'LLMClient',
    'OpenAIClient',
    'LLMConfig',
    # Errors
    'RateLimitError',
    'RefusalError',
    'EmptyResponseError',
    'LLMUnavailableError',
    'LLMAuthenticationError',
    'LLMRateLimitError',
    # Availability
    'LLMAvailabilityManager',
    'LLMAvailabilityConfig',
    'LLMHealthMonitor',
    'HealthCheckConfig',
    'HealthCheckResult',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitState',
    'LLMErrorClassifier',
    'LLMError',
    'LLMErrorType',
]
