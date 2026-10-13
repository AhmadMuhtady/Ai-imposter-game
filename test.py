import os
import unittest
from unittest.mock import MagicMock, patch
import openai
import anthropic

# Ensure fake credentials exist before SDK imports in local offline environments
os.environ.setdefault("OPENAI_API_KEY", "mock-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "mock-anthropic-key")
os.environ.setdefault("GOOGLE_API_KEY", "mock-google-key")
os.environ.setdefault("GROQAI_API_KEY", "mock-groq-key")

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

    def test_punctuation_only_rejected(self):
        # Reject punctuation-only category
        with self.assertRaises(ValueError):
            user_input("???", "Lion")
        # Reject punctuation-only secret word
        with self.assertRaises(ValueError):
            user_input("Animals", "!!!")


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

        # Secret word revealed with edge punctuation rejected ("Lion!")
        with self.assertRaises(ValueError):
            add_clue(clues, "Claude", "Lion!", "Lion")

        # Punctuation-only clue rejected ("!!!")
        with self.assertRaises(ValueError):
            add_clue(clues, "Claude", "!!!", "Lion")

        # Duplicate clue text rejected
        with self.assertRaises(ValueError):
            add_clue(clues, "Gemini", "Mane", "Lion")

        # Duplicate clue text with edge punctuation rejected ("Mane!")
        with self.assertRaises(ValueError):
            add_clue(clues, "Gemini", "Mane!", "Lion")

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
            secret_word="icecream",
        )
        self.assertEqual(len(votes), 1)

        # Self-voting rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Claude",
                {"vote": "Claude", "reason": "Self vote."},
                candidates,
                secret_word="icecream",
            )

        # Duplicate voter rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Groq",
                {"vote": "ChatGPT", "reason": "Another vote."},
                candidates,
                secret_word="icecream",
            )

        # Multi-sentence reason rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "Gemini",
                {"vote": "Claude", "reason": "First sentence. Second sentence."},
                candidates,
                secret_word="icecream",
            )

        # Secret word leaked (exact) rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "Claude", "reason": "I think the secret word is icecream."},
                candidates,
                secret_word="icecream",
            )

        # Secret word leaked with space rejected ("ice cream")
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "Claude", "reason": "It definitely tastes like ice cream."},
                candidates,
                secret_word="icecream",
            )

        # Secret word leaked with hyphen rejected ("ice-cream")
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "Claude", "reason": "They are talking about ice-cream."},
                candidates,
                secret_word="icecream",
            )

        # Unknown candidate rejected
        with self.assertRaises(ValueError):
            add_vote(
                votes,
                "ChatGPT",
                {"vote": "UnknownBot", "reason": "Suspicious play."},
                candidates,
                secret_word="icecream",
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

        # Case 3: Incomplete voting round (fewer votes than players) rejected
        incomplete_votes = [
            {"name": "ChatGPT", "vote": "Groq", "reason": "Vague."},
            {"name": "Claude", "vote": "Groq", "reason": "Suspicious."},
        ]
        with self.assertRaises(ValueError):
            resolve_game(players, incomplete_votes, imposter="Groq")

        # Case 4: Unknown voter name rejected
        unknown_voter = [
            {"name": "ChatGPT", "vote": "Groq", "reason": "Vague."},
            {"name": "Claude", "vote": "Groq", "reason": "Suspicious."},
            {"name": "Gemini", "vote": "Groq", "reason": "Off-theme."},
            {"name": "GhostVoter", "vote": "Claude", "reason": "Deflecting."},
        ]
        with self.assertRaises(ValueError):
            resolve_game(players, unknown_voter, imposter="Groq")

        # Case 5: Unknown candidate target rejected
        invalid_target = [
            {"name": "ChatGPT", "vote": "GhostPlayer", "reason": "Invalid."},
            {"name": "Claude", "vote": "Groq", "reason": "Suspicious."},
            {"name": "Gemini", "vote": "Groq", "reason": "Off-theme."},
            {"name": "Groq", "vote": "Claude", "reason": "Deflecting."},
        ]
        with self.assertRaises(ValueError):
            resolve_game(players, invalid_target, imposter="Groq")

        # Case 6: Self-voting rejected in resolver
        self_vote = [
            {"name": "ChatGPT", "vote": "ChatGPT", "reason": "Self vote."},
            {"name": "Claude", "vote": "Groq", "reason": "Suspicious."},
            {"name": "Gemini", "vote": "Groq", "reason": "Off-theme."},
            {"name": "Groq", "vote": "Claude", "reason": "Deflecting."},
        ]
        with self.assertRaises(ValueError):
            resolve_game(players, self_vote, imposter="Groq")


class TestAIModels(unittest.TestCase):
    """Tests for ai_models.py response parsing and custom exceptions."""

    def test_empty_choice_list_raises_invalid_ai_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = []
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
        mock_gen.side_effect = openai.InternalServerError(
            message="Internal Server Error",
            response=MagicMock(status_code=500),
            body=None,
        )
        with self.assertRaises(RuntimeError) as ctx:
            run_clue_phase(self.players, "Lion")
        self.assertIn("failed to produce a valid clue after 3 attempts", str(ctx.exception))

    @patch("main.generate_vote")
    def test_voting_phase_authentication_error_aborts(self, mock_vote):
        mock_vote.side_effect = openai.AuthenticationError(
            message="Invalid API Key",
            response=MagicMock(status_code=401),
            body=None,
        )
        clues = [
            {"name": "ChatGPT", "clue": "Mane"},
            {"name": "Claude", "clue": "Predator"},
            {"name": "Gemini", "clue": "Savannah"},
            {"name": "Groq", "clue": "Jungle"},
        ]
        with self.assertRaises(RuntimeError) as ctx:
            run_voting_phase(self.players, clues, "Lion")
        self.assertIn("Authentication failed", str(ctx.exception))

    @patch("main.setup_players")
    @patch("main.generate_vote")
    @patch("main.generate_clue")
    def test_full_game_simulation(self, mock_clue, mock_vote, mock_setup):
        # 1. Force a deterministic player arrangement (eliminates random shuffle flakiness)
        deterministic_players = [
            {"name": "ChatGPT", "category": "Animals", "secret_word": "Lion"},
            {"name": "Claude", "category": "Animals", "secret_word": "Lion"},
            {"name": "Gemini", "category": "Animals", "secret_word": "Lion"},
            {"name": "Groq", "category": "Animals", "secret_word": "Imposter"},
        ]
        mock_setup.return_value = (deterministic_players, "Groq")

        # 2. Sequential clues for each player in order
        mock_clue.side_effect = ["Mane", "Predator", "Savannah", "Jungle"]

        # 3. Deterministic votes tailored to each player's turn:
        # ChatGPT -> votes Groq
        # Claude  -> votes Groq
        # Gemini  -> votes Groq
        # Groq    -> votes Claude (Groq cannot vote for itself)
        mock_vote.side_effect = [
            {"vote": "Groq", "reason": "Jungle is an unfitting habitat."},
            {"vote": "Groq", "reason": "Groq seems disconnected from the savannah."},
            {"vote": "Groq", "reason": "Jungle clue points directly to an imposter."},
            {"vote": "Claude", "reason": "Predator was overly vague."},
        ]

        result = run_game("Animals", "Lion")

        # 4. Strict assertions on the deterministic outcome
        self.assertEqual(result["category"], "Animals")
        self.assertEqual(result["secret_word"], "Lion")
        self.assertEqual(result["imposter"], "Groq")
        self.assertEqual(len(result["clues"]), 4)
        self.assertEqual(len(result["votes"]), 4)
        self.assertEqual(result["results"]["winner"], "Innocents")
        self.assertFalse(result["results"]["is_tie"])
        self.assertEqual(result["results"]["scores"]["Groq"], 3)
        self.assertEqual(result["results"]["scores"]["Claude"], 1)


if __name__ == "__main__":
    unittest.main()