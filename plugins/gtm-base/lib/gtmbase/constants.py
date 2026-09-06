"""Fixed values every GTM Base script shares.

Every path here is relative to the base root (the company-base folder). Nothing
in this module reads the filesystem, imports a third-party package, or uses any
syntax newer than Python 3.9, because the hooks run on the system interpreter.
"""

# --- Folder and file paths, relative to the base root ------------------------

# Everything the AI reads for meaning lives under this folder.
CONTEXT_DIR = "context"
# The map: where everything lives, plus the two settings the plugin reads.
MAP_PATH = "context/map.md"
# One dated entry per decision the team made.
DECISIONS_DIR = "work/decisions"
# One append-only file per context file, holding the owner's yes lines.
CONFIRMATIONS_DIR = "work/confirmations"
# Dropped transcripts and notes waiting to be read. Not shared with the team.
INBOX_DIR = "work/inbox"
# Staged proposals. Not shared with the team.
PROPOSALS_DIR = "work/proposals"
# A staged proposal that has not been opened for review yet.
PROPOSALS_PENDING_DIR = "work/proposals/pending"
# A staged proposal whose review is open, kept so it can be reopened.
PROPOSALS_OPENED_DIR = "work/proposals/opened"
# What each run found wrong and which rule changed as a result.
CORRECTIONS_DIR = "corrections"
# Exact literals the outgoing-content scan is allowed to let through.
ALLOWLIST_PATH = "gate-allowlist.txt"
# Which files need the owner's review before a change to them is accepted.
CODEOWNERS_PATH = "CODEOWNERS"
# The two-key settings file that installs and pins the plugin for the team.
SETTINGS_PATH = ".claude/settings.json"

# Folders whose contents belong to one seat only and are never shared.
TRANSIENT_DIRS = (INBOX_DIR, PROPOSALS_DIR)

# Every folder the company-base template must contain.
TEMPLATE_TREE_DIRS = (
    "context",
    "context/strategy",
    "context/metrics",
    "context/plan",
    "context/notes",
    "work/decisions",
    "work/confirmations",
    "work/inbox",
    "work/proposals",
    "corrections",
    ".claude",
)

# --- The seat directory (per person, per machine, never shared) --------------

# Overrides the seat directory location. Tests set it to a temporary folder.
SEAT_HOME_ENV = "GTM_BASE_HOME"
# Where per-seat state lives when the override is not set.
SEAT_HOME_DEFAULT = "~/.gtm-base"
# Account state: the offer answer and the list of bases this account joined.
MACHINE_STATE_FILE = "machine.json"
# The sentinel file that says a capture run is armed right now.
ARMED_SENTINEL = "armed"

# --- Size caps ---------------------------------------------------------------

# Most text one hook may add to a session. The client's own cap is 10,000.
MAX_INJECTION_CHARS = 8000
# Most of the map that is ever injected into a session.
MAX_MAP_CHARS = 4000
# Largest outgoing change the gate will scan. Anything larger is refused.
MAX_DIFF_BYTES = 2000000
# Longest redacted excerpt a proposal may carry.
MAX_EXCERPT_CHARS = 1200
# Longest verbatim span a proposal may cite from an inbox item.
MAX_RAW_SPAN_CHARS = 2000

# --- Time windows ------------------------------------------------------------

# How long an armed capture run stays armed without being refreshed.
CAPTURE_MARKER_EXPIRY_SECONDS = 20 * 60
# How long a confirmation question id stays usable after it is issued.
QUESTION_ID_WINDOW_SECONDS = 60 * 60
# How long the session-start work may take before the client gives up on it.
SESSION_START_TIMEOUT_SECONDS = 15
# How long the analysis path guard may take before the client gives up on it.
PATH_GUARD_TIMEOUT_SECONDS = 5

# --- Settings the map may carry, and their allowed range --------------------

