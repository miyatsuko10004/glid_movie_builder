#!/usr/bin/osascript

-- Execute.applescript
-- execute.shを実行するためのAppleScript
-- ダブルクリックで実行できるようにするためのラッパー

on run
	-- スクリプトのディレクトリを取得
	set scriptPath to POSIX path of ((path to me as text) & "::")
	
	tell application "Terminal"
		activate
		
		-- 新しいウィンドウを開くか、既存のウィンドウを使用
		if (count of windows) is 0 then
			do script ""
		end if
		
		-- 最前面のウィンドウでコマンドを実行
		do script "cd \"" & scriptPath & "\" && ./execute.sh" in window 1
	end tell
end run 