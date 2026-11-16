---
id: host-ui
type: module-design
status: draft
title: Host UI localization
---

## Responsibility

The host settings menu and performance overlay share a UTF-8 text catalog. English, Russian, Simplified Chinese and Traditional Chinese have complete menu catalogs. Language names remain in their native scripts; printf arguments and description-buffer limits remain consistent across translations.

## Boundary

`TOTK_MENU_LANG` selects `en`, `ru`, `zh-Hans` or `zh-Hant` independently of the game's language and software keyboard. Selection changes apply live through the configuration version and persist through the existing configuration store. Environment overrides retain their existing precedence.

An automatic choice follows the system UI language. Explicit Chinese script subtags take precedence over region; Taiwan, Hong Kong and Macao otherwise select Traditional Chinese, while other Chinese locales select Simplified Chinese. Unsupported system languages and missing catalog entries fall back to English.

## Fonts and verification

The menu uses platform font discovery, without distributing game fonts. Both Chinese catalogs contribute their glyphs to the atlas at creation so language switches require no font upload. Font availability remains a platform requirement: missing system CJK fonts can produce missing glyphs. The existing atlas lifecycle rebuilds for window scale changes.

Host-only tests compile the actual catalog and configuration store with platform providers, covering complete catalogs, formatted strings, description capacity, locale selection, live changes and persistence. They do not establish actual GPU rendering, font availability or visual layout.
