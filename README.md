# 模擬テスト生成サポート

## 使い方（ローカル実行）

1. 依存関係をインストール
```
pip install -r requirements.txt
```

2. サーバー起動
```
uvicorn server.app:app --reload
```

3. ブラウザで `http://127.0.0.1:8000/` にアクセス

## PDF保管ルール

- 過去問PDF: `past_tests_db/中学校名/学年/実施年_学期.pdf`
- 問題集PDF:
  - 問題: `problem_sets/準拠/questions/`
  - 解答: `problem_sets/準拠/answers/`

### 教科書ページの対応表（任意）

教科書ページと問題集PDFページの対応が必要な場合は、
`problem_sets/準拠/page_map.csv` を用意してください。

```
textbook_page,pdf_file,pdf_page
12,math_text01.pdf,3
13,math_text01.pdf,4
```

### 教科書ページ自動マッピング

`page_map.csv` が無い場合、OCRで「p.12」「ページ12」などの表記を検出して
教科書ページとPDFページを自動対応付けします。

## 出力

- 生成されたPDFは `generated/` に保存されます。

## OCRを使う場合

スキャンPDFの文字抽出にTesseractを使います。

- Windows: Tesseractをインストールし、`TESSERACT_CMD` にパスを設定
- 画像化に `poppler` が必要です（`pdf2image` 利用）

例:
```
setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
setx OCR_ENABLED "true"
```