# Smallest value either map setting may hold.
MAP_SETTING_MIN = 1
# Largest value either map setting may hold.
MAP_SETTING_MAX = 365
# Days a context file may go unconfirmed before it is treated as out of date.
DEFAULT_CONFIRMATION_THRESHOLD_DAYS = 30
# Days a declined question waits before it is asked again.
DEFAULT_NOT_NOW_DAYS = 7

# --- The outgoing-content allowlist -----------------------------------------

# Most entries the allowlist may hold.
ALLOWLIST_MAX_LINES = 200
# Longest single allowlist entry.
ALLOWLIST_MAX_LINE_LENGTH = 200

# --- What an automatic update from the team is never allowed to carry -------

# Folders whose incoming changes are refused and left for a person to review.
PULL_REFUSED_PATH_PREFIXES = (".claude/", ".codex/", ".agents/")
# Filenames whose incoming changes are refused and left for a person to review.
PULL_REFUSED_FILENAMES = ("CLAUDE.md", "AGENTS.md", ".gitattributes", ".gitmodules")
# File types whose incoming changes are refused, because they are code.
PULL_REFUSED_SUFFIXES = (".sh", ".py", ".js")

# --- What a folder may never contain before it is trusted as a base ---------

# Refused anywhere in the tree, not only at the root, before a folder is trusted.
TRUST_REFUSED_TREE_NAMES = (
    "CLAUDE.md",
    "AGENTS.md",
    ".codex",
    ".agents",
    ".mcp.json",
    ".gitmodules",
    ".gitattributes",
    "plugins",
)
# Code files are refused anywhere in the tree as well.
TRUST_REFUSED_SUFFIXES = PULL_REFUSED_SUFFIXES
# Under the .claude folder this is the only name the trust check allows.
TRUST_ALLOWED_CLAUDE_ENTRY = "settings.json"

# --- How the plugin is installed and pinned for a team ----------------------

# The public repository that holds this marketplace.
MARKETPLACE_REPO = "brandon-sellers13/gtm-base"
# The marketplace name a base's settings file names.
MARKETPLACE_NAME = "gtm-base"
# The plugin key a base's settings file enables, as plugin@marketplace.
PLUGIN_KEY = "gtm-base@gtm-base"
# The release step replaces this with a real 40-character commit hash.
PINNED_SHA_PLACEHOLDER = "0" * 40

# --- Vocabularies ------------------------------------------------------------

# The reasons a confirmation line may record.
CONFIRMATION_TRIGGERS = ("threshold", "ledger", "drafted")
# Words that must never appear in a document written for a marketer to read.
BANNED_GIT_WORDS = ("commit", "branch", "pull request", "merge", "rebase", "clone")

# --- Placeholders the creation step replaces --------------------------------

# The template's owner address. Base creation replaces it with a real one.
OWNER_PLACEHOLDER_EMAIL = "owner@example.com"

# --- Vocabularies the file formats accept (added by Unit 2) -----------------

# Where a ledger entry came from.
LEDGER_ORIGINS = ("inbox", "ledger", "local-edit", "reject-keep", "join", "manual")
# Where a ledger entry stands.
LEDGER_STATUSES = ("open", "done", "dismissed")
# The kinds of file the corrections folder holds.
CORRECTION_KINDS = ("correction", "onboarding-note")
# How the material behind a proposal reached the base.
INTAKE_PATHS = ("connected", "drop", "ledger", "local-edit", "join", "none")
# How a source was read: as a sales call, as a decision, or not read at all.
ANALYSIS_MODES = ("sales-call", "decision", "none")
# What a correction was about.
CORRECTION_CLASSES = (
    "wrong-number",
    "wrong-definition",
    "stale-source",
    "wrong-tone",
    "new-decision",
    "other",
)
# How sure a proposal is of itself.
CONFIDENCE_LEVELS = ("low", "medium", "high")
# What one proposed edit does to a section.
EDIT_OPERATIONS = ("add", "replace")
# How widely the conversation behind an inbox item was already shared.
INBOX_VISIBILITIES = ("public-channel", "private-channel", "direct-message")
# How an inbox item reached the inbox.
INBOX_INTAKE_PATHS = ("connected", "drop")
# What an inbox item's row in the index says about it.
INBOX_STATUSES = ("landing", "landed", "processed", "processed-elsewhere", "closed")
# Which client a seat is running.
CLIENTS = ("claude", "codex")
# What a person answered when offered a base.
OFFER_ANSWERS = ("unset", "not-now", "set-up", "join")
# What a confirmation question was answered with.
ASKED_OUTCOMES = ("yes", "no", "not-now", "unanswered")

