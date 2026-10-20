"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask

対話モードでは会話履歴を保持したまま続けて質問できる。
``/refresh`` で履歴と累積トークン数をリセットし、``/quit`` で終了する。

ツールを持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import sys

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


class Conversation:
    """1つの会話における履歴と累積トークン数を管理する。"""

    def __init__(self) -> None:
        self.client = genai.Client(api_key=get_api_key())
        self.history: list[types.Content] = []
        self.input_tokens = 0
        self.output_tokens = 0

    def refresh(self) -> None:
        self.history.clear()
        self.input_tokens = 0
        self.output_tokens = 0

    def ask(self, question: str) -> str:
        self.history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)],
            )
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=self.history,
        )
        if not response.candidates or response.candidates[0].content is None:
            raise RuntimeError("モデルから回答を受け取れませんでした。")

        self.history.append(response.candidates[0].content)
        usage = response.usage_metadata
        self.input_tokens += usage.prompt_token_count or 0
        self.output_tokens += usage.candidates_token_count or 0
        print(
            f"[tokens] input={self.input_tokens}, "
            f"output={self.output_tokens}"
        )
        return response.text


def ask(question: str) -> str:
    """後方互換のため、1回だけ質問する。"""
    return Conversation().ask(question)


def _run_interactive(conversation: Conversation, first_question: str | None) -> None:
    if first_question:
        print(f"[質問] {first_question}\n")
        print(conversation.ask(first_question))

    while True:
        try:
            question = input("\n質問> ").strip()
        except EOFError:
            print()
            return
        if not question:
            continue
        if question in {"/quit", "/exit"}:
            return
        if question in {"/refresh", "/reset"}:
            conversation.refresh()
            print("[conversation] 履歴と累積トークン数をリセットしました。")
            continue
        print(conversation.ask(question))


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    parser.add_argument(
        "--once",
        action="store_true",
        help="対話モードに入らず、1回だけ質問する",
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        interactive = not args.once and sys.stdin.isatty()
        if interactive:
            _run_interactive(Conversation(), args.question)
        else:
            question = args.question or DEFAULT_QUESTION
            print(f"[質問] {question}\n")
            print(ask(question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
