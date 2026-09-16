# APKをGitHub Actionsで自動作成する手順

このプロジェクトには `.github/workflows/build-apk.yml` を追加済みです。
GitHubに置くと、Android StudioなしでGitHub側がAPKを自動ビルドします。

## 最初の1回

1. GitHubで新しい空のリポジトリを作成します。
2. このZIPを解凍し、`GreenReaderPrototype` フォルダの**中身を丸ごと**リポジトリへアップロードします。
   - `.github` フォルダも必ず含めます。
3. `main` ブランチへ保存（commit）します。
4. GitHubのリポジトリ上部にある **Actions** を開きます。
5. 左側の **Build Android APK** を選びます。
6. 初回pushで自動実行されていれば、その実行を開きます。実行されていなければ **Run workflow** → **Run workflow** を押します。
7. ビルドが成功すると、実行ページ下部の **Artifacts** に
   `GreenReaderPrototype-v0.2-debug-apk` が表示されます。
8. そのArtifactをダウンロードしてZIPを開くと、
   `GreenReaderPrototype-v0.2-debug.apk` が入っています。

## M07へのインストール

1. APKをFCNT arrows We2 M07へ保存します。
2. M07のファイルアプリで `GreenReaderPrototype-v0.2-debug.apk` をタップします。
3. 初回だけ「この提供元のアプリを許可」等が表示されたら、インストールを許可します。
4. **インストール**を押します。
5. インストール後、アプリ一覧から GreenReaderPrototype を起動します。

## 更新するとき

コードをGitHubへpushするたびに自動ビルドされます。
また、Actions画面から **Run workflow** を押して手動ビルドすることもできます。

## 注意

- このAPKは開発用の `debug` APKです。個人のM07で試す目的には十分です。
- Google Play公開用の正式な署名済みリリースAPK/AABではありません。
- 初回ビルド時はAndroid SDKや依存ライブラリをGitHub側で取得するため、数分かかることがあります。
