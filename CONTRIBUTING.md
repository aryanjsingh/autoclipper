# Contributing Guide

Thank you for your interest in the AutoClip project! We welcome all forms of contributions, including but not limited to:

- 🐛 Bug fixes
- ✨ New feature development
- 📚 Documentation improvements
- 🧪 Test cases
- 💡 Feature suggestions
- 🎨 UI/UX improvements

## Development Environment Setup

### 1. Fork and Clone the Project

```bash
# Fork the project to your GitHub account, then clone
git clone https://github.com/your-username/autoclip.git
cd autoclip

# Add upstream repository
git remote add upstream https://github.com/original-username/autoclip.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Configure environment variables
cp env.example .env
# Edit .env file and fill in necessary configurations
```

### 3. Start Development Server

```bash
# Start Redis
brew services start redis  # macOS
# or sudo systemctl start redis-server  # Linux

# Start backend
python -m uvicorn backend.main:app --reload --port 8000

# Start Celery Worker
celery -A backend.core.celery_app worker --loglevel=info

# Start frontend
cd frontend && npm run dev
```

## Development Workflow

### 1. Create Feature Branch

```bash
# Create new branch from main
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

### 2. Development Standards

#### Code Style

**Python (Backend)**
- Follow PEP 8 standards
- Use Black for code formatting
- Use isort for import sorting
- Functions and classes need docstrings

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Example function docstring
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        Description of return value
    """
    pass
```

**TypeScript (Frontend)**
- Use ESLint and Prettier
- Components need JSDoc comments
- Use functional components and Hooks
- Follow Ant Design design specifications

```typescript
/**
 * Example component description
 */
interface ExampleProps {
  /** Property description */
  title: string;
  /** Optional property description */
  optional?: boolean;
}

const ExampleComponent: React.FC<ExampleProps> = ({ title, optional = false }) => {
  return <div>{title}</div>;
};
```

#### Commit Message Standards

Use conventional commit format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code format adjustment
- `refactor`: Code refactoring
- `test`: Test related
- `chore`: Build process or auxiliary tool changes

**Examples:**
```
feat(api): add video download endpoint
fix(ui): resolve upload modal display issue
docs(readme): update installation instructions
```

### 3. Testing

#### Backend Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Generate coverage report
pytest --cov=backend --cov-report=html
```

#### Frontend Testing

```bash
cd frontend

# Run tests
npm test

# Run lint check
npm run lint

# Type check
npm run type-check
```

### 4. Submit Code

```bash
# Add changes
git add .

# Commit changes
git commit -m "feat(api): add video download endpoint"

# Push branch
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Create Pull Request on GitHub
2. Fill in PR template
3. Ensure all checks pass
4. Wait for code review

## Code Review Process

### Review Standards

- ✅ Code conforms to project standards
- ✅ Features work correctly
- ✅ Test case coverage
- ✅ Documentation updated
- ✅ No security vulnerabilities
- ✅ Performance impact assessment

### Review Feedback

- Respond actively to review comments
- Fix issues promptly
- Keep PR updated
- Maintain communication with reviewers

## Issue Reporting

### Bug Reports

When reporting bugs using GitHub Issues, please include:

1. **Environment Information**
   - Operating system version
   - Python version
   - Node.js version
   - Browser version

2. **Reproduction Steps**
   - Detailed operation steps
   - Expected results
   - Actual results

3. **Error Information**
   - Complete error logs
   - Screenshots or screen recordings

4. **Additional Information**
   - Related configuration files
   - Network environment
   - Other potentially relevant information

### Feature Suggestions

When proposing new feature suggestions, please describe:

1. **Feature Description**
   - Detailed feature description
   - Usage scenarios
   - Expected effects

2. **Implementation Plan**
   - Technical implementation ideas
   - Possible challenges
   - Alternative solutions

3. **Impact Assessment**
   - Impact on existing features
   - Performance impact
   - User experience impact

## Documentation Contributions

### Documentation Types

- 📖 User documentation
- 🔧 Developer documentation
- 🚀 Deployment guide
- ❓ FAQ
- 📝 API documentation

### Documentation Standards

- Use Markdown format
- Add table of contents structure
- Include code examples
- Keep content updated
- Use clear heading hierarchy

## Community Code of Conduct

### Our Commitment

To create an open and friendly environment, we commit to:

- Respect all contributors
- Accept constructive criticism
- Focus on the best interests of the community
- Show empathy to other community members

### Unacceptable Behavior

- Use of sexualized language or imagery
- Personal attacks or insulting comments
- Public or private harassment
- Publishing others' private information without permission
- Other behavior inappropriate in professional settings

## Contact Information

- **GitHub Issues**: [Project Issues](https://github.com/your-username/autoclip/issues)
- **GitHub Discussions**: [Project Discussions](https://github.com/your-username/autoclip/discussions)
- **Email**: support@autoclip.com

## Acknowledgments

Thanks to all developers who have contributed to the AutoClip project! Your contributions make this project better.

---

**Thank you again for your contributions!** 🎉
