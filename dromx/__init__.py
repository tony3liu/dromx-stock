import contextlib
import warnings

# Load .env files at package import so DEFAULT_CONFIG's env-var overlay
# (and every llm_clients consumer) sees the user's keys regardless of
# which entry point started the process. find_dotenv(usecwd=True) walks
# from the CWD, so the installed `dromx` console script picks up
# the project's .env instead of stepping up from site-packages.
# load_dotenv defaults to override=False, so it never clobbers values
# the caller has already exported.
try:
    import os

    from dotenv import find_dotenv, load_dotenv

    # Primary: walk up from the CWD so the installed console script picks up
    # the .env of whatever project directory the user launched from.
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(find_dotenv(".env.enterprise", usecwd=True), override=False)

    # Fallback: if the process was started from an unrelated directory (e.g.
    # the user's home), find_dotenv(usecwd=True) returns "" and nothing loads,
    # which silently drops the provider config and fails back to the OpenAI
    # default. Anchor to the .env that ships alongside this package so the
    # project's own config is honoured regardless of CWD. override=False keeps
    # any value the caller already exported (or a CWD .env) authoritative.
    _pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_pkg_root, ".env"), override=False)
    load_dotenv(os.path.join(_pkg_root, ".env.enterprise"), override=False)
except ImportError:
    pass

# langchain-core 1.3.3 calls surface_langchain_deprecation_warnings() in
# its own __init__, which prepends default-action filters for its
# subclassed warning categories. To suppress a specific warning we must
# install our filter AFTER langchain-core has installed its own, so import
# it first. The package is a guaranteed transitive dep via langgraph.
with contextlib.suppress(ImportError):
    import langchain_core  # noqa: F401

# langgraph-checkpoint 4.0.3 calls Reviver() at module load without an
# explicit allowed_objects, which triggers a noisy pending-deprecation
# warning from langchain-core 1.3.3 on every interpreter start. The fix
# is already merged upstream (langchain-ai/langgraph#7743, 2026-05-08)
# and will arrive in the next langgraph-checkpoint release. Remove this
# block (and the langchain_core preload above) when we bump past it.
warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects`.*",
    category=PendingDeprecationWarning,
)
