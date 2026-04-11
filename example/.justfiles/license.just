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
    Set-Content -Path $pyprojectPath -Value $updated -Encoding UTF8; \
    Write-Host ('Updated ' + $pyprojectPath + ' license/classifiers for ' + $chosenName) \
    } else { \
    Write-Host 'pyproject.toml not found, skipping pyproject license update.' \
    }
