# Windows x64 packages with GitHub Actions

The **Windows x64 setup** workflow builds `Ocarina-Setup-<VERSION>-windows-x64.zip` on GitHub-hosted `windows-2025` runners. It contains the installer, project sources and Windows x64 build tools. The player supplies their own game locally when running the installer; the workflow never needs a game upload, game keys or game-related secrets.

## Run and download

1. Push the workflow and its helper scripts to your GitHub repository. For the **Run workflow** button to appear, `.github/workflows/windows-x64-setup.yml` must exist on the repository's default branch. Enable Actions in your fork if GitHub asks.
2. Open **Actions → Windows x64 setup → Run workflow**, select the branch and run it.
3. Open the successful run. Use **Download Windows x64 installer** in its summary, or download the ZIP from **Artifacts**. Sign in to GitHub to download it. Artifacts are kept for 30 days, subject to repository retention policy.
4. Extract the ZIP and run `Instalar-Ocarina.exe`. The ZIP is uploaded directly, so there is no extra artifact ZIP wrapped around it. Its SHA-256 appears in the run summary.

The workflow also runs when a tag matching `v*` is pushed. The tag must equal `v` followed by the contents of `VERSION`; for example, `VERSION` containing `0.3.4` requires tag `v0.3.4`. The tagged commit must include the workflow and packaging scripts. A mismatch fails before compiling.

The workflow uploads an Actions artifact; it does not create or modify a GitHub Release. No repository write token or additional repository secrets are required.

## Build environment

The workflow uses the existing `tools/build_xlate.py` and `tools/oot/make_setup.py`, including the packaging script's pinned downloads and SHA-256 checks. Source line endings are preserved before checkout, because the shader translator applies patches and the installer uses a shell script.

Python 3.14 runs as x64. The shader translator builds with .NET 10 NativeAOT for `win-x64`; a temporary, untracked `global.json` selects the SDK installed by the action, preventing the runner's newer preinstalled SDKs from taking precedence. The MSYS2 action updates the runner's existing `C:\msys64` installation and installs UCRT64 Clang, matching the path expected by the packaging script. NativeAOT uses the runner's Visual Studio tools. The package's compiler is the separate llvm-mingw version pinned by `make_setup.py`.

The actions are pinned to full commit SHAs from these verified stable releases, all using the Node.js 24 action runtime:

| Action | Release |
| --- | --- |
| `actions/checkout` | [v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) |
| `actions/setup-python` | [v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0) |
| `actions/setup-dotnet` | [v6.1.0](https://github.com/actions/setup-dotnet/releases/tag/v6.1.0) |
| `actions/upload-artifact` | [v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) |
| `msys2/setup-msys2` | [v2.33.0](https://github.com/msys2/setup-msys2/releases/tag/v2.33.0) |

When updating an action, verify the stable release's tag-to-commit mapping and its `action.yml` inputs, update the SHA and adjacent version comment together, and run actionlint. The direct ZIP upload uses the v7 `archive: false` input; it is not a drop-in configuration for older upload-artifact versions. This workflow targets GitHub.com, not GitHub Enterprise Server.

## Checks and troubleshooting

Before building, CI runs the repository content guard and its tests. Before uploading, `tools/oot/check_setup.py` verifies required package files, applies the content guard with the existing toolchain-size allowance, rejects game executables and packages, and checks every `.exe`, `.dll` and `.pyd` for the x64 PE machine type. It also compares every ZIP member with the corresponding validated file by size and SHA-256, rejecting missing, extra or duplicate members.

Local checks that do not need Windows or game data:

```sh
python3 tests/check_setup_test.py
python3 tests/check_content_test.py
python3 tools/check_content.py
actionlint .github/workflows/content-guard.yml .github/workflows/windows-x64-setup.yml
```

If a pinned download fails or its hash changes, inspect that dependency's official release before updating its URL and hash together. Do not remove hash checks. A failed build uploads no installer. Each step reports errors separately for dependencies, translator compilation, packaging and validation.

The workflow configuration and validator can be checked on other operating systems, but a successful Windows Actions run is still needed to verify the complete NativeAOT build and installer package. These checks do not test gameplay or the installer's actual window.
