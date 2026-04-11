Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Test-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return [bool](Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Install-Uv {
    if (Test-Command -Name 'uv') {
        Write-Host 'uv is already installed.'
        return
    }

    Write-Host 'uv was not found. Installing uv...'

    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

    # The official installer puts uv in %USERPROFILE%\.local\bin on Windows.
    $uvBin = Join-Path $HOME '.local\bin'
    if (Test-Path $uvBin) {
        $env:Path = "$uvBin;$env:Path"
    }

    if (-not (Test-Command -Name 'uv')) {
        throw 'uv installation appears to have failed. Open a new shell and run this script again.'
    }

    Write-Host 'uv installed successfully.'
}

function New-Justfile {
    $justfilePath = Join-Path (Get-Location) 'justfile'
    $justfilesDir = Join-Path (Get-Location) '.justfiles'
    $initJustPath = Join-Path $justfilesDir 'init.just'
    $licenseJustPath = Join-Path $justfilesDir 'license.just'
    $prekJustPath = Join-Path $justfilesDir 'prek.just'
    $githubActionsJustPath = Join-Path $justfilesDir 'github_actions.just'
    $cleanJustPath = Join-Path $justfilesDir 'clean.just'

    if (-not (Test-Path $justfilesDir)) {
        New-Item -ItemType Directory -Path $justfilesDir | Out-Null
    }

    $initJustContent = @'
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
    Write-Utf8NoBom -Path $pyprojectPath -Content ($pyprojectLines -join "`n"); \
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
    Write-Utf8NoBom -Path $smokeTestPath -Content ($smokeTestLines -join "`n"); \
    Write-Host ('Created smoke test at ' + $smokeTestPath); \
    Push-Location $packageDirFull; try { uv venv --python $python_version } finally { Pop-Location }; \
    $gitignorePath = Join-Path $packageDir '.gitignore'; \
    $gitignoreLines = @( \
    'src/', '__pycache__/', '*.py[cod]', '*$py.class', '.venv/', 'venv/', 'env/', '.python-version', '.pytest_cache/', '.mypy_cache/', '.ruff_cache/', '.pyright/', '.coverage', 'coverage.xml', 'htmlcov/', 'build/', 'dist/', '.eggs/', '*.egg-info/', 'pip-wheel-metadata/', '.ipynb_checkpoints/' \
    ); \
    if (-not (Test-Path $gitignorePath)) { \
    Write-Utf8NoBom -Path $gitignorePath -Content ($gitignoreLines -join "`n"); \
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
    Write-Utf8NoBom -Path $yamllintPath -Content ($yamllintLines -join "`n"); \
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
    Write-Utf8NoBom -Path $settingsPath -Content ($settingsLines -join "`n"); \
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
'@

    $licenseJustContent = @'
# Select and download a software license from scancode-licensedb.
license:
    $indexUrl = 'https://scancode-licensedb.aboutcode.org/index.json'; \
    $baseUrl = 'https://scancode-licensedb.aboutcode.org/'; \
    $all = Invoke-RestMethod -Uri $indexUrl -TimeoutSec 30; \
    $licenses = $all | Where-Object { \
    -not $_.is_exception -and -not $_.is_deprecated -and $_.license \
    } | Sort-Object spdx_license_key, license_key; \
    if (-not $licenses -or $licenses.Count -eq 0) { throw 'No licenses found in remote index.' }; \
    Write-Host ('Found ' + $licenses.Count + ' licenses.'); \
    $query = Read-Host 'Filter licenses by text (blank for all)'; \
    if ($query) { \
    $licenses = $licenses | Where-Object { \
    (($_.spdx_license_key) -and ($_.spdx_license_key -match [regex]::Escape($query))) -or \
    (($_.license_key) -and ($_.license_key -match [regex]::Escape($query))) \
    }; \
    if (-not $licenses -or $licenses.Count -eq 0) { throw ('No licenses matched filter: ' + $query) } \
    }; \
    Write-Host ('Showing ' + $licenses.Count + ' licenses.'); \
    for ($i = 0; $i -lt $licenses.Count; $i++) { \
    $name = if ($licenses[$i].spdx_license_key) { $licenses[$i].spdx_license_key } else { $licenses[$i].license_key }; \
    Write-Host ([string]($i + 1) + '. ' + $name) \
    }; \
    $selection = Read-Host 'Enter number'; \
    [int]$parsed = 0; \
    if (-not [int]::TryParse($selection, [ref]$parsed)) { throw 'Invalid selection.' }; \
    $selectedIndex = $parsed - 1; \
    if ($selectedIndex -lt 0 -or $selectedIndex -ge $licenses.Count) { throw 'Selection out of range.' }; \
    $chosen = $licenses[$selectedIndex]; \
    $fileName = $chosen.license; \
    $url = $baseUrl + $fileName; \
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile 'LICENSE'; \
    $chosenName = if ($chosen.spdx_license_key) { $chosen.spdx_license_key } else { $chosen.license_key }; \
    $licenseClassifier = 'License :: Other/Proprietary License'; \
    switch -Regex ($chosenName) { \
    '^MIT$' { $licenseClassifier = 'License :: OSI Approved :: MIT License' } \
    '^Apache-2\.0$' { $licenseClassifier = 'License :: OSI Approved :: Apache Software License' } \
    '^BSD-3-Clause$' { $licenseClassifier = 'License :: OSI Approved :: BSD License' } \
    '^BSD-2-Clause$' { $licenseClassifier = 'License :: OSI Approved :: BSD License' } \
    '^LGPL-3\.0(-or-later)?$' { $licenseClassifier = 'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)' } \
    '^LGPL-2\.1(-or-later)?$' { $licenseClassifier = 'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)' } \
    '^GPL-3\.0(-or-later)?$' { $licenseClassifier = 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)' } \
    '^GPL-2\.0(-or-later)?$' { $licenseClassifier = 'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)' } \
    '^AGPL-3\.0(-or-later)?$' { $licenseClassifier = 'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)' } \
    '^MPL-2\.0$' { $licenseClassifier = 'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)' } \
    '^ISC$' { $licenseClassifier = 'License :: OSI Approved :: ISC License (ISCL)' } \
    '^Unlicense$' { $licenseClassifier = 'License :: Public Domain' } \
    }; \
    Write-Host ('Downloaded ' + $chosenName + ' to LICENSE'); \
    $pyprojectPath = 'pyproject.toml'; \
    if (Test-Path $pyprojectPath) { \
    $content = Get-Content -Path $pyprojectPath -Raw; \
    $licenseLine = 'license = "' + $chosenName + '"'; \
    $pythonVersion = '3'; \
    if ($content -match '(?m)^requires-python\s*=\s*">=([^\"]+)"') { $pythonVersion = $Matches[1] }; \
    $pythonClassifier = 'Programming Language :: Python :: 3'; \
    if ($pythonVersion -match '^3($|\.)') { $pythonClassifier = 'Programming Language :: Python :: ' + $pythonVersion }; \
    if ($content -match '(?m)^license\s*=') { \
    $updated = [regex]::Replace($content, '(?m)^license\s*=.*$', $licenseLine, 1) \
    } else { \
    $updated = [regex]::Replace($content, '(?m)^readme\s*=.*$', ('$0' + "`n" + $licenseLine), 1); \
    if ($updated -eq $content) { $updated = ($content.TrimEnd() + "`n" + $licenseLine + "`n") } \
    }; \
    $classifiersBlock = @( \
    'classifiers = [', \
    ('  "' + $licenseClassifier + '",'), \
    '  "Operating System :: Microsoft :: Windows",', \
    '  "Programming Language :: Python :: 3",', \
    ('  "' + $pythonClassifier + '",'), \
    ']' \
    ) -join "`n"; \
    if ($updated -match '(?ms)^classifiers\s*=\s*\[.*?^\]') { \
    $updated = [regex]::Replace($updated, '(?ms)^classifiers\s*=\s*\[.*?^\]', $classifiersBlock, 1) \
    } else { \
    $updated = [regex]::Replace($updated, '(?m)^requires-python\s*=.*$', ('$0' + "`n" + $classifiersBlock), 1); \
    if ($updated -eq $content) { $updated = ($updated.TrimEnd() + "`n" + $classifiersBlock + "`n") } \
    }; \
    Write-Utf8NoBom -Path $pyprojectPath -Content $updated; \
    Write-Host ('Updated ' + $pyprojectPath + ' license/classifiers for ' + $chosenName) \
    } else { \
    Write-Host 'pyproject.toml not found, skipping pyproject license update.' \
    }
'@

    $prekJustContent = @'
prek-init:
    if (-not (Test-Path 'pyproject.toml')) { throw 'pyproject.toml not found. Run just init first.' }; \
    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^\s*name\s*=\s*"([^\"]+)"' -AllMatches | Select-Object -First 1; if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' }; $projectName = $projectNameMatch.Matches[0].Groups[1].Value; \
    $packageName = $projectName -replace '-', '_'; \
    uv add --optional dev prek; \
    $lines = @( \
    'default_language_version:', \
    '  python: python3.14', \
    'repos:', \
    '  - repo: local', \
    '    hooks:', \
    '      - id: prek-auto-update', \
    '        name: prek-auto-update', \
    '        entry: uv run prek auto-update', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '        fail_fast: true', \
    '  - repo: https://github.com/bwhmather/ssort', \
    '    rev: 0.16.0', \
    '    hooks:', \
    '      - id: ssort', \
    '  - repo: https://github.com/pre-commit/pre-commit-hooks', \
    '    rev: v6.0.0', \
    '    hooks:', \
    '      - id: fix-byte-order-marker', \
    '      - id: check-merge-conflict', \
    '      - id: end-of-file-fixer', \
    '        exclude: ^static/.*\.svg$', \
    '      - id: trailing-whitespace', \
    '      - id: mixed-line-ending', \
    '        exclude: ^static/.*\.svg$', \
    '      - id: check-yaml', \
    '      - id: check-toml', \
    '      - id: check-added-large-files', \
    '        exclude: ^tests/media/.*\.cbz$', \
    '      - id: debug-statements', \
    '        language_version: python3.14', \
    '      - id: check-executables-have-shebangs', \
    '      - id: check-shebang-scripts-are-executable', \
    '  - repo: https://github.com/google/yamlfmt', \
    '    rev: v0.21.0', \
    '    hooks:', \
    '      - id: yamlfmt', \
    '        files: \.(yml|yaml)$', \
    '  - repo: https://github.com/adrienverge/yamllint', \
    '    rev: v1.38.0', \
    '    hooks:', \
    '      - id: yamllint', \
    '        files: \.(yml|yaml)$', \
    '  - repo: https://github.com/shellcheck-py/shellcheck-py', \
    '    rev: v0.11.0.1', \
    '    hooks:', \
    '      - id: shellcheck', \
    '  - repo: https://github.com/scop/pre-commit-shfmt', \
    '    rev: v3.13.1-1', \
    '    hooks:', \
    '      - id: shfmt', \
    '  - repo: https://github.com/crate-ci/typos', \
    '    rev: v1.45.0', \
    '    hooks:', \
    '      - id: typos', \
    '  - repo: https://github.com/executablebooks/mdformat', \
    '    rev: 1.0.0', \
    '    hooks:', \
    '      - id: mdformat', \
    '        files: \.md$', \
    '  - repo: https://github.com/DavidAnson/markdownlint-cli2', \
    '    rev: v0.22.0', \
    '    hooks:', \
    '      - id: markdownlint-cli2', \
    '  - repo: https://github.com/ComPWA/taplo-pre-commit', \
    '    # toml formatter', \
    '', \
    '    rev: v0.9.3', \
    '    hooks:', \
    '      - id: taplo-format', \
    '      - id: taplo-lint', \
    '  - repo: https://github.com/asottile/pyupgrade', \
    '    rev: v3.21.2', \
    '    hooks:', \
    '      - id: pyupgrade', \
    '        language_version: python3.14', \
    '        args: [--py314-plus, --keep-runtime-typing]', \
    '        files: ^(src|tests)/.*\.py$', \
    '  - repo: https://github.com/hadialqattan/pycln', \
    '    rev: v2.6.0', \
    '    hooks:', \
    '      - id: pycln', \
    '        language_version: python3.14', \
    '        args: [src, tests]', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '  - repo: https://github.com/astral-sh/ruff-pre-commit', \
    '    rev: v0.15.10', \
    '    hooks:', \
    '      - id: ruff-check', \
    '        language_version: python3.14', \
    '        args: [--fix, --exclude, typings]', \
    '        files: ^(src|tests)/.*\.py$', \
    '      - id: ruff-format', \
    '        language_version: python3.14', \
    '        args: [--exclude, typings]', \
    '        files: ^(src|tests)/.*\.py$', \
    '      - id: ruff-check', \
    '        name: ruff-check-post-format', \
    '        language_version: python3.14', \
    '        args: [--exclude, typings]', \
    '        files: ^(src|tests)/.*\.py$', \
    '  - repo: local', \
    '    hooks:', \
    '      - id: autopep695-format', \
    '        name: autopep695-format', \
    '        entry: uvx autopep695 format', \
    '        language: system', \
    '        files: ^(src|tests)/.*\.py$', \
    '        stages: [pre-commit]', \
    '      - id: vulture', \
    '        name: vulture', \
    '        entry: |', \
    '          uvx --python 3.14 vulture src --min-confidence 80 --ignore-names', \
    '          dst,secure,httponly,samesite,unc_path,package_family_name,logo44x44', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: deptry', \
    '        name: deptry', \
    '        entry: uvx deptry . --ignore DEP001,DEP002', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: refurb', \
    '        name: refurb', \
    '        entry: uvx ruff check --select FURB --ignore FURB110 src tests', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: basedpyright', \
    '        name: basedpyright', \
    '        entry: uvx basedpyright', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: ty-check', \
    '        name: ty-check', \
    '        entry: uvx ty check', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: pip-audit', \
    '        name: pip-audit', \
    '        entry: uvx pip-audit', \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '      - id: coverage-100', \
    '        name: coverage-100', \
    ('        entry: uv run pytest --doctest-modules --cov=src/' + $packageName + ' --cov-report=term-missing --cov-fail-under=100 src/' + $packageName), \
    '        language: system', \
    '        pass_filenames: false', \
    '        always_run: true', \
    '        stages: [pre-commit]', \
    '  - repo: https://github.com/Yelp/detect-secrets', \
    '    rev: v1.5.0', \
    '    hooks:', \
    '      - id: detect-secrets', \
    '        language_version: python3.14', \
    '        args: ["--baseline", ".secrets.baseline"]', \
    '        stages: [pre-commit]' \
    ); \
    $preCommitYaml = $lines -join "`n"; \
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false); \
    [System.IO.File]::WriteAllText('.pre-commit-config.yaml', $preCommitYaml, $utf8NoBom); \
    uv run prek install
