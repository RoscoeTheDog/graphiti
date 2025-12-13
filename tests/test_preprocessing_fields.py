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

"""
Unit tests for preprocessing field additions to GraphitiClients and Graphiti.
Tests Story 2: Extend GraphitiClients with Preprocessing Fields
"""

from unittest.mock import Mock

import pytest

from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.driver.driver import GraphDriver
from graphiti_core.embedder import EmbedderClient
from graphiti_core.graphiti import Graphiti
from graphiti_core.graphiti_types import GraphitiClients
from graphiti_core.llm_client import LLMClient
from graphiti_core.tracer import Tracer


@pytest.fixture
def mock_driver():
    """Create a mock graph driver"""
    driver = Mock(spec=GraphDriver)
    driver.close = Mock()
    return driver


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    mock_llm = Mock(spec=LLMClient)
    mock_llm.config = Mock()
    mock_llm.model = 'test-model'
    mock_llm.set_tracer = Mock()
    mock_llm.health_check = Mock(return_value=True)
    return mock_llm


@pytest.fixture
def mock_embedder():
    """Create a mock embedder"""
    return Mock(spec=EmbedderClient)


@pytest.fixture
def mock_cross_encoder():
    """Create a mock cross encoder"""
    return Mock(spec=CrossEncoderClient)


@pytest.fixture
def mock_tracer():
    """Create a mock tracer"""
    return Mock(spec=Tracer)


class TestGraphitiClientsPreprocessingDefaults:
    """Test GraphitiClients instantiation with default preprocessing values"""

    def test_default_preprocessing_prompt_is_none(self, mock_driver, mock_llm_client,
                                                   mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_prompt defaults to None (AC-2.1)"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer
        )

        assert clients.preprocessing_prompt is None

    def test_default_preprocessing_mode_is_prepend(self, mock_driver, mock_llm_client,
                                                    mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode defaults to 'prepend' (AC-2.2)"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer
        )

        assert clients.preprocessing_mode == "prepend"