# --- More size caps ----------------------------------------------------------

# Largest pending file the choke point will read from the analysis step.
MAX_PENDING_ITEM_BYTES = 400000
# Largest proposal staging file, inbox item, or corrections file we will read.
MAX_ARTIFACT_BYTES = 1000000
# Most days an issued question id is kept before it is thrown away.
QUESTION_ID_KEEP_DAYS = 7
# How long a lock on the account state file may be held before it is stale.
LOCK_STALE_SECONDS = 30
# How long a writer waits for the account state lock before giving up.
LOCK_WAIT_SECONDS = 5.0

# --- The sources-read marker (added by Unit 4) -------------------------------

# The file that says this session already read the person's own documents.
SOURCES_READ_MARKER_FILE = "sources-read.json"
# How long a sources-read marker keeps the terminal safeguard refusing, in
# seconds. The installed git hook cannot see a session id, so it goes by age.
SOURCES_READ_GIT_HOOK_WINDOW_SECONDS = 12 * 3600

# --- The GitHub commands the gate knows about (added by Unit 4) -------------

# GitHub commands that write something a person would read, so their whole
# command line and any file they name is read before they are allowed to run.
GH_GATED_WRITES = (
    ("pr", "create"),
    ("pr", "edit"),
    ("pr", "comment"),
    ("pr", "review"),
    ("issue", "create"),
    ("issue", "comment"),
    ("release", "create"),
)
# GitHub commands no GTM Base skill ever uses. They are refused outright,
# because one of them would change who can see the base without sending
# anything the scan could read.
GH_DENIED_OUTRIGHT = (
    ("repo", "edit"),
    ("repo", "delete"),
    ("repo", "archive"),
    ("repo", "rename"),
    ("repo", "fork"),
    ("repo", "sync"),
    ("secret", "set"),
    ("variable", "set"),
    ("gist", "create"),
    ("ssh-key", "add"),
    ("gpg-key", "add"),
    ("auth", "token"),
    ("auth", "refresh"),
    ("auth", "setup-git"),
    ("codespace",),
    ("workflow", "run"),
)

# --- The session-start hook (added by Unit 3) -------------------------------

# The context files a base is expected to hold before it counts as set up.
REQUIRED_CONTEXT_FILES = (
    "context/strategy/icp.md",
    "context/strategy/positioning.md",
)
# The one sentence that starts setup again, printed wherever setup can resume.
RESTART_SENTENCE = 'Say "set up my company base" whenever you are ready.'
# How long the update from the shared copy may take before it is given up on.
FETCH_TIMEOUT_SECONDS = 10
# Longest piece of a remote address that is ever shown to a person.
MAX_ORIGIN_CHARS = 120
# Most entries the trust check will walk before it refuses the folder outright.
TRUST_WALK_CAP = 20000

# --- Proposals and confirmations (added by Unit 7) --------------------------

# The name every line of work carrying one proposal starts with.
PROPOSAL_BRANCH_PREFIX = "proposal/"
# The name the line of work carrying one seat's confirmations starts with.
CONFIRMATIONS_BRANCH_PREFIX = "confirmations/"
# Most text a hand edit may add before the local-edit path refuses it.
LOCAL_EDIT_MAX_CHARS = 4800
# The address saved work is recorded under when the base names none.
COMMIT_AUTHOR_FALLBACK_EMAIL = "gtm-base@localhost"
# The name saved work is recorded under when the base names none.
COMMIT_AUTHOR_FALLBACK_NAME = "GTM Base"
