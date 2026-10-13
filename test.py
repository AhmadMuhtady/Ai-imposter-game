import unittest
from unittest.mock import MagicMock, patch
import openai
import anthropic

from input_and_validation import user_input
from game_logic import (
    add_clue,
    add_vote,
    resolve_game,
    prepare_player_context,
    prepare_voting_context,
)
from ai_models import (
    InvalidAIResponseError,
    generate_compatible_clue,
    generate_compatible_vote,
    generate_claude_clue,
    generate_claude_vote,
)
from main import run_clue_phase, run_voting_phase, run_game
from players import setup_players


class TestInputValidation(unittest.TestCase):
    """Tests for input_and_validation.py."""

    def test_valid_input(self):
        cat, word = user_input("Animals", "Lion")
        self.assertEqual(cat, "Animals")
        self.assertEqual(word, "Lion")

    def test_multi_word_secret_rejected(self):
        with self.assertRaises(ValueError):
            user_input("Dessert", "Ice Cream")

    def test_reserved_imposter_rejected(self):
        with self.assertRaises(ValueError):
            user_input("Roles", "Imposter")
        with self.assertRaises(ValueError):
            user_input("Roles", "impostor")

    def test_length_and_empty_checks(self):
        with self.assertRaises(ValueError):
            user_input("", "Valid")
        with self.assertRaises(ValueError):
            user_input("Valid", "A" * 35)


class TestGameLogic(unittest.TestCase):
    """Tests for game_logic.py."""

    def test_clue_validation(self):
        clues = []
        # Valid clue
        add_clue(clues, "ChatGPT", "Mane", "Lion")
        self.assertEqual(len(clues), 1)

        # Multi-word clue rejected
        with self.assertRaises(ValueError):
            add_clue(clues, "Claude", "Big Cat", "Lion")

        # Secret word revealed rejected
        with self.assertRaises(ValueError):
            add_clue(clues, "Claude", "Lion", "Lion")

        # Duplicate clue text rejected
        with self.assertRaises(ValueError):
            add_clue(clues, "Gemini", "Mane", "Lion")

        # Duplicate player clue submission rejected
        with self.assertRaises(ValueError):
            add_clue(clues, "ChatGPT", "Roar", "Lion")

    def test_vote_validation(self):
        votes = []
        candidates = ["ChatGPT", "Claude", "Gemini"]

        # Valid vote
        add_vote(
            votes,
            "Groq",
            {"vote": "Claude", "reason": "Their clue was suspicious."},
            candidates,
            secret_word="Lion",
        )
        self.assertEqual(len(votes), 1)

        # Self-voting rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Claude",
                {"vote": "Claude", "reason": "Self vote."},
                candidates,
                secret_word="Lion",
            )

        # Duplicate voter rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Groq",
                {"vote": "ChatGPT", "reason": "Another vote."},
                candidates,
                secret_word="Lion",
            )

        # Multi-sentence reason rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Gemini",
                {"vote": "Claude", "reason": "First sentence. Second sentence."},
                candidates,
                secret_word="Lion",
            )

        # Secret word leaked in reason rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "Claude", "reason": "I think the secret word is Lion."},
                candidates,
                secret_word="Lion",
            )

        # Unknown candidate rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "UnknownBot", "reason": "Suspicious play."},
                candidates,
                secret_word="Lion",
            )

    def test_resolve_game_outcomes(self):
        players = [
            {"name": "ChatGPT"},
            {"name": "Claude"},
            {"name": "Gemini"},
            {"name": "Groq"},
        ]

        # Case 1: Imposter correctly identified
        votes_innocent_win = [
            {"name": "ChatGPT", "vote": "Groq", "reason": "Vague."},
            {"name": "Claude", "vote": "Groq", "reason": "Suspicious."},
            {"name": "Gemini", "vote": "Groq", "reason": "Off-theme."},
            {"name": "Groq", "vote": "Claude", "reason": "Deflecting."},
        ]
        res = resolve_game(players, votes_innocent_win, imposter="Groq")
        self.assertEqual(res["winner"], "Innocents")
        self.assertFalse(res["is_tie"])

        # Case 2: Imposter survives due to tie
        votes_tie = [
            {"name": "ChatGPT", "vote": "Groq", "reason": "Vague."},
            {"name": "Claude", "vote": "Gemini", "reason": "Suspicious."},
            {"name": "Gemini", "vote": "Claude", "reason": "Off-theme."},
            {"name": "Groq", "vote": "ChatGPT", "reason": "Deflecting."},
        ]
        res_tie = resolve_game(players, votes_tie, imposter="Groq")
        self.assertEqual(res_tie["winner"], "Imposter")
        self.assertTrue(res_tie["is_tie"])

        # Case 3: Unknown target in votes raises ValueError
        invalid_votes = [
            {"name": "ChatGPT", "vote": "GhostPlayer", "reason": "Invalid."}
        ]
        with self.assertRaises(ValueError):
            resolve_game(players, invalid_votes, imposter="Groq")