'@

    $githubActionsJustContent = @'
# Create GitHub automation files (.github/dependabot.yml and workflows).
github-actions-init:
    $pyprojectPath = 'pyproject.toml'; \
    if (-not (Test-Path $pyprojectPath)) { throw 'pyproject.toml not found. Run this from your project root.' }; \
    $pythonVersion = '3.14'; \
    $requiresMatch = Select-String -Path $pyprojectPath -Pattern '^requires-python\s*=\s*">=([0-9]+\.[0-9]+)"' -AllMatches | Select-Object -First 1; \
    if ($requiresMatch -and $requiresMatch.Matches.Count -gt 0) { $pythonVersion = $requiresMatch.Matches[0].Groups[1].Value }; \
    $targetGithubDir = '.github'; \
    $targetWorkflowsDir = Join-Path $targetGithubDir 'workflows'; \
    if (-not (Test-Path $targetGithubDir)) { New-Item -ItemType Directory -Path $targetGithubDir | Out-Null }; \
    if (-not (Test-Path $targetWorkflowsDir)) { New-Item -ItemType Directory -Path $targetWorkflowsDir | Out-Null }; \
    $dependabotPath = Join-Path $targetGithubDir 'dependabot.yml'; \
    $lintFormatPath = Join-Path $targetWorkflowsDir 'lint-format.yml'; \
    $publishPath = Join-Path $targetWorkflowsDir 'publish-pypi.yml'; \
    $qualityPath = Join-Path $targetWorkflowsDir 'quality-security.yml'; \
    $testsPath = Join-Path $targetWorkflowsDir 'tests.yml'; \
    $typecheckPath = Join-Path $targetWorkflowsDir 'typecheck.yml'; \
    $dependabotLines = @( \
    'version: 2', \
    'updates:', \
    '  - package-ecosystem: "github-actions"', \
    '    directory: "/"', \
    '    schedule:', \
    '      interval: "weekly"', \
    '    open-pull-requests-limit: 10', \
    '  - package-ecosystem: "uv"', \
    '    directory: "/"', \
    '    schedule:', \
    '      interval: "weekly"', \
    '    open-pull-requests-limit: 10' \
    ); \
    $lintFormatLines = @( \
    'name: Lint and Format', \
    '"on":', \
    '  pull_request:', \
    '  push:', \
    '    branches: [main]', \
    '  workflow_dispatch:', \
    'permissions:', \
    '  contents: read', \
    'jobs:', \
    '  lint-format:', \
    '    name: Lint and format checks', \
    '    runs-on: ubuntu-latest', \
    '    timeout-minutes: 30', \
    '    steps:', \
    '      - name: Checkout repository', \
    '        uses: actions/checkout@v6', \
    '      - name: Set up Python', \
    '        uses: actions/setup-python@v6', \
    '        with:', \
    ('          python-version: "' + $pythonVersion + '"'), \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Install project with dev dependencies', \
    '        run: uv sync --extra dev', \
    '      - name: Run lint and format hooks', \
    '        run: |', \
    '          uv run prek run ssort --all-files', \
    '          uv run prek run fix-byte-order-marker check-merge-conflict \', \
    '            end-of-file-fixer trailing-whitespace mixed-line-ending --all-files', \
    '          uv run prek run check-yaml check-toml check-added-large-files \', \
    '            check-executables-have-shebangs \', \
    '            check-shebang-scripts-are-executable \', \
    '            --all-files', \
    '          uv run prek run yamlfmt yamllint --all-files', \
    '          uv run prek run typos mdformat markdownlint-cli2 --all-files', \
    '          uv run prek run taplo-format taplo-lint --all-files', \
    '          uv run prek run pyupgrade pycln autopep695-format --all-files', \
    '          uv run prek run ruff-check ruff-format ruff-check-post-format \', \
    '            refurb --all-files' \
    ); \
    $publishLines = @( \
    'name: Publish to PyPI', \
    '"on":', \
    '  release:', \
    '    types: [published]', \
    '  workflow_dispatch:', \
    'permissions:', \
    '  contents: read', \
    'jobs:', \
    '  build:', \
    '    name: Build distributions', \
    '    runs-on: ubuntu-latest', \
    '    steps:', \
    '      - name: Checkout repository', \
    '        uses: actions/checkout@v6', \
    '      - name: Set up Python', \
    '        uses: actions/setup-python@v6', \
    '        with:', \
    ('          python-version: "' + $pythonVersion + '"'), \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Install check tooling', \
    '        run: |', \
    '          python -m pip install --upgrade pip', \
    '          python -m pip install twine', \
    '      - name: Build sdist and wheel', \
    '        run: uv build --no-sources', \
    '      - name: Check distributions', \
    '        run: python -m twine check dist/*', \
    '      - name: Upload distributions artifact', \
    '        uses: actions/upload-artifact@v7', \
    '        with:', \
    '          name: python-distributions', \
    '          path: dist/', \
    '  publish:', \
    '    name: Publish to PyPI', \
    '    needs: build', \
    '    runs-on: ubuntu-latest', \
    '    environment:', \
    '      name: pypi', \
    '    permissions:', \
    '      contents: read', \
    '      id-token: write', \
    '    steps:', \
    '      - name: Download distributions artifact', \
    '        uses: actions/download-artifact@v8', \
    '        with:', \
    '          name: python-distributions', \
    '          path: dist/', \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Publish package to PyPI', \
    '        run: uv publish --trusted-publishing always --check-url https://pypi.org/simple dist/*' \
    ); \
    $qualityLines = @( \
    'name: Quality and Security', \
    '"on":', \
    '  pull_request:', \
    '  push:', \
    '    branches: [main]', \
    '  workflow_dispatch:', \
    'permissions:', \
    '  contents: read', \
    'jobs:', \
    '  quality-security:', \
    '    name: Quality and security checks', \
    '    runs-on: ubuntu-latest', \
    '    timeout-minutes: 20', \
    '    steps:', \
    '      - name: Checkout repository', \
    '        uses: actions/checkout@v6', \
    '      - name: Set up Python', \
    '        uses: actions/setup-python@v6', \
    '        with:', \
    ('          python-version: "' + $pythonVersion + '"'), \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Install project with dev dependencies', \
    '        run: uv sync --extra dev', \
    '      - name: Run quality and security hooks', \
    '        run: uv run prek run vulture deptry detect-secrets --all-files' \
    ); \
    $testsLines = @( \
    'name: Tests', \
    '"on":', \
    '  pull_request:', \
    '  push:', \
    '    branches: [main]', \
    '  workflow_dispatch:', \
    'permissions:', \
    '  contents: read', \
    'jobs:', \
    '  tests:', \
    '    name: Test suite with coverage', \
    '    runs-on: ubuntu-latest', \
    '    timeout-minutes: 20', \
    '    steps:', \
    '      - name: Checkout repository', \
    '        uses: actions/checkout@v6', \
    '      - name: Set up Python', \
    '        uses: actions/setup-python@v6', \
    '        with:', \
    ('          python-version: "' + $pythonVersion + '"'), \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Install project with dev dependencies', \
    '        run: uv sync --extra dev', \
    '      - name: Run coverage gate hook', \
    '        run: uv run prek run coverage-100 --all-files' \
    ); \
    $typecheckLines = @( \
    'name: Typecheck', \
    '"on":', \
    '  pull_request:', \
    '  push:', \
    '    branches: [main]', \
    '  workflow_dispatch:', \
    'permissions:', \
    '  contents: read', \
    'jobs:', \
    '  typecheck:', \
    '    name: Type analysis', \
    '    runs-on: ubuntu-latest', \
    '    timeout-minutes: 20', \
    '    steps:', \
    '      - name: Checkout repository', \
    '        uses: actions/checkout@v6', \
    '      - name: Set up Python', \
    '        uses: actions/setup-python@v6', \
    '        with:', \
    ('          python-version: "' + $pythonVersion + '"'), \
    '      - name: Set up uv', \
    '        uses: astral-sh/setup-uv@v7', \
    '      - name: Install project with dev dependencies', \
    '        run: uv sync --extra dev', \
    '      - name: Run type-check hooks', \
    '        run: uv run prek run basedpyright ty-check --all-files' \
    ); \
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false); \
    [System.IO.File]::WriteAllText($dependabotPath, ($dependabotLines -join "`n"), $utf8NoBom); \
    [System.IO.File]::WriteAllText($lintFormatPath, ($lintFormatLines -join "`n"), $utf8NoBom); \
    [System.IO.File]::WriteAllText($publishPath, ($publishLines -join "`n"), $utf8NoBom); \
    [System.IO.File]::WriteAllText($qualityPath, ($qualityLines -join "`n"), $utf8NoBom); \
    [System.IO.File]::WriteAllText($testsPath, ($testsLines -join "`n"), $utf8NoBom); \
    [System.IO.File]::WriteAllText($typecheckPath, ($typecheckLines -join "`n"), $utf8NoBom); \
    Write-Host ('Created GitHub automation files under ' + $targetGithubDir)
