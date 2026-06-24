# ISRO SOC Platform — Release Process

The SOC platform rigidly adheres to [Semantic Versioning](https://semver.org/).

## Versioning Rules
- **MAJOR (`v1.x.x -> v2.x.x`)**: Breaking changes to the core architecture (e.g., migrating from Elasticsearch to OpenSearch, completely altering the React Component tree, breaking backward compatibility on the REST API).
- **MINOR (`vx.1.x -> vx.2.x`)**: New features added in a backward-compatible manner (e.g., adding a new Sub-Model to the Threat Ensemble, adding a new MLflow tracking parameter, creating a new Dashboard view).
- **PATCH (`vx.x.1 -> vx.x.2`)**: Backward-compatible bug fixes and security hotfixes (e.g., patching a Regex bypass in the Rule Engine, fixing a CSS overflow in the UI).

## Git Tagging Procedure

Before triggering the final CI/CD pipeline to push Docker artifacts into the production registry, the repository MUST be strictly tagged.

1. Update `backend/app/__version__.py` to reflect the new version.
2. Update the `CHANGELOG.md` with explicit details of what was Added, Fixed, Changed, or Removed.
3. Commit the documentation changes:
   ```bash
   git commit -am "chore(release): bump version to v1.0.0"
   ```
4. Create the annotated Git Tag:
   ```bash
   git tag -a v1.0.0 -m "ISRO ISTRAC SOC Platform v1.0.0 — Initial Production Release"
   ```
5. Push the tag to the remote tracking server (this triggers GitHub Actions):
   ```bash
   git push origin v1.0.0
   ```

## Post-Release Verification
After a tag is pushed, ensure the Docker registry builds the `<image>:v1.0.0` artifact rather than relying on `<image>:latest`. Production configurations MUST explicitly reference the tagged version to prevent silent upgrade breaks.
