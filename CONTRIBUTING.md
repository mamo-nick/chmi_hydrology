# Contributing to CHMI Hydrology

Thank you for your interest in contributing! Here is how you can help.

---

## Reporting Bugs

Use the [Bug report](.github/ISSUE_TEMPLATE/bug_report.md) issue template. Please include logs from **Settings → System → Logs** filtered by `chmi_hydrology`.

## Suggesting Features

Use the [Feature request](.github/ISSUE_TEMPLATE/feature_request.md) issue template.

## Contributing Code

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test on a real Home Assistant instance
5. Submit a Pull Request with a clear description of the changes

### Code Style

- Python code follows [PEP 8](https://pep8.org/)
- All code and comments must be in **English**
- Use type hints where possible
- Keep functions small and focused

### Testing

Before submitting a PR, please verify:
- Integration loads without errors in HA logs
- Config flow works (add/remove station)
- All sensors update correctly
- No regressions in existing functionality

## Adding Translations

Translations are located in `custom_components/chmi_hydrology/translations/`.

To add a new language:
1. Copy `translations/en.json` to `translations/{language_code}.json`
2. Translate all strings
3. Submit a Pull Request

Currently supported: `en`, `cs`, `sk`

## Questions

For general questions please use [Discussions](https://github.com/mamo-nick/chmi_hydrology/discussions) instead of Issues.