'@

    $cleanJustContent = (@(
        'clean:',
        '    $confirmation = Read-Host ''Are you sure you want to clean this project directory? Type "delete my stuff" to continue''; \',
        "    if (`$confirmation -ne 'delete my stuff') { throw 'Clean cancelled.' }; \\",
        "    `$root = (Resolve-Path '.').Path; \\",
        "    if (-not (Test-Path (Join-Path `$root 'pyproject.toml'))) { throw 'Refusing to clean: run this only from a project root (pyproject.toml required).' }; \\",
        "    `$protected = @( \\",
        "    (Join-Path `$root 'init.ps1') \\",
        '    ); \',
        "    `$items = Get-ChildItem -LiteralPath `$root -Force; \\",
        "    foreach (`$item in `$items) { \\",
        "        if (`$protected -contains `$item.FullName) { continue }; \\",
        "        Remove-Item -LiteralPath `$item.FullName -Recurse -Force -ErrorAction SilentlyContinue; \\",
        '    }; \',
        "    Write-Host ('Clean complete for ' + `$root + '. Protected root files: init.ps1.')"
    ) -join "`n")

    Write-Utf8NoBom -Path $licenseJustPath -Content $licenseJustContent
    Write-Utf8NoBom -Path $prekJustPath -Content $prekJustContent
    Write-Utf8NoBom -Path $githubActionsJustPath -Content $githubActionsJustContent
    Write-Utf8NoBom -Path $initJustPath -Content $initJustContent
    Write-Utf8NoBom -Path $cleanJustPath -Content $cleanJustContent

    if (Test-Path $justfilePath) {
        Write-Host 'Using existing justfile.'
        return $justfilePath
    }

    Write-Host 'No justfile found. Creating a default justfile with an init recipe.'

    $justfileContent = @'
