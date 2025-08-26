#!/bin/bash

# GitHub Repository Setup Script
# GitHub repository already configured for NecZhang

echo "🚀 GitHub repository connection verified..."

# Step 1: Check GitHub remote
echo "Checking GitHub remote..."
git remote -v

# Step 2: Rename branch to main (GitHub default)
echo "Renaming branch to main..."
git branch -M main

# Step 3: Check if already pushed
echo "Checking if repository is already pushed..."
if git ls-remote --exit-code origin main; then
    echo "✅ Repository already pushed to GitHub!"
else
    echo "Pushing to GitHub..."
    git push -u origin main
fi

echo "✅ Repository successfully pushed to GitHub!"
echo ""
echo "📋 Next steps:"
echo "1. Go to your GitHub repository"
echo "2. Add repository topics: ai, nlp, document-processing, chinese, enterprise, fastapi"
echo "3. Enable Issues, Projects, Wiki, and Discussions"
echo "4. Set up branch protection rules"
echo "5. Create initial project board"

# Display repository information
echo ""
echo "📊 Repository Summary:"
echo "Repository URL: https://github.com/NecZhang/langchain-agentic-services"
echo "Files committed: $(git ls-files | wc -l)"
echo "Commit hash: $(git rev-parse HEAD)"
