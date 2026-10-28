import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.rag import generator


class GeneratorCompletionTests(unittest.TestCase):
    def test_retries_temporary_provider_unavailability(self):
        response = SimpleNamespace(text="Câu trả lời.", candidates=[], usage_metadata=None)
        temporary_error = RuntimeError("model is currently experiencing high demand")
        temporary_error.code = 503
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=unittest.mock.Mock(side_effect=[temporary_error, response])
            )
        )

        with (
            patch.object(generator, "_client", client),
            patch.object(generator.time, "sleep") as sleep,
            patch.object(generator.random, "uniform", return_value=0),
        ):
            result = generator._generate_content_with_retry(model="test")

        self.assertIs(result, response)
        self.assertEqual(client.models.generate_content.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_does_not_retry_non_transient_provider_errors(self):
        error = RuntimeError("invalid API key")
        error.code = 401
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=unittest.mock.Mock(side_effect=error))
        )

        with patch.object(generator, "_client", client), patch.object(generator.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "invalid API key"):
                generator._generate_content_with_retry(model="test")

        self.assertEqual(client.models.generate_content.call_count, 1)
        sleep.assert_not_called()

    def test_retries_an_answer_without_a_complete_ending(self):
        usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=8)
        incomplete = SimpleNamespace(
            text="Bạn muốn tìm hiểu về ngành, bạn quan tâm đến",
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=usage,
        )
        complete = SimpleNamespace(
            text="Bạn quan tâm đến chương trình học hay cơ hội nghề nghiệp?",
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=usage,
        )
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=unittest.mock.Mock(side_effect=[incomplete, complete])
            )
        )

        with patch.object(generator, "_client", client):
            answer, _ = generator.generate("ngành công nghệ thông tin", [], True)

        self.assertEqual(answer, complete.text)
        self.assertEqual(client.models.generate_content.call_count, 2)
        retry_prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("CÂU TRẢ LỜI TRƯỚC BỊ NGẮT GIỮA CHỪNG", retry_prompt)

    def test_retries_when_model_reports_max_tokens(self):
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")],
        )

        self.assertTrue(generator._needs_completion(response, "Câu trả lời đầy đủ."))

    def test_keeps_a_complete_answer_with_source_citation(self):
        response = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason="STOP")],
        )

        self.assertFalse(generator._needs_completion(response, "Câu trả lời. [Tài liệu]"))


if __name__ == "__main__":
    unittest.main()
