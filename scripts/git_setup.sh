#!/bin/bash
# scripts/git_setup.sh
# usage: ./git_setup.sh <email> <name> <remote_url>

EMAIL=$1
NAME=$2
REMOTE_URL=$3

if [ -z "$EMAIL" ] || [ -z "$NAME" ] || [ -z "$REMOTE_URL" ]; then
  echo "Usage: $0 <email> <name> <remote_url>"
  exit 1
fi

git config user.email "$EMAIL"
git config user.name "$NAME"
git remote remove origin 2>/dev/null
git remote add origin "$REMOTE_URL"
git branch -M main

echo "Local git identity and remote 'origin' configured successfully."
