@echo off
setlocal enabledelayedexpansion

echo Создание структуры папок и файлов...
powershell -NoProfile -Command ^
    "$exclude = @('.git', 'venv');" ^
    "function Get-Tree($Path = '.', $Indent = '') {" ^
        "$items = Get-ChildItem -Path $Path | Where-Object { $_.Name -notin $exclude };" ^
        $count = ($items | Measure-Object).Count;" ^
        $i = 0;" ^
        "foreach ($item in $items) {" ^
            $i++;" ^
            $isLast = ($i -eq $count);" ^
            "if ($item.PSIsContainer) {" ^
                "Write-Output (\"!Indent!$(if ($isLast) {'└──'} else {'├──'}) $($item.Name)\");" ^
                "$newIndent = \"!Indent!$(if ($isLast) {'    '} else {'│   '})\";" ^
                "Get-Tree -Path $item.FullName -Indent $newIndent;" ^
            "} else {" ^
                "Write-Output (\"!Indent!$(if ($isLast -and ($items.PSIsContainer -contains $true).Count -eq 0) {'└──'} else {'├──'}) $($item.Name)\");" ^
            "}" ^
        "}" ^
    "};" ^
    "Get-Tree | Out-File -FilePath 'structure.txt' -Encoding UTF8"

echo Готово! Результат сохранен в structure.txt
endlocal