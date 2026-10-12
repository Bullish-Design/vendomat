# NON-PRODUCTION spike fixture (project 20, spike S1).
# DOOR-014 recognizer: false-positive and false-negative check on realistic option names.
# usage: python -I secrets_check.py DEVENV_LEAF_NAMES_FILE
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import hand

SHOULD_FLAG = [
    "password", "hashedPassword", "initialPassword", "initialHashedPassword", "initialAdminPassword",
    "apiKey", "APIKey", "privateKey", "secretKey", "authKey", "signingKey", "adminToken", "client-token",
    "server-token", "rpcSecret", "secret", "clientSecret", "jwtSecret", "passphrase", "credentials",
    "token", "DB_PASSWORD", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "passwordHash", "initDatabasePassword",
    "wifi_psk_passphrase",
]
SHOULD_PASS = [
    "passwordFile", "hashedPasswordFile", "initialPasswordFile", "tokenFile", "secretKeyFile", "privateKeyFile",
    "apiKeyFile", "keyFile", "certFile", "sslCertificateKey", "initialScript", "PasswordAuthentication",
    "passwordAuthentication", "permitRootLogin", "secrets", "secretspec", "tokenizer", "passthru",
    "bypassPermissions", "apiKeyHelper", "authentication", "hostKeys", "keyboard", "monkey", "compass",
    "maxTokens", "tokens", "passwordMinLength", "passwordPolicy", "DB_PASSWORD_FILE", "TOKEN_FILE",
    "accessKey", "key", "keymap", "sshKey", "authorizedKeys", "publicKey", "hasRootAuth", "mode", "port",
    "name", "enable", "package", "exec", "text", "url", "client_id", "clientId", "tokenUrl", "secretName",
    "passwordEnv", "initialDatabases", "authMethod",
]
bad = 0
print("== should be flagged")
for k in SHOULD_FLAG:
    v = hand.is_secret_key(k)
    bad += not v
    print(f"  {'ok  ' if v else 'MISS'} {k}")
print("== should pass")
for k in SHOULD_PASS:
    v = hand.is_secret_key(k)
    bad += v
    print(f"  {'ok  ' if not v else 'FALSE POSITIVE'} {k}")
print("curated mismatches:", bad)

names = [l.strip() for l in open(sys.argv[1]) if l.strip()]
flagged = [n for n in names if hand.is_secret_key(n)]
naive = re.compile(r"pass|secret|token|key|cred|auth|priv", re.I)
naive_flagged = [n for n in names if naive.search(n)]
print(f"\ndevenv option leaf names scanned: {len(names)}")
print(f"word recognizer flags {len(flagged)}: {' '.join(flagged)}")
print(f"naive substring recognizer (pass|secret|token|key|cred|auth|priv) flags {len(naive_flagged)}: {' '.join(naive_flagged)}")
