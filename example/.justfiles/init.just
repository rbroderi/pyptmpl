init:
    $python_version = $env:UV_INIT_PYTHON; \
    if (-not $python_version) { throw 'python_version is required. Run via init.ps1.' }; \
    $project_description = $env:UV_INIT_DESCRIPTION; \
    if (-not $project_description) { throw 'description is required. Run via init.ps1.' }; \
    $project_description_escaped = $project_description -replace '"', '\\"'; \
    $project_name = Read-Host 'project_name'; \
    if (-not $project_name) { throw 'project_name is required.' }; \
    uv init --lib --python $python_version $project_name; \
    $workspaceRoot = (Get-Location).Path; \
    $packageDir = $project_name; \
    if (-not (Test-Path $packageDir)) { \
    $altPackageDir = ($project_name -replace '-', '_'); \
    if (Test-Path $altPackageDir) { $packageDir = $altPackageDir } \
    }; \
    if (-not (Test-Path $packageDir)) { throw ('Package directory not found for: ' + $project_name) }; \
    $packageDirFull = (Resolve-Path $packageDir).Path; \
    $package_name = ($project_name -replace '-', '_'); \
    $project_version = (Get-Date -Format 'yyyy.MM.dd') + '.00'; \
    $license_id = 'LGPL-3.0-or-later'; \
    $license_classifier = 'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)'; \
    $gitAuthorName = ''; \
    $gitAuthorEmail = ''; \
    if (Get-Command git -ErrorAction SilentlyContinue) { \
    $gitAuthorName = (git config --get user.name 2>$null); \
    $gitAuthorEmail = (git config --get user.email 2>$null) \
    }; \
    if (-not $gitAuthorName) { $gitAuthorName = 'Your Name' }; \
    if (-not $gitAuthorEmail) { $gitAuthorEmail = 'you@example.com' }; \
    $gitAuthorNameEscaped = $gitAuthorName -replace '"', '\\"'; \
    $gitAuthorEmailEscaped = $gitAuthorEmail -replace '"', '\\"'; \
    $pyNoDot = ($python_version -replace '\.', ''); \
    $pyprojectPath = Join-Path $packageDir 'pyproject.toml'; \
    $pyprojectLines = @( \
    '[project]', \
    ('name = "' + $project_name + '"'), \
    ('version = "' + $project_version + '"'), \
    ('description = "' + $project_description_escaped + '"'), \
    'readme = "README.md"', \
    ('license = "' + $license_id + '"'), \
    ('authors = [{ name = "' + $gitAuthorNameEscaped + '", email = "' + $gitAuthorEmailEscaped + '" }]'), \
    ('requires-python = ">=' + $python_version + '"'), \
    'classifiers = [', \
    ('  "' + $license_classifier + '",'), \
    '  "Operating System :: Microsoft :: Windows",', \
    '  "Programming Language :: Python :: 3",', \
    ('  "Programming Language :: Python :: ' + $python_version + '",'), \
    ']', \
    'dependencies = ["beartype>=0.22.9"]', \
    '', \
    '[project.optional-dependencies]', \
    'dev = ["pytest>=9.0.3", "pytest-cov>=7.1.0", "pytest-sugar>=1.1.1"]', \
    '', \
    '[build-system]', \
    'requires = ["uv_build>=0.11.6"]', \
    'build-backend = "uv_build"', \
    '', \
    '[tool.basedpyright]', \
    'venvPath = "."', \
    'venv = ".venv"', \
    ('include = ["src", "src/' + $package_name + '/tests"]'), \
    ('pythonVersion = "' + $python_version + '"'), \
    'reportUnusedCallResult = "none"', \
    'reportAny = "none"', \
    'reportExplicitAny = "none"', \
    'reportImplicitStringConcatenation = "none"', \
    'reportUnusedFunction = "none"', \
    'reportMissingParameterType = "none"', \
    'reportUnknownParameterType = "none"', \
    'reportUnknownVariableType = "none"', \
    'reportUnknownArgumentType = "none"', \
    'reportUnknownMemberType = "none"', \
    '', \
    '[tool.ruff]', \
    'line-length = 120', \
    ('target-version = "py' + $pyNoDot + '"'), \
    '', \
    '[tool.ruff.lint.isort]', \
    'force-single-line = true', \
    '', \
    '[tool.coverage.run]', \
    ('source = ["src/' + $package_name + '"]'), \
    ('omit = ["src/' + $package_name + '/tests/*"]'), \
    '', \
    '[tool.ty.src]', \
    'exclude = ["typings"]' \
    ); \
    Set-Content -Path $pyprojectPath -Value ($pyprojectLines -join "`n") -Encoding UTF8; \
    Write-Host ('Updated ' + $pyprojectPath + ' with project/build/tool settings.'); \
    $testsDir = Join-Path (Join-Path (Join-Path $packageDir 'src') $package_name) 'tests'; \
    if (-not (Test-Path $testsDir)) { New-Item -ItemType Directory -Path $testsDir -Force | Out-Null }; \
    $smokeTestPath = Join-Path $testsDir 'test_smoke.py'; \
    $smokeTestLines = @( \
    'import importlib', \
    '', \
    '', \
    'def test_package_importable() -> None:', \
    ('    module = importlib.import_module("' + $package_name + '")'), \
    '    assert module is not None' \
    ); \
    Set-Content -Path $smokeTestPath -Value ($smokeTestLines -join "`n") -Encoding UTF8; \
    Write-Host ('Created smoke test at ' + $smokeTestPath); \
    Push-Location $packageDirFull; try { uv venv --python $python_version } finally { Pop-Location }; \
    $gitignorePath = Join-Path $packageDir '.gitignore'; \
    $gitignoreLines = @( \
    'src/', '__pycache__/', '*.py[cod]', '*$py.class', '.venv/', 'venv/', 'env/', '.python-version', '.pytest_cache/', '.mypy_cache/', '.ruff_cache/', '.pyright/', '.coverage', 'coverage.xml', 'htmlcov/', 'build/', 'dist/', '.eggs/', '*.egg-info/', 'pip-wheel-metadata/', '.ipynb_checkpoints/' \
    ); \
    if (-not (Test-Path $gitignorePath)) { \
    Set-Content -Path $gitignorePath -Value ($gitignoreLines -join "`n") -Encoding UTF8; \
    Write-Host ('Created ' + $gitignorePath + ' with Python defaults.') \
    } else { \
    $existing = Get-Content -Path $gitignorePath -ErrorAction SilentlyContinue; \
    $missing = $gitignoreLines | Where-Object { ($_ -ne '') -and ($_ -notin $existing) }; \
    if ($missing.Count -gt 0) { \
    Add-Content -Path $gitignorePath -Value ("`n" + ($missing -join "`n")); \
    Write-Host ('Updated ' + $gitignorePath + ' with ' + $missing.Count + ' missing Python defaults.') \
    } else { \
    Write-Host ($gitignorePath + ' already contains Python defaults.') \
    } \
    }; \
    $yamllintPath = Join-Path $packageDir '.yamllint'; \
    $yamllintLines = @( \
    '---', 'extends: default', '', 'rules:', '  new-lines: disable', '  document-start: disable', '  line-length: disable' \
    ); \
    if (-not (Test-Path $yamllintPath)) { \
    Set-Content -Path $yamllintPath -Value ($yamllintLines -join "`n") -Encoding UTF8; \
    Write-Host ('Created ' + $yamllintPath + '.') \
    } else { \
    Write-Host ($yamllintPath + ' already exists, leaving it unchanged.') \
    }; \
    $vscodeDir = Join-Path $packageDir '.vscode'; \
    if (-not (Test-Path $vscodeDir)) { New-Item -ItemType Directory -Path $vscodeDir | Out-Null }; \
    $settingsPath = Join-Path $vscodeDir 'settings.json'; \
    $settingsLines = @( \
    '{', \
    '  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",', \
    '  "python.terminal.activateEnvironment": true,', \
    '  "python.analysis.extraPaths": ["${workspaceFolder}/src"],', \
    '  "python.analysis.typeCheckingMode": "off",', \
    '  "basedpyright.analysis.diagnosticMode": "workspace",', \
    '  "editor.formatOnSave": true,', \
    '  "ruff.nativeServer": "on",', \
    '  "[python]": {', \
    '    "editor.defaultFormatter": "charliermarsh.ruff",', \
    '    "editor.codeActionsOnSave": {', \
    '      "source.fixAll.ruff": "explicit",', \
    '      "source.organizeImports.ruff": "explicit"', \
    '    }', \
    '  }', \
    '}' \
    ); \
    Set-Content -Path $settingsPath -Value ($settingsLines -join "`n") -Encoding UTF8; \
    Write-Host ('Wrote VS Code settings to ' + $settingsPath); \
    $sourceJustfilesDir = Join-Path $workspaceRoot '.justfiles'; \
    $targetJustfilesDir = Join-Path $packageDirFull '.justfiles'; \
    if (-not (Test-Path $targetJustfilesDir)) { New-Item -ItemType Directory -Path $targetJustfilesDir | Out-Null }; \
    if (Test-Path $sourceJustfilesDir) { \
    Get-ChildItem -Path $sourceJustfilesDir -File -Filter '*.just' -ErrorAction SilentlyContinue | ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $targetJustfilesDir $_.Name) -Force }; \
    Remove-Item -LiteralPath $sourceJustfilesDir -Recurse -Force -ErrorAction SilentlyContinue \
    }; \
    $sourceJustfile = Join-Path $workspaceRoot 'justfile'; \
    $targetJustfile = Join-Path $packageDirFull 'justfile'; \
    if (Test-Path $sourceJustfile) { Move-Item -LiteralPath $sourceJustfile -Destination $targetJustfile -Force; Write-Host ('Moved justfile to ' + $targetJustfile) }
