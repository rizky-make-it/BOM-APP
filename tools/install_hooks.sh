#!/bin/sh
# Install the post-commit hook (push to GitHub + log into the Obsidian vault). Run once per clone.
ROOT="$(git rev-parse --show-toplevel)"
cat > "$ROOT/.git/hooks/post-commit" <<'EOF'
#!/bin/sh
python "$(git rev-parse --show-toplevel)/tools/post_commit_sync.py"
exit 0
EOF
chmod +x "$ROOT/.git/hooks/post-commit"
echo "post-commit hook installed"
