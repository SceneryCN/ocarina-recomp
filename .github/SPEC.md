---
id: ci-packaging
type: module-design
status: draft
title: CI content and Windows installer packaging
---

## Responsibility

CI enforces the repository's exclusion of game content and produces the Windows x64 setup package from the checked-out commit. The content guard runs for pushes and pull requests. Packaging runs only on manual dispatch or pushed `v*` tags; a tag must match `VERSION` to keep the artifact's version tied to its source.

## Boundary

The public installer contains original host tools, source and redistributable dependencies. Game data, keys, generated game code and the final game executable are neither build inputs nor upload outputs. The player supplies their own game locally. Packaging uses GitHub-hosted Windows 2025 with read-only repository permissions and does not publish GitHub Releases.

Actions use verified stable releases pinned by full commit SHA. The existing package script owns dependency download hashes and package composition. CI supplies x64 Python, the project's .NET 10 SDK and UCRT64 tools. A temporary SDK selection prevents unrelated preinstalled .NET versions from silently changing NativeAOT builds.

## Artifact contract

Only a validated ZIP is uploaded. Required package files must exist; all Windows executables and libraries must report the x64 PE machine type. Folder contents pass the repository's content rules with the existing allowance for large toolchain binaries, plus rejection of game executables, NUP packages and shader binaries. ZIP members must match validated files by name, size and SHA-256.

The ZIP is uploaded directly through upload-artifact v7, with 30-day retention and its file checksum and download link in the job summary. Unit tests use synthetic host files; workflow lint and those tests do not substitute for a successful Windows packaging run or validate gameplay.
