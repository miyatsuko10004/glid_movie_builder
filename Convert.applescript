#!/usr/bin/osascript

-- Convert.applescript
-- convert.shを実行するためのAppleScript
-- ダブルクリックで実行できるようにするためのラッパー

on run
	tell application "Terminal"
		-- スクリプトのディレクトリを取得
		set scriptPath to (POSIX path of ((path to me as text) & "::"))
		-- activateをtrueにすると、Terminal.appがフォーカスされる
		do script "cd \"" & scriptPath & "\" && ./convert.sh" in front window
		activate
	end tell
end run 