"""
Unit tests for TextAnalyzer.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestTextAnalyzer:
    """Tests for TextAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create TextAnalyzer with mocked model."""
        with patch('app.analysis.text_analyzer.get_model_manager') as mock_manager:
            mock_classifier = MagicMock()
            mock_classifier.return_value = [{'label': 'non-toxic', 'score': 0.9}]
            mock_manager.return_value.text_classifier = mock_classifier

            from app.analysis.text_analyzer import TextAnalyzer
            return TextAnalyzer()

    def test_analyze_empty_text(self, analyzer):
        """Test analyzing empty text returns error."""
        result = analyzer.analyze("")
        assert result['class'] == 'Error'

    def test_analyze_none_text(self, analyzer):
        """Test analyzing None returns error."""
        result = analyzer.analyze(None)
        assert result['class'] == 'Error'

    def test_analyze_violent_keywords(self, analyzer):
        """Test detection of violent keywords."""
        result = analyzer.analyze("I will kill you")
        assert result['class'] == 'Violence'
        assert 'kill' in str(result.get('keywords_found', []))

    def test_analyze_safe_text(self, analyzer):
        """Test safe text returns non-violence."""
        result = analyzer.analyze("The sun is shining today")
        assert result['class'] == 'Non-Violence'

    def test_analyze_threat_patterns(self, analyzer):
        """Test detection of threat patterns."""
        result = analyzer.analyze("I will destroy everything")
        assert result['class'] == 'Violence'

    def test_result_has_required_fields(self, analyzer):
        """Test that result has all required fields."""
        result = analyzer.analyze("Test text")
        assert 'class' in result
        assert 'confidence' in result
        assert 'reasoning' in result

    def test_confidence_in_valid_range(self, analyzer):
        """Test that confidence is between 0 and 100."""
        result = analyzer.analyze("I will kill you with love and kindness")
        assert 0 <= result['confidence'] <= 100


class TestTextAnalyzerKeywords:
    """Tests for keyword detection."""

    @pytest.fixture
    def analyzer(self):
        """Create TextAnalyzer with mocked model."""
        with patch('app.analysis.text_analyzer.get_model_manager') as mock_manager:
            mock_classifier = MagicMock()
            mock_classifier.return_value = [{'label': 'non-toxic', 'score': 0.5}]
            mock_manager.return_value.text_classifier = mock_classifier

            from app.analysis.text_analyzer import TextAnalyzer
            return TextAnalyzer()

    def test_extreme_keywords(self, analyzer):
        """Test detection of extreme violence keywords."""
        extreme_words = ['kill', 'murder', 'assassinate', 'massacre']
        for word in extreme_words:
            result = analyzer.analyze(f"I will {word}")
            assert result['class'] == 'Violence', f"Failed to detect: {word}"

    def test_weapon_keywords(self, analyzer):
        """Test detection of weapon keywords."""
        weapon_words = ['gun', 'knife', 'bomb']
        for word in weapon_words:
            result = analyzer.analyze(f"He has a {word}")
            assert result['class'] == 'Violence', f"Failed to detect: {word}"

    def test_case_insensitive(self, analyzer):
        """Test that detection is case insensitive."""
        result = analyzer.analyze("I WILL KILL YOU")
        assert result['class'] == 'Violence'
