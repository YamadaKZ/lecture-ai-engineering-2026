# 第6回 解答

## 演習

## 演習

<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：[tool call]   glossary_search_glossary({'query': '3レベル'})
- STEP 3 の [tool call]：[tool call]   fetch_fetch({'url': 'https://modelcontextprotocol.io/'})
- STEP 4 の [tool call]：
  - [tool call]   aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング 概要', 'topics': ['general']})
  - [tool call]   aws_aws___search_documentation({'search_phrase': 'Using versioning in S3 buckets Amazon S3', 'topics': ['general']})
- 気づき・疑問：
  - STEP 4 で1回目に日本語クエリで検索した結果が意図とズレていたため、モデルが自律的に英語クエリへ言い換えて再検索し、正しいドキュメントを取得できていた。
  - ローカルコマンド起動（glossary, fetch）とリモートURL接続（aws）という異なる方式の MCP サーバーを同じ仕組みで扱え、ツール名にはサーバー名のプレフィックスが自動で付与されることが分かった。
  - ツール数やツール説明文が増えるにつれて入力トークン数が STEP 2（697）→ STEP 3（2,161）→ STEP 4（11,087）と大きく増加しており、繋ぐサーバーの取捨選択がコストや精度面で重要だと感じた。

## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎
- やったこと：
  - サーバー側の `app/mcp_server.py` に `server.tool()(tools.get_lecture_summary)` の 1 行を追加し、用語集 MCP サーバーから `get_lecture_summary` を公開した。
  - エージェント側の設定ファイル（`app/mcp_servers.json`）およびコード（`app/mcp_agent.py`）は変更せずに、`--list-tools`・`--trace` での質問・`pytest` を順に実行して動作を確認した。
- 結果：
  - `uv run python -m app.mcp_agent --list-tools` を実行したところ、モデルに見えているツールが 8 個となり、一覧に `glossary_get_lecture_summary`（引数：`{"lecture": {"title": "Lecture", "type": "integer"}}`）が追加されていることを確認した。
  - `uv run python -m app.mcp_agent --trace "第2回では何を学びますか？"` を実行したところ（モデル：`gemini-3.5-flash-lite`）、以下の通り追加したツールが呼び出され、第2回「ファインチューニングとLoRA」の要点（事前学習との違い、SFT、PEFTとLoRA、QLoRAとの関係、演習内容）が正しく回答された。
    - `[tool call]   glossary_get_lecture_summary({'lecture': 2})`
    - `[tool return] glossary_get_lecture_summary -> # 第2回 ファインチューニングとLoRA ...`
    - `[usage] 入力 5,920 tokens / 出力 269 tokens / モデル応答 2 回`
  - `uv run pytest -q` を実行し、`21 passed`（1 warning）でテストがすべて通ることを確認した。
- 気づき・疑問：
  - エージェント側の設定やコードを一切書き換えなくても、サーバー側に 1 行足すだけで、起動時に取得するツール一覧へ自動的に反映され、モデルが適切に呼び出せることを確認できた。サーバー側とエージェント側を疎結合に保ったまま機能を拡張できる点が MCP の大きな利点だと感じた。
  - `app/tools.py` の関数の docstring と型ヒント（`lecture: int`）がそのまま MCP のツール説明文・引数スキーマとしてモデルに渡っており、関数定義の分かりやすさがそのままツールの使いやすさに直結することが分かった。
  - 今回は `glossary` だけでなく `fetch` や `aws` のサーバーも接続した状態で実行したため、講義の要点を 1 回取得しただけでも入力トークン数が 5,920 tokens になっていた。演習での気づきと同様に、用途に応じて接続するサーバーや公開ツールを絞る設計がコスト・精度の両面で重要だと改めて感じた。

---

- 取り組んだレベル：実装
- やったこと：
  - 第3回で作成した `app/tools.py` の `make_quiz` を、`app/mcp_server.py` に `server.tool()(tools.make_quiz)` として追加し、MCP ツールとして公開した。
  - 範囲外の講義回が指定された場合にモデルが状況を正しく判断できるよう、`app/tools.py` の `make_quiz` でクイズを作成できる回の一覧（`クイズを作れる回: 第1回, 第2回, 第3回, 第4回, 第6回`）も添えて `return` で返すように修正した。
  - エージェント側（`app/mcp_agent.py`・`app/mcp_servers.json`）は変更せず、範囲外（第99回）と正常系（第2回）の質問を `--trace` 付きで実行して挙動を確認した。
- 結果：
  - モデルに見えているツール数は 9 個に増え、`glossary_make_quiz` が認識されていた（モデル：`gemini-3.5-flash-lite`）。
  - **範囲外の質問**：`uv run python -m app.mcp_agent --trace "第99回のクイズを作って"`
    - `[tool call]   glossary_make_quiz({'lecture': 99})`
    - `[tool return] glossary_make_quiz -> 第99回の用語は用語集にありません。クイズを作れる回: 第1回, 第2回, 第3回, 第4回, 第6回…`
    - `[usage] 入力 5,630 tokens / 出力 96 tokens / モデル応答 2 回`
    - モデルは推測でクイズを作らず、第99回が用語集に登録されていないことと、作成可能な回（第1回・第2回・第3回・第4回・第6回）を一覧で案内し、どの回のクイズを希望するか聞き返す回答を生成した。
  - **正常系の質問**：`uv run python -m app.mcp_agent --trace "第2回のクイズを作って"`
    - `[tool call]   glossary_make_quiz({'lecture': 2})`
    - `[tool return] glossary_make_quiz -> {"question": "「事前学習」の意味は？", "answer": "大量の汎用テキストで、次のトークンを予測するようにモデルを学習させる最初の段階。言語の知識や一般的な常識の多くはここで身につく。"}…`
    - `[usage] 入力 5,643 tokens / 出力 91 tokens / モデル応答 2 回`
    - モデルは返却された JSON をもとに、「事前学習」の意味を問う確認問題を作成し、答えをそのまま出さずにヒントと「関係する回：第2回」を添えて出題した。
- 気づき・疑問：
  - 範囲外の入力に対して、利用可能な回の一覧を含めたメッセージを `return` で返すことで、`[tool return]` としてそのままモデルに伝わり、無駄な再試行をせずにユーザーへ次の選択肢を案内できた。
  - 正常系では、`make_quiz` が返した JSON に `answer` が含まれていたにもかかわらず、モデルは確認問題としての文脈を踏まえて答えを伏せ、問題とヒントだけを提示できていた。
  - ツールの戻り値はモデルが読んで次の応答を組み立てるための入力になるため、範囲外や失敗時に「何が問題か」だけでなく「次に選べる有効な値」も返すと、エージェントの応答品質が大きく上がると分かった。
