# Contributing to GitHub Activity Batch Pipeline

Thank you for contributing! This document outlines how to contribute effectively.

## 🎯 How to Contribute

### 1. Report Bugs

Use GitHub Issues with the "Bug" template. Include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Logs or error messages

### 2. Suggest Features

Use GitHub Issues with the "Feature Request" template. Include:
- Problem statement
- Proposed solution
- Use cases
- Alternatives considered

### 3. Submit Code

#### Before You Start
1. Check existing issues/PRs for similar work
2. Create a new issue if none exists
3. Fork the repository
4. Create a feature branch: `git checkout -b feature/your-feature`

#### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/github-activity-batch-pipeline.git
cd github-activity-batch-pipeline

# Install dependencies
make install

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run tests
make test

# Run validation
make validate
```

#### Coding Standards

**Python:**
- Follow PEP 8
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions small and focused

**Terraform:**
- Use consistent formatting: `terraform fmt`
- Document variables and outputs
- Follow resource naming conventions

**dbt:**
- Use descriptive model names
- Add tests for all models
- Document columns in schema.yml
- Use CTEs for complex transformations

**SQL:**
- Use uppercase for keywords (SELECT, FROM, WHERE)
- Indent consistently
- Comment complex logic

#### Testing Requirements

All contributions must include tests:

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Validate all components
make validate
```

#### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add validation script for dbt models
fix: correct partition field in daily_stats
docs: update README with troubleshooting section
test: add pytest tests for Airflow DAG
refactor: extract GCS upload logic to function
```

#### Pull Request Process

1. **Update documentation** if behavior changes
2. **Add tests** for new functionality
3. **Run validation**: `make validate`
4. **Update CHANGELOG.md** with your changes
5. **Request review** from maintainers
6. **Squash commits** if needed before merge

PR Template:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] Validation passed (`make validate`)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## 📁 Project Structure

```
github-activity-batch-pipeline/
├── terraform/          # Infrastructure as Code
├── airflow/            # Orchestration
│   └── dags/          # DAG definitions
├── dbt/               # Data transformation
│   └── models/        # SQL models
├── tests/             # Unit tests
├── scripts/           # Validation scripts
├── looker/            # Dashboard configs
└── docs/              # Additional documentation
```

## 🔧 Development Tools

**Required:**
- Python 3.9+
- Terraform >= 1.0
- Docker & Docker Compose
- pytest

**Recommended:**
- tfsec (Terraform security)
- black (Python formatting)
- flake8 (Python linting)
- sqlfluff (SQL linting)

## 📝 Areas for Contribution

### High Priority
- Additional dbt models (weekly/monthly aggregations)
- Performance optimizations for large datasets
- Enhanced error handling and alerting
- Cost monitoring and optimization

### Medium Priority
- Support for additional data sources
- Real-time streaming alternative
- Enhanced Looker Studio templates
- CI/CD pipeline configuration

### Nice to Have
- Example dashboards and reports
- Performance benchmarks
- Migration guides from other tools
- Tutorial videos or blog posts

## 🤝 Code Review

Reviews focus on:
1. **Correctness**: Does it work as intended?
2. **Testing**: Are there adequate tests?
3. **Documentation**: Is it clear how to use?
4. **Performance**: Any obvious inefficiencies?
5. **Security**: Any vulnerabilities introduced?

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

- Check existing issues first
- Read README.md and documentation
- Ask in GitHub Discussions
- Contact maintainers

Thank you for contributing! 🎉
