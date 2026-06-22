# AGILANG Static Documentation Site

AGILANG includes a static HTML documentation landing page under:

```text
docs-site/index.html
```

This is useful when GitHub Markdown is not enough and the project needs a polished public documentation homepage.

## Recommended documentation types

Use three documentation layers:

| Layer | Location | Purpose |
|---|---|---|
| GitHub README | `README.md` | First explanation for visitors and developers |
| Markdown docs | `docs/*.md` | Full technical documentation, guides, references |
| HTML docs site | `docs-site/index.html` | Polished public documentation homepage or GitHub Pages site |

## Recommended HTML docs sections

A professional AGILANG HTML documentation site should include:

1. Hero introduction: what AGILANG is.
2. Quick start commands.
3. Language basics.
4. Web app starter.
5. CMS/blog starter.
6. AGS templates.
7. CLI reference.
8. Blockchain generator.
9. SBQ Beacon layer.
10. Ethereum runtime boundary.
11. Deployment and production notes.
12. Links to GitHub branches.

## GitHub Pages setup

In GitHub:

```text
Repository -> Settings -> Pages -> Deploy from branch -> main -> /docs-site
```

Then GitHub Pages can serve the documentation homepage from the `docs-site` directory.

## Documentation design rule

The HTML documentation should be beautiful and readable, but it must not replace technical Markdown docs. It should link back to the detailed docs in `docs/`.
