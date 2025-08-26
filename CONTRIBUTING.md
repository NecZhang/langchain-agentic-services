# Contributing to Enterprise Agentic Services

We welcome contributions to the Enterprise Agentic Services project! This document provides guidelines for contributing.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- UV package manager (recommended)
- Git

### Development Setup
1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/langchain-agentic-services.git
   cd langchain-agentic-services
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## 🔧 Development Workflow

### Making Changes
1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test your changes:
   ```bash
   python -m pytest tests/
   ```
4. Commit with clear messages:
   ```bash
   git commit -m "Add: new feature description"
   ```

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for public functions
- Keep functions focused and well-documented

### Testing
- Add tests for new features
- Ensure existing tests pass
- Test both Chinese and English functionality

## 📋 Contribution Types

### Bug Reports
When filing a bug report, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Error logs if applicable

### Feature Requests
For new features, please:
- Describe the use case
- Explain why it would be valuable
- Consider implementation complexity
- Check if it aligns with project goals

### Code Contributions
We welcome:
- Bug fixes
- New file format support
- Performance improvements
- Documentation improvements
- New language support
- Enhanced chunking strategies

## 🌐 Language Support

This project is Chinese-first with English support:
- All new features should support both languages
- Error messages should be bilingual
- Documentation should be available in both languages
- Test cases should cover both language scenarios

## 📝 Pull Request Process

1. **Before submitting:**
   - Ensure your code follows the style guidelines
   - Add or update tests as needed
   - Update documentation if necessary
   - Test both Chinese and English functionality

2. **Pull Request requirements:**
   - Clear title and description
   - Link to related issues
   - List of changes made
   - Screenshots if UI changes
   - Test results

3. **Review process:**
   - Maintainers will review your PR
   - Address any feedback
   - Ensure CI passes
   - Squash commits if requested

## 🏗️ Architecture Guidelines

### Core Principles
- **Modularity**: Keep components loosely coupled
- **Extensibility**: Design for easy feature additions
- **Performance**: Consider memory and processing efficiency
- **Security**: Follow security best practices
- **Reliability**: Prefer explicit error handling

### Key Components
- **Agent**: Core AI processing logic
- **File Parser**: Document processing and text extraction
- **Chunking**: Advanced text segmentation strategies
- **Storage**: User session and document management
- **API**: FastAPI web service layer
- **Language Utils**: Bilingual support utilities

## 🔍 Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] Changes are well-tested
- [ ] Documentation is updated
- [ ] Bilingual support is maintained
- [ ] Performance impact is considered
- [ ] Security implications are addressed
- [ ] Error handling is appropriate

## 🐛 Debugging

### Common Issues
- **Import errors**: Check virtual environment activation
- **File processing**: Verify Tesseract installation
- **Memory issues**: Monitor chunk sizes and caching
- **Language detection**: Test with various input types

### Debugging Tools
- Use Python debugger (pdb) for step-through debugging
- Check logs for detailed error information
- Test with sample documents in both languages
- Use curl for API testing

## 📚 Documentation

### What to Document
- New API endpoints
- Configuration options
- Usage examples
- Breaking changes
- Migration guides

### Documentation Style
- Clear and concise
- Include code examples
- Provide both English and Chinese versions
- Use consistent formatting

## 🎯 Best Practices

### Code Quality
- Write self-documenting code
- Use meaningful variable names
- Keep functions small and focused
- Handle edge cases gracefully
- Log important operations

### Performance
- Profile code for bottlenecks
- Use appropriate data structures
- Consider memory usage
- Optimize for common use cases
- Cache expensive operations

### Security
- Validate all inputs
- Sanitize file uploads
- Use secure defaults
- Follow principle of least privilege
- Document security considerations

## 🤝 Community

### Communication
- Be respectful and inclusive
- Ask questions if unclear
- Help others when possible
- Share knowledge and experiences

### Recognition
Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

## 📞 Getting Help

If you need help:
- Check existing documentation
- Search existing issues
- Ask in discussions
- Contact maintainers

Thank you for contributing to Enterprise Agentic Services! 🚀
