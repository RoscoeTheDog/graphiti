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


class RateLimitError(Exception):
    """Exception raised when the rate limit is exceeded."""

    def __init__(self, message='Rate limit exceeded. Please try again later.'):
        self.message = message
        super().__init__(self.message)


class RefusalError(Exception):
    """Exception raised when the LLM refuses to generate a response."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EmptyResponseError(Exception):
    """Exception raised when the LLM returns an empty response."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class LLMUnavailableError(Exception):
    """Exception raised when LLM is unavailable (circuit breaker open or health check failed)."""

    def __init__(
        self, message: str = "LLM is currently unavailable", retryable: bool = True
    ):
        self.message = message
        self.retryable = retryable
        super().__init__(self.message)


class LLMAuthenticationError(Exception):
    """Exception raised when LLM authentication fails (invalid API key, suspended account)."""

    def __init__(self, message: str = "LLM authentication failed"):
        self.message = message
        super().__init__(self.message)


class LLMRateLimitError(Exception):
    """Exception raised when LLM rate limit is exceeded (transient, retryable)."""

    def __init__(
        self,
        message: str = "LLM rate limit exceeded",
        retry_after: float | None = None,
    ):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