class TestAIModels(unittest.TestCase):
    """Tests for ai_models.py response parsing and custom exceptions."""

    def test_empty_choice_list_raises_invalid_ai_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices simulation
        mock_client.chat.completions.create.return_value = mock_response

        ctx = {
            "category": "Animals",
            "secret_word": "Lion",
            "previous_clues": [],
        }
        with self.assertRaises(InvalidAIResponseError):
            generate_compatible_clue(ctx, mock_client, {"model": "test"}, {})

        vote_ctx = {"name": "ChatGPT", "secret_word": "Lion", "category": "Animals", "clues": [], "candidates": []}
        with self.assertRaises(InvalidAIResponseError):
            generate_compatible_vote(vote_ctx, mock_client, {"model": "test"}, {})

    def test_malformed_json_raises_invalid_ai_response(self):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Not Valid JSON {"
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        ctx = {
            "category": "Animals",
            "secret_word": "Lion",
            "previous_clues": [],
        }
        with self.assertRaises(InvalidAIResponseError):
            generate_compatible_clue(ctx, mock_client, {"model": "test"}, {})

    def test_invalid_structure_raises_invalid_ai_response(self):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        # Missing 'clue' key
        mock_choice.message.content = '{"wrong_key": "Roar"}'
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        ctx = {
            "category": "Animals",
            "secret_word": "Lion",
            "previous_clues": [],
        }
        with self.assertRaises(InvalidAIResponseError):
            generate_compatible_clue(ctx, mock_client, {"model": "test"}, {})

    def test_claude_invalid_context_type(self):
        with self.assertRaises(TypeError):
            generate_claude_clue("Not a dict")
        with self.assertRaises(TypeError):
            generate_claude_vote(["Not a dict"])


class TestMainErrorHandlingAndFlow(unittest.TestCase):
    """Tests for main.py retry behavior, exception hierarchy, and game execution."""

    def setUp(self):
        self.players = [
            {"name": "ChatGPT", "secret_word": "Lion", "category": "Animals"},
            {"name": "Claude", "secret_word": "Lion", "category": "Animals"},
            {"name": "Gemini", "secret_word": "Lion", "category": "Animals"},
            {"name": "Groq", "secret_word": "Imposter", "category": "Animals"},
        ]

    @patch("main.generate_clue")
    def test_authentication_error_aborts_immediately(self, mock_gen):
        mock_gen.side_effect = openai.AuthenticationError(
            message="Invalid API Key",
            response=MagicMock(status_code=401),
            body=None,
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_clue_phase(self.players, "Lion")
        self.assertIn("Authentication failed", str(ctx.exception))

    @patch("main.generate_clue")
    def test_rate_limit_error_aborts_immediately(self, mock_gen):
        mock_gen.side_effect = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_clue_phase(self.players, "Lion")
        self.assertIn("Rate limit reached", str(ctx.exception))

    @patch("main.generate_clue")
    def test_connection_error_retries_and_succeeds(self, mock_gen):
        # Fails once with connection error, then succeeds
        mock_gen.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            "Roar",
            "Claw",
            "Safari",
            "Cat",
        ]
        clues = run_clue_phase(self.players, "Lion")
        self.assertEqual(len(clues), 4)
        self.assertEqual(clues[0]["clue"], "Roar")

    @patch("main.generate_clue")
    def test_exhausted_retries_aborts_game(self, mock_gen):
        # 3 consecutive 500 server errors
        mock_gen.side_effect = openai.InternalServerError(
            message="Internal Server Error",
            response=MagicMock(status_code=500),
            body=None,
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_clue_phase(self.players, "Lion")
        self.assertIn("failed to produce a valid clue after 3 attempts", str(ctx.exception))

    @patch("main.generate_vote")
    @patch("main.generate_clue")
    def test_full_game_simulation(self, mock_clue, mock_vote):
        mock_clue.side_effect = ["Mane", "Predator", "Savannah", "Jungle"]
        mock_vote.side_effect = [
            {"vote": "Groq", "reason": "Jungle was a weak clue."},
            {"vote": "Groq", "reason": "They are clearly the imposter."},
            {"vote": "Groq", "reason": "Jungle is not accurate."},
            {"vote": "Claude", "reason": "Predator was too generic."},
        ]

        result = run_game("Animals", "Lion")
        self.assertEqual(result["category"], "Animals")
        self.assertEqual(result["secret_word"], "Lion")
        self.assertEqual(len(result["clues"]), 4)
        self.assertEqual(len(result["votes"]), 4)
        self.assertIn(result["results"]["winner"], ["Innocents", "Imposter"])


if __name__ == "__main__":
    unittest.main()