class TestGraphitiClientsPreprocessingExplicit:
    """Test GraphitiClients instantiation with explicit preprocessing values"""

    def test_explicit_preprocessing_prompt_string(self, mock_driver, mock_llm_client,
                                                    mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_prompt accepts string value (AC-2.1)"""
        prompt = "Test preprocessing prompt"
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_prompt=prompt
        )

        assert clients.preprocessing_prompt == prompt

    def test_explicit_preprocessing_prompt_none(self, mock_driver, mock_llm_client,
                                                 mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_prompt accepts None explicitly (AC-2.1)"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_prompt=None
        )

        assert clients.preprocessing_prompt is None

    def test_explicit_preprocessing_mode_prepend(self, mock_driver, mock_llm_client,
                                                  mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode accepts 'prepend' (AC-2.2)"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_mode="prepend"
        )

        assert clients.preprocessing_mode == "prepend"

    def test_explicit_preprocessing_mode_append(self, mock_driver, mock_llm_client,
                                                 mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode accepts 'append' (AC-2.2)"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_mode="append"
        )

        assert clients.preprocessing_mode == "append"


class TestGraphitiInitPreprocessingParameters:
    """Test Graphiti.__init__ accepts and passes preprocessing parameters"""

    def test_graphiti_accepts_preprocessing_prompt(self, mock_driver, mock_llm_client,
                                                     mock_embedder, mock_cross_encoder):
        """Test Graphiti.__init__ accepts preprocessing_prompt parameter (AC-2.3)"""
        prompt = "Test prompt for Graphiti"

        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            preprocessing_prompt=prompt
        )

        # Verify the parameter was passed to GraphitiClients
        assert graphiti.clients.preprocessing_prompt == prompt

    def test_graphiti_accepts_preprocessing_mode(self, mock_driver, mock_llm_client,
                                                   mock_embedder, mock_cross_encoder):
        """Test Graphiti.__init__ accepts preprocessing_mode parameter (AC-2.3)"""
        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            preprocessing_mode="append"
        )

        # Verify the parameter was passed to GraphitiClients
        assert graphiti.clients.preprocessing_mode == "append"

    def test_graphiti_passes_both_preprocessing_params(self, mock_driver, mock_llm_client,
                                                        mock_embedder, mock_cross_encoder):
        """Test Graphiti.__init__ passes both preprocessing params to GraphitiClients (AC-2.3)"""
        prompt = "Combined test prompt"
        mode = "append"

        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            preprocessing_prompt=prompt,
            preprocessing_mode=mode
        )

        assert graphiti.clients.preprocessing_prompt == prompt
        assert graphiti.clients.preprocessing_mode == mode


class TestGraphitiBackwardCompatibility:
    """Test backward compatibility: existing instantiation patterns still work"""

    def test_graphiti_without_preprocessing_params(self, mock_driver, mock_llm_client,
                                                     mock_embedder, mock_cross_encoder):
        """Test Graphiti instantiation without preprocessing params works (AC-2.4)"""
        # This should not raise any errors - backward compatible
        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder
        )

        # Verify defaults are applied
        assert graphiti.clients.preprocessing_prompt is None
        assert graphiti.clients.preprocessing_mode == "prepend"

    def test_graphiti_with_only_required_params(self, mock_driver):
        """Test minimal Graphiti instantiation still works (AC-2.4)"""
        # Graphiti with only driver - should use defaults for everything
        graphiti = Graphiti(
            graph_driver=mock_driver
        )

        # Verify preprocessing defaults
        assert graphiti.clients.preprocessing_prompt is None
        assert graphiti.clients.preprocessing_mode == "prepend"


class TestPreprocessingTypeValidation:
    """Test type validation for preprocessing parameters"""

    def test_preprocessing_prompt_accepts_none(self, mock_driver, mock_llm_client,
                                                mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_prompt type validation: accepts None"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_prompt=None
        )

        assert clients.preprocessing_prompt is None

    def test_preprocessing_prompt_accepts_string(self, mock_driver, mock_llm_client,
                                                  mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_prompt type validation: accepts string"""
        prompt = "Valid string prompt"
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_prompt=prompt
        )

        assert clients.preprocessing_prompt == prompt

    def test_preprocessing_mode_accepts_prepend(self, mock_driver, mock_llm_client,
                                                 mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode type validation: accepts 'prepend'"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_mode="prepend"
        )

        assert clients.preprocessing_mode == "prepend"

    def test_preprocessing_mode_accepts_append(self, mock_driver, mock_llm_client,
                                                mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode type validation: accepts 'append'"""
        clients = GraphitiClients(
            driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            tracer=mock_tracer,
            preprocessing_mode="append"
        )

        assert clients.preprocessing_mode == "append"

    def test_preprocessing_mode_rejects_invalid_value(self, mock_driver, mock_llm_client,
                                                       mock_embedder, mock_cross_encoder, mock_tracer):
        """Test preprocessing_mode type validation: rejects invalid values"""
        with pytest.raises(Exception):  # Pydantic validation error
            GraphitiClients(
                driver=mock_driver,
                llm_client=mock_llm_client,
                embedder=mock_embedder,
                cross_encoder=mock_cross_encoder,
                tracer=mock_tracer,
                preprocessing_mode="invalid_mode"  # Should fail validation
            )


class TestGraphitiIntegrationPreprocessing:
    """Integration tests: Full Graphiti initialization with preprocessing parameters"""

    def test_full_graphiti_initialization_with_preprocessing(self, mock_driver, mock_llm_client,
                                                              mock_embedder, mock_cross_encoder):
        """Test full Graphiti initialization with preprocessing parameters set"""
        prompt = "Full integration test prompt"
        mode = "append"

        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            preprocessing_prompt=prompt,
            preprocessing_mode=mode
        )

        # Verify all clients are initialized
        assert graphiti.clients is not None
        assert graphiti.clients.driver == mock_driver
        assert graphiti.clients.llm_client == mock_llm_client
        assert graphiti.clients.embedder == mock_embedder
        assert graphiti.clients.cross_encoder == mock_cross_encoder

        # Verify preprocessing fields are set correctly
        assert graphiti.clients.preprocessing_prompt == prompt
        assert graphiti.clients.preprocessing_mode == mode

    def test_graphiti_clients_accessible_with_preprocessing(self, mock_driver, mock_llm_client,
                                                             mock_embedder, mock_cross_encoder):
        """Test GraphitiClients can be accessed via Graphiti.clients with preprocessing fields"""
        prompt = "Accessibility test prompt"

        graphiti = Graphiti(
            graph_driver=mock_driver,
            llm_client=mock_llm_client,
            embedder=mock_embedder,
            cross_encoder=mock_cross_encoder,
            preprocessing_prompt=prompt
        )

        # Access clients through graphiti instance
        clients = graphiti.clients

        # Verify preprocessing fields are accessible
        assert hasattr(clients, 'preprocessing_prompt')
        assert hasattr(clients, 'preprocessing_mode')
        assert clients.preprocessing_prompt == prompt
        assert clients.preprocessing_mode == "prepend"