set shell := ["powershell", "-NoProfile", "-Command"]

import '.justfiles/init.just'
import '.justfiles/license.just'
import '.justfiles/prek.just'
import '.justfiles/github_actions.just'
import '.justfiles/clean.just'

_default:
    @just --list

ruff:
    uvx ruff check --exclude typings
    uvx ruff format --exclude typings

# Run Python type checking with basedpyright.
typecheck:
    uvx basedpyright

# Run prek hooks against all files.
prek:
    uv run prek run --all-files; uv run prek run --all-files

test:
    uv run pytest --doctest-modules

# Run tests with coverage report.
test-cov:
    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^name\s*=\s*"([^\"]+)"' -AllMatches | Select-Object -First 1; if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' }; $packageName = $projectNameMatch.Matches[0].Groups[1].Value -replace '-', '_'; uv run pytest --doctest-modules --cov=('src/' + $packageName) --cov-report=term-missing
'@

    Write-Utf8NoBom -Path $justfilePath -Content $justfileContent

    return $justfilePath
}

Install-Uv
$justfilePath = New-Justfile
$pythonVersion = Read-Host 'python_version'
$projectDescription = Read-Host 'description'

if (-not $pythonVersion) {
    throw 'python_version is required.'
}

if (-not $projectDescription) {
    throw 'description is required.'
}

