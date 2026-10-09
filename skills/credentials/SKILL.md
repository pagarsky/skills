---
name: credentials
description: Obtain a secret (password, API token, sudo password, basic-auth) without the user pasting it into chat. Use whenever a task needs a credential that isn't already in the environment — auth prompts, private registries, sudo, signed URLs, anything where typing the secret into the conversation would leak it. macOS only.
---

# Credentials Skill

Goal: get a secret into the shell I run commands in, without it ever appearing in the chat transcript, my context, or shell history.

## Decision tree

Pick the first option that applies:

1. **Tool has a native credential helper** — use it instead of this skill.
   - git → `git credential-osxkeychain` (already default on macOS)
   - aws → `~/.aws/credentials` or `credential_process`
   - gcloud → `gcloud auth login` / ADC
   - gh → `gh auth login`
   - docker → `docker login` (uses Keychain via `docker-credential-osxkeychain`)
   - kubectl → context already in `~/.kube/config`
   These handle expiry/refresh that this skill won't.

2. **Credential is already in Keychain** — read it, don't re-prompt.
   ```bash
   security find-generic-password -a "$USER" -s "claude-code/<purpose>" -w
   ```
   If this returns a value, use it. If it errors with `SecKeychainSearchCopyNext`, fall through to (3).

3. **Need a new credential, will be reused** — prompt via osascript, store in Keychain.
   ```bash
   security add-generic-password -a "$USER" -s "claude-code/<purpose>" -U -w "$(
     osascript -e 'display dialog "<one-line reason>" default answer "" with hidden answer' \
               -e 'text returned of result'
   )"
   ```
   Then read it back with the command in (2) when needed.

4. **Genuinely one-shot, will never reuse** — single Bash call, no persistence.
   ```bash
   PW=$(osascript -e 'display dialog "..." default answer "" with hidden answer' \
                  -e 'text returned of result') \
     && curl -u "user:$PW" https://...
   ```

## sudo

```bash
cat > /tmp/claude-askpass.sh <<'EOF'
#!/bin/bash
security find-generic-password -a "$USER" -s "claude-code/sudo" -w 2>/dev/null \
  || osascript -e 'display dialog "sudo password" default answer "" with hidden answer' \
               -e 'text returned of result'
EOF
chmod +x /tmp/claude-askpass.sh
SUDO_ASKPASS=/tmp/claude-askpass.sh sudo -A <cmd>
```

For multi-call sudo in a session, stash it in Keychain first via (3) with `-s claude-code/sudo`.

## Naming convention

Keychain `-s` (service) values use `claude-code/<purpose>` so I can find what I stored without guessing. Examples:
- `claude-code/flywheel-basic-auth`
- `claude-code/github-pat`
- `claude-code/sudo`

Use `-a "$USER"` for the account field.

## Discipline

- Never echo `$PW` (or whatever variable holds the secret) — tool output comes back to me.
- Never `set -x` while the secret is in scope.
- Don't write secrets to files outside Keychain. `/tmp` is not safe.
- Don't log the `osascript` *result* — only consume it via `$(...)` or pipe directly into `security add-generic-password -w`.
- When `security add-generic-password` succeeds, no confirmation is needed; the command exits 0 silently.

## List / cleanup

```bash
# list all credentials this skill created
security dump-keychain | grep -A1 '"claude-code/'

# delete one
security delete-generic-password -a "$USER" -s "claude-code/<purpose>"
```