Write-Host 'Running init recipe via rust-just using uvx...'
$env:UV_INIT_PYTHON = $pythonVersion
$env:UV_INIT_DESCRIPTION = $projectDescription

try {
    & uvx --from rust-just just.exe --justfile $justfilePath init
}
finally {
    Remove-Item Env:UV_INIT_PYTHON -ErrorAction SilentlyContinue
    Remove-Item Env:UV_INIT_DESCRIPTION -ErrorAction SilentlyContinue
}

if ($LASTEXITCODE -ne 0) {
    throw "Init failed with exit code $LASTEXITCODE."
}

$licenseJustfilePath = $justfilePath
if (-not (Test-Path $licenseJustfilePath)) {
    $candidate = Get-ChildItem -Path (Get-Location) -Recurse -File -Filter 'justfile' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($candidate) {
        $licenseJustfilePath = $candidate.FullName
    }
}

if (-not (Test-Path $licenseJustfilePath)) {
    throw 'Could not locate justfile after init, cannot run license recipe.'
}

Write-Host 'Running license recipe...'
Push-Location (Split-Path -Parent $licenseJustfilePath)
try {
    & uvx --from rust-just just.exe --justfile $licenseJustfilePath license
}
finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) {
    throw "License setup failed with exit code $LASTEXITCODE."
}

Write-Host 'Bootstrap complete.'